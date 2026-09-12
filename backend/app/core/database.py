from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 开发阶段：为新列做向前兼容（后续可用 Alembic 替代）
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS search_references TEXT"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE research_files ADD COLUMN IF NOT EXISTS research_subject_id VARCHAR(36)"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE document_evidence ADD COLUMN IF NOT EXISTS research_subject_id VARCHAR(36)"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_research_files_research_subject_id ON research_files (research_subject_id)"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_document_evidence_research_subject_id ON document_evidence (research_subject_id)"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_document_evidence_file_id ON document_evidence (file_id)"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_document_evidence_user_id ON document_evidence (user_id)"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS evidence_ids TEXT"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) DEFAULT 'needs_review'"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE research_assumptions ADD COLUMN IF NOT EXISTS evidence_ids TEXT"
            )
        )
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                "ALTER TABLE research_assumptions ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) DEFAULT 'needs_review'"
            )
        )
