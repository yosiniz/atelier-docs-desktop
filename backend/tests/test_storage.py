import os
import time
import uuid

from backend.app import storage


def test_safe_filename_strips_paths_and_control_characters():
    assert storage.safe_filename("../../gizli\\rapor?.pdf") == "rapor_.pdf"
    assert "/" not in storage.safe_filename("../dosya.pdf")
    assert "\\" not in storage.safe_filename("..\\dosya.pdf")


def test_cleanup_removes_only_old_uuid_workspaces(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "WORKSPACE_ROOT", tmp_path)
    old_workspace = tmp_path / uuid.uuid4().hex
    recent_workspace = tmp_path / uuid.uuid4().hex
    unrelated = tmp_path / "kullanici-dosyasi"
    old_workspace.mkdir()
    recent_workspace.mkdir()
    unrelated.mkdir()
    old_time = time.time() - 10_000
    os.utime(old_workspace, (old_time, old_time))

    assert storage.cleanup_stale_workspaces(max_age_seconds=3_600) == 1
    assert not old_workspace.exists()
    assert recent_workspace.exists()
    assert unrelated.exists()
