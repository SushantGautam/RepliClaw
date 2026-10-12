"""Three-arm HiddenBench protocol: escrow, open-share, central.

The three arms share the official HiddenBench tasks, official prompt
templates, agent count, fact assignment (same seed), and round count. The
only difference is the information mechanic under study:

* ``open-share`` — the official HiddenBench protocol: agents see other
  agents' messages while reasoning, then final-vote by majority.
* ``escrow``     — RepliClaw-style: per-round evidence packets and a
  ranked-answer commitment are held in escrow (PhaseGate COMMIT), revealed
  only just before the final vote (REVEAL). Commitments are hashed with
  ``repliclaw.canonical`` so the pre-reveal state is content-free.
* ``central``    — one controller receives the pooled information
  (shared + all hidden facts) directly and decides in a single vote.

Non-completions are recorded as failures, never dropped.
"""
from __future__ import annotations

import random
import time
from collections import Counter
from typing import Any, Optional

from repliclaw.canonical import commit_hash
from repliclaw.escrow.phase import Phase, PhaseGate

from ._vendor import ensure_path
from .client import Usage

ensure_path()

from hiddenbench.benchmark import BenchmarkTask  # noqa: E402
from hiddenbench.prompts import PromptSet, load_prompts, render_prompt  # noqa: E402
from hiddenbench.simulator import format_facts, vote_json_schema  # noqa: E402

ESCROW_NOTE = (
    "(Escrow protocol: statements from other agents are held in escrow and are "
    "NOT visible before the reveal phase. Write your evidence packet now; it "
    "will be recorded and revealed only at the end.)"
)

RANKED_COMMIT_PROMPT = (
    "Escrow protocol — commitment phase. Based on your own information and your "
    "own evidence packets only, commit to a ranked answer.\n"
    "Possible answers: {answers}\n"
    "Return JSON: {{"
    ' "vote": your top-choice answer (exactly one of the possible answers), '
    '"ranking": all possible answers ordered from best to worst, '
    '"rationale": short reason'
    "}}."
)

REVEALED_EVIDENCE_HEADER = (
    "Escrow reveal — the following evidence packets were committed by each "
    "agent and are now revealed (rounds in order):\n"
)


class AgentState:
    """Per-agent LLM state (mirrors the official HiddenBench AgentState)."""

    def __init__(self, name: str, client: Any, system_prompt: str) -> None:
        self.name = name
        self.client = client
        self.history: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    def chat(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})
        response = self.client.chat(self.history)
        self.history.append({"role": "assistant", "content": str(response)})
        return str(response)

    def vote(self, message: str, possible_answers: list[str], retries: int = 3) -> dict[str, str]:
        schema = vote_json_schema(possible_answers)
        local_history = list(self.history)
        local_history.append({"role": "user", "content": message})
        vote = ""
        for attempt in range(retries):
            response = self.client.chat_json(local_history, schema)
            vote = str(response.get("vote", "")).strip()
            rationale = str(response.get("rationale", "")).strip()
            if vote in possible_answers and rationale:
                return {"vote": vote, "rationale": rationale}
            local_history.append({"role": "assistant", "content": str(response)})
            local_history.append(
                {
                    "role": "user",
                    "content": f"The vote must be exactly one of {possible_answers}. Return valid JSON again.",
                }
            )
        raise ValueError(f"agent {self.name}: invalid vote {vote!r}; expected one of {possible_answers}")

    def commit_ranked(self, possible_answers: list[str], retries: int = 3) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "vote": {"type": "string", "enum": possible_answers},
                "ranking": {
                    "type": "array",
                    "items": {"type": "string", "enum": possible_answers},
                    "minItems": len(possible_answers),
                    "maxItems": len(possible_answers),
                },
                "rationale": {"type": "string"},
            },
            "required": ["vote", "ranking", "rationale"],
            "additionalProperties": False,
        }
        message = render_prompt(
            RANKED_COMMIT_PROMPT, {"answers": ", ".join(possible_answers)}
        )
        local_history = list(self.history)
        local_history.append({"role": "user", "content": message})
        raw = ""
        for attempt in range(retries):
            response = self.client.chat_json(local_history, schema)
            raw = str(response)
            vote = str(response.get("vote", "")).strip()
            ranking = response.get("ranking")
            if (
                vote in possible_answers
                and isinstance(ranking, list)
                and sorted(ranking) == sorted(possible_answers)
                and str(response.get("rationale", "")).strip()
            ):
                return {"vote": vote, "ranking": list(ranking),
                        "rationale": str(response["rationale"]).strip()}
            local_history.append({"role": "assistant", "content": raw})
            local_history.append(
                {
                    "role": "user",
                    "content": (
                        "Your JSON was invalid. 'vote' must be exactly one of "
                        f"{possible_answers} and 'ranking' must list ALL of them, "
                        "best to worst. Return valid JSON again."
                    ),
                }
            )
        raise ValueError(f"agent {self.name}: invalid ranked commitment")


