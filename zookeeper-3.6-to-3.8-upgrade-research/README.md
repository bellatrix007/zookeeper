# Apache ZooKeeper 3.6 → 3.8 Upgrade Research

A vendor-neutral, open-source–only research pack for planning and validating an upgrade of an
Apache ZooKeeper **server** ensemble from the **3.6.x** line to the **3.8.x** line (validated
against 3.8.4). It focuses on what changes between the two releases, how to roll the upgrade out
safely with a working rollback path, and how to test it so nothing breaks after rollout.

All of docs 01–03 and the examples are about **upstream Apache ZooKeeper** and are drawn from the
official Apache documentation and release notes — nothing in them is specific to any particular
deployment, company, or fork. Doc 04 is a separate, clearly-labeled **reference appendix** that
cites only **publicly visible** facts (commits, PRs, branches, tags) from the open-source
`linkedin/zookeeper` repository, as a concrete real-world example of the forward-port problem.

## Contents

| Doc | What it covers |
|-----|----------------|
| [`01-upgrade-overview.md`](01-upgrade-overview.md) | What actually changes 3.6 → 3.8 (logging, JDK, TLS/Netty, metrics, config), and the shape/scope of the upgrade. |
| [`02-compatibility-and-rollback.md`](02-compatibility-and-rollback.md) | Client/server and quorum compatibility, the rolling-upgrade procedure, and the rollback-safety rules for the mixed-version window. |
| [`03-testing-strategy.md`](03-testing-strategy.md) | The test layers that give confidence (unit → cross-version → functional → mixed-version/rollback → soak → staged rollout), plus a gap checklist. |
| [`04-downstream-fork-reference.md`](04-downstream-fork-reference.md) | Reference appendix: a real-world example of the patches a public downstream fork (`linkedin/zookeeper`) carries on top of Apache 3.8.4, and the forward-port debt vs. its long-lived 3.6 branch — sourced entirely from the public repo. |
| [`examples/`](examples/) | A small, illustrative config-invariant test and a sample upgrade checklist you can adapt. |

## TL;DR

- **It is a server-side upgrade.** ZooKeeper keeps client↔server wire compatibility across
  3.4–3.8, so existing clients generally keep working against a 3.8 server without a client bump.
- **The headline change is logging:** 3.8 moved from Log4j 1.x to **Logback**. This is the most
  likely source of silent operational breakage (log file/format/levels → log-scraping alerts).
- **Rolling upgrade 3.6 → 3.8 is supported** (one node at a time, quorum stays up).
- **Rollback is safe only if you do not turn on any newer, on-disk-format feature** during the
  mixed-version window — otherwise an older binary may be unable to read what a newer node wrote.
- **The real risk is in validation, not in the code change.** Budget most of the effort for the
  cross-version, mixed-version/rollback, and soak testing described in doc 03.

## How to use this pack

1. Read `01` to size the change for your deployment and list the config/behavior deltas you must
   re-verify.
2. Use `02` to write your concrete rolling-upgrade and rollback runbooks.
3. Use `03` to build (or close the gaps in) your test plan before touching production.

## References

- ZooKeeper 3.8 Administrator's Guide — <https://zookeeper.apache.org/doc/r3.8.4/zookeeperAdmin.html>
- ZooKeeper 3.8 Getting Started / Programmer's Guide — <https://zookeeper.apache.org/doc/r3.8.4/>
- Apache ZooKeeper releases & release notes — <https://zookeeper.apache.org/releases.html>
