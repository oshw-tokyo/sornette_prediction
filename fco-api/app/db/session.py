"""
Database Session Management
"""

from typing import Generator
from .base import SessionLocal


def get_db() -> Generator:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()