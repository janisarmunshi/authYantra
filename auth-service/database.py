from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
from config import get_settings

settings = get_settings()


async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    # Use NullPool for serverless/VPS environments where connections shouldn't be pooled
    # For production with PgBouncer, consider using QueuePool instead
    poolclass=NullPool,
    # Connection pool settings (if using QueuePool in future)
    # pool_size=20,
    # max_overflow=40,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncSession:
    """Dependency for getting database session in routes"""
    async with AsyncSessionLocal() as session:
        yield session
