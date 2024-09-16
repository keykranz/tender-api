from fastapi import APIRouter
from .bid import router as bid_router
from .tender import router as tender_router
from .debug import router as debug_router

api_router = APIRouter()

api_router.include_router(bid_router, prefix="/api/bids", tags=["bids"])
api_router.include_router(tender_router, prefix="/api/tenders", tags=["tenders"])
api_router.include_router(debug_router, prefix="/api/debug", tags=["debug"])
