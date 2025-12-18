from fastapi import APIRouter, HTTPException
import base64
import os

from ..integrations.obj_storage import obj_storage
from ..schemas.ops import UploadBase64, ReadmeRequest

router = APIRouter(tags=["Ops"])

@router.post("/media/upload_base64")
async def upload_base64(payload: UploadBase64):
    data = base64.b64decode(payload.content_base64)
    url = obj_storage.put_bytes(payload.filename, data, content_type=payload.content_type)
    return {"key": payload.filename, "url": url}

@router.get("/ops/readmes")
async def list_readmes():
    """Scan the project for README files."""
    project_root = "/app" # Docker path
    readmes = []
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file.lower() in ['readme.md', 'readme.txt']:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_root)
                readmes.append({
                    "name": file,
                    "path": rel_path,
                    "dir": os.path.dirname(rel_path)
                })
    return readmes

@router.post("/ops/readme/content")
async def get_readme_content(payload: ReadmeRequest):
    """Read content of a specific README file."""
    # Security check: simple path traversal prevention
    if ".." in payload.path or payload.path.startswith("/"):
         raise HTTPException(status_code=400, detail="Invalid path")
    
    file_path = os.path.join("/app", payload.path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
