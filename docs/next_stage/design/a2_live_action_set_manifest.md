# A2 — Live Action-Set Manifest (Freeze-Design, Track-I)

**Worker:** W2f (A2 live action-set manifest) · **Stage-2 fleet — G2 unblock**
**Status:** FREEZE-DESIGN (offline, read-only against AIOpsLab; no deployment, no k8s/kind run, no spend)
**Companion artifact:** `src/repliclaw/benchmarks/common/schemas/live_action_manifest.schema.json`

All AIOpsLab citations are `file:line` references read directly from the scratch checkout at
`/Users/sushantgautam/Documents/stg2-worktrees/AIOpsLab/`, pinned at
**`ccf08d0d1d5fa5b30f120e2e8549662d44411b35`** (verified `git rev-parse HEAD`).
Submodule `aiopslab-applications` @ `8038be6b4989c647126f27715acc591c47133c2d` (`.gitmodules`).
This document is the **single source of truth** from which both intervention-matched arms
(**D-E centralized**, **C-EQ**) draw their admissible action vocabulary, budget caps,
escrow→action mapping, and reset digest — so tool parity holds by construction
(`docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md:44` — matching = available action
vocabulary, authorization, max number of tests, environment reset state, cumulative
compute budget, information timing, simulator access).

---

## 1. FROZEN ACTION SET

### 1.1 What the code's action registry actually contains

The mitigation task's action surface is built by `get_actions(task="mitigation")`
(`aiopslab/utils/actions.py:51-79`), which introspects `MitigationActions` and returns every
method carrying the `is_action` flag (set by the `@action`/`@read`/`@write` decorators,
`aiopslab/utils/actions.py:8-38`). `MitigationTask.get_available_actions()` returns exactly
that dict (`aiopslab/orchestrator/tasks/mitigation.py:65-66`); unknown names raise
`InvalidActionError` in `perform_action` (`tasks/mitigation.py:68-73`), and the
orchestrator surfaces them as the environment response (`orchestrator.py:133-140`).

`MitigationActions(TaskActions)` (`aiopslab/orchestrator/actions/mitigation.py:11`) therefore
exposes, for **every** registered mitigation problem:

| # | action_id | Kind | Evidence | changed_factors (frozen) |
|---|---|---|---|---|
| 1 | `get_logs(namespace, service)` | read | `aiopslab/orchestrator/actions/base.py:34` | `["observation"]` |
| 2 | `exec_shell(command, timeout=30)` | write (intervention channel) | `aiopslab/orchestrator/actions/base.py:80` (BLOCK_LIST at `:95-101`; `Shell.exec` at `:110`) | `["cluster_state"]` |
| 3 | `get_metrics(namespace, duration=5)` | read | `aiopslab/orchestrator/actions/base.py:115` | `["observation"]` |
| 4 | `read_metrics(file_path)` | read | `aiopslab/orchestrator/actions/base.py:145` | `["observation"]` |
| 5 | `get_traces(namespace, duration=5)` | read | `aiopslab/orchestrator/actions/base.py:168` | `["observation"]` |
| 6 | `read_traces(file_path)` | read | `aiopslab/orchestrator/actions/base.py:195` | `["observation"]` |
| 7 | `submit()` | terminal | `aiopslab/orchestrator/actions/mitigation.py:18-33` (returns `VALID_SUBMISSION`) | `["episode_termination"]` |

**Frozen action-set size per registered mitigation problem: 7 actions, identical across all
14 registered mitigation problems** — the registry is task-level, not problem-level: every
`*Mitigation` class composes the same `MitigationTask` (e.g.
`k8s_target_port_misconfig/target_port.py:171-175`, `kafka_queue_problems.py:173-177`).
Problem-specificity enters only through the *prompt* (app summary,
`tasks/mitigation.py:20-29`) and the *evaluator* — not through the action set. That is
exactly what matched-tools parity needs: same menu, same grammar (`api_name(args)` parsed
by `ResponseParser`, `orchestrator.py:118-121`), same `exec_shell` bounds (30 s default,
`actions/base.py:80`).

