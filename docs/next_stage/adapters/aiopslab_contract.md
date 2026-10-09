# AIOpsLab Adapter Contract — Stage 2 (G0, interactive/counterfactual track)

**Role:** L3 (AIOpsLab team). Read-only feasibility study; no cluster was deployed, no
resources created, no money spent. All citations below are `file:line` references into the
scratch clone at `stg2-worktrees/AIOpsLab` (verified by direct file reads).

## 1. Pin, license, runtime

| Item | Value | Evidence |
|---|---|---|
| Repo | `https://github.com/microsoft/AIOpsLab` | — |
| **Pinned SHA** | `ccf08d0d1d5fa5b30f120e2e8549662d44411b35` (commit "build(deps-dev): bump transformers from 4.54.1 to 5.10.1 (#198)", 2026-09-14) | `git rev-parse HEAD` of clone |
| Submodule | `aiopslab-applications` @ `8038be6b4989c647126f27715acc591c47133c2d` (xlab-uiuc/aiopslab-applications) | `.gitmodules:2-4`, `git submodule status` |
| License | MIT (Copyright (c) Microsoft Corporation) | `LICENSE.txt:1-2` |
| Python | `>=3.11,<3.13` (Poetry) | `pyproject.toml:[tool.poetry.dependencies]` |
| Kind image | `kindest/node:v1.32.1` base + udev/socat | `kind/Dockerfile:1-4` |
| k8s version | 1.32 (kind node image) | `kind/Dockerfile:1` |

## 2. Deployment stack

- **No Helm chart for AIOpsLab itself, no local single-node mode.** AIOpsLab is a Python
  orchestrator (`Orchestrator`, `aiopslab/orchestrator/orchestrator.py:21`) that drives an
  **existing Kubernetes cluster** via `kubectl`/kubeconfig (`aiopslab/service/kubectl.py:12-40`),
  and uses **Helm** to install stack components *inside* that cluster:
  - OpenEBS local storage: applied + made default storageclass per problem
    (`aiopslab/orchestrator/orchestrator.py:54-64`).
  - Prometheus telemetry: deployed/teardown per problem
    (`aiopslab/orchestrator/orchestrator.py:66-68`, `orchestrator.py:199-201`).
  - Chaos-Mesh (for chaos-based faults): helm-installed lazily by the symptom injector
    (`aiopslab/generators/fault/inject_symp.py:19-47`).
- **Cluster options** (documented): (a) local **kind** cluster — x86 or ARM configs
  (`kind/kind-config-x86.yaml`, `kind/kind-config-arm.yaml`, README Quick Start §a);
  (b) any remote k8s cluster that the default kubeconfig context targets, with Ansible
  setup playbooks (README Quick Start §b, `scripts/ansible`); (c) Azure VMs via
  Terraform+Ansible (README Quick Start §c).
- **Exception:** two "Flower" problems run on **plain Docker** (not k8s):
  `registry.py:222-224` (`DOCKER_REGISTRY`), `aiopslab/orchestrator/problems/flower_node_stop/node_stop.py:1-16`
  (uses `aiopslab/service/dock.py`, `flwr` flower framework). These skip OpenEBS/Prometheus
  (`orchestrator.py:53`).

### Hardware / resource requirements

- No explicit minimums documented. What the stack actually needs (read from code):
  - kind 2-node cluster (control-plane + worker), each node a container running K8s 1.32,
    with **`/run/udev` host-mounted into both nodes**
    (`kind/kind-config-arm.yaml:4-13`, `kind-config-x86.yaml` identical) — needed for
    disk-level fault injection and udev availability in the custom kind image.
  - Custom kind node images `jacksonarthurclark/aiopslab-kind-{arm,x86}:latest`
    (`kind-config-arm.yaml:5,10`); a **non-pinned `:latest`** tag (risk: drift between runs —
    pin after first verified pull).
  - The kind node image ships **~100 preloaded app images** (`kind/images.txt`), so first-run
    pull is large (multi-GB image cache).
  - OpenEBS hostpath storage requires direct host-disk access inside kind nodes
    (`orchestrator.py:57-62`); apps use MongoDB, Kafka, Cassandra, TiDB, OpenWhisk
    (social network), SkyWalking — heavy microservice stacks.
  - Workload generation via `wrk`/`wrk2` in-cluster (`aiopslab/generators/workload/wrk.py`).
