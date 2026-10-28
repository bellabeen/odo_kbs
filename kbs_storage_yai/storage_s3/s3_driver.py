"""S3 provider. boto3. ADR-001 (SAL), ADR-004 (streaming), ADR-007 (IAM first).

Config keys:
  bucket (required), region, endpoint_url, access_key, secret_key,
  storage_class, server_side_encryption, kms_key_id.

Credentials: IAM role / env / instance profile by default (ADR-007).
Explicit access_key+secret_key only as fallback.
"""

from __future__ import annotations

import logging
from typing import Any, BinaryIO, Iterator, Optional, Union

from storage_core.domain import ObjectMetadata
from storage_core.exceptions import (
    ObjectNotFoundError,
    StorageConfigurationError,
    StorageOperationError,
)
from storage_core.interfaces import StorageBackend

_logger = logging.getLogger(__name__)

Readable = Union[bytes, BinaryIO, Iterator[bytes]]
_CHUNK = 8 * 1024 * 1024  # 8 MiB multipart part


class S3StorageDriver(StorageBackend):
    """S3 backend with multipart upload, streaming, presigned URLs."""

    backend_code = "s3"

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self.bucket: str = cfg.get("bucket", "")
        if not self.bucket:
            raise StorageConfigurationError(
                "storage_s3 requires 'bucket'", backend=self.backend_code,
            )
        self.storage_class: str = cfg.get("storage_class", "STANDARD")
        self.sse: Optional[str] = cfg.get("server_side_encryption")  # AES256 | aws:kms
        self.kms_key_id: Optional[str] = cfg.get("kms_key_id")

        try:
            import boto3  # noqa: PLC0415
            from botocore.config import Config as BotoConfig  # noqa: PLC0415
        except ImportError as err:
            raise StorageConfigurationError(
                "boto3 not installed — pip install boto3",
                backend=self.backend_code, cause=err,
            ) from err

        # ADR-007: no keys -> default credential chain (IAM role > env > profile).
        session_kwargs: dict[str, Any] = {"region_name": cfg.get("region")}
        if cfg.get("access_key"):
            _logger.warning(
                "storage_s3: static access key in use — prefer IAM role (ADR-007)"
            )
            session_kwargs.update(
                aws_access_key_id=cfg["access_key"],
                aws_secret_access_key=cfg["secret_key"],
            )
        session = boto3.Session(**session_kwargs)
        client_kwargs: dict[str, Any] = {
            "config": BotoConfig(retries={"max_attempts": 5, "mode": "adaptive"}),
        }
        if cfg.get("endpoint_url"):  # S3-compatible (MinIO, Ceph, ...)
            client_kwargs["endpoint_url"] = cfg["endpoint_url"]
        self._client = session.client("s3", **client_kwargs)

    # ---------- helpers ----------

    def _extra_args(self, mime: Optional[str] = None) -> dict[str, Any]:
        args: dict[str, Any] = {"StorageClass": self.storage_class}
        if mime:
            args["ContentType"] = mime
        if self.sse:
            args["ServerSideEncryption"] = self.sse
            if self.kms_key_id:
                args["SSEKMSKeyId"] = self.kms_key_id
        return args

    def _wrap(self, op: str, key: str, err: Exception) -> StorageOperationError:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        if isinstance(err, ClientError):
            code = err.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return ObjectNotFoundError(key, backend=self.backend_code, cause=err)
        return StorageOperationError(
            f"S3 {op} failed on s3://{self.bucket}/{key}: {err}",
            backend=self.backend_code, key=key, cause=err,
        )

    # ---------- interface ----------

    def write(
        self,
        key: str,
        payload: Readable,
        *,
        mime: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ObjectMetadata:
        extra = self._extra_args(mime)
        if metadata:
            extra["Metadata"] = {str(k): str(v) for k, v in metadata.items()}
        try:
            if isinstance(payload, (bytes, bytearray)):
                self._client.put_object(
                    Bucket=self.bucket, Key=key, Body=bytes(payload), **extra,
                )
            else:
                # Multipart streaming upload (read()able or chunk iterator).
                self._multipart_write(key, payload, extra)
        except Exception as err:
            raise self._wrap("write", key, err) from err
        _logger.info("stored s3://%s/%s", self.bucket, key)
        return self.head(key)

    def _multipart_write(self, key: str, src: Readable, extra: dict) -> None:
        mpu = self._client.create_multipart_upload(
            Bucket=self.bucket, Key=key, **extra,
        )
        upload_id = mpu["UploadId"]
        parts: list[dict] = []
        buf = bytearray()
        part_no = 0

        def _as_iter(p: Readable) -> Iterator[bytes]:
            if hasattr(p, "read"):
                while True:
                    block = p.read(_CHUNK)  # type: ignore[union-attr]
                    if not block:
                        return
                    yield block
            else:
                yield from p  # type: ignore[misc]

        try:
            for block in _as_iter(src):
                buf.extend(block)
                while len(buf) >= _CHUNK:
                    part_no += 1
                    chunk = bytes(buf[:_CHUNK])
                    del buf[:_CHUNK]
                    resp = self._client.upload_part(
                        Bucket=self.bucket, Key=key, UploadId=upload_id,
                        PartNumber=part_no, Body=chunk,
                    )
                    parts.append({"PartNumber": part_no, "ETag": resp["ETag"]})
            if buf:
                part_no += 1
                resp = self._client.upload_part(
                    Bucket=self.bucket, Key=key, UploadId=upload_id,
                    PartNumber=part_no, Body=bytes(buf),
                )
                parts.append({"PartNumber": part_no, "ETag": resp["ETag"]})
            self._client.complete_multipart_upload(
                Bucket=self.bucket, Key=key, UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except Exception:
            self._client.abort_multipart_upload(
                Bucket=self.bucket, Key=key, UploadId=upload_id,
            )
            raise

    def read(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except Exception as err:
            raise self._wrap("read", key, err) from err

    def stream(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
        except Exception as err:
            raise self._wrap("stream", key, err) from err
        body = resp["Body"]
        try:
            while True:
                block = body.read(chunk_size)
                if not block:
                    return
                yield block
        finally:
            body.close()

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as err:
            raise self._wrap("delete", key, err) from err

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def head(self, key: str) -> ObjectMetadata:
        try:
            r = self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception as err:
            raise self._wrap("head", key, err) from err
        return ObjectMetadata(
            backend=self.backend_code,
            bucket=self.bucket,
            object_key=key,
            checksum=(r.get("Metadata") or {}).get("sha256",
                      r.get("ETag", "").strip('"')),
            size=r.get("ContentLength", 0),
            mime=r.get("ContentType", "application/octet-stream"),
            etag=(r.get("ETag") or "").strip('"'),
            version_id=r.get("VersionId"),
            storage_class=r.get("StorageClass", self.storage_class),
            encryption=r.get("ServerSideEncryption"),
            created=None,
            modified=r.get("LastModified"),
        )

    def copy(self, source: str, target: str) -> ObjectMetadata:
        try:
            self._client.copy_object(
                Bucket=self.bucket, Key=target,
                CopySource={"Bucket": self.bucket, "Key": source},
                **self._extra_args(),
            )
        except Exception as err:
            raise self._wrap("copy", source, err) from err
        return self.head(target)

    def move(self, source: str, target: str) -> ObjectMetadata:
        meta = self.copy(source, target)
        self.delete(source)
        return meta

    def list(self, prefix: str = "", limit: Optional[int] = None) -> Iterator[str]:
        kwargs: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
        if limit is not None:
            kwargs["MaxKeys"] = min(limit, 1000)
        seen = 0
        while True:
            try:
                resp = self._client.list_objects_v2(**kwargs)
            except Exception as err:
                raise self._wrap("list", prefix, err) from err
            for obj in resp.get("Contents", []):
                yield obj["Key"]
                seen += 1
                if limit is not None and seen >= limit:
                    return
            if not resp.get("IsTruncated"):
                return
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]

    def checksum(self, key: str) -> str:
        return self.head(key).checksum

    def generate_url(
        self, key: str, *, expires_in: int = 3600, method: str = "GET",
    ) -> str:
        op = "get_object" if method == "GET" else "put_object"
        try:
            return self._client.generate_presigned_url(
                op,
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception as err:
            raise self._wrap("generate_url", key, err) from err

    def healthcheck(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False
