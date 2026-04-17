from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
from ..core.ingest import ingest_pdf
from ..core.rag import query_kb

router = APIRouter(
    prefix="/ai/kb",
    tags=["knowledge-base"]
)

class QueryRequest(BaseModel):
    question: str
    collection: str = "manuals"

@router.post("/ingest")
async def upload_manual(file: UploadFile = File(...)):
    """
    Upload a PDF Manual to ingest into the Knowledge Base.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
        
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        count = ingest_pdf(temp_file)
        return {"status": "success", "chunks_added": count, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@router.post("/ask")
async def ask_question(req: QueryRequest):
    """
    Ask a question to the Knowledge Base.
    """
    try:
        result = query_kb(req.question, req.collection)
        return result
    except Exception as e:
        # In case of OpenAI errors (e.g. missing key), return a friendly error
        if "api_key" in str(e).lower():
             raise HTTPException(status_code=500, detail="OpenAI API Key missing. Please configure OPENAI_API_KEY env.")
        raise HTTPException(status_code=500, detail=str(e))