`changed_factors` follows the RepliClaw `InterventionSpec.changed_factors` convention
(`src/repliclaw/counterfactual/case.py:77-100` — the spec declares which factor dimensions
it perturbs; here the dimensions are environment dimensions, not prompt factors):
`cluster_state` is the only factor an action perturbs environmentally (and only
`exec_shell` does), `observation` marks reads, `episode_termination` marks `submit`.
Selection between arms is measured on this *factor menu + action ids*, never on outcomes.

### 1.2 Registered mitigation problems (action-set owners)

Verified line-by-line from `aiopslab/orchestrator/problems/registry.py` (pinned SHA).
**14 registered mitigation problems** — these are the only problems with an intervention
vocabulary:

| problem_id | registry.py line | app (code, authoritative) |
|---|---|---|
| `k8s_target_port-misconfig-mitigation-{1,2,3}` | `:47, :59, :71` | SocialNetwork (`target_port.py:22`) |
| `auth_miss_mongodb-mitigation-1` | `:78` | SocialNetwork (`auth_miss_mongodb.py:22`) |
| `revoke_auth_mongodb-mitigation-{1,2}` | `:89, :101` | HotelReservation (`revoke_auth.py:22`) |
| `user_unregistered_mongodb-mitigation-{1,2}` | `:114, :126` | HotelReservation (`storage_user_unregistered.py:22`) |
| `misconfig_app_hotel_res-mitigation-1` | `:133` | HotelReservation (`misconfig_app_hotel_res.py:22`) |
| `scale_pod_zero_social_net-mitigation-1` | `:138` | SocialNetwork (`scale_pod_social_net.py:23`) |
| `assign_to_non_existent_node_social_net-mitigation-1` | `:143` | SocialNetwork (`assign_non_existent_node_social_net.py:23`) |
| `astronomy_shop_kafka_queue_problems-mitigation-1` | `:185` | AstronomyShop (`kafka_queue_problems.py:15`) |
| `redeploy_without_PV-mitigation-1` | `:200` | HotelReservation (`redeploy_without_pv.py:19`) |
| `wrong_bin_usage-mitigation-1` | `:205` | HotelReservation (`wrong_bin_usage.py:19`) |

**Correction to the G0 contract** (`docs/next_stage/adapters/aiopslab_contract.md` verdict
table): the contract lists `auth_miss_mongodb-mitigation-1` in the hotel-res/Mongo row and
`redeploy_without_PV-mitigation-1` as social net ("(social net)" in the heading; the app
column says social). The code says: `auth_miss_mongodb` → SocialNetwork
(`auth_miss_mongodb.py:22`) and `redeploy_without_PV` → HotelReservation
(`redeploy_without_pv.py:19`). This manifest follows the code; G0 feasibility verdicts
for those two rows should be re-checked against it before any live run.

### 1.3 Excluded actions / surfaces (and why) — arm-identical exclusion