- **Verified reference host** in docs: 4 vCPU / 8 GB Ubuntu 24.04
  (`kind/README.md:43`); cloud path uses 2+ worker VMs (README §c).

## 3. macOS / Apple Silicon feasibility

- **Official ARM path exists:** `kind create cluster --config kind/kind-config-arm.yaml`
  (README line 81-82, `kind/kind-config-arm.yaml`) — ARM64 kind node image is provided.
- **This machine:** 10 cores / 16 GB RAM Apple Silicon (`sysctl hw.ncpu hw.memsize` = 10,
  17179869184).
- **Assessment:**
  - *Works in principle on macOS:* Docker Desktop (Linux VM) + kind ARM + kubectl + Helm
    all support Apple Silicon. The framework is pure-Python orchestration over kubectl, so
    nothing is Linux-privileged on the host.
  - *Practical caveats (FEASIBLE-WITH-VM bias):*
    1. 16 GB host RAM is the tight dimension: one kind node + OpenEBS + Prometheus +
       Chaos-Mesh + a ~30-service microservice app (social network incl. OpenWhisk, or
       Astronomy Shop with Kafka/TiDB) plus Docker Desktop's own overhead. The documented
       working reference is a *dedicated* 4 vCPU/8 GB VM; on a shared 16 GB laptop expect
       OOM/eviction risk for the largest apps. Recommend 16-32 GB **Linux cloud VM** for
       runs where the full app stack (social network / astronomy shop / hotel reservation
       with TiDB) must be reliable.
    2. `/run/udev` host mount into kind nodes (`kind-config-arm.yaml:6-8`) — on macOS this
       path does not exist on the host; Docker Desktop may silently ignore the mount.
       Only a problem for udev-dependent faults (disk wearout); container-level faults
       are unaffected. Needs a one-time verification (not performed in this G0 pass).
    3. `:latest` kind image tags → must pull and re-tag to a digest before any benchmark
       run to guarantee reproducibility across arms.
    4. `poetry install` pulls CUDA/CUDA-dependent client extras by default
       (`pyproject.toml` clients group: vllm, flwr…) — use `poetry install --without clients`
       on macOS (vLLM is unusable there anyway; agents will be external LLMs).

**Verdict:** local macOS run is *possible* for the lighter apps (social network
misconfig/scale problems); for repeatable multi-arm benchmarking, treat a Linux VM
(4 vCPU/16 GB class, or 8 vCPU/32 GB for astronomy shop) as the recommended baseline.

## 4. Problem registry

97 registered problem IDs (script-extracted from
`aiopslab/orchestrator/problems/registry.py:15-222`). Problem families by task type:

