import os
import boto3
from botocore.exceptions import ClientError
from backend.app.config import settings
import logging

logger = logging.getLogger("marketai.storage")

class StorageService:
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception as e:
                logger.warning(f"Could not auto-create S3 bucket {self.bucket}: {e}")

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Uploads bytes to S3/MinIO under the specified key.
        Returns the object key.
        """
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        return key

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generates a pre-signed S3 download URL.
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in
        )

    def get_object_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

storage_service = StorageService()