| AIOpsLab action/surface | Verdict | Reason (evidence) |
|---|---|---|
| `get_microservice_repo_diff` | **EXCLUDED** | `@read` decorator disabled ("seems like a cheat for code changes") and the body is `pass` — it is *not* in the `get_actions` output (`actions/base.py:217-219`). Not an action; no arm may call it. |
| `submit(has_anomaly)` / `submit(faulty_components)` / `submit(analysis dict)` | **OUT OF SCOPE (per task)** | Those signatures belong to the detection/localization/analysis action classes (`actions/detection.py:18`, `localization.py:18`, `analysis.py:18`). Only the parameterless `submit()` (`actions/mitigation.py:18`) is registered for mitigation. All non-mitigation problems are out of the intervention track (no intervention action exists there — G0 contract §5 verdicts; protocol `EXPERIMENT_PROTOCOL_V3_DRAFT.md:31`: "No executable intervention ⇒ cannot claim benefits from counterfactual execution"). |
| All detection/localization/analysis problem variants | **BLOCKED (counterfactual track)** | No intervention action: the action surface is reads + a single `submit(answer)`, so intervention-matched comparison is undefined (G0 contract §5; remains usable as *diagnostic*-track benchmarks only). |
| `kernel_fault_*`, `disk_woreout_*` | **BLOCKED-NOT-FAKE** | Commented out of the registry (`registry.py:176-180`); acknowledged Chaos-Mesh kernel-fault bug in-repo (registry comment citing the upstream issue, `registry.py:173-175`); udev host mount absent on macOS (G0 contract §3 caveat 2). **No manifest entry, no live state.** |
| `operator_*` (5 misoperations, TiDBCluster) | **BLOCKED-NOT-FAKE** | Commented out of the registry (`registry.py:196-207`); no registered problem exists. |
| `flower_node_stop-detection`, `flower_model_misconfig-detection` | **BLOCKED-NOT-FAKE** | Docker-only (`registry.py:221-224` DOCKER_REGISTRY); detection-only, no mitigation variant, no k8s action vocabulary. |
| `noop_detection_{hotel_reservation,social_network,astronomy_shop}-1` | **BLOCKED-NOT-FAKE** | Null-class controls; detection action surface only. |
| Chaos-Mesh / injector fault actions as *agent* actions | **EXCLUDED (injector-side only)** | Fault injection is performed by the orchestrator/injectors before the agent's first step (`orchestrator.py:78`; `inject_virtual.py:32-257`, `inject_app.py:13+`, `generators/fault/inject_symp.py`), never exposed as an agent action. Arms must not be able to re-inject; any `exec_shell` command that writes a Chaos-Mesh object is a rule violation caught at evaluation (second, post-hoc layer), **not part of the vocabulary**; the pre-flight write restriction (§1.4) is the first, mechanized layer. |
| Anything not in the 7-action table §1.1 | **EXCLUDED by construction** | The `InvalidActionError` path (`tasks/mitigation.py:68-73`); the per-problem manifest JSON (schema `live_action_manifest.schema.json`) is the only admissible list; the unregistered-intervention canary (§6) fails loud on any deviation. |

### 1.4 `exec_shell` write channel — residual risk statement + pre-flight safeguard (S-W2-8 fix, J-SCI W2)

**Residual risk (stated, not downplayed).** At pinned `ccf08d0`, the *only* in-band
restriction on `exec_shell` is `BLOCK_LIST` at `aiopslab/orchestrator/actions/base.py:95-101`
— **5 substring patterns** (`kubectl edit`, `edit svc`, `kubectl port-forward`,
`docker logs -f`, `kubectl logs -f`). `Shell.exec` (`aiopslab/service/shell.py:16-47`)
then runs the remaining command with **no scope limitation**: `subprocess.run(command,
shell=True, timeout=30)` on the service host (`service/shell.py:49-70`), `ssh_exec`
(`service/shell.py:72-91`), or `docker exec kind-control-plane sh -c "…"`
(`service/shell.py:93-117`). Concretely, nothing in-repo stops an agent from:
(i) `kubectl delete`-ing evaluation infrastructure (namespaces, CRDs, the Prometheus
teardown target, cron jobs); (ii) reading evaluator-side files if any such path is
reachable from the execution host/container; or (iii) writing **Chaos-Mesh objects**
(re-injection of faults). The previous text of §1.3 relied on that last class being
"caught at evaluation" — that is a **post-hoc** check only, and the §4.2 reset digest
certifies cluster-resource state at t0 but **cannot certify off-cluster tampering** or
tampering that is later reverted. **Parity is preserved** — both arms receive the
identical unbounded channel, so the D-E vs C-EQ comparison remains valid; identical
exposure is part of the frozen environment, not a bias. The risk is campaign-level:
a single tampering incident can poison both arms' runs and invalidate a trial batch.
No in-repo mechanism closes this gap: the `AIOPSLAB_CLUSTER` → `kind-<cluster>`
kubecontext selection (`aiopslab/service/kubectl.py:23-35`) only switches *which*
kubeconfig context the python client and host kubectl use — it is not an authorization
boundary; RBAC yaml in the checkout belongs to observer stack templates
(`aiopslab/observer/{logstash,filebeat}/templates/`) and constrains only those
workloads, not the `exec_shell` channel.

