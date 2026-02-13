"""
Shared fixtures for plugin-architecture unit tests.

Provides a session-scoped DES source copy to eliminate repeated
shutil.copytree calls (~3.5s each) across test modules.
"""

import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def shared_des_source(tmp_path_factory) -> Path:
    """
    Copy src/des once per session and return the path.

    Tests that need a DES module installed should symlink or copy
    from this shared directory instead of copying from source each time.
    The directory is READ-ONLY to tests -- never mutate its contents.
    """
    project_root = Path(__file__).resolve().parents[4]
    source_des = project_root / "src" / "des"

    shared_dir = tmp_path_factory.mktemp("shared_des")
    target_des = shared_dir / "des"
    shutil.copytree(source_des, target_des)

    return target_des
