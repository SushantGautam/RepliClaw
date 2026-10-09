#!/usr/bin/env python3
"""Small standard-library progress ledger for a local Copilot CLI fleet.

This is NOT a Copilot daemon, LLM call monitor or periodic hook scheduler.
Hooks observe lifecycle/tool events. Explicit worker beats measure task progress.
A separate `watch --loop` process detects missing task beats; only a live
orchestrator with write_agent can steer/reassign subagents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from datetime import datetime, timezone


def data_root() -> Path:
    root = os.environ.get("REPLICLAW_FLEET_DIR")
    if root:
        return Path(root).expanduser()
    return Path(__file__).resolve().parents[1] / ".artifacts" / "copilot-fleet"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def key(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:20]


def safe_id(s: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", s):
        raise ValueError("Task ID must be 1–80 alphanumeric/._- characters")
    return s


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump(payload, h, sort_keys=True, ensure_ascii=False)
            h.write("\n")
            h.flush()
            os.fsync(h.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def record_task(task: str, status: str, agent: str = "", progress: str = "", artifact: str = "", deadline_min: int = 0) -> dict:
    safe_id(task)
    path = data_root() / "tasks" / f"{task}.json"
    old = load(path)
    now = time.time()
    if not old and status != "assigned":
        raise ValueError(f"Unknown task {task}: coordinator must assign it first")
    if old and old.get("state") in {"done", "blocked"} and status not in {"assigned"}:
        raise ValueError(f"Task {task} is terminal; use a new task ID for rework")
    if status == "assigned":
        obj = {"task": task, "agent": agent, "state": "assigned", "created": now,
               "last_beat": now, "last_progress": now, "progress": progress or "assigned",
               "artifact": artifact, "deadline": now + max(0, deadline_min) * 60 if deadline_min else None,
               "updated_utc": utc()}
    else:
        obj = {**old, "state": status, "last_beat": now, "updated_utc": utc()}
        if progress:
            obj["progress"] = progress[:500]
            obj["last_progress"] = now
        if artifact:
            obj["artifact"] = artifact[:500]
    atomic_json(path, obj)
    return obj


def scan(heartbeat_seconds: int, progress_seconds: int) -> tuple[list[dict], bool]:
    now = time.time()
    result = []
    stale = False
    for p in sorted((data_root() / "tasks").glob("*.json")):
        d = load(p)
        state = d.get("state", "unknown")
        if state in {"done", "blocked"}:
            health = state.upper()
        elif now - d.get("last_beat", 0) > heartbeat_seconds:
            health, stale = "STALE_HEARTBEAT", True
        elif now - d.get("last_progress", 0) > progress_seconds:
            health, stale = "NO_MEASURABLE_PROGRESS", True
        elif d.get("deadline") and now > d["deadline"]:
            health, stale = "OVERDUE", True
        else:
            health = "ACTIVE"
        result.append({"task": d.get("task"), "agent": d.get("agent"), "state": state,
                       "health": health, "seconds_since_beat": round(now - d.get("last_beat", now)),
                       "seconds_since_progress": round(now - d.get("last_progress", now)),
                       "progress": d.get("progress", ""), "artifact": d.get("artifact", "")})
    return result, stale


def handle_hook(event: str) -> None:
    """Record only metadata, never original prompts, tool args, responses or keys.

    Copilot's postToolUse event has no subagent ID; session-level tool activity
    cannot be interpreted as proof that a particular worker is progressing.
    """
    try:
        inp = json.load(sys.stdin)
    except (ValueError, OSError):
        print("{}")
        return
    session = key(str(inp.get("sessionId", inp.get("session_id", "unknown"))))
    agent = str(inp.get("agentName", inp.get("agent_name", "")))[:100]
    snapshot = {"session_hash": session, "last_event": event, "updated_utc": utc(),
                "last_event_unix": time.time(), "tool": str(inp.get("toolName", ""))[:80]}
    root = data_root()
    atomic_json(root / "sessions" / f"{session}.json", snapshot)
    if event in {"subagentStart", "subagentStop"}:
        name = key(str(inp.get("agentId", agent)))
        atomic_json(root / "agents" / f"{session}-{name}.json",
                    {"session_hash": session, "agent_hash": name, "name": agent,
                     "state": "started" if event == "subagentStart" else "finished",
                     "updated_utc": utc()})
    if event == "subagentStart" and agent.startswith("rc-"):
        print(json.dumps({"additionalContext":
            "FOCUS RULE: own one assigned task; emit a measurable artifact quickly; call "
            "`python scripts/copilot_fleet_watch.py beat TASK --progress TEXT --artifact PATH` "
            "at checkpoints and at least every 2 minutes when making progress. "
            "End with STATUS:, ARTIFACT:, CHECK:, NEXT:. Do not expand scope."}))
        return
    if event == "subagentStop" and agent.startswith("rc-"):
        response = str(inp.get("response", inp.get("last_assistant_message", "")))
        if not all(k in response for k in ("STATUS:", "ARTIFACT:", "CHECK:")):
            # One forced repair, then allow and surface to coordinator.
            attempt_key = key(str(inp.get("agentId", "")) + response[:80])
            gate = root / "stop-retry" / f"{session}-{attempt_key}.json"
            if not gate.exists():
                atomic_json(gate, {"retried": True, "at": utc()})
                print(json.dumps({"decision": "block", "reason":
                    "Your final report is missing a required evidence field. "
                    "Return STATUS: DONE|BLOCKED; ARTIFACT: path/sha or none; "
                    "CHECK: exact test command/result; NEXT: shortest unblock. "
                    "Do not start new scope."}))
                return
    print("{}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    hook = sub.add_parser("hook")
    hook.add_argument("event", choices=["sessionStart", "sessionEnd", "subagentStart", "subagentStop",
                                       "preToolUse", "postToolUse", "postToolUseFailure", "agentStop", "errorOccurred"])
    for op in ("assign", "beat", "done", "block"):
        p = sub.add_parser(op)
        p.add_argument("task")
        p.add_argument("--agent", default="")
        p.add_argument("--progress", default="")
        p.add_argument("--artifact", default="")
        if op == "assign":
            p.add_argument("--deadline-min", type=int, default=30)
    stat = sub.add_parser("watch")
    stat.add_argument("--loop", action="store_true")
    stat.add_argument("--every", type=int, default=60)
    stat.add_argument("--heartbeat-seconds", type=int, default=240)
    stat.add_argument("--progress-seconds", type=int, default=480)
    stat.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.command == "hook":
        handle_hook(args.event)
        return 0
    if args.command in {"assign", "beat", "done", "block"}:
        state = {"assign": "assigned", "beat": "working", "done": "done", "block": "blocked"}[args.command]
        result = record_task(args.task, state, args.agent, args.progress, args.artifact,
                             getattr(args, "deadline_min", 0))
        print(json.dumps({k: result[k] for k in ("task", "state", "updated_utc", "progress", "artifact")}))
        return 0
    if args.command == "watch":
        while True:
            results, stale = scan(args.heartbeat_seconds, args.progress_seconds)
            if args.json:
                print(json.dumps({"at": utc(), "tasks": results, "attention": stale}), flush=True)
            else:
                print(f"[{utc()}] {len(results)} tasks, attention={stale}", flush=True)
                for r in results:
                    print(f"  {r['health']:<24} {r['task']:<22} {r['agent']:<15} "
                          f"beat={r['seconds_since_beat']}s progress={r['progress'][:95]}", flush=True)
            if not args.loop:
                return int(stale)
            time.sleep(max(5, args.every))
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print(f"fleet-watch: {exc}", file=sys.stderr)
        sys.exit(2)
