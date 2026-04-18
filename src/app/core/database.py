from typing import AsyncGenerator, Generator
from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy.exc import SQLAlchemyError

from src.app.core.config import config
from src.app.core.logging import get_logger

logger = get_logger(__name__)

class DatabaseSessionManager:
    def __init__(self, async_mode: bool = True):
        self._async_mode = async_mode
        self._engine = None
        self._session_maker = None

    # ---------- INIT ----------
    def init(self) -> None:
        if self._engine:
            return
        
        if self._async_mode:
            logger.info("====INITIALIZING ASYNC DATABASE ENGINE====")

            self._engine = create_async_engine(
                config.DB_CONFIG.db_url, 
                poolclass=AsyncAdaptedQueuePool,
                pool_size=config.DB_CONFIG.pool_size,
                max_overflow=config.DB_CONFIG.max_overflow,
                pool_timeout=config.DB_CONFIG.pool_timeout,
                pool_recycle=1800,
                pool_pre_ping=True,
            )

            self._session_maker = async_sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )

        else:
            logger.info("====INITIALIZING SYNC DATABASE ENGINE====")
            self._engine = create_engine(
                config.DB_CONFIG.sync_db_url,
                pool_size=config.DB_CONFIG.pool_size,
                max_overflow=config.DB_CONFIG.max_overflow,
                pool_timeout=config.DB_CONFIG.pool_timeout,
                pool_recycle=1800,
                pool_pre_ping=True,
            )
            self._session_maker = sessionmaker(
                bind=self._engine,
                autocommit=False, 
                autoflush=False, 
                expire_on_commit=False
            )

    # ---------- CLOSE ----------
    async def close(self) -> None:
        if not self._engine:
            return

        if self._async_mode:
            await self._engine.dispose()
        else:
            self._engine.dispose()

        self._engine = None
        self._session_maker = None
        logger.info("Database engine closed")

    # ---------- ASYNC ----------
    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._async_mode:
            raise RuntimeError("Async connect() used on sync manager")

        if not self._session_maker:
            raise RuntimeError("DatabaseSessionManager not initialized")

        session: AsyncSession = self._session_maker()
        try:
            yield session
            await session.commit()
        except Exception: # as e:
            await session.rollback()
            # logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise
        finally:
            await session.close()
   
    # ---------- SYNC ---------- 
    @contextmanager
    def connect_sync(self) -> Generator[Session, None, None]:
        logger.info("====CONNECTING TO SYNC DATABASE====")
        if self._async_mode:
            raise RuntimeError("Sync connect_sync() used on async manager")

        if not self._session_maker:
            raise RuntimeError("DatabaseSessionManager not initialized")

        session: Session = self._session_maker()
        try:
            yield session
            session.commit()
        except (SQLAlchemyError, Exception): # as e:
            session.rollback()
            # logger.error(f"Database error: {str(e)}", exc_info=True)
            raise
        finally:
            session.close()

async_db_session_manager = DatabaseSessionManager(async_mode=True)
sync_db_session_manager = DatabaseSessionManager(async_mode=False)

# FastAPI startup event
async def on_startup():
    """Initialize database connection on startup."""
    async_db_session_manager.init()
    sync_db_session_manager.init()
    
# FastAPI shutdown event
async def on_shutdown():
    """Close database connection on shutdown."""
    await async_db_session_manager.close()
    await sync_db_session_manager.close()

# Database dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_db_session_manager.connect() as session:
        yield session