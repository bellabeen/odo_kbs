"""Mocked S3 driver tests. Run: python -m pytest"""

from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = []
pytestmark = pytest.mark.skipif(pytest is None, reason="pytest not available")
if pytest is None:
    raise unittest.SkipTest("pytest not available")

# Stub boto3/botocore if absent so tests run without the SDK installed.
if "boto3" not in sys.modules:
    boto3 = MagicMock(name="boto3")
    sys.modules["boto3"] = boto3
if "botocore" not in sys.modules:
    botocore = MagicMock(name="botocore")
    sys.modules["botocore"] = botocore
if "botocore.config" not in sys.modules:
    sys.modules["botocore.config"] = MagicMock(name="botocore.config")
if "botocore.exceptions" not in sys.modules:
    exc_mod = MagicMock(name="botocore.exceptions")

    class ClientError(Exception):
        def __init__(self, response=None, operation_name=""):
            self.response = response or {}
            super().__init__(str(self.response))

    exc_mod.ClientError = ClientError
    sys.modules["botocore.exceptions"] = exc_mod

from storage_core.exceptions import ObjectNotFoundError, StorageConfigurationError  # noqa: E402
from storage_s3.s3_driver import S3StorageDriver  # noqa: E402


def _driver(bucket: str = "test-bucket") -> S3StorageDriver:
    drv = S3StorageDriver({"bucket": bucket, "region": "us-east-1"})
    drv._client = MagicMock()
    return drv


def test_requires_bucket() -> None:
    with pytest.raises(StorageConfigurationError):
        S3StorageDriver({})


def test_write_put_object() -> None:
    drv = _driver()
    drv._client.put_object.return_value = {"ETag": '"abc"', "VersionId": "v1"}
    drv._client.head_object.return_value = {
        "ContentLength": 3,
        "ContentType": "application/octet-stream",
        "ETag": '"abc"',
        "Metadata": {"sha256": "abc"},
        "LastModified": None,
        "StorageClass": "STANDARD",
        "ServerSideEncryption": None,
        "VersionId": "v1",
    }
    meta = drv.write("a.txt", b"foo")
    drv._client.put_object.assert_called_once()
    assert meta.object_key == "a.txt"
    assert meta.checksum == "abc"


def test_stream_yields_chunks() -> None:
    body = MagicMock()
    body.read.side_effect = [b"he", b"llo", b""]
    drv = _driver()
    drv._client.get_object.return_value = {"Body": body}
    chunks = list(drv.stream("x", chunk_size=2))
    assert chunks == [b"he", b"llo"]
    body.close.assert_called_once()


def test_read_missing_raises() -> None:
    botocore_exc = sys.modules["botocore.exceptions"]
    err = botocore_exc.ClientError({"Error": {"Code": "NoSuchKey"}})
    drv = _driver()
    drv._client.get_object.side_effect = err
    with pytest.raises(ObjectNotFoundError):
        drv.read("nope")


def test_exists_true_false() -> None:
    drv = _driver()
    drv._client.head_object.return_value = {}
    assert drv.exists("a") is True

    botocore_exc = sys.modules["botocore.exceptions"]
    drv._client.head_object.side_effect = botocore_exc.ClientError(
        {"Error": {"Code": "404"}}
    )
    assert drv.exists("b") is False


def test_delete_idempotent() -> None:
    drv = _driver()
    drv.delete("gone")  # no raise
    drv._client.delete_object.assert_called_once()


def test_list_pagination() -> None:
    drv = _driver()
    drv._client.list_objects_v2.side_effect = [
        {"Contents": [{"Key": "a"}, {"Key": "b"}], "IsTruncated": True,
         "NextContinuationToken": "tok"},
        {"Contents": [{"Key": "c"}], "IsTruncated": False},
    ]
    keys = list(drv.list())
    assert keys == ["a", "b", "c"]
    assert drv._client.list_objects_v2.call_count == 2


def test_generate_url_get_put() -> None:
    drv = _driver()
    drv._client.generate_presigned_url.side_effect = [
        "https://example/get", "https://example/put",
    ]
    assert drv.generate_url("k", method="GET") == "https://example/get"
    assert drv.generate_url("k", method="PUT") == "https://example/put"
    calls = drv._client.generate_presigned_url.call_args_list
    assert calls[0][0][0] == "get_object"
    assert calls[1][0][0] == "put_object"


def test_multipart_abort_on_failure() -> None:
    drv = _driver()
    drv._client.create_multipart_upload.return_value = {"UploadId": "U1"}
    drv._client.upload_part.side_effect = RuntimeError("boom")
    big = io.BytesIO(b"x" * (S3_CHUNK := 8 * 1024 * 1024 + 1))
    with pytest.raises(Exception):
        drv._multipart_write("big", big, {})
    drv._client.abort_multipart_upload.assert_called_once_with(
        Bucket="test-bucket", Key="big", UploadId="U1",
    )
