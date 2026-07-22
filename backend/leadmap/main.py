from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api.capture_routes import router as capture_router
from .api.geography_routes import router as geography_router
from .api.routes import router
from .config import get_settings

settings = get_settings()
app = FastAPI(
    title="LeadMap Local API",
    version="0.3.0",
    description="Local-first territory intelligence and lead research workbench.",
)
app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(capture_router)
app.include_router(geography_router)