class EscrowBox:
    """Minimal RepliClaw-style escrow: commit in COMMIT, read after REVEAL."""

    def __init__(self) -> None:
        self._gate = PhaseGate()
        self._items: list[dict[str, Any]] = []

    def commit(self, agent_id: str, kind: str, round_: int, content: dict[str, Any]) -> str:
        self._gate.assert_can(agent_id, "commit")
        payload = {"agent_id": agent_id, "kind": kind, "round": round_, "content": content}
        sha = commit_hash(payload)
        # Pre-reveal state is content-free: only hashes are observable.
        self._items.append({"agent_id": agent_id, "kind": kind, "round": round_,
                            "commitment_sha256": sha, "content": content})
        return sha

    def pre_reveal_digest(self) -> list[dict[str, Any]]:
        return [
            {"agent_id": i["agent_id"], "kind": i["kind"], "round": i["round"],
             "commitment_sha256": i["commitment_sha256"]}
            for i in self._items
        ]

    def reveal(self) -> list[dict[str, Any]]:
        if self._gate.phase != Phase.REVEAL:
            self._gate.advance()
        self._gate.assert_can("orchestrator", "reveal")
        return self._items


def build_agents(
    task: BenchmarkTask,
    client: Any,
    prompts: PromptSet,
    seed: int,
) -> tuple[list[AgentState], list[dict[str, Any]]]:
    """Hidden-profile agent construction (identical to the official one)."""
    rng = random.Random(seed)
    hidden_info = list(task.hidden_information)
    rng.shuffle(hidden_info)
    num_agents = len(hidden_info)
    agents: list[AgentState] = []
    assignments: list[dict[str, Any]] = []
    for index in range(num_agents):
        facts = list(task.shared_information)
        facts.append(hidden_info[index])
        rng.shuffle(facts)
        system_prompt = render_prompt(
            prompts.system_prompt,
            {
                "description": task.description,
                "information": format_facts(facts),
                "extra": "",
            },
        )
        agents.append(AgentState(f"Person {index + 1}", client, system_prompt))
        assignments.append(
            {
                "agent": f"Person {index + 1}",
                "visible_facts": list(facts),
                "assigned_hidden_information": [hidden_info[index]],
            }
        )
    return agents, assignments


def _base_run_data(task: BenchmarkTask, client: Any, arm: str, seed: int, rounds: int,
                   profile: str) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "scenario": task.name,
        "arm": arm,
        "profile": profile,
        "model": client.model,
        "num_agents": None,
        "correct_answer": task.correct_answer,
        "possible_answers": list(task.possible_answers),
        "seed": seed,
        "rounds_planned": rounds,
        "initial_votes": [],
        "rounds": [],
        "final_votes": [],
        "group_decision": None,
        "completed": False,
        "failure": None,
    }


