from fastapi import APIRouter

from .travels import router as travel_router

router = APIRouter(prefix="/v1")
router.include_router(travel_router)
