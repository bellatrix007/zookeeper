# 03 — Testing Strategy and Gap Checklist

A layered plan for gaining confidence in a 3.6 → 3.8 ZooKeeper **server** upgrade, plus the gaps
that most often go unnoticed until production. It is deployment-neutral: adapt the tooling to
whatever harness you already run, but aim to cover every layer below.

## The layers

Think of confidence as six layers. Each catches a different class of failure; skipping one leaves
a blind spot that the others do not cover.

### Layer 1 — Build, unit, integration

- Build the 3.8 server artifact on **every JDK you will run** (e.g. 8 and 11) and run the
  project's own unit + integration suites green on each.
- This catches packaging/JDK/dependency breakage early and is the cheapest signal.

### Layer 2 — Cross-version compatibility matrix

- Automate the matrix from doc 02 §5: **old client ↔ new server** and **new client ↔ old server**,
  plus a **mixed 3.6/3.8 quorum**.
- Minimum per cell: connect, create/get/set/delete, watches fire, ACL/auth path, session expiry.
- **Don't stop at "it connected."** A connectivity-only smoke test is the single most common false
  sense of security — it proves the port is open, not that data operations are correct across
  versions.

### Layer 3 — Functional / feature certification

- On a dedicated **certification ensemble** that mirrors prod topology (same node count, TLS,
  auth), exercise the features you actually use: ACLs, authentication, quotas, reconfiguration,
  watches (including persistent/recursive if used), ephemeral/session semantics, and
  backup/restore if your deployment has it.
- Run this on the **target version** and on a **mixed-version** ensemble.

### Layer 4 — Mixed-version rolling upgrade + rollback (the decisive layer)

- Stand up a 3.6 ensemble, apply **continuous read/write load**, then perform the **full
  node-by-node rolling upgrade** from doc 02 while asserting **data integrity** throughout
  (e.g. a verifier that writes monotonic/known data and reads it back from every node).
- Then perform the **full rollback** (no newer-only on-disk feature enabled) and assert no data
  loss.
- Inject faults **during** the mixed window: kill the leader, kill a follower, partition the
  network. Confirm recovery, no split-brain, no lost acknowledged writes.
- This layer is what actually proves the upgrade — most real incidents are mixed-window or
  rollback-path failures, which Layers 1–3 do not exercise.

### Layer 5 — Soak / performance

- Run the target version under **representative load for 24–72h**. Compare against a 3.6 baseline:
  - latency p50/p99 (reads and writes),
  - GC pauses / JVM pause time,
  - heap, file descriptors, connection counts (watch for leaks),
  - snapshot/txnlog growth and purge behavior.
- Soak surfaces slow leaks and tail-latency regressions that short tests miss — and it is where
  logging/metrics changes (doc 01 §2, §4) show up as cost or noise.

### Layer 6 — Staged rollout with health gates

- Roll to production in **stages** (e.g. canary → small % → broader → full), each with an explicit
  **go / no-go gate**:
  - synthetic **read/write probes** external to the ensemble,
  - the key metrics from doc 01 §4 with alert thresholds,
  - automatic halt/rollback trigger if a gate fails.
- Keep the previous artifact pinned at every stage so each stage is independently reversible.

## Putting it in sequence

```
Layer 1  build+unit+integration on all JDKs          ── fast, every change
   │
Layer 2  cross-version matrix (old/new client+server) ── before any cluster test
   │
Layer 3  functional certification on production-like cluster
   │
Layer 4  rolling upgrade + rollback + fault injection ── the gate to touch prod
   │
Layer 5  24–72h soak vs baseline
   │
Layer 6  staged rollout with health gates + canary
```

Do not promote to the next layer while the current one is red.

## Gap checklist (the ones that bite)

Use this to audit an existing test plan. Each unchecked box is a known blind spot.

- [ ] **No cross-version peer for the new version.** The matrix tests old↔old or new↔new but never
      actually pairs a 3.8 node with a 3.6 node.
- [ ] **Connectivity-only smoke.** Tests assert "connected" but never assert data correctness
      (CRUD + watch + read-back) across versions.
- [ ] **No mixed-version proof.** No test ever runs a real mixed 3.6/3.8 quorum under load.
- [ ] **No rollback proof.** Rollback is documented but never executed end-to-end with a
      data-loss assertion.
- [ ] **On-disk rollback-safety not enforced.** Nothing fails the build if a newer-only on-disk
      feature is enabled during the mixed window (see `examples/`).
- [ ] **Metrics/alerts not re-validated.** Dashboards/alerts assume 3.6 metric names/meanings;
      nobody confirmed they exist and mean the same on 3.8.
- [ ] **Logging change unverified.** Log-scraping alerts were never re-checked against real 3.8
      (Logback) output — they silently match nothing.
- [ ] **No soak.** Confidence rests on minutes-long tests; no 24–72h run vs baseline.
- [ ] **No per-stage gate / canary.** Rollout is "deploy everywhere and watch," with no automatic
      halt/rollback trigger.
- [ ] **Faults not injected during the mixed window.** Leader kill / partition only tested at a
      single version, not mid-upgrade.

## How to close the gaps (cheapest first)

1. Add **data-correctness assertions** to the existing cross-version smoke (turns Layer 2 real).
2. Add the **mixed-version + rollback** scenario with a data-integrity verifier (Layer 4).
3. Add a **config-invariant check** that enforces the rollback-safety rule in CI (`examples/`).
4. Re-validate **metrics and log-scrape alerts** against a real 3.8 node (a half-day audit).
5. Add a **soak** job and **per-stage health gates** before the production rollout.
