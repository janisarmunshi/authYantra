from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import text
from config import get_settings
from middleware import TenantIsolationMiddleware, ErrorHandlerMiddleware
from routes import auth, health, entra_id, roles, organizations
from routes import oauth, mfa, admin
from database import async_engine
from models import Base
import logging

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run_safe_migrations(conn):
    """
    Add new columns to existing tables without dropping data.
    Uses IF NOT EXISTS so it is idempotent — safe to run on every startup.
    """
    migrations = [
        # organizations
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS slug VARCHAR(255) UNIQUE",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS allowed_email_domains JSON DEFAULT '[]'",
        # users
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE",
        # roles
        "ALTER TABLE roles ADD COLUMN IF NOT EXISTS description VARCHAR(500)",
        "ALTER TABLE roles ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE",
        # registered_apps
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS client_id VARCHAR(255) UNIQUE",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS client_secret_hash VARCHAR(255)",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS allowed_scopes JSON DEFAULT '[]'",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS allowed_grant_types JSON DEFAULT '[]'",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS access_token_lifetime INTEGER DEFAULT 900",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS refresh_token_lifetime INTEGER DEFAULT 604800",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS is_confidential BOOLEAN DEFAULT TRUE",
        "ALTER TABLE registered_apps ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)",
    ]
    for sql in migrations:
        try:
            await conn.execute(text(sql))
        except Exception as e:
            logger.warning("Migration skipped (%s): %s", sql[:60], e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting authYantra IAM Service")
    async with async_engine.begin() as conn:
        # Create all new tables
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns to existing tables
        await _run_safe_migrations(conn)
    yield
    logger.info("Shutting down authYantra IAM Service")
    await async_engine.dispose()


app = FastAPI(
    title="authYantra IAM",
    version="2.0.0",
    description=(
        "Multi-tenant Identity and Access Management service. "
        "Supports OAuth 2.0, OIDC, SAML, MFA, RBAC, and SSO."
    ),
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(TenantIsolationMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(entra_id.router)
app.include_router(roles.router)
app.include_router(organizations.router)
app.include_router(oauth.router)       # OAuth 2.0 / OIDC
app.include_router(mfa.router)         # MFA management
app.include_router(admin.router)       # Audit logs

# ── Static UI ────────────────────────────────────────────────────────────────
_STATIC_DIR = Path(__file__).parent / "static"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{_path:path}", include_in_schema=False)
    async def serve_spa(_path: str = ""):
        return FileResponse(_STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
