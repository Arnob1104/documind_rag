from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.database import supabase
from app.auth import get_current_user, CurrentUser
from app.services.pdf_extract import extract_text_from_pdf
from app.services.rag import build_index_text, index_document

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/pdf")
async def upload_pdf(
    document_id: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    doc = supabase.table("documents").select("author_id, title, content").eq("id", document_id).maybe_single().execute().data
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc["author_id"] != user.id:
        raise HTTPException(403, "Only the author can attach a PDF to this document")

    file_bytes = await file.read()
    extracted_text = extract_text_from_pdf(file_bytes)

    existing = supabase.table("pdf_data").select("id").eq("document_id", document_id).execute().data
    row = {
        "document_id": document_id,
        "filename": file.filename,
        "file_size": len(file_bytes),
        "extracted_text": extracted_text,
    }
    if existing:
        saved = supabase.table("pdf_data").update(row).eq("id", existing[0]["id"]).execute().data[0]
    else:
        saved = supabase.table("pdf_data").insert(row).execute().data[0]

    # re-index the document including the newly extracted PDF text so it's searchable/chattable
    index_document(document_id, build_index_text(doc["title"], doc["content"], extracted_text))

    return saved
