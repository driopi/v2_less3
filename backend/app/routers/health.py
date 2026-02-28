from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    return {
        "status": "healthy",
        "whisper_loaded": request.app.state.transcription_service.is_loaded,
    }
