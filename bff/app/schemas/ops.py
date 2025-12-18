from pydantic import BaseModel

class UploadBase64(BaseModel):
    filename: str
    content_base64: str
    content_type: str = "application/octet-stream"

class ReadmeRequest(BaseModel):
    path: str
