# Examples

Small, illustrative artifacts you can adapt to your own harness. They are **generic** — they read
a standard Apache ZooKeeper `zoo.cfg` and demonstrate patterns from docs 01–03. Nothing here is
specific to any deployment.

| File | Purpose |
|------|---------|
| [`zoo.cfg.sample`](zoo.cfg.sample) | A minimal, annotated 3.8-style `zoo.cfg` used by the example test. |
| [`test_upgrade_config_guards_example.py`](test_upgrade_config_guards_example.py) | A pytest that enforces the **rollback-safety invariant** from doc 02 §4 against a `zoo.cfg`. |
| [`upgrade-checklist.md`](upgrade-checklist.md) | A copy-pasteable rolling-upgrade / rollback runbook skeleton. |

## Running the example test

```bash
# no third-party deps required beyond pytest
pip install pytest
pytest test_upgrade_config_guards_example.py -v
```

The test is written to **pass** against `zoo.cfg.sample` (which keeps newer-only on-disk features
off) and to **fail** if you flip one of those features on — demonstrating how to make the
rollback-safety rule an enforced invariant rather than a convention.
