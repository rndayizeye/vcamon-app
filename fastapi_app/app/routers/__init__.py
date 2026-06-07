from fastapi import APIRouter

from .analytics import router as analytics_router
from .auth import router as auth_router
from .cases import router as cases_router
from .ghosting import router as ghosting_router
from .labs import router as labs_router
from .relationships import router as relationships_router
from .symptoms import router as symptoms_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(analytics_router)
router.include_router(cases_router)
router.include_router(ghosting_router)
router.include_router(labs_router)
router.include_router(relationships_router)
router.include_router(symptoms_router)


@router.get("/")
def read_api_root():
    return {"message": "API Root"}
