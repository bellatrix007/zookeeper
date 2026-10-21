# 02 — Compatibility and Rollback

This document covers what is compatible with what across the 3.6 → 3.8 boundary, the
node-by-node rolling-upgrade procedure, and the rules that keep rollback working. It describes
**upstream Apache ZooKeeper** behavior only.

## 1. Compatibility model

### Client ↔ server (wire protocol)

- Apache ZooKeeper maintains **client/server wire compatibility across the 3.4–3.8 lines**. An
  existing client built against 3.5/3.6/3.7 continues to talk to a **3.8 server**.
- The practical rule is **"old client ↔ new server" is safe**; the reverse ("new client ↔ old
  server") is only safe for features the old server understands. **Feature-gated client calls**
  (e.g. TTL nodes, persistent/recursive watches, certain multi/transaction ops, newer ACL
  schemes) require a **server that is new enough**, so during a rolling upgrade a client may hit a
  not-yet-upgraded node that rejects a newer op.
- Implication: don't adopt new **client-side** features until every server is on 3.8.

### Server ↔ server (quorum)

- A **rolling upgrade from 3.6 to 3.8 is supported** — mixed 3.6/3.8 members form a quorum during
  the upgrade window long enough to move one node at a time.
- Keep the mixed window **as short as practical** and never run split-version as a steady state.

### On-disk format (snapshots & txn logs)

- The 3.8 server reads 3.6 snapshots/txn logs, so an upgraded node recovers from existing data.
- **Rollback depends on the older binary being able to read what the newer node wrote.** That is
  guaranteed **only if you did not enable a newer-only on-disk feature** during the mixed window
  (see §4).

## 2. Rolling upgrade procedure (generic)

Assume an ensemble of `2f+1` nodes with one leader.

**Pre-flight**

1. Confirm the ensemble is healthy: one leader, all followers `synced`
   (`echo stat | nc host port`, or `mntr`). No pending reconfig.
2. **Back up `dataDir` and `dataLogDir`** (latest snapshot + trailing txn logs) on **every** node.
3. Pin the **current (3.6) artifact** so you can reinstall it unchanged.
4. Freeze config changes and any dynamic reconfiguration for the duration of the upgrade.

**Per-node loop (followers first, leader last)**

1. Pick a **follower**. Stop the ZooKeeper process gracefully.
2. Replace the binaries with 3.8. **Leave `dataDir`/`dataLogDir` in place.** Apply the ported
   Logback logging config.
3. Start the node. Wait until it **rejoins and syncs**:
   - `echo stat` shows it `Following` with a non-stale `zxid`,
   - `mntr` shows `zk_synced_followers` back to the expected count on the leader,
   - no errors in the (now Logback) server log.
4. Run your **per-node health gate** (synthetic read/write, latency within budget). Only then
   proceed to the next follower.
5. Upgrade the **leader last**. Either let it fail over naturally on stop, or trigger a clean
   leadership change first; then upgrade it as a follower and let the ensemble re-elect.

**Post-upgrade**

1. Confirm one leader, all followers synced, all nodes reporting 3.8.
2. **Bake** at the current version before enabling any 3.8-only feature (§4).

## 3. Rollback procedure (generic)

Rollback is the rolling procedure in reverse, with one hard precondition: **no newer-only on-disk
feature was enabled** (§4).

1. Stop a 3.8 node. Reinstall the **pinned 3.6 artifact**. Restore the matching logging config.
2. Start it; confirm it reads the on-disk data and rejoins the quorum.
3. Repeat node-by-node. Leader last, same as the upgrade.
4. If a node's 3.6 binary **cannot read** the on-disk data (because a newer on-disk feature was
   enabled), restore that node's **pre-upgrade `dataDir` backup** before starting 3.6 — this is
   why the pre-flight backup is mandatory.

> Prefer **roll-forward-fix** over rollback once the ensemble is fully on 3.8 and has written
> meaningful new data; rollback is primarily a safety net for the **mixed-version window**.

## 4. The rollback-safety rule (most important)

**During the mixed-version window, do not enable any configuration or feature that changes the
on-disk format in a way older binaries cannot read.**

- Examples of the *class* of settings to hold back: new snapshot-format or snapshot-compression
  options, any flag documented as "new on-disk/serialization format," or data types only the
  newer server understands.
- Keep such settings at their **rollback-safe default (off/unset)** until:
  1. every node is on 3.8, **and**
  2. the bake period has passed and you have accepted you will not roll back.
- Make this an **enforced invariant**, not a convention — assert it in config validation/CI so a
  well-meaning change can't quietly strip your rollback path (see `examples/`).

## 5. Compatibility test matrix (what to actually exercise)

| Axis | Cases to cover |
|------|----------------|
| Old client ↔ new server | Each supported client line (3.5/3.6/3.7) against a 3.8 server: connect, CRUD, watches, ACL/auth, session expiry. |
| New client ↔ old server | A 3.8 client against a 3.6 server: confirm baseline ops work and that **feature-gated ops fail cleanly** (don't corrupt). |
| Mixed quorum | 3.6+3.8 members forming a quorum: writes replicate, leader election works, a follower can sync from either. |
| Rolling upgrade | Full node-by-node upgrade with continuous read/write load and data-integrity assertions. |
| Rollback | Full node-by-node rollback **without** any newer-only on-disk feature enabled; assert no data loss. |
| Fault injection | Kill leader/follower and partition **during** the mixed window; confirm recovery and no split-brain. |

Doc 03 turns this matrix into a layered test plan and a gap checklist.
