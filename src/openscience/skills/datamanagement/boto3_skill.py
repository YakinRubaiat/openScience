"""boto3 skill: S3 object operations via optional boto3 dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import optional_import, result, skill_run


def _client():
    boto3 = optional_import("boto3")
    return boto3.client("s3")


def list_objects(bucket: str, prefix: str = "", max_keys: int = 1000) -> dict[str, Any]:
    """List objects in an S3 bucket under a prefix."""
    s3 = _client()
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=int(max_keys))
    contents = resp.get("Contents", [])
    return result(
        bucket=bucket,
        prefix=prefix,
        n_objects=len(contents),
        truncated=bool(resp.get("IsTruncated", False)),
        objects=[
            {"key": o["Key"], "size_bytes": int(o["Size"]),
             "last_modified": o["LastModified"].isoformat()}
            for o in contents
        ],
    )


def upload(file_path: str, bucket: str, key: str | None = None) -> dict[str, Any]:
    """Upload a local file to S3. Returns the object ETag."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    key = key or path.name
    s3 = _client()
    resp = s3.upload_file(str(path), bucket, key)
    head = s3.head_object(Bucket=bucket, Key=key)
    return result(
        bucket=bucket, key=key,
        etag=str(head.get("ETag", "")).strip('"'),
        size_bytes=int(head["ContentLength"]),
    )


def download(bucket: str, key: str, dest_path: str) -> dict[str, Any]:
    """Download an S3 object to a local path."""
    s3 = _client()
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(dest))
    return result(bucket=bucket, key=key, dest_path=str(dest),
                  size_bytes=int(dest.stat().st_size))


_OPS = {"list_objects": list_objects, "upload": upload, "download": download}

run = skill_run(_OPS)
register_skill("boto3", run)
