from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore

try:
    import pyarrow.parquet as pq  # type: ignore
    import pyarrow as pa  # type: ignore
except Exception:  # pragma: no cover
    pq = None  # type: ignore
    pa = None  # type: ignore


def _parse_s3_uri(uri: str) -> Tuple[str, str]:
    # s3://bucket/key
    assert uri.startswith("s3://")
    no_scheme = uri[len("s3://") :]
    bucket, _, key = no_scheme.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid s3 uri: {uri}")
    return bucket, key


def read_bytes(uri: str) -> bytes:
    """Read bytes from local path or s3://bucket/key.

    This is intentionally minimal and avoids heavy dependencies.
    """
    if uri.startswith("s3://"):
        if boto3 is None:
            raise RuntimeError("boto3 is required to read from s3:// URIs.")
        bucket, key = _parse_s3_uri(uri)
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    # file:// or plain path
    if uri.startswith("file://"):
        uri = uri[len("file://") :]
    with open(uri, "rb") as f:
        return f.read()


def download_to_file(uri: str, dst_path: str) -> str:
    """Download a URI to a local file and return the path."""
    data = read_bytes(uri)
    with open(dst_path, "wb") as f:
        f.write(data)
    return dst_path


def load_manifest(uri: str) -> Dict[str, Any]:
    """Load a dataset manifest JSON.

    Expected minimal format:
    {
      "files": ["s3://bucket/path/part-000.parquet", "..."],
      "format": "parquet"
    }
    """
    raw = read_bytes(uri)
    return json.loads(raw.decode("utf-8"))


def read_parquet(uri: str) -> pd.DataFrame:
    """Read a parquet file from local or S3 (via boto3 download).

    We avoid relying on pandas' remote filesystem integrations to keep images light.
    """
    if pq is None:
        # fallback to pandas, might work for local paths
        return pd.read_parquet(uri)

    if uri.startswith("s3://"):
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            download_to_file(uri, tmp_path)
            table = pq.read_table(tmp_path)
            return table.to_pandas()
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # local
    table = pq.read_table(uri if not uri.startswith("file://") else uri[len("file://") :])
    return table.to_pandas()


def load_dataset_from_uri(uri: str) -> pd.DataFrame:
    """Load a dataset from either:
    - a Parquet file URI (.parquet)
    - a manifest JSON (.json) listing parquet files
    """
    if uri.endswith(".parquet"):
        return read_parquet(uri)
    if uri.endswith(".json"):
        manifest = load_manifest(uri)
        files = manifest.get("files") or manifest.get("paths") or []
        if not files:
            raise ValueError(f"Manifest has no files/paths: {uri}")
        frames = [read_parquet(f) for f in files]
        return pd.concat(frames, ignore_index=True)
    # last resort: try pandas parquet
    return pd.read_parquet(uri)
