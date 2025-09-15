"""
Database Base Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path to import existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from app.core.config import settings

# Create engine
engine = create_engine(
    settings.get_database_url(),
    connect_args={"check_same_thread": False} if "sqlite" in settings.get_database_url() else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()