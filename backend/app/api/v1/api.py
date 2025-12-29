from fastapi import APIRouter
from app.api.v1 import auth, pdf_upload, quiz

api_router = APIRouter()

# Include auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include PDF upload routes
api_router.include_router(pdf_upload.router, prefix="/pdf", tags=["pdf-processing"])

# Include quiz routes
api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz-generation"])

# Placeholder for future endpoints
@api_router.get("/status")
async def api_status():
    return {"status": "API v1 is running"}