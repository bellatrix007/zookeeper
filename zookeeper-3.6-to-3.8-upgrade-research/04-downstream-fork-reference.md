# 04 — Reference: Apache 3.8.4 Patches Carried by a Public Downstream Fork

This appendix is a **concrete, real-world example** of what an organization layers on top of a
stock Apache ZooKeeper release for this exact upgrade. Every fact below is sourced from the
**public** `linkedin/zookeeper` repository on GitHub and is verifiable there — commit SHAs, pull
request numbers, branches, and tags are all public.

> Source repo: <https://github.com/linkedin/zookeeper>
> This document records only publicly visible repository facts (commits/PRs/branches/tags). It
> does not contain any private deployment, configuration, or operational detail.

It is included because it makes the abstract guidance in docs 01–03 tangible: it shows the *kinds*
of changes a serious production fork accumulates (backup, ACL/auth, pagination, metrics, TLS,
build/CI) and illustrates the **forward-port problem** — keeping a long-lived 3.6 production
branch and a new 3.8.4 base branch in sync.

## 1. The 3.8.4 base branch (`li-dev/base-3.8.4`)

Measured against the Apache tag boundary `9316c2a7` ("Prepared 3.8.4", 2024-02-12), the fork's
`li-dev/base-3.8.4` branch carries **13 patches** on top of stock 3.8.4 (branch tip `67bbe1b6`).

Reproduce:

```bash
git clone https://github.com/linkedin/zookeeper
cd zookeeper
git rev-list --count 9316c2a7..origin/li-dev/base-3.8.4   # => 13
```

| # | SHA | PR | Area / description (from the public commit subject) |
|---|-----|----|-----------------------------------------------------|
| 1 | 7f196780 | #129 | Backup: consolidate backup changes for upgrade integration |
| 2 | 716d0cdd | #132 | ACL: consolidate ACL changes for upgrade integration |
| 3 | e97800c9 | — | Cherry-pick & adapt ZOOKEEPER-2260 — `getChildren` pagination |
| 4 | 411a5f6f | #136 | Optimize paginated `getChildren` |
| 5 | aa1e240e | #138 | Ephemeral-node limit change |
| 6 | 9ef65cb6 | #134 | Add various operational metrics |
| 7 | 67bbe1b6 | #139 | Build/test configuration consolidated for upgrade integration (tip) |
| 8 | 97121578 | #126 | CI/CD pipeline configuration consolidated |
| 9 | 56a21cbd | #97 | Apache RAT (license-header) fixes |
| 10 | 9c9d96e9 | — | ZOOKEEPER-4276 — serving only with `secureClientPort` fails |
| 11 | 4d861b85 | #48 | ZOOKEEPER-4281 — allow max-length packet to be deserialized |
| 12 | ed5f4b69 | #131 | Test for LearnerHandler queue growth despite shutdown |
| 13 | 32a1e91c | — | Log remote socket address on auth failure |

Note how several of these are **cherry-picks of upstream Apache JIRAs** (ZOOKEEPER-2260, -4276,
-4281) — i.e. fixes that exist upstream but were pulled forward into this branch deliberately.

## 2. Forward-port debt: the long-lived 3.6 branch vs. the new 3.8.4 base

A production fork typically keeps shipping on an older line (`branch-3.6`, tip `860a0353`,
tag `3.6.3-35-1`) while standing up the next base (`li-dev/base-3.8.4`). Changes that land on the
old branch but are **not yet on the new base** are *forward-port debt* — they must be re-applied
to 3.8.4 before it can replace 3.6 in production.

Check whether a given commit is already on the new base:

```bash
git merge-base --is-ancestor <sha> origin/li-dev/base-3.8.4 && echo "already on base" || echo "NOT on base"
```

The following **10** commits are on `branch-3.6` but **absent** from `li-dev/base-3.8.4`
(the window starts at `556551a3` / #140):

| PR | SHA | Description (public commit subject) |
|----|-----|-------------------------------------|
| #140 | 556551a3 | Skip synchronous snapshot during leader election to unblock quorum formation |
| #143 | fbd911f9 | Enable TLSv1.3; remove default cipher overrides (ZOOKEEPER-4415 / -4912) |
| #147 | 1d05536a | Fix C-client SSL test hang on long-hostname runners (cap cert CN at 64 chars) |
| #142 | 5f9a2368 | Add SPIFFE v2 URI-SAN based principal extraction |
| #149 | 22859e1f | Support one-way SPIFFE compatibility with legacy identities |
| #153 | 9b0eeefa | Backport the native snapshot size comparer |
| #160 | d7d56cf3 | Fix paginated `getChildren` returning no children for the **root** path |
| #158 | feb36b5a | Store SPIFFE creator ACLs as legacy service principals |
| #163 | 068213ca | Add dryrun mode to `zookeeper.skipACL` |
| #151 | 860a0353 | Backport the recursive snapshot summary tool (branch tip) |

### Why this list matters for the upgrade

- **A known bug ships on the new base.** `#160` (`d7d56cf3`) fixes paginated `getChildren`
  returning no children for the **root path** — a bug in the pagination feature that *is* already
  on `li-dev/base-3.8.4` (patches #3/#4 above). So the new base carries the feature **and** its
  root-path bug until #160 is forward-ported. This is a textbook "feature landed, follow-up fix
  didn't" gap to catch during an upgrade.
- **A coherent new workstream is only on the old branch.** The three SPIFFE commits
  (`#142`, `#149`, `#158`) add server-side SPIFFE URI-SAN identity support as a group; none are on
  the new base yet. When porting debt, port related commits together, not piecemeal.
- **Correctness/availability fixes come first.** `#140` (skip synchronous snapshot during leader
  election) is an availability fix for quorum formation — exactly the class of change you forward-
  port and regression-test before promoting a new base.

## 3. Example: an operational metric added downstream

Forks commonly add operational metrics beyond the stock set. A concrete, publicly visible example
from this fork is the counter **`EPHEMERAL_NODE_LIMIT_VIOLATION`** (added with the ephemeral-node
limit change, `#138` / `aa1e240e`). The general lesson for doc 01 §4 stands: **enumerate the
metrics your fork adds or renames and make sure your dashboards/alerts account for them on the new
version.**

## 4. How to use this as a template for your own fork

1. Pin your Apache base tag and run `git rev-list --count <apache-tag>..<your-base-branch>` to get
   your true patch count.
2. Tabulate each patch by area (backup, ACL/auth, protocol, metrics, build/CI) and note which are
   upstream cherry-picks vs. local-only.
3. Diff your long-lived production branch against the new base with the
   `git merge-base --is-ancestor` check to produce your **forward-port debt** list.
4. For every debt item, classify it: correctness/availability (port first), feature follow-up fix
   (port with its feature), or isolated workstream (port as a group). Regression-test each on the
   new base before promotion.