| Family (app / fault) | Detection | Localization | Analysis | Mitigation |
|---|---|---|---|---|
| k8s target-port misconfig — social network (user/text/post-storage) ×3 | ✔ | ✔ | ✔ | ✔ |
| MongoDB auth missing (hotel res) | ✔ | ✔ | ✔ | ✔ |
| MongoDB auth revoked (geo/rate) ×2 | ✔ | ✔ | ✔ | ✔ |
| MongoDB user unregistered (geo/rate) ×2 | ✔ | ✔ | ✔ | ✔ |
| App misconfig (hotel res, wrong mongo) | ✔ | ✔ | ✔ | ✔ |
| Pod scaled to zero (social net) | ✔ | ✔ | ✔ | ✔ |
| Pod assigned to non-existent node (social net) | ✔ | ✔ | ✔ | ✔ |
| Container kill (hotel res, Chaos-Mesh) | ✔ | ✔ | — | — |
| Pod failure / pod kill (hotel res, Chaos-Mesh) | ✔ | ✔ | — | — |
| Network loss / delay (hotel res, Chaos-Mesh) | ✔ | ✔ | — | — |
| Kernel fault (hotel res) | **commented out** (registry lines ~175-178) — known Chaos-Mesh bug | same | — | — |
| Disk wearout | **commented out** (registry ~179-180) | same | — | — |
| Astronomy Shop feature-flag faults: ad failure, ad high-CPU, ad manual-GC, cart failure, image slow load, kafka queue, load-generator flood, payment failure, payment unreachable, product-catalog failure, recommendation-cache failure | ✔ | ✔ | — | kafka queue only (✔) |
| No-op (hotel / social / astronomy) | ✔ (null class) | — | — | — |
| Redeploy without PV (social net) | ✔ | **commented out** | ✔ | ✔ |
| Wrong bin usage (social net, go/profile) | ✔ | ✔ | ✔ | ✔ |
| K8s operator misoperation ×5 | **all commented out** (registry ~196-207) | same | — | — |
| Flower node-stop / model-misconfig (Docker, not k8s) | ✔ | — | — | — |

### Ground-truth labels and official evaluators

- **Detection** (`aiopslab/orchestrator/tasks/detection.py:76`): solution is a string;
  ground truth `"Yes"` (yes/no anomaly), metric `TTD` (time to detect) +
  `"Detection Accuracy": Correct/Incorrect/Invalid Format`. E.g.
  `container_kill/container_kill.py:68-83`, `wrong_bin_usage.py:64-85`.
- **Localization** (`tasks/localization.py:80`): ground truth = specific faulty service
  name(s); exact-match vs subset scoring (`evaluators/quantitative.py:36-67`), metric `TTL`.
  E.g. `container_kill.py:87-120` (`self.faulty_service = "geo"`).
- **Analysis** (`tasks/analysis.py:91`): dict answer; ground truth = system level + fault
  type (e.g. `expected_system_level = "Application"`, `expected_fault_type = "Misconfiguration"`,
  `auth_miss_mongodb.py:131-150`), metric `TTA`.
- **Mitigation** (`tasks/mitigation.py`): **no label** — success is verified against the
  *live system state after `submit()`*: `self.results["success"] = wait_until_pods_healthy(namespace)`
  (`tasks/mitigation.py:158-184`), or problem-specific postconditions such as
  targetPort == 9090 (`k8s_target_port_misconfig/target_port.py:176-183`). Metric `TTM`.
- All tasks also record `steps`, `in_tokens`, `out_tokens` (`tasks/base.py:31-41`), and
  optionally an LLM-judge reasoning score (`evaluators/qualitative.py:16`, gated by
  `qualitative_eval: false` in `aiopslab/config.yml.example`).
- Orchestrator loop: `Orchestrator.start_problem` (`orchestrator.py:145-214`) — agent
  proposes one action per turn in `api_name(args)` format, parsed by
  `parser.parse` (`orchestrator.py:118`), executed by `problem.perform_action`
  (`orchestrator.py:133`), terminated by `submit()`.

### Capability matrix (injection / reset / isolation / action API)

**Fault injection (a) — genuine, code-verified:**
- Chaos-Mesh experiments for container/pod faults: `SymptomFaultInjector`
  (`generators/fault/inject_symp.py:49-61,111-132,66-86,171-200`) — real `kubectl apply`
  of PodChaos objects.
- Manifest/config mutation for misconfig faults: `VirtualizationFaultInjector._inject`
  (used by `target_port.py:41-48`, `scale_pod_social_net.py:45-49`,
  `misconfig_app_hotel_res.py:41-48`, flower problems).
- Feature-flag/env flips for Astronomy Shop: `ApplicationFaultInjector`
  (`generators/fault/inject_app.py:13`, used in `ad_service_failure.py:25-32`).
- MongoDB admin ops (auth missing/revoked/unregistered), bin swap (wrong_bin_usage),
  redeploy-without-PV orchestration.
