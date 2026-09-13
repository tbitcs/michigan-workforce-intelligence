from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from mijobs.canonical import sha256_hex


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    sha256: str
    path: Path
    byte_size: int
    created: bool


class ArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("digest must be a lower-case SHA-256 hex string")
        return self.root / digest[:2] / digest[2:4] / digest

    def put(self, content: bytes) -> StoredArtifact:
        digest = sha256_hex(content)
        path = self.path_for(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if sha256_hex(path.read_bytes()) != digest:
                raise OSError(f"artifact collision/corruption at {path}")
            return StoredArtifact(digest, path, len(content), False)

        with NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)
        os.replace(temp_path, path)
        return StoredArtifact(digest, path, len(content), True)

    def verify(self, digest: str) -> bool:
        path = self.path_for(digest)
        return path.exists() and sha256_hex(path.read_bytes()) == digest