**Pre-flight safeguard spec (arm-identical, mechanizable, UNTESTED-DESIGN).** To be
applied at first deployment — **DEPLOYMENT-GATED: no deployment is performed in this
design pass, and this safeguard is NOT claimed to work until tested at deployment.**
Both arms must operate against the *same* restricted identity in the *same* cluster
context; the safeguard must be installed and verified **before** `init_problem` of the
first trial and re-asserted by the pre-flight canary at every trial start.

1. **Mechanism (chosen): scoped service-account RBAC for the `exec_shell` host
   identity.** The agent-facing kubectl identity is switched from the full-privilege
   context user to a dedicated `ServiceAccount` `agent-exec-<cluster>` bound to
   a **namespaced** `Role` in the problem's app namespace (GET/LIST/WATCH on all app
   resources; create/update/patch/delete on workloads, configmaps, PVCs *inside that
   namespace only* — the legitimate mitigation surface). Everything else is
   **denied by omission** (Kubernetes RBAC is allow-only — no positive grant ⇒
   `403 Forbidden`): no cluster-scoped rules at all (so `kubectl delete
   namespace`, CRD, cron-job, or node writes are denied), and **no grant for the
   `chaos-mesh.org` API group** (so any Chaos-Mesh object
   create/update/patch/delete is denied). Both arms: same ServiceAccount, same
   binding,
   same kubeconfig context entry (`kind-<cluster>` context pointed at the scoped
   SA token per `aiopslab/service/kubectl.py:23-35` context mechanics).
2. **Fallback / co-equal mechanism (if RBAC token injection is unavailable on a
   given deployment target):** a **pre-eval kubectl audit hook** on the host identity
   (kubectl plugin or wrapper shim in front of the `exec_shell` execution host,
   arm-identical) that **DENIES** any mutating command outside the app namespace and
   any command creating/updating Chaos-Mesh objects, logging every denied attempt to
   the run record. Same arm-identical rule set as (1); either (1) or (2) — never
   neither — is a hard G2 launch precondition, recorded in the run record with the
   verification evidence.
3. **Oracle-location assertion (G2 pre-deployment check, arm-identical):** the eval
   oracle / answer store (`submit()` solution storage, `orchestrator.py:127-129`
   `set_solution` path and its host-side persistence) is declared at deployment
   config time and **asserted to be outside the filesystem reachable from the
   `exec_shell` execution host/container** — mechanically verified (path check from
   the execution host) before the first trial, not by review alone.
4. **Deployment gate status: UNTESTED-DESIGN / DEPLOYMENT-GATED.** The RBAC manifest
   in (1) is specified, not applied. At first deployment the pre-flight canary must
   demonstrate, per arm: (a) a legal in-namespace write succeeds; (b)
   `kubectl delete namespace <app-ns>` is denied; (c) creating any `chaos-mesh.org`
   object is denied; (d) reading a probe file placed in the declared
   oracle-reachable region is denied (or the region is proven unreachable per 3).
   Until (a)–(d) pass on both arms, no live trial may start.

**Layering (never weakened, never claimed beyond evidence):**
- **Layer 1 (pre-flight, new §1.4):** scoped RBAC/audit deny of out-of-namespace
  writes + Chaos-Mesh writes, both arms — UNTESTED-DESIGN until the deployment
  canary above passes.
- **Layer 2 (post-hoc, existing):** the §1.3 Chaos-Mesh rule-violation check at
  evaluation, the §4.2 t0 reset digest (certifies reset stability of *cluster*
  resources), plus the §6 note that live `exec_shell` boundary behavior is trusted
  only after the first live canary trial. A tamper-detecting post-episode rescan
  (residual/added objects outside the `init_problem` resource set: namespaces, CRDs,
  cron jobs, chaos-mesh objects → trial marked invalid) is a required second-layer
  addition at G2; it detects what Layer 1 fails to prevent, it does not replace it.

