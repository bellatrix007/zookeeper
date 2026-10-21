# Rolling Upgrade / Rollback Runbook Skeleton (3.6 → 3.8)

A copy-pasteable checklist derived from `02-compatibility-and-rollback.md`. Fill in the blanks for
your environment. Generic Apache ZooKeeper only.

## Pre-flight

- [ ] Ensemble healthy: one leader, all followers synced (`echo stat | nc <host> <port>`).
- [ ] No pending dynamic reconfiguration.
- [ ] `dataDir` + `dataLogDir` backed up on **every** node. Backup location: `__________`
- [ ] Current (3.6) artifact pinned and reinstallable unchanged. Version/ref: `__________`
- [ ] 3.8 artifact built on target JDK(s): `__________`
- [ ] Logging config ported to Logback and staged.
- [ ] Metrics + log-scrape alerts re-validated against a real 3.8 node.
- [ ] Rollback-safety confirmed: **no newer-only on-disk feature enabled** for the mixed window.
- [ ] Synthetic read/write probe ready and alerting.

## Upgrade (followers first, leader last)

For each follower, then the leader:

- [ ] Stop node `__________` gracefully.
- [ ] Replace binaries with 3.8; **leave dataDir/dataLogDir in place**; apply Logback config.
- [ ] Start node; wait until `Following` + synced (`stat`/`mntr` on leader shows expected
      `synced_followers`).
- [ ] Per-node health gate green (synthetic read/write, latency within budget).
- [ ] Proceed to next node only after the gate passes.

Leader step:

- [ ] Trigger clean leadership change (or let it fail over on stop).
- [ ] Upgrade former leader as a follower; confirm re-election and full sync.

## Post-upgrade

- [ ] One leader, all followers synced, all nodes report 3.8.
- [ ] Bake period: `__________` (no 3.8-only feature enabled yet).
- [ ] After bake + go decision, enable any desired 3.8-only features one at a time.

## Rollback (only valid if no newer-only on-disk feature was enabled)

For each node, leader last:

- [ ] Stop 3.8 node.
- [ ] Reinstall pinned 3.6 artifact + 3.6 logging config.
- [ ] Start; confirm it reads on-disk data and rejoins quorum.
- [ ] If 3.6 cannot read the data, **restore that node's pre-upgrade backup** before starting.
- [ ] Confirm quorum healthy and data-integrity verifier passes.

## Abort criteria (halt + rollback)

- [ ] Any health gate fails and does not recover within `__________`.
- [ ] Data-integrity verifier reports a mismatch.
- [ ] Quorum cannot be maintained / repeated leader churn.
- [ ] Latency or error-rate SLO breached beyond `__________`.
