import os
from fastapi import HTTPException
from .config import settings
class LocalStorage:
    def put(self, key: str, data: bytes):
        path = os.path.join(settings.STORAGE_LOCAL_DIR, key); os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(data)
    def get(self, key: str) -> bytes: return open(os.path.join(settings.STORAGE_LOCAL_DIR, key), "rb").read()
class S3Storage:  # Neon Bucket / any S3-compatible provider
    def __init__(self):
        if not (settings.S3_BUCKET and settings.S3_ACCESS_KEY):
            raise HTTPException(503, "Object storage is not configured (S3_* variables missing)")
        import boto3
        self.c = boto3.client("s3", endpoint_url=settings.S3_ENDPOINT_URL or None, aws_access_key_id=settings.S3_ACCESS_KEY,
                              aws_secret_access_key=settings.S3_SECRET_KEY, region_name=settings.S3_REGION)
    def put(self, key, data):
        try: self.c.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data)
        except Exception: raise HTTPException(503, "Object storage unavailable")
    def get(self, key): return self.c.get_object(Bucket=settings.S3_BUCKET, Key=key)["Body"].read()
def get_storage(): return S3Storage() if settings.STORAGE_PROVIDER == "s3" else LocalStorage()