def _majority(votes: list[dict[str, str]]) -> Optional[str]:
    counts = Counter(v["vote"] for v in votes)
    return counts.most_common(1)[0][0] if counts else None


def run_open_share(
    task: BenchmarkTask, client: Any, prompts: PromptSet, seed: int, rounds: int
) -> dict[str, Any]:
    """Official HiddenBench hidden-profile discussion protocol."""
    agents, assignments = build_agents(task, client, prompts, seed)
    run = _base_run_data(task, client, "open-share", seed, rounds, "hidden")
    run["num_agents"] = len(agents)
    run["fact_assignments"] = assignments

    initial_prompt = render_prompt(
        prompts.first_vote_prompt,
        {
            "group_discussion": "No discussion has occurred yet. This is your initial vote "
            "based solely on the information available to you.",
            "possible_answers": ", ".join(task.possible_answers),
        },
    )
    for agent in agents:
        response = agent.vote(initial_prompt, task.possible_answers)
        run["initial_votes"].append({"agent": agent.name, **response})

    transcript: list[dict[str, Any]] = []
    for round_index in range(rounds):
        round_data: dict[str, Any] = {"round": round_index + 1, "messages": []}
        if round_index == 0:
            previous: list[str] = []
            for agent_index, agent in enumerate(agents):
                initial_vote = run["initial_votes"][agent_index]
                prefix = (
                    f"Your initial vote was: {initial_vote['vote']}\n"
                    f"Your initial rationale was: {initial_vote['rationale']}\n\n"
                )
                if not previous:
                    prompt = prefix + prompts.first_user_prompt
                else:
                    prompt = prefix + render_prompt(
                        prompts.user_prompt, {"messages": "\n".join(previous), "extra": ""}
                    )
                response = agent.chat(prompt)
                previous.append(f"{agent.name}: {response}")
                message = {"agent": agent.name, "prompt": prompt, "response": response}
                round_data["messages"].append(message)
                transcript.append({"round": round_index + 1, "agent": agent.name,
                                   "response": response})
        else:
            for current_index, agent in enumerate(agents):
                previous = []
                for offset in range(1, len(agents)):
                    other = agents[(current_index + offset) % len(agents)]
                    previous.append(f"{other.name}: {other.history[-1]['content']}")
                prompt = render_prompt(
                    prompts.user_prompt, {"messages": "\n".join(previous), "extra": ""}
                )
                response = agent.chat(prompt)
                round_data["messages"].append(
                    {"agent": agent.name, "prompt": prompt, "response": response}
                )
                transcript.append({"round": round_index + 1, "agent": agent.name,
                                   "response": response})
        if round_index == rounds - 1:
            group_discussion = "\n".join(
                f"{m['agent']}: {m['response']}" for m in round_data["messages"]
            )
            vote_prompt = render_prompt(
                prompts.vote_prompt,
                {"group_discussion": group_discussion,
                 "possible_answers": ", ".join(task.possible_answers)},
            )
            for agent in agents:
                response = agent.vote(vote_prompt, task.possible_answers)
                run["final_votes"].append({"agent": agent.name, **response})
        run["rounds"].append(round_data)

    run["group_decision"] = _majority(run["final_votes"])
    run["completed"] = True
    return run


