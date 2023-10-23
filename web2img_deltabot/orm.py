"""database"""
from contextlib import contextmanager
from threading import Lock

from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
_Session = sessionmaker()
_lock = Lock()
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


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    with _lock:
        session = _Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def init(path: str, debug: bool = False) -> None:
    """Initialize engine."""
    engine = create_engine(path, echo=debug)
    Base.metadata.create_all(engine)
    _Session.configure(bind=engine)