---

## 2. max_steps / budget caps per problem

**AIOpsLab has no per-problem step cap in code.** `Orchestrator.start_problem(max_steps)`
simply loops `for step in range(max_steps)` (`orchestrator.py:145-161`); the HTTP layer
defaults to 10 when the caller omits it (`service.py:140-141`, example payload `:55`). No
per-problem config sets a cap (searched: `registry.py`, all 14 mitigation problem
`__init__`s, `aiopslab/config.yml.example`, `service.py` — no step-cap field exists).

**Frozen cap (RepliClaw freeze decision): `max_steps = 20` for every registered mitigation
problem**, passed identically to both arms' `start_problem`. Arm-neutrality rationale:
- **Per-arm allocation semantics (S-W2-7 fix, J-SCI W2):** `max_steps=20` is the per-episode
  step count in `Orchestrator.start_problem`, identical for both arms — both arms enter the
  same single loop `for step in range(max_steps)` at `orchestrator.py:161` (method at
  `orchestrator.py:145`), with one `ask_agent`/`ask_env` exchange per iteration; how each
  arm's internal structure maps its agents/rounds onto the 20 episode steps is **arm-policy
  (part of the treatment)** — e.g. a manager+investigators arm may spend one episode step
  on a manager decision plus nested agent calls inside it, while a decentralized arm may
  spend one step per agent action — and this mapping is bounded identically by the same
  20-step loop and the shared `BudgetEnvelope` (token/compute side, §2 / CEQ design
  §3.3); the G2 budget-cap canary (§6 canary #5) asserts the 20-step *loop* itself
  (present, equal, enforced in the harness-loop fixture), **not** per-agent allocations.
  The per-episode-level parity claim is therefore the one made in the prereg; effective
  per-decision-maker budget differences are acknowledged as treatment content, not drift.
- it is a single integer applied to both arms through the same code path
  (`orchestrator.py:161`); the arms cannot receive different values without a harness
  change, which the parity canary (§6) detects;
- 20 ≥ the upstream default of 10 (no arm starved relative to upstream norms) while
  staying small enough that one trial fits the per-trial time budget;
- the other environment time parameter, the mitigation settle window
  `AIOPSLAB_MITIGATION_SETTLE_SECONDS` (default 120 s, `tasks/mitigation.py:119-134`), is
  frozen at its default 120 for all problems — it runs inside the *evaluator* after
  `submit()`, identically for both arms, so it cannot bias selection.

Per-problem caps in the manifest:

| Problem family | max_steps | Notes |
|---|---|---|
| All 14 registered mitigation problems | **20** | Same value; any per-problem override is a pre-registered amendment, not an arm choice. |

Actual spend is auditable per arm from the session JSON: `steps`, `in_tokens`, `out_tokens`
are recorded per session by `Task.common_eval` (`tasks/base.py:48-50`). Token/compute
envelope parity for the LLM side is carried by the shared `BudgetEnvelope` (CEQ design
`docs/next_stage/design/ceq_arm_design.md` §3.3), orthogonal to this step cap.

---

## 3. ESCROW-SELECTION → ACTION MAPPING

**Chosen mechanism: explicit table lookup (`explicit_table_lookup_v1`), NOT a hash.**

Definition (identical on both arms; the manifest *is* the table):

1. The manifest's `action_set` is a **fixed-order** array (the §1.1 order:
   `get_logs, exec_shell, get_metrics, read_metrics, get_traces, read_traces, submit`).
2. An escrow-side selection is expressed as an **ordinal** `i` in
   `[0, len(action_set))` (or directly as an `action_id` — both must agree; disagreement
   is a hard failure). Resolution: `action = action_set[i]`.
3. A resolved action is *admissible* iff its `action_id` is in `action_set` and
   `arm_visible: true`; otherwise it is rejected exactly as upstream rejects unknown
   names (`InvalidActionError`, `tasks/mitigation.py:68-73`).

