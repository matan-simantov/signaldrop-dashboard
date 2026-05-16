"""
Abstract base loader for ingesting posts from any source into the normalized schema.
To support a new data source (e.g., Facebook, Reddit), implement a subclass that
maps source-specific fields into the common schema defined here.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator


@dataclass
class NormalizedPost:
    """Common schema for posts from any source."""
    id: str
    published_at: datetime
    content: str
    source_name: str
    source_id: str
    source_type: str


class BaseLoader(ABC):
    """
    All data source loaders inherit from this class.
    Each implementation maps source-specific fields into NormalizedPost.
    """

    @abstractmethod
    def load(self) -> Iterator[NormalizedPost]:
        """Yield normalized posts from the data source."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Identifier for the source type, e.g. 'telegram', 'facebook'."""
        ...
