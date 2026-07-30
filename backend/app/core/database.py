from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_pg_kwargs = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_pre_ping": True,       # discard stale connections before use
    "pool_recycle": 300,         # recycle connections every 5 min to avoid stale-after-restart issues
    "connect_args": {"ssl": False},
}
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    **({} if _is_sqlite else _pg_kwargs),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