**Justification over hashing:**
- The menu has 7 entries; a hash mod-7 (or truncated-hash) mapping is sensitive to the
  hash family and to action ordering in ways that are not auditable at freeze time. An
  explicit table is re-derivable from the pinned SHA (`ccf08d0`) by anyone, and any change
  is visible as a manifest diff.
- Arm-identity is trivial to certify: both arms validate selections against the *same
  frozen array*; the G2 escrow-mapping canary (§6) asserts identical resolution on a fixed
  selection probe.
- The D-R comparator (random selection, `EXPERIMENT_PROTOCOL_V3_DRAFT.md:17`) consumes the
  same table: a seeded RNG samples the ordinal uniformly over `[0, len(action_set))` with
  `escrow_mapping.seed`. D-R therefore never leaves the matched vocabulary.

The `seed` field in the schema is used **only** by D-R; D-E and C-EQ use pure
deterministic lookup (seed irrelevant, frozen at 0 by default for record-keeping).

---

## 4. RESET DIGEST

### 4.1 AIOpsLab's actual reset mechanism (code-cited)

Per-run lifecycle in `Orchestrator`:
1. **Tear-down of the previous run** (end of `start_problem`): `recover_fault()` — the
   fault-specific inverse op (`orchestrator.py:198`), with
   `atexit.register(exit_cleanup_fault, prob)` as crash guard (`orchestrator.py:79`,
   function at `:233-235`); then `app.cleanup()` — `kubectl delete namespace <ns>`
   (`orchestrator.py:205`; `service/apps/base.py:82-84`), and for hotel-reservation
   additionally PV finalizer-stripping + PV deletion
   (`service/apps/hotelres.py:85-104`); then Prometheus teardown + OpenEBS uninstall
   (`orchestrator.py:208-214`).
2. **Fresh bring-up** (`init_problem`, `orchestrator.py:34-91`): OpenEBS install +
   default storageclass patch (`:51-61`), Prometheus deploy (`:64-66`),
   **`app.delete(); app.deploy()`** — full re-deploy from helm/k8s manifests
   (`orchestrator.py:71-72`; e.g. `service/apps/socialnet.py:45-53` helm install,
   `service/apps/hotelres.py:67-71` kubectl apply), fault injection
   (`orchestrator.py:78`), workload start (`:82-85`).

Reset semantics = **redeploy + targeted fault recovery + namespace/PV purge + telemetry
teardown**. `init_problem` is exactly the per-trial reset primitive.

### 4.2 Digest of post-reset state (frozen spec)

Computed **after** `init_problem` completes (deploy + fault injection + workload start)
and **before** the agent's first step, on each arm's own cluster context
(`AIOPSLAB_CLUSTER` → `kind-<cluster>` kubecontext, `service/kubectl.py:23-35`) — i.e.,
the digest certifies "both arms started from the same baseline fault state"; comparing
digest(t0 of trial n+1) against digest(t0 of trial n) for the same problem certifies
reset stability.

- **Resources hashed** (namespace-scoped to the problem's app namespace, + PVs by name for
  hotel-res): `deployments`, `services`, `pods`, `configmaps`, `statefulsets`,
  `persistentvolumeclaims`, `persistentvolumes` (hotel-res only).
- **Normalization (volatility stripped before hashing):** per pod — drop
  `status.podIP`, `status.hostIP`, `metadata.uid`, `metadata.resourceVersion`,
  `status.startTime`, `status.containerStatuses[*].restartCount`; keep name, node, ready
  flag, container images. Per other resource — keep only `metadata.name` and the spec
  fields `init_problem` sets, recursively sorted. This is the single place the digest can
  be made stable across runs; it is fixed here, arm-identical.
- **Canonicalization + algorithm:** `sha256` over
  `json.dumps({resource: sorted_objects}, sort_keys=True, separators=(",",":"))` with
  resources in the fixed order above (matches the RepliClaw
  `canonical_bytes`/`sha256_bytes` convention,
  `src/repliclaw/counterfactual/case.py:37-41`).
