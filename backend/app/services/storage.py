import os
import time
import logging
from typing import Dict, Any
try:
    import boto3
    from botocore.exceptions import ClientError, EndpointConnectionError
except ImportError:
    boto3 = None # type: ignore
    class ClientError(Exception): pass # type: ignore
    class EndpointConnectionError(Exception): pass # type: ignore
from backend.app.config import settings

logger = logging.getLogger("marketai.storage")

class StorageService:
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.local_fallback_dir = "/tmp/marketai_storage"
        os.makedirs(self.local_fallback_dir, exist_ok=True)
        self.use_fallback = False

        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        except Exception as e:
            logger.warning(f"S3 client initialization warning: {e}. Falling back to local storage.")
            self.client = None
            self.use_fallback = True

    def resilient_init(self, max_retries: int = 3, initial_delay: float = 1.0) -> bool:
        """
        Attempts to ensure S3/MinIO bucket readiness with exponential backoff on startup.
        If S3 is permanently unavailable, switches seamlessly to local storage cache.
        """
        if self.use_fallback or not self.client:
            logger.info("Storage operating in local filesystem mode.")
            return True

        delay = initial_delay
        for attempt in range(1, max_retries + 1):
            try:
                self.client.head_bucket(Bucket=self.bucket)
                logger.info(f"S3 bucket '{self.bucket}' verified successfully.")
                self.use_fallback = False
                return True
            except ClientError as ce:
                error_code = ce.response.get("Error", {}).get("Code")
                if error_code in ("404", "NoSuchBucket"):
                    try:
                        self.client.create_bucket(Bucket=self.bucket)
                        logger.info(f"Created S3 bucket '{self.bucket}'.")
                        self.use_fallback = False
                        return True
                    except Exception as create_err:
                        logger.warning(f"Could not create bucket: {create_err}")
                else:
                    logger.warning(f"S3 head_bucket attempt {attempt} returned: {ce}")
            except (EndpointConnectionError, Exception) as conn_err:
                logger.warning(f"S3 connection attempt {attempt}/{max_retries} failed: {conn_err}")

            time.sleep(delay)
            delay *= 2.0

        logger.warning(f"S3 service unreachable after {max_retries} attempts. Enabling local fallback storage at {self.local_fallback_dir}")
        self.use_fallback = True
        return False

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Uploads bytes to S3/MinIO, or safely writes to local fallback storage.
        """
        if not self.use_fallback and self.client:
            try:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type
                )
                return key
            except Exception as e:
                logger.warning(f"S3 put_object failed ({e}). Writing to local storage fallback.")

        # Local fallback execution
        safe_name = key.replace("/", "_")
        local_path = os.path.join(self.local_fallback_dir, safe_name)
        with open(local_path, "wb") as f:
            f.write(data)
        return key

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generates a pre-signed S3 download URL, or falls back to direct API download path.
        """
        if not self.use_fallback and self.client:
            try:
                return self.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expires_in
                )
            except Exception as e:
                logger.warning(f"Could not generate presigned URL: {e}")

        # Local fallback route
        return f"/api/v1/reports/{key}/download"

    def get_object_bytes(self, key: str) -> bytes:
        if not self.use_fallback and self.client:
            try:
                response = self.client.get_object(Bucket=self.bucket, Key=key)
                return response["Body"].read()
            except Exception as e:
                logger.warning(f"Failed to fetch {key} from S3 ({e}), trying local fallback.")

        safe_name = key.replace("/", "_")
        local_path = os.path.join(self.local_fallback_dir, safe_name)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"Artifact {key} not found in S3 or local storage.")

    def check_health(self) -> Dict[str, Any]:
        """Probes storage readiness."""
        if self.use_fallback:
            return {"status": "degraded", "mode": "local_filesystem", "path": self.local_fallback_dir}
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return {"status": "ok", "mode": "s3", "bucket": self.bucket}
        except Exception as e:
            return {"status": "error", "mode": "s3", "error": str(e)}

storage_service = StorageService()