- Kernel fault & disk wearout: implemented (`inject_symp.py:206-228`) but **disabled in
  the registry** due to a known Chaos-Mesh bug (registry comment, `kernel_fault.py:4-9`).

**Reset (b) — actual reset mechanism found in code:**
1. `prob.app.delete()` + `prob.app.deploy()` at problem init: full re-deploy of the
   microservice app from manifests/helm, *before* fault injection
   (`orchestrator.py:70-72`; `service/apps/base.py` `deploy`/`delete`,
   e.g. `socialnet.py:45,65`).
2. `prob.recover_fault()` — fault-specific inverse operation, called on exception
   (`orchestrator.py:167-171`) and at the end of every run
   (`orchestrator.py:202-204`), plus `atexit.register(exit_cleanup_fault, prob)` as a
   crash guard (`orchestrator.py:76-79`, `orchestrator.py:233-235`).
3. `prob.app.cleanup()` — `kubectl delete namespace <app-namespace>` plus PV
   finalizer-stripping and PV deletion (hotel res) — full state wipe
   (`orchestrator.py:207`, `service/apps/base.py:82`, `service/apps/hotelres.py:81-104`).
4. OpenEBS + Prometheus teardown after each run (`orchestrator.py:199-208`).
   ⇒ Reset semantics = **redeploy + targeted fault recovery + namespace/PV purge**.
   Deterministic starting state is obtained every time `init_problem` is called
   (`orchestrator.py:34-91`), which is exactly the per-arm reset primitive we need.

**Per-arm isolation (c):**
- Applications are namespace-scoped: `test-social-network`, `test-hotel-reservation`,
  `astronomy-shop`, `tidb-cluster`, `openwhisk`, `train-ticket`, `docker` (flower)
  (`aiopslab/service/metadata/*.json`). Within one cluster, two different apps (hence
  different namespaces) can coexist; two arms of the *same* problem would collide on the
  same namespace/PVs.
- **First-class parallel-arm support exists at the cluster level:** `KubeCtl` selects the
  kubecontext by `AIOPSLAB_CLUSTER` env var → `context = f"kind-{cluster_env}"`
  (`service/kubectl.py:23-31`). i.e., one kind cluster per arm, each arm's process
  pointed at its own context. This is the intended mechanism for parallel/repeatable
  arms.

**Action API an agent can call (d):**
- Shared read/act surface for all tasks (`actions/base.py:34,80,115,145,168,195,219`):
  `get_logs`, `exec_shell(command, timeout)` — **arbitrary in-namespace shell, this is
  the controlled-intervention channel**, `get_metrics`, `read_metrics`, `get_traces`,
  `read_traces`, `get_microservice_repo_diff`.
- Task-specific `submit` actions: `submit(has_anomaly)` (detection, `actions/detection.py:18`),
  `submit(faulty_components)` (localization, `actions/localization.py:18`),
  `submit(analysis dict)` (analysis, `actions/analysis.py:18`),
  `submit()` (mitigation, `actions/mitigation.py:17-26`).
- Mitigation problems explicitly hand the agent the whole app API list:
  `MitigationTask` passes `Supported Operations` from app metadata into the task prompt
  (`tasks/mitigation.py:28-47`; e.g. "Supported Operations" in
  `service/metadata/social-network.json`). ⇒ For mitigation problems the *same* action
  vocabulary is available to any policy (centralized or decentralized) registered as an
  `agent` object with `get_action(input)` (`orchestrator.py:93-111`,
  `service.py` FastAPI harness `SimulationRequest`).
- HTTP layer for external orchestration: `service.py` FastAPI app (`/problems`,
  simulation endpoint) — each call spins up a fresh Orchestrator session.

## 5. Decisive question — intervention-matched centralized vs decentralized policies

Requirements: SAME registered problem, identical action vocabulary, safe reset, per-arm
isolation.

### Verdicts

