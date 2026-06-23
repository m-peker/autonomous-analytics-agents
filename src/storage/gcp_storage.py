"""Google Cloud Storage adapter for file persistence on GCP.

When deployed on Cloud Run, this module replaces local disk I/O with
Cloud Storage operations.  It auto-detects the GCP environment and
falls back to local storage when running outside GCP.

Usage:
    from src.storage.gcp_storage import get_storage

    storage = get_storage()
    storage.upload("data/uploads/report.xlsx", file_bytes)
    storage.download("data/outputs/report.pdf")
"""
from __future__ import annotations

import io
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)


# ── Abstract storage interface ───────────────────────────────────────────────

class StorageBackend(ABC):
    """Unified interface for file I/O — local or cloud."""

    @abstractmethod
    def upload(self, path: str, data: bytes | BinaryIO) -> str:
        """Store a file. Returns the storage path/URI."""
        ...

    @abstractmethod
    def download(self, path: str) -> bytes:
        """Retrieve file contents as bytes."""
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        ...

    @property
    @abstractmethod
    def is_cloud(self) -> bool:
        ...


# ── Local filesystem backend ─────────────────────────────────────────────────

class LocalStorage(StorageBackend):
    """Read/write to the local filesystem."""

    @property
    def is_cloud(self) -> bool:
        return False

    def upload(self, path: str, data: bytes | BinaryIO) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_bytes(data.read())
        logger.debug("Local upload → %s", p)
        return str(p)

    def download(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def delete(self, path: str) -> None:
        Path(path).unlink(missing_ok=True)


# ── Google Cloud Storage backend ─────────────────────────────────────────────

class GCSStorage(StorageBackend):
    """Read/write to Google Cloud Storage buckets."""

    def __init__(self, bucket_name: str) -> None:
        self._bucket_name = bucket_name
        self._client = None

    @property
    def is_cloud(self) -> bool:
        return True

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client()
        return self._client

    def _get_bucket(self):
        return self._get_client().bucket(self._bucket_name)

    def upload(self, path: str, data: bytes | BinaryIO) -> str:
        blob = self._get_bucket().blob(path)
        if isinstance(data, bytes):
            blob.upload_from_string(data)
        else:
            blob.upload_from_file(data, rewind=True)
        gs_uri = f"gs://{self._bucket_name}/{path}"
        logger.info("GCS upload → %s", gs_uri)
        return gs_uri

    def download(self, path: str) -> bytes:
        blob = self._get_bucket().blob(path)
        return blob.download_as_bytes()

    def exists(self, path: str) -> bool:
        return self._get_bucket().blob(path).exists()

    def delete(self, path: str) -> None:
        self._get_bucket().blob(path).delete()


# ── Auto-detecting factory ───────────────────────────────────────────────────

_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return the appropriate storage backend for the current environment.

    Detection logic:
      1. GCS_BUCKET_NAME env var set → GCS storage
      2. Running on Cloud Run (K_SERVICE env var) + GCS_BUCKET_NAME → GCS
      3. Otherwise → local filesystem
    """
    global _storage

    if _storage is not None:
        return _storage

    bucket = os.getenv("GCS_BUCKET_NAME", "")
    is_cloud_run = bool(os.getenv("K_SERVICE", ""))

    if bucket:
        logger.info("🌐 Storage: Google Cloud Storage (bucket=%s)", bucket)
        _storage = GCSStorage(bucket)
    elif is_cloud_run:
        logger.warning(
            "Running on Cloud Run but GCS_BUCKET_NAME not set. "
            "Using local storage (will be ephemeral!)."
        )
        _storage = LocalStorage()
    else:
        logger.info("💻 Storage: Local filesystem")
        _storage = LocalStorage()

    return _storage


def reset_storage() -> None:
    """Reset the storage singleton (useful for testing)."""
    global _storage
    _storage = None
