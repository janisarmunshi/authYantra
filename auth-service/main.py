from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from config import get_settings
from middleware import TenantIsolationMiddleware, ErrorHandlerMiddleware
from routes import auth, health, entra_id, roles, organizations
from database import async_engine
from models import Base
import logging

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Authentication Service")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    logger.info("Shutting down Authentication Service")
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Central authentication service with OAuth2 and JWT support",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(TenantIsolationMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(entra_id.router)
app.include_router(roles.router)
app.include_router(organizations.router)


@app.get("/api/info")
async def root():
    """API info endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# ── Static UI (built with `npm run build` inside ui/) ────────────────────────
_STATIC_DIR = Path(__file__).parent / "static"

if _STATIC_DIR.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    # Serve index.html for all non-API routes so React Router handles navigation
    @app.get("/{_path:path}", include_in_schema=False)
    async def serve_spa(_path: str = ""):
        return FileResponse(_STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