- **Gate:** a trial is invalid (re-run from reset) if its t0 digest differs from the
  problem's reference digest recorded at first verified deployment. Digests are written
  into the run record, not the agent-visible state.

### 4.3 GATED-PENDING-APPROVAL (never faked)

| Problem family | Gate |
|---|---|
| `k8s_target_port-misconfig-mitigation-{1,2,3}`, `auth_miss_mongodb-mitigation-1`, `scale_pod_zero_social_net-mitigation-1`, `assign_to_non_existent_node_social_net-mitigation-1` (SocialNetwork, 6 problems) | **LOCAL-APPROVED** (macOS + kind, no spend; G0 contract §6 item 5: no approval required to *attempt*). Digest reference values: pending first verified deployment. |
| `revoke_auth_mongodb-mitigation-{1,2}`, `user_unregistered_mongodb-mitigation-{1,2}`, `misconfig_app_hotel_res-mitigation-1`, `redeploy_without_PV-mitigation-1`, `wrong_bin_usage-mitigation-1` (HotelReservation, 7 problems) | **GATED-PENDING-APPROVAL** — VM-backed deployment + spend approval (G0 contract §6 item 1, FEASIBLE-WITH-VM verdicts). No live state recorded until approved. |
| `astronomy_shop_kafka_queue_problems-mitigation-1` (AstronomyShop, 1 problem) | **GATED-PENDING-APPROVAL** — heaviest stack (Kafka/TiDB, ~30 services); 8 vCPU/32 GB-class VM (G0 contract §3). No live state recorded until approved. |

No manifest entry for a gated problem carries a digest reference value until a
human-approved deployment produces one; the schema deliberately keeps reference digests
out of the frozen file (they belong in the run record).

---

## 5. JSON schema

`src/repliclaw/benchmarks/common/schemas/live_action_manifest.schema.json`
(`repliclaw.live_action_manifest/v1`, JSON Schema draft 2020-12, style-matched to the
other schemas in `src/repliclaw/benchmarks/common/schemas/`): `schema` const,
`additionalProperties: false`, no custom vocabulary — validatable with any stock
JSON-Schema validator (e.g. Python `jsonschema`). One manifest instance per problem_id.
Fields: `problem_id`, `pinned_repo_sha` (40-hex pattern; frozen `ccf08d0…`), `app`,
`namespace`, `action_set[]` (`action_id`, `changed_factors` enum, `arm_visible`, optional
`params`), `max_steps`, `escrow_mapping {function_id: "explicit_table_lookup_v1", seed}`,
`reset_digest_spec {resources[], hash_algorithm: "sha256", canonicalization}`,
`approval_gate {required, gates}`, `excluded_actions[{action_id, reason}]`, optional
`notes`.

**BLOCKED-NOT-FAKE items (searched, not findable):**
- No per-problem step cap exists anywhere in AIOpsLab (searched `registry.py`, all 14
  mitigation problem `__init__`s, `config.yml.example`, `service.py`) — hence the §2
  freeze decision rather than an upstream citation.
- No upstream "baseline state" object or digest exists; the §4.2 digest is a RepliClaw
  addition built on the cited reset procedure.
- `get_microservice_repo_diff` parameters are not recoverable (body is `pass`,
  `actions/base.py:219`) — excluded, not guessed.

---

## 6. G2 UNBLOCK STATEMENT

**Enabled now — offline fixture canaries runnable against this manifest, NO deployment:**
1. **Action-menu parity canary:** both arms' adapters load the same per-problem manifest;
   assert the ordered `action_set` (ids + `changed_factors`) is byte-identical for D-E and
   C-EQ (protocol `:65` — "same action schema and executor").
2. **Action-schema hash canary:** record sha256 of the canonical `action_set` in the
   prereg; both arms' harnesses assert against it (protocol `:65` — "allowed action schema
   hash").
