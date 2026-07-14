"""Admin file upload + public streaming from Emergent Object Storage."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, Query
from fastapi.responses import Response as FastResponse

from core import db, now_iso, APP_NAME, logger
from security import require_admin
from storage import put_object, get_object

router = APIRouter(tags=["files"])


@router.post("/admin/upload")
async def upload_file(file: UploadFile = File(...), kind: str = Form("image"),
                      user: dict = Depends(require_admin)):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{kind}/{file_id}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    doc = {
        "id": file_id, "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type,
        "size": result.get("size", len(data)), "kind": kind,
        "uploaded_by": user["id"], "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(doc)
    doc.pop("_id", None)
    doc["url"] = f"/api/files/{result['path']}"
    return doc


@router.get("/files/{path:path}")
async def serve_file(path: str, auth: Optional[str] = Query(None),
                      authorization: Optional[str] = Header(None)):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = get_object(path)
    except Exception as e:
        logger.error(f"file fetch error: {e}")
        raise HTTPException(status_code=502, detail="Storage error")
    return FastResponse(content=data, media_type=rec.get("content_type") or content_type)