def run_escrow(
    task: BenchmarkTask, client: Any, prompts: PromptSet, seed: int, rounds: int
) -> dict[str, Any]:
    """RepliClaw-style escrow: blind packets + commitment, reveal, final vote."""
    agents, assignments = build_agents(task, client, prompts, seed)
    run = _base_run_data(task, client, "escrow", seed, rounds, "hidden")
    run["num_agents"] = len(agents)
    run["fact_assignments"] = assignments
    escrow = EscrowBox()

    initial_prompt = render_prompt(
        prompts.first_vote_prompt,
        {
            "group_discussion": "No discussion has occurred yet. This is your initial vote "
            "based solely on the information available to you.",
            "possible_answers": ", ".join(task.possible_answers),
        },
    )
    for agent in agents:
        response = agent.vote(initial_prompt, task.possible_answers)
        escrow.commit(agent.name, "initial_vote", 0, response)
        run["initial_votes"].append({"agent": agent.name, **response})

    for round_index in range(rounds):
        round_data: dict[str, Any] = {"round": round_index + 1, "packets": []}
        for agent_index, agent in enumerate(agents):
            initial_vote = run["initial_votes"][agent_index]
            prefix = (
                f"Your initial vote was: {initial_vote['vote']}\n"
                f"Your initial rationale was: {initial_vote['rationale']}\n\n"
            ) if round_index == 0 else ""
            note = (
                ESCROW_NOTE
                if round_index == 0
                else ESCROW_NOTE + " Your earlier packets are in your private history."
            )
            template = prompts.first_user_prompt if round_index == 0 else prompts.user_prompt
            prompt = prefix + render_prompt(template, {"messages": note, "extra": ""})
            packet = agent.chat(prompt)
            escrow.commit(agent.name, "evidence_packet", round_index + 1,
                          {"agent": agent.name, "response": packet})
            round_data["packets"].append(
                {"agent": agent.name, "prompt": prompt, "committed": True}
            )
        run["rounds"].append(round_data)

    # Commitment: ranked answer from own packets only (still pre-reveal).
    commitments = []
    for agent in agents:
        commit = agent.commit_ranked(task.possible_answers)
        escrow.commit(agent.name, "ranked_commitment", rounds + 1, commit)
        commitments.append({"agent": agent.name, **commit})
    run["commitments"] = commitments
    run["pre_reveal_digest"] = escrow.pre_reveal_digest()

    # Reveal: only now do agents see everyone's packets and commitments.
    revealed = escrow.reveal()
    lines: list[str] = [REVEALED_EVIDENCE_HEADER]
    for item in revealed:
        content = item["content"]
        if item["kind"] == "initial_vote":
            lines.append(f"{item['agent_id']} [initial vote]: {content.get('vote')} "
                         f"— {content.get('rationale')}")
        elif item["kind"] == "evidence_packet":
            lines.append(f"{content.get('agent')} [evidence packet, round {item['round']}]: "
                         f"{content.get('response')}")
        elif item["kind"] == "ranked_commitment":
            lines.append(f"{item['agent_id']} [ranked commitment]: "
                         f"{content.get('ranking')} — {content.get('rationale')}")
    group_discussion = "\n".join(lines)
    vote_prompt = render_prompt(
        prompts.vote_prompt,
        {"group_discussion": group_discussion,
         "possible_answers": ", ".join(task.possible_answers)},
    )
    for agent in agents:
        response = agent.vote(vote_prompt, task.possible_answers)
        run["final_votes"].append({"agent": agent.name, **response})

    run["group_decision"] = _majority(run["final_votes"])
    run["completed"] = True
    return run


def run_central(
    task: BenchmarkTask, client: Any, prompts: PromptSet, seed: int, rounds: int
) -> dict[str, Any]:
    """Centralized controller with pooled information (C-EQ-style control)."""
    run = _base_run_data(task, client, "central", seed, rounds, "pooled-central")
    run["num_agents"] = 1

    rng = random.Random(seed)
    facts = list(task.shared_information) + list(task.hidden_information)
    rng.shuffle(facts)
    system_prompt = render_prompt(
        prompts.system_prompt,
        {
            "description": task.description,
            "information": format_facts(facts),
            "extra": "",
        },
    )
    agent = AgentState("Controller", client, system_prompt)
    initial_prompt = render_prompt(
        prompts.first_vote_prompt,
        {
            "group_discussion": "No discussion has occurred yet. This is your initial vote "
            "based solely on the information available to you.",
            "possible_answers": ", ".join(task.possible_answers),
        },
    )
    response = agent.vote(initial_prompt, task.possible_answers)
    run["initial_votes"] = [{"agent": "Controller", **response}]
    run["final_votes"] = [{"agent": "Controller", **response}]
    run["group_decision"] = response["vote"]
    run["completed"] = True
    return run


