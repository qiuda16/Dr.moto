from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..core.ingest import ingest_records
from ..core.ocr import parse_document

router = APIRouter(prefix="/ai/ocr", tags=["ocr"])


@router.post("/parse")
async def parse_manual_document(
    file: UploadFile = File(...),
    document_id: int = Form(...),
    model_id: int = Form(...),
    title: str = Form(""),
    category: str = Form(""),
    job_id: int = Form(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")

    try:
        file_bytes = await file.read()
        result = parse_document(file_bytes, file.filename, file.content_type, job_id=job_id)
        page_records = [
            {
                "page_number": item.get("page_number"),
                "page_content": item.get("text") or "",
                "summary": item.get("summary"),
                "specs": item.get("specs") or [],
                "procedures": item.get("procedures") or [],
            }
            for item in result.get("pages") or []
        ]

        collections = []
        for collection_name in (f"catalog_model_{model_id}", f"knowledge_document_{document_id}"):
            if ingest_records(page_records, collection_name=collection_name):
                collections.append(collection_name)

        result.update(
            {
                "document_id": document_id,
                "model_id": model_id,
                "title": title or file.filename,
                "category": category or "",
                "job_id": job_id,
                "file_name": file.filename,
                "kb_collections": collections,
            }
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {exc}") from exc
