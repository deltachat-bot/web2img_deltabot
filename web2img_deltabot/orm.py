"""database"""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_session = None  # noqa


class User(Base):  # noqa
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    browser = Column(Integer)
    img_type = Column(String(50))
    quality = Column(Integer)
    scale = Column(String(50))
    omit_background = Column(Boolean)
    full_page = Column(Boolean)
    animations = Column(String(50))


def async_session():
    """Get session"""
    return _session()


async def init(path: str, debug: bool = False) -> None:
    """Initialize engine."""
    global _session  # noqa
    engine = create_async_engine(path, echo=debug)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _session = sessionmaker(engine, class_=AsyncSession)
