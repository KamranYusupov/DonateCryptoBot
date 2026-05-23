from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

from app.core.config import settings


metadata = MetaData(naming_convention=settings.metadata_naming_convention)
Base = declarative_base(metadata=metadata)
