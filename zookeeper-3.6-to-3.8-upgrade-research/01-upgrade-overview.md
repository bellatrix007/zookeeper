# 01 — Upgrade Overview: What Changes from 3.6 to 3.8

This document summarizes the differences between the Apache ZooKeeper 3.6.x and 3.8.x server
lines that matter for an upgrade, and the overall shape of the work. It is intentionally
deployment-neutral — treat each item as "verify this against your own configuration."

## 1. Runtime / JDK

- ZooKeeper 3.8 runs on **Java 8 or newer** (JDK 8 LTS and JDK 11 LTS are the commonly tested
  targets; Java 9 and 10 are not supported).
- If you are moving your build/runtime JDK at the same time (e.g. 8 → 11), treat that as a
  separate variable and test both JDKs explicitly so a GC/latency regression is attributable.

## 2. Logging: Log4j 1.x → Logback (the biggest operational change)

- 3.8 replaced the legacy **Log4j 1.x** logging stack with **Logback**.
- Practical consequences to verify:
  - The logging configuration file changes (a `logback.xml`-style config instead of
    `log4j.properties`). Port your appenders, rolling policy, and log levels.
  - **Log line format, levels, and MDC fields can differ.** Anything that greps server logs —
    dashboards, log-scraping alerts, parsers — must be re-validated against real 3.8 output.
  - Audit logging and request/connection log lines should be diffed 3.6 vs 3.8 before rollout.
- This change does **not** affect the wire protocol or on-disk format — it is purely operational,
  but it is the most common source of "nothing errored, but our alerts went quiet" surprises.

## 3. TLS / Netty

- TLS serving uses the **Netty** connection factory
  (`serverCnxnFactory=org.apache.zookeeper.server.NettyServerCnxnFactory`), with
  `secureClientPort` for TLS clients and **Quorum TLS** for server-to-server traffic.
- The admin guide documents a **zero-downtime path to add TLS to a running non-TLS cluster**
  using port unification — useful to keep in mind if you combine the version upgrade with a TLS
  rollout (recommended: do them as separate, independently reversible changes).
- If you already run Netty + TLS on 3.6, this is not a protocol risk for the 3.8 upgrade; just
  re-confirm your keystore/truststore wiring on the new version.

## 4. Metrics / monitoring

- ZooKeeper exposes server metrics via the four-letter word `mntr`, the AdminServer, JMX, and a
  pluggable **MetricsProvider** (a Prometheus provider is available).
- Between minor versions, **metrics can be added, renamed, or change meaning.** Before rollout:
  - Enumerate the metrics your dashboards and alerts depend on.
  - Confirm each still exists (and means the same thing) on 3.8.
  - Add dashboards/alerts for any new metrics you intend to gate the rollout on (e.g. sync/diff
    in-flight counts, JVM pause time, throttling counters — whichever your build exposes).

## 5. Configuration surface to re-validate

Most 3.6 `zoo.cfg` settings carry forward, but validate these explicitly:

- **Connection factory / ports:** `serverCnxnFactory`, `secureClientPort`, `sslQuorum`,
  `client.portUnification` / `portUnification`, AdminServer (`admin.serverPort`,
  `admin.portUnification`).
- **Client port in dynamic config:** when using dynamic reconfiguration, the client port is
  expressed on the `server.N` line; a static `clientPort`/`clientPortAddress` in `zoo.cfg` can
  conflict with dynamic config. Validate your template.
- **Data/log dirs and purging:** `dataDir`, `dataLogDir`, `autopurge.snapRetainCount`,
  `autopurge.purgeInterval`.
- **Snapshot/txnlog sizing:** `snapCount`, `snapSizeLimitInKb`, `txnLogSizeLimitInKb`,
  `preAllocSize`.
- **Sessions:** `minSessionTimeout`, `maxSessionTimeout`, `localSessionsEnabled`.
- **Throttling / limits:** `globalOutstandingLimit`, `maxClientCnxns`, `maxCnxns`.
- **Extended types (TTL nodes):** `extendedTypesEnabled` (note the server-id < 255 caveat).

> On-disk format note: avoid enabling any **new, newer-only on-disk feature** (for example a
> snapshot-format or compression option that only the newer version understands) until the whole
> ensemble is upgraded and has passed its bake period. Enabling it during the mixed-version window
> is what breaks rollback — see doc 02.

## 6. Shape of the upgrade

For a typical deployment the upgrade is:

1. **Produce the 3.8 server artifact/package** your environment deploys (same packaging you use
   today, built from the 3.8 release).
2. **Carry forward configuration**, applying the deltas in §2–§5 above (logging config is the
   main rewrite).
3. **Roll it out node-by-node** per doc 02, with the old artifact pinned for rollback.
4. **Gate each stage** on the tests and signals in doc 03.

The binary/config change itself is small and mostly mechanical. The effort and risk live in
**validation and staged rollout**, not in the swap.

## 7. Pre-upgrade checklist (quick)

- [ ] Target JDK chosen and tested (8 and/or 11).
- [ ] Logging config ported to Logback; log-scrape alerts re-validated against real 3.8 output.
- [ ] Metrics dependency list re-verified on 3.8; new gating metrics have dashboards/alerts.
- [ ] `zoo.cfg` deltas in §5 reviewed; template validated.
- [ ] No newer-only on-disk feature enabled for the mixed-version window.
- [ ] dataDir/dataLogDir backup taken on every node.
- [ ] Old artifact pinned and a rollback runbook written (doc 02).
