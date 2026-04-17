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
        self._bucket_ready = False
    
    def _ensure_bucket(self):
        if self._bucket_ready:
            return
        found = self.client.bucket_exists(self.bucket)
        if not found:
            self.client.make_bucket(self.bucket)
        self._bucket_ready = True
    
    def put_bytes(self, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
        self._ensure_bucket()
        stream = io.BytesIO(data)
        self.client.put_object(self.bucket, object_name, stream, length=len(data), content_type=content_type)
        return self.presigned_get(object_name)

    def get_bytes(self, object_name: str) -> bytes:
        self._ensure_bucket()
        response = self.client.get_object(self.bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def remove(self, object_name: str):
        self._ensure_bucket()
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error:
            raise

    def presigned_get(self, object_name: str, expires_seconds: int = 3600):
        self._ensure_bucket()
        url = self.client.presigned_get_object(self.bucket, object_name, expires=datetime.timedelta(seconds=expires_seconds))
        return url

obj_storage = ObjectStorageClient()
