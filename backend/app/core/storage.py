
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import logging

# Configuration (In a real app, use settings.py/pydantic)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "voicebrain-audio-dev")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL") # For MinIO or Cloudflare R2
S3_REGION_NAME = os.getenv("S3_REGION_NAME", "us-east-1")

logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self):
        # If no keys, maybe we are in mock mode?
        self.is_mock = not (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
        
        if not self.is_mock:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                endpoint_url=S3_ENDPOINT_URL,
                region_name=S3_REGION_NAME
            )
        else:
            logger.warning("AWS Credentials not found. Using MockStorage.")
            # Ensure local temp dir
            os.makedirs("temp_storage", exist_ok=True)

import shutil
from typing import Union, BinaryIO

# ... imports ...

    async def upload_file(self, file_content: Union[bytes, BinaryIO], file_name: str, content_type: str = "audio/mpeg") -> str:
        """
        Uploads file to S3 and returns the key/url. 
        For mock, saves locally.
        """
        if self.is_mock:
            path = f"temp_storage/{file_name}"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                if isinstance(file_content, bytes):
                    f.write(file_content)
                else:
                    # Reset position just in case
                    if hasattr(file_content, 'seek'):
                        file_content.seek(0)
                    shutil.copyfileobj(file_content, f)
            return f"local://{path}"

        try:
            # Upload
            if hasattr(file_content, 'seek') and not isinstance(file_content, bytes):
                file_content.seek(0)
                
            self.s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=file_name,
                Body=file_content,
                ContentType=content_type
            )
            # URL Generation (Simplified)
            # If standard S3
            if not S3_ENDPOINT_URL:
                 return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{file_name}"
            # If Custom (R2/MinIO)
            return f"{S3_ENDPOINT_URL}/{S3_BUCKET_NAME}/{file_name}"

        except ClientError as e:
            logger.error(f"S3 Upload Error: {e}")
            raise e

    async def read_file(self, file_key: str) -> bytes:
        """
        Reads file content from S3 or local storage.
        """
        if self.is_mock or file_key.startswith("local://"):
            path = file_key.replace("local://", "").replace("https://", "") # cleanup
            # Handles if path was absolute or relative inconsistencies in mock
            if "temp_storage" not in path and os.path.exists(f"temp_storage/{path}"):
                 path = f"temp_storage/{path}"
            
            with open(path, "rb") as f:
                return f.read()

        try:
            # Use key directly (Robust Path Handling)
            response = self.s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"S3 Read Error: {e}")
            raise e

    async def get_presigned_url(self, file_key: str, expiration=3600) -> str:
        """
        Generates a presigned URL for secure access.
        """
        if self.is_mock or file_key.startswith("local://"):
             # In dev, we might serve via a static endpoint or just return the path
             return file_key

        try:
            response = self.s3_client.generate_presigned_url('get_object',
                                                        Params={'Bucket': S3_BUCKET_NAME,
                                                                'Key': file_key},
                                                        ExpiresIn=expiration)
            return response
        except ClientError as e:
            logger.error(e)
            return None

    async def delete_file(self, file_key: str):
        if self.is_mock:
            try:
                path = file_key.replace("local://", "")
                os.remove(path)
            except Exception:
                pass
            return

        try:
            self.s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=file_key)
        except ClientError as e:
            logger.error(e)

# Global Instance
storage_client = StorageClient()