3. **Unregistered-intervention execution canary:** feed a selection outside `action_set` to
   both arms' resolvers; both must reject (D-E/C-EQ: lookup miss; live analogue:
   `InvalidActionError`, `tasks/mitigation.py:68-73`).
4. **Escrow-mapping determinism canary:** fixed ordinal probes resolve to the same
   `action_id` in both arm harnesses (`explicit_table_lookup_v1`).
5. **Budget-cap canary:** `max_steps=20` present, equal, and enforced in the harness-loop
   fixture (offline stand-in for the 20-step loop at `orchestrator.py:161`) — this canary
   asserts the *episode-step loop* only, not per-agent allocations (S-W2-7; §2).
6. **Parity instrumentation canary (offline fixture arms):** the existing Track-II
   `test_v3_ceq_parity` family (J-SCI Wave-1 §5) extended to read `changed_factors` from
   the manifest instead of ad-hoc literals.

**Still requiring human-approved deployment:**
- **Pre-flight `exec_shell` safeguard canary** (S-W2-8, §1.4): apply scoped RBAC (or the
  audit-hook fallback) to both arms' identities and pass checks (a)–(d) — legal in-namespace
  write OK; `kubectl delete namespace` denied; Chaos-Mesh object creation denied;
  oracle-region read denied/unreachable — plus the oracle-location assertion and the
  post-episode rescan wired in as Layer 2. UNTESTED-DESIGN until this passes; no live
  trial before it.
- First-verified-deployment **reference reset digests** for the 6 local SocialNetwork
  problems (kind on macOS; no spend, but an actual cluster run — not done in this pass).
- All 7 HotelReservation + 1 AstronomyShop problems: VM provisioning + spend
  (**GATED-PENDING-APPROVAL**), then their reference digests.
- Reset-stability verification (digest(t0, n+1) == digest(t0, n)) and live `exec_shell`
  boundary behavior — trusted only after the first live canary trial.

---

## 7. Return summary (for integrator)

- **Files:** `docs/next_stage/design/a2_live_action_set_manifest.md` (this file) +
  `src/repliclaw/benchmarks/common/schemas/live_action_manifest.schema.json`.
- **Action-set size per problem:** **7 actions for each of the 14 registered mitigation
  problems** (task-level registry, identical); excluded/invalid surfaces documented §1.3.
- **Reset digest spec:** sha256 over canonical sorted-compact JSON of
  `deployments, services, pods, configmaps, statefulsets, persistentvolumeclaims,
  persistentvolumes` (hotel-res) for the app namespace, volatility-stripped (§4.2),
  computed after `init_problem` (`orchestrator.py:34-91`) and before step 1, per-arm
  cluster context (`service/kubectl.py:23-35`).
- **max_steps:** 20 (frozen, arm-neutral; upstream has no cap — default 10 in
  `service.py:140-141`). Per-arm allocation semantics (S-W2-7): 20 is the per-episode step
  count in `Orchestrator.start_problem` (`orchestrator.py:145`, loop at `:161`), identical
  for both arms; agent/round mapping onto those steps is arm-policy (treatment), bounded by
  the same 20-step loop + shared `BudgetEnvelope`; canary #5 asserts the loop, not
  per-agent allocations.
- **exec_shell safeguard (S-W2-8):** §1.4 — residual risk of the 5-pattern BLOCK_LIST
  stated; pre-flight arm-identical RBAC/audit deny of out-of-namespace + Chaos-Mesh writes
  specified as **UNTESTED-DESIGN, DEPLOYMENT-GATED**; post-hoc eval check retained as layer
  2.
- **BLOCKED:** `kernel_fault_*` / `disk_woreout_*` / `operator_*` / `flower_*` /
  `noop_*` — not registered or Docker-only; no manifest entries, no fake state.
  Gated VM families: 7 hotel-res + 1 astronomy-shop problems GATED-PENDING-APPROVAL.
- **Correction flagged:** G0 contract mis-assigned apps for `auth_miss_mongodb` (→
  SocialNetwork) and `redeploy_without_PV` (→ HotelReservation); this manifest follows code.
