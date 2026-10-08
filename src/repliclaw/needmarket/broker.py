"""File-based atomic need broker (F04 §4, contract §4).

State lives in two append-only JSONL files under the broker root plus one
lock file per need:

- ``needs.jsonl`` — published needs (append-only).
- ``events.jsonl`` — broker events: need_published, need_claimed,
  need_released, need_expired, need_fulfilled, fulfilment_unverified
  (contract §2 kind names).
- ``locks/<need_id>.lock`` — claim file; the file *is* the lease (holder,
  deadline, generation, claim token). The lock NEVER exists empty or
  partial: every publish path is one atomic kernel op.
  * First-ever claim: the full lease payload is written to a per-process
    unique staging file, then a single ``os.link(staging, lock)`` —
    ``EEXIST`` makes every other process a definite loser (the old
    O_EXCL-create-then-write window let a racer see an empty lock and
    double-win; code judge B1).
  * Expired re-claim: exactly one process ``O_EXCL``-creates the
    generation-unique sidecar ``<need>.claim.gen<G+1>``, writes the new
    lease into it, and publishes it over the lock with ``os.replace``
    ONLY while the lock still holds the exact raw bytes observed when the
    lease was read as dead (byte-exact compare-and-swap); a lock that
    moved ahead is detected, the sidecar rolled back, and the attempt
    loses. Exactly one winner, one ``need_claimed`` event.

Rules (F04 design §4 + carry-overs):

- Claim requires a live, non-expired need: no live lock, not fulfilled,
  not cancelled. On an expired lock the winner rewrites with
  ``generation + 1``.
- Only ``verified=True`` fulfilment marks a need done (carry-over 8). An
  unverified fulfilment is an event (``fulfilment_unverified``), not a
  state change.
- The broker ENFORCES lease/dedup/budget only. It never ranks scientific
  options; ranking is per-agent (``policy.py``).
- Expiry is lazy-on-access: any broker read (``open_needs`` / ``claim`` /
  ``expire_due``) re-derives liveness from the clock and unlinks dead locks.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from repliclaw.canonical import canonical_json, sha256_hex
from repliclaw.needmarket.needs import Need

LOCK_STALE_S = 0.0  # a lock file older than its own deadline is dead


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_clock() -> float:
    return time.monotonic()


class BrokerError(RuntimeError):
    """Base broker error."""


class BudgetExhausted(BrokerError):
    """The agent's remaining budget cannot cover the need's cost estimate."""


@dataclass(frozen=True)
class Lease:
    """A live lease on a need (the lock file parsed)."""

    need_id: str
    holder_id: str
    claim_token: str
    acquired_at: float
    deadline: float
    generation: int


def _deterministic_claim_token(
    need_id: str, holder_id: str, generation: int
) -> str:
    """uuid4-shaped (``c-`` + 12 hex) but content-derived, so same-seed
    reruns produce identical broker event logs (P08 determinism). The token
    still uniquely identifies a lease *within* a run: a given (need, holder,
    generation) triple is claimed at most once, and cross-run uniqueness is
    not required for verification (verification uses need_id + generation).
    """
    return "c-" + sha256_hex(
        canonical_json({"need": need_id, "holder": holder_id, "gen": generation})
    )[:12]


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


class NeedBroker:
    """Append-only, O_EXCL-lease need broker (no central ranker).

    ``clock`` is injectable so ranking/lease tests can freeze time
    (F04 carry-over 5). All deadline math uses that clock.
    """

    def __init__(
        self,
        root: Path,
        lease_ttl_s: float = 120.0,
        clock: Callable[[], float] = _default_clock,
    ) -> None:
        self.root = Path(root)
        self.lease_ttl_s = float(lease_ttl_s)
        self._clock = clock
        self._needs_path = self.root / "needs.jsonl"
        self._events_path = self.root / "events.jsonl"
        self._locks_dir = self.root / "locks"
        self._locks_dir.mkdir(parents=True, exist_ok=True)

    # -- clock -------------------------------------------------------------
    @property
    def now(self) -> float:
        return self._clock()

    # -- events ------------------------------------------------------------
    def record(self, kind: str, **payload: Any) -> Dict[str, Any]:
        """Append a non-broker event (e.g. choice_ranked from a worker).

        Workers record their *choice* trail here; the broker still refuses
        to rank — it only stores what an agent chose and why.
        """
        return self._append_event(kind, **payload)

    def _append_event(self, kind: str, **payload: Any) -> Dict[str, Any]:
        event = {"ts": _now_iso(), "kind": kind, "payload": payload}
        _append_line(self._events_path, canonical_json(event))
        return event

    def events(self) -> List[Dict[str, Any]]:
        return _read_jsonl(self._events_path)

    def claim_history(self, need_id: str) -> List[Dict[str, Any]]:
        """Audit trail: every broker event touching ``need_id``."""
        return [e for e in self.events() if e["payload"].get("need_id") == need_id]

    # -- publish -------------------------------------------------------------
    def publish(self, need: Need) -> str:
        """Append a new need (append-only; duplicate need_id is an error)."""
        for existing in self.needs():
            if existing.need_id == need.need_id:
                raise BrokerError(f"need {need.need_id} already published")
        _append_line(self._needs_path, canonical_json(need.to_dict()))
        self._append_event(
            "need_published",
            need_id=need.need_id,
            proposer_id=need.proposer_id,
            required_capability=need.required_capability,
        )
        return need.need_id

    def needs(self) -> List[Need]:
        return [Need.model_validate(r) for r in _read_jsonl(self._needs_path)]

    def _need(self, need_id: str) -> Need:
        for n in self.needs():
            if n.need_id == need_id:
                return n
        raise BrokerError(f"unknown need {need_id}")

    # -- locks (the lease files) ---------------------------------------------
    def _lock_path(self, need_id: str) -> Path:
        return self._locks_dir / f"{need_id}.lock"

    def _read_lock(self, need_id: str) -> Optional[Lease]:
        p = self._lock_path(need_id)
        if not p.exists():
            return None
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None  # partial write from a killed process; treat as stale
        return Lease(
            need_id=need_id,
            holder_id=raw["holder_id"],
            claim_token=raw["claim_token"],
            acquired_at=raw["acquired_at"],
            deadline=raw["deadline"],
            generation=raw["generation"],
        )

    def _write_lock(self, lease: Lease) -> None:
        p = self._lock_path(lease.need_id)
        raw = {
            "need_id": lease.need_id,
            "holder_id": lease.holder_id,
            "claim_token": lease.claim_token,
            "acquired_at": lease.acquired_at,
            "deadline": lease.deadline,
            "generation": lease.generation,
        }
        tmp = p.with_suffix(".tmp")
        tmp.write_text(canonical_json(raw), encoding="utf-8")
        os.replace(tmp, p)  # atomic swap (POSIX rename)

    def _is_live(self, lease: Lease) -> bool:
        return lease.deadline > self.now

    def _is_fulfilled(self, need_id: str) -> bool:
        return any(
            e["kind"] == "need_fulfilled"
            for e in self.events()
            if e["payload"].get("need_id") == need_id
        )

    def _is_cancelled(self, need_id: str) -> bool:
        return any(
            e["kind"] == "need_released"
            and e["payload"].get("reason") == "cancelled"
            for e in self.events()
            if e["payload"].get("need_id") == need_id
        )

    def expire_due(self) -> List[str]:
        """Lazy expiry pass: unlink dead locks, emit need_expired.

        Chosen over a background reaper: every read already re-derives
        liveness, so a reaper thread would be unsound without a lock on
        every access. Returns the need_ids that expired.
        """
        expired: List[str] = []
        for p in self._locks_dir.glob("*.lock"):
            need_id = p.name[: -len(".lock")]
            lease = self._read_lock(need_id)
            if lease is None or self._is_live(lease):
                continue
            # Idempotent: one need_expired event per (need, generation).
            already = any(
                e["kind"] == "need_expired"
                and e["payload"].get("need_id") == need_id
                and e["payload"].get("generation") == lease.generation
                for e in self.events()
            )
            if not already:
                self._append_event(
                    "need_expired",
                    need_id=need_id,
                    holder_id=lease.holder_id,
                    generation=lease.generation,
                )
                expired.append(need_id)
            # Deliberately do NOT unlink here: the dead lock file is a
            # generation tombstone that claim() reads to derive
            # generation+1 and uses as the byte-exact CAS baseline in
            # _acquire_expired — unlinking here would let a re-claim
            # start fresh at generation 1 (or race the re-claim's own
            # observation read).
        return expired

    # -- open needs ------------------------------------------------------------
    def open_needs(self, exclude_agent: str) -> List[Need]:
        """Needs claimable by another agent (carry-over 1).

        EXCLUDES: needs with a live lease, fulfilled needs, cancelled
        needs, and needs proposed by ``exclude_agent`` (an agent does not
        claim its own need — self-fulfilment of your own need is not
        decentralized work).
        """
        self.expire_due()
        out: List[Need] = []
        for n in self.needs():
            if n.proposer_id == exclude_agent:
                continue
            lease = self._read_lock(n.need_id)
            if lease is not None and self._is_live(lease):
                continue  # leased (live)
            if self._is_fulfilled(n.need_id) or self._is_cancelled(n.need_id):
                continue  # done / expired-cancelled
            out.append(n)
        return out

    # -- budget ------------------------------------------------------------------
    def _spend_tokens(self, agent_id: str) -> int:
        """Tokens committed by fulfilled, verified work claimed by agent."""
        total = 0
        for e in self.events():
            if e["kind"] == "need_fulfilled" and e["payload"].get("holder_id") == agent_id:
                need = self._need(e["payload"]["need_id"])
                total += int(need.cost_estimate.tokens or 0)
        return total

    # -- claim ---------------------------------------------------------------------
    def claim(
        self,
        need_id: str,
        agent_id: str,
        agent_budget_tokens: Optional[int] = None,
    ) -> Optional[Lease]:
        """Atomically claim a need. Losers get ``None``.

        Winner is decided by ONE kernel call: a fresh claim is a single
        ``os.link`` of the fully staged lease onto the lock path; an
        expired re-claim is a single ``O_EXCL`` on the generation sidecar
        followed by a byte-exact compare-and-swap (see ``_acquire_expired``).
        On an expired lock the winner rewrites with ``generation + 1``.
        Budget enforcement (no ranking): if the agent declared a token
        budget and the need's cost would exceed remaining tokens, the
        claim is refused with :class:`BudgetExhausted`.
        """
        self.expire_due()
        need = self._need(need_id)

        if agent_budget_tokens is not None and need.cost_estimate.tokens is not None:
            remaining = agent_budget_tokens - self._spend_tokens(agent_id)
            if need.cost_estimate.tokens > remaining:
                raise BudgetExhausted(
                    f"{agent_id}: need {need_id} costs {need.cost_estimate.tokens} "
                    f"tokens; remaining budget {remaining}"
                )

        lock = self._lock_path(need_id)
        try:
            # Raw bytes are the CAS baseline for expired re-claims — the
            # canonical re-serialization is NOT guaranteed to round-trip
            # to the on-disk form.
            observed_lock: Optional[str] = lock.read_text(encoding="utf-8")
        except (OSError, FileNotFoundError):
            observed_lock = None
        if observed_lock is not None:
            existing = self._read_lock(need_id)
            if existing is not None and self._is_live(existing):
                return None  # live lease held by someone
            lease = self._acquire_expired(
                need_id, agent_id, existing, lock, observed_lock
            )
        else:
            lease = self._claim_fresh(need_id, agent_id, lock)
        if lease is None:
            return None
        self._append_event(
            "need_claimed",
            need_id=need_id,
            holder_id=agent_id,
            claim_token=lease.claim_token,
            generation=lease.generation,
        )
        return lease

    def _lock_payload(self, lease: Lease) -> str:
        return canonical_json(
            {
                "need_id": lease.need_id,
                "holder_id": lease.holder_id,
                "claim_token": lease.claim_token,
                "acquired_at": lease.acquired_at,
                "deadline": lease.deadline,
                "generation": lease.generation,
            }
        )

    def _claim_fresh(
        self, need_id: str, agent_id: str, lock: Path
    ) -> Optional[Lease]:
        """First-ever claim: single atomic ``os.link`` of the staged, fully
        written lease onto the lock path. The lock never exists empty or
        partial — a reader sees either the complete previous payload or the
        complete new one (the old ``O_EXCL``-create-then-write window let a
        racer read an empty lock as 'stale' and double-win; code judge B1).
        ``link()`` fails with ``EEXIST`` for every loser."""
        lease = Lease(
            need_id=need_id,
            holder_id=agent_id,
            claim_token=_deterministic_claim_token(need_id, agent_id, 1),
            acquired_at=self.now,
            deadline=self.now + self.lease_ttl_s,
            generation=1,
        )
        staged = self._locks_dir / f"{need_id}.stage.{os.getpid()}.{uuid.uuid4().hex[:8]}"
        staged.write_text(self._lock_payload(lease), encoding="utf-8")
        try:
            os.link(staged, lock)
        except FileExistsError:
            staged.unlink(missing_ok=True)
            return None  # a lock appeared while we staged; loser
        staged.unlink(missing_ok=True)
        return lease

    def _acquire_expired(
        self,
        need_id: str,
        agent_id: str,
        existing: Optional[Lease],
        lock: Path,
        observed_lock: str,
    ) -> Optional[Lease]:
        """Claim an expired tombstone; winner decided by ONE kernel call.

        The old ``unlink()`` + ``O_EXCL`` pair is two syscalls with a race
        window between them (two processes could both win — code judge B1
        reproduced 7 misfires under 6-process stress). Here exactly one
        process can ``O_EXCL``-create the generation-unique sidecar
        ``<need>.claim.gen<G+1>``; losers get ``FileExistsError`` and
        return ``None`` untouched.

        The winner then compare-and-swaps: it publishes its sidecar over
        the lock ONLY while the lock still holds the exact bytes observed
        when this call decided the lease was dead, and re-reads the lock
        to confirm the swap stuck. Any interleaving in which the lock
        moved ahead (fresh live lease, competing re-claim, a swap that
        clobbered ours) is detected and rolled back — the sidecar is
        consumed by the winner, so no later process can double-win the
        same generation.
        """
        gen = existing.generation + 1 if existing is not None else 2
        lease = Lease(
            need_id=need_id,
            holder_id=agent_id,
            claim_token=_deterministic_claim_token(need_id, agent_id, gen),
            acquired_at=self.now,
            deadline=self.now + self.lease_ttl_s,
            generation=gen,
        )
        sidecar = self._locks_dir / f"{need_id}.claim.gen{gen}"
        try:
            fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return None  # another process already took this generation
        os.close(fd)
        payload = self._lock_payload(lease)
        try:
            sidecar.write_text(payload, encoding="utf-8")
            try:
                current = lock.read_text(encoding="utf-8")
            except (OSError, FileNotFoundError):
                current = None
            if current != observed_lock:
                sidecar.unlink(missing_ok=True)
                return None  # lock moved ahead of our observation; we lose
            os.replace(sidecar, lock)
            # Two swaps can race into the same target; if the lock no
            # longer holds our bytes, the other publisher won.
            if lock.read_text(encoding="utf-8") != payload:
                return None
        except OSError:
            sidecar.unlink(missing_ok=True)
            return None
        return lease

    # -- lease lifecycle ----------------------------------------------------------
    def renew(self, lease: Lease) -> bool:
        """Extend a live lease the holder still owns (no v1 event kind for
        renewal, so this is a pure lease-file update — the deadline bump is
        observable in the lock file)."""
        current = self._read_lock(lease.need_id)
        if (
            current is None
            or current.claim_token != lease.claim_token
            or not self._is_live(current)
        ):
            return False
        extended = Lease(
            need_id=lease.need_id,
            holder_id=lease.holder_id,
            claim_token=lease.claim_token,
            acquired_at=current.acquired_at,
            deadline=self.now + self.lease_ttl_s,
            generation=current.generation,
        )
        self._write_lock(extended)
        return True

    def release(self, lease: Lease, reason: str) -> None:
        """Release a live lease (reason: failed | abandoned | cancelled)."""
        current = self._read_lock(lease.need_id)
        if current is None or current.claim_token != lease.claim_token:
            return
        self._lock_path(lease.need_id).unlink(missing_ok=True)
        self._append_event(
            "need_released",
            need_id=lease.need_id,
            holder_id=lease.holder_id,
            reason=reason,
        )

    # -- fulfilment -----------------------------------------------------------------
    def fulfill(
        self,
        need_id: str,
        artifact_id: str,
        lease: Lease,
        verified: bool,
    ) -> bool:
        """Record a fulfilment. Only ``verified=True`` marks the need done.

        Carry-over 8: an unverified fulfilment is an event
        (``fulfilment_unverified``), NOT a state change — the lease is
        released so the need can be claimed again, and no ``done`` marker
        is written. A verified fulfilment without a live, holder-matching
        lease is recorded as ``late_fulfilment`` (F04 §4.5) and still marks
        done if verified.
        """
        current = self._read_lock(need_id)
        holder_ok = current is not None and current.claim_token == lease.claim_token
        live = holder_ok and current is not None and self._is_live(current)

        if not verified:
            self._append_event(
                "fulfilment_unverified",
                need_id=need_id,
                holder_id=lease.holder_id,
                artifact_id=artifact_id,
            )
            if live:
                self.release(lease, "failed")
            return False

        if self._is_fulfilled(need_id):
            # At-least-once work, effectively-once effects (F04 §4.3).
            self._append_event(
                "fulfilment_duplicate_suppressed",
                need_id=need_id,
                holder_id=lease.holder_id,
                artifact_id=artifact_id,
            )
            return False

        flag = "late_fulfilment" if (not live) else "verified_fulfilment"
        self._append_event(
            "need_fulfilled",
            need_id=need_id,
            holder_id=lease.holder_id,
            artifact_id=artifact_id,
            generation=lease.generation,
            flag=flag,
        )
        if live:
            self._lock_path(need_id).unlink(missing_ok=True)
        return True

    # -- no central ranking (asserted by tests) -------------------------------------
    # The public surface intentionally has NO method that returns a ranked
    # list of needs or assigns needs to agents. Claim requires an agent_id;
    # open_needs only filters, never orders scientifically.


__all__ = [
    "NeedBroker",
    "Lease",
    "BrokerError",
    "BudgetExhausted",
]
