from pathlib import Path

from mijobs.artifact_store import ArtifactStore


def test_artifact_store_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    first = store.put(b"official data")
    second = store.put(b"official data")
    assert first.sha256 == second.sha256
    assert first.created is True
    assert second.created is False
    assert store.verify(first.sha256)
    assert first.path.read_bytes() == b"official data"