ARM_RUNNERS = {
    "escrow": run_escrow,
    "open-share": run_open_share,
    "central": run_central,
}


def scenario_seed(base_seed: Optional[int], task_index: int, duplication: int = 0) -> Optional[int]:
    """Same per-scenario seeding as the official HiddenBench harness."""
    if base_seed is None:
        return None
    return base_seed + task_index * 10_000 + duplication


def run_arm_task(
    arm: str,
    task: BenchmarkTask,
    task_index: int,
    client: Any,
    prompts: PromptSet,
    seed: Optional[int],
    rounds: int,
) -> dict[str, Any]:
    """Run one task under one arm; record failures, never drop them."""
    before = client.usage.to_dict()
    started = time.monotonic()
    run = _base_run_data(task, client, arm, scenario_seed(seed, task_index) or -1, rounds,
                         "hidden" if arm != "central" else "pooled-central")
    try:
        run = ARM_RUNNERS[arm](task, client, prompts, scenario_seed(seed, task_index) or -1, rounds)
    except Exception as exc:
        run["failure"] = f"{type(exc).__name__}: {exc}"
    after = client.usage.to_dict()
    run["usage_delta"] = {
        "calls": after["calls"] - before["calls"],
        "total_tokens": after["total_tokens"] - before["total_tokens"],
    }
    run["wall_s"] = round(time.monotonic() - started, 2)
    return run


def score_arm(runs: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in runs if r.get("completed")]
    failures = [r for r in runs if not r.get("completed")]
    correct_completed = [
        r for r in completed if r.get("group_decision") == r.get("correct_answer")
    ]
    individual = []
    for run in completed:
        votes = run.get("final_votes") or []
        if votes:
            individual.append(
                sum(1 for v in votes if v.get("vote") == run.get("correct_answer")) / len(votes)
            )
    return {
        "num_tasks": len(runs),
        "completed": len(completed),
        "failures": len(failures),
        "failure_reasons": [
            {"task_id": r.get("task_id"), "scenario": r.get("scenario"),
             "failure": r.get("failure")}
            for r in failures
        ],
        "group_decision_accuracy_completed": (
            len(correct_completed) / len(completed) if completed else 0.0
        ),
        "group_decision_accuracy_all_tasks": (
            len(correct_completed) / len(runs) if runs else 0.0
        ),
        "mean_individual_final_vote_accuracy": (
            sum(individual) / len(individual) if individual else 0.0
        ),
        "total_llm_calls": sum(int(r.get("usage_delta", {}).get("calls", 0)) for r in runs),
        "total_tokens": sum(int(r.get("usage_delta", {}).get("total_tokens", 0)) for r in runs),
        "total_wall_s": round(sum(float(r.get("wall_s", 0.0)) for r in runs), 2),
        "by_task": [
            {
                "task_id": r.get("task_id"),
                "scenario": r.get("scenario"),
                "completed": bool(r.get("completed")),
                "group_decision": r.get("group_decision"),
                "correct": r.get("group_decision") == r.get("correct_answer")
                and bool(r.get("completed")),
                "failure": r.get("failure"),
                "llm_calls": r.get("usage_delta", {}).get("calls", 0),
                "tokens": r.get("usage_delta", {}).get("total_tokens", 0),
                "wall_s": r.get("wall_s", 0.0),
            }
            for r in runs
        ],
    }


__all__ = [
    "ARM_RUNNERS",
    "AgentState",
    "EscrowBox",
    "Usage",
    "build_agents",
    "load_prompts",
    "run_arm_task",
    "score_arm",
    "scenario_seed",
]
