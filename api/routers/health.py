from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health():
    return JSONResponse({"status": "ok", "service": "diretto-api"})