| Problem (registered ID) | Verdict | Rationale & evidence |
|---|---|---|
| `k8s_target_port-misconfig-mitigation-{1,2,3}` (social net) | **FEASIBLE** | Mitigation task gives both policies the identical action API (`MitigationActions` + base actions, `tasks/mitigation.py:40-72`); deterministic object-level ground truth (targetPort==9090, `target_port.py:176-183`); reset = redeploy + `VirtualizationFaultInjector._recover` + namespace cleanup; lightest k8s app of the mitigation set (no MongoDB/TiDB/Kafka) → best fit for 10-core/16 GB macOS host. Arms isolated via one kind cluster per arm (`kubectl.py:23-31`). |
| `scale_pod_zero_social_net-mitigation-1` (social net) | **FEASIBLE** | Same action API; reset verified: `_inject/_recover(fault_type="scale_pods_to_zero")` (`scale_pod_social_net.py:45-60`) + health-gated eval (`:176-222`). Counterfactuals (scale up vs restart vs delete Pod) are all expressible through `exec_shell`/kubectl + app ops. |
| `misconfig_app_hotel_res-mitigation-1` | **FEASIBLE-WITH-VM** | Same mechanics, but hotel-reservation app adds MongoDB + wrk2 workload; reliability on 16 GB shared laptop is doubtful; 4-8 vCPU Linux VM recommended. |
| `auth_miss_mongodb-mitigation-1`, `revoke_auth_mongodb-mitigation-{1,2}`, `user_unregistered_mongodb-mitigation-{1,2}` | **FEASIBLE-WITH-VM** | Mitigation success = namespace health after agent restores Mongo auth (`auth_miss_mongodb.py:158-184`, settle window `AIOPSLAB_MITIGATION_SETTLE_SECONDS`, `tasks/mitigation.py:158-184`); distinct alternative interventions (create user vs recreate creds vs restart pods) all in same action vocabulary. App is medium weight. |
| `redeploy_without_PV-mitigation-1` (social net) | **FEASIBLE** | Clean PV-finalizer failure, deterministic fix (delete PV/PVC + redeploy); eval = all pods healthy (`redeploy_without_pv.py:158-191`); social-net app again the lightest k8s stack. |
| `wrong_bin_usage-mitigation-1` (social net) | **FEASIBLE** | Ground truth is inspectable binary selection (`wrong_bin_usage.py:162-199`); fix = copy/symlink profile→geo binary via `exec_shell`; good minimal counterfactual pair (copy vs symlink vs pod restart). |
| `astronomy_shop_kafka_queue_problems-mitigation-1` | **FEASIBLE-WITH-VM** | The only astronomy-shop mitigation; app is the heaviest stack (Kafka, TiDB, ~30 services) → VM baseline. |
| All detection/localization/analysis variants | **BLOCKED (for the counterfactual track)** | Not because they don't run — they do — but because their agent action surface is `get_logs/metrics/traces` + a single `submit(answer)`; there is **no intervention action** the policy can take, so "intervention-matched centralized vs decentralized" is undefined for them. They remain usable as *diagnostic*-track benchmarks (labels + TTD/TTL/TTA evaluators are first-class). |
| `kernel_fault_*`, `disk_woreout_*` | **BLOCKED** | Commented out of the registry (registry ~L175-180); upstream Chaos-Mesh kernel-fault bug acknowledged in-repo (`kernel_fault.py:4-9`). Also the udev host mount needed by these faults doesn't exist on macOS hosts. |
| `operator_*` (5 misoperations) | **BLOCKED** | Commented out of the registry (registry ~L196-207) — no registered problems available. |
| `flower_node_stop-detection`, `flower_model_misconfig-detection` | **BLOCKED** | Docker-only deployment path (`registry.py:222-224`) with no mitigation variant, no k8s action vocabulary; outside the intervention scope. |
| `noop_detection_*` | **BLOCKED** | Null-class controls only; detection action surface only. |

### Recommended decisive benchmark set (G0 candidate)

