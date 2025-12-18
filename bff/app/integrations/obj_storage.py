from minio import Minio
from minio.error import S3Error
from ..core.config import settings
import datetime
import io

class ObjectStorageClient:
    def __init__(self):
        endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        secure = settings.MINIO_ENDPOINT.startswith("https://")
        self.client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=secure
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        found = self.client.bucket_exists(self.bucket)
        if not found:
            self.client.make_bucket(self.bucket)
    
    def put_bytes(self, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
        stream = io.BytesIO(data)
        self.client.put_object(self.bucket, object_name, stream, length=len(data), content_type=content_type)
        return self.presigned_get(object_name)
    
    def presigned_get(self, object_name: str, expires_seconds: int = 3600):
        url = self.client.presigned_get_object(self.bucket, object_name, expires=datetime.timedelta(seconds=expires_seconds))
        return url

obj_storage = ObjectStorageClient()
