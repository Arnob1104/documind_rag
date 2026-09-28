from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import documents, tags, upload, search, chat

app = FastAPI(title="DocuMind API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(tags.router)
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
