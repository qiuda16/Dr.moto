from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging
import uuid

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])
logger = logging.getLogger("ai")

class SearchRequest(BaseModel):
    query: str
    limit: int = 3

class SearchResult(BaseModel):
    doc_id: str
    content: str
    score: float

# Mock Vector Store
MOCK_VECTORS = {
    "manual_v1": "To replace the battery, unscrew the back panel (Philips #2) and disconnect the terminal.",
    "manual_v2": "Safety First: Always wear gloves when handling the engine block.",
    "manual_v3": "Torque settings for wheel nuts: 120Nm."
}

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a PDF/Text file into the Vector DB.
    (Mock implementation)
    """
    content = await file.read()
    doc_id = str(uuid.uuid4())
    logger.info(f"Ingested document {file.filename} as {doc_id}")
    return {"status": "ingested", "doc_id": doc_id, "chunks": 1}

@router.post("/search", response_model=List[SearchResult])
async def search_kb(req: SearchRequest):
    """
    Semantic Search.
    (Mock: keyword matching)
    """
    results = []
    q = req.query.lower()
    
    for doc_id, text in MOCK_VECTORS.items():
        score = 0.0
        if q in text.lower():
            score = 0.9
        else:
            # Simple word overlap
            common = set(q.split()) & set(text.lower().split())
            if common:
                score = 0.1 * len(common)
        
        if score > 0:
            results.append(SearchResult(doc_id=doc_id, content=text, score=score))
            
    return sorted(results, key=lambda x: x.score, reverse=True)[:req.limit]
