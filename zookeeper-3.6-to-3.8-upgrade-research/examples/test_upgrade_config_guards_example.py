"""
Illustrative config-invariant test for a ZooKeeper 3.6 -> 3.8 rolling upgrade.

It enforces the rollback-safety rule from 02-compatibility-and-rollback.md (section 4):

    During the mixed-version window, no "newer-only on-disk feature" may be enabled,
    because an older binary might be unable to read what a newer node wrote -- which
    would break the rollback path.

This is a GENERIC example. It parses a standard Apache ZooKeeper `zoo.cfg` and asserts a
set of invariants. Adapt ON_DISK_FORMAT_KEYS to whatever your specific build documents as
changing the on-disk / serialization format.

Run:
    pip install pytest
    pytest test_upgrade_config_guards_example.py -v
"""

import os
import pytest


# ---------------------------------------------------------------------------
# Config: the set of keys that (for the purpose of this example) represent a
# "newer-only on-disk feature" which must stay OFF during a mixed-version window.
#
# Replace / extend this with the exact keys your build documents as changing the
# on-disk or serialization format. The names below are ILLUSTRATIVE placeholders.
# ---------------------------------------------------------------------------
ON_DISK_FORMAT_KEYS = {
    # key_name: value(s) that are considered "rollback-safe" (feature OFF)
    "snapshot.compression.method": {None, "", "none", "uncompressed"},
}

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_CFG = os.path.join(HERE, "zoo.cfg.sample")


def parse_zoo_cfg(path):
    """Parse a zoo.cfg into a dict of key -> value, ignoring comments/blanks."""
    cfg = {}
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip()
    return cfg


@pytest.fixture
def cfg():
    return parse_zoo_cfg(SAMPLE_CFG)


# --- Invariant 1: rollback safety -----------------------------------------

def test_no_newer_only_on_disk_feature_enabled(cfg):
    """Fails if any on-disk-format feature is enabled during the mixed window."""
    violations = []
    for key, safe_values in ON_DISK_FORMAT_KEYS.items():
        value = cfg.get(key)  # None if unset -> rollback-safe
        if value is not None and value.lower() not in {
            v for v in safe_values if isinstance(v, str)
        }:
            violations.append(f"{key}={value}")
    assert not violations, (
        "Newer-only on-disk feature(s) enabled during a mixed-version window; "
        f"this breaks rollback: {violations}"
    )


# --- Invariant 2: basic quorum sanity --------------------------------------

def test_quorum_is_odd_and_at_least_three(cfg):
    """A production ensemble should have an odd number of >= 3 servers."""
    servers = [k for k in cfg if k.startswith("server.")]
    assert len(servers) >= 3, "Expected at least 3 quorum members for HA"
    assert len(servers) % 2 == 1, "Quorum size should be odd to avoid split votes"


# --- Invariant 3: data durability basics -----------------------------------

def test_data_dirs_and_autopurge_present(cfg):
    """dataDir must be set; autopurge should be configured to bound disk growth."""
    assert cfg.get("dataDir"), "dataDir must be set"
    assert "autopurge.snapRetainCount" in cfg, "autopurge.snapRetainCount should be set"
    retain = int(cfg.get("autopurge.snapRetainCount", "0"))
    assert retain >= 3, "Keep at least 3 snapshots so recovery/rollback has headroom"


# --- Demonstration that the guard actually fails when the feature is on -----

def test_guard_trips_when_feature_enabled(tmp_path):
    """Sanity: enabling a newer-only on-disk feature must fail invariant 1."""
    bad = tmp_path / "zoo.cfg"
    bad.write_text(
        "dataDir=/var/lib/zookeeper/data\n"
        "autopurge.snapRetainCount=5\n"
        "server.1=zk1:2888:3888\n"
        "server.2=zk2:2888:3888\n"
        "server.3=zk3:2888:3888\n"
        "snapshot.compression.method=gz\n",
        encoding="utf-8",
    )
    cfg = parse_zoo_cfg(str(bad))
    with pytest.raises(AssertionError):
        test_no_newer_only_on_disk_feature_enabled(cfg)