Primary: **`k8s_target_port-misconfig-mitigation-1`** and **`scale_pod_zero_social_net-mitigation-1`**
(same app, lightest stack, object-level + health-level ground truth, fully reversible
faults). Secondary (VM): `misconfig_app_hotel_res-mitigation-1`, one Mongo-auth mitigation.

**Minimal deployment plan (proposed, not executed):**
1. On host (macOS or Linux VM): Docker + kind + kubectl + helm; `poetry install --without clients` (Python 3.11).
2. Pull `jacksonarthurclark/aiopslab-kind-arm:latest` (or `-x86`), **re-tag to a pinned digest**; update a local copy of `kind-config-*.yaml` to the digest.
3. Create **N kind clusters** `kind-arm-a … kind-arm-n` (one per policy arm; each `kind-<name>` context matches `AIOPSLAB_CLUSTER=<name>`, `kubectl.py:23-31`). Size: 2 nodes each; on one host, ≤2 arms concurrently at 10-core/16 GB, else a 16-32 GB Linux VM.
4. `cp aiopslab/config.yml.example aiopslab/config.yml`, set `k8s_host: kind`, `qualitative_eval: false` (keeps evals deterministic, no LLM judge cost).
5. Per arm: `Orchestrator.init_problem(<problem_id>)` → inject → register the arm's policy as `agent` (`register_agent`, `orchestrator.py:93-91`) → `start_problem(max_steps)` → read `results["success"]`, `results["TTM"]`, `steps`, tokens from the returned dict / session JSON (`orchestrator.py:185-231`).
6. Reset between replications: implicit — `init_problem` always runs `app.delete(); app.deploy()` and `recover_fault()` runs at the end of the previous episode (`orchestrator.py:70-72, 202-207`).
7. Identical action vocabulary guarantee: both policies read the same `get_available_actions()` output (`tasks/mitigation.py:49-51`) and submit in the same `api(args)` grammar parsed by `ResponseParser` (`orchestrator.py:118`); `exec_shell` bounds: same 30 s default timeout for both arms (`actions/base.py:80`).

## 6. Blockers (require approval / external resources)

1. **No hardware minimum is documented**; the 16 GB shared macOS host may be insufficient
   for hotel-reservation/astronomy-shop apps — if so, a Linux cloud VM (8 vCPU/32 GB
   class) must be provisioned → **approval + spend** before the FEASIBLE-WITH-VM set.
2. Kind node image tags are `:latest` → must be pinned to a digest before any run
   (cheap, no approval) to avoid cross-arm environment drift.
3. `/run/udev` host mount is invalid on macOS → disk/kernel fault family is effectively
   macOS-blocked regardless (kernel/disk already unregistered).
4. `poetry install` default group pulls vLLM/CUDA deps — must use `--without clients` on
   macOS; if a local LLM client is wanted, that's a VM-only path.
5. No blocker for the primary social-net mitigation pair: no approvals required to
   attempt a local macOS kind deployment (still not executed in this G0 pass — read-only
   mandate).

## 7. RepliClaw integration notes (for later stages)

- Adapter interface = the `Agent` protocol: implement `async get_action(input) -> str`
  returning exactly one `api(args)` line in a markdown code block
  (`orchestrator.py:103-111`, task instruction strings in `tasks/mitigation.py:35-47`).
  A decentralized policy (e.g., manager + workers) can be wrapped as a single
  `get_action` implementation without touching AIOpsLab code; a centralized policy is a
  direct LLM loop. This gives *identical* action vocabulary by construction.
- Session trace (`session.history`) + results dict are JSON-serializable
  (`session.py`, `orchestrator.py:222-231`) — sufficient for pre-outcome logs needed by
  the evidence-escrow protocol; `qualitative_eval: false` recommended so scores are not
  LLM-dependent.
- Cost class: primary set (social-net mitigation) = **low** (2-node kind, 1 app, no
  external services); secondary set = **medium** (Mongo/TiDB/Kafka in-cluster, VM
  recommended). No external paid dependencies beyond optional LLM API calls.
