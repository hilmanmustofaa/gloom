"""Base class for sync backends."""

from abc import ABC, abstractmethod


class SyncBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def push_data(self, name: str, data: bytes) -> None:
        """Upload data to storage."""
        pass

    @abstractmethod
    def pull_data(self, name: str) -> bytes:
        """Download data from storage."""
        pass

    @abstractmethod
    def list_contexts(self) -> list[str]:
        """List available contexts in storage."""
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if context exists in storage."""
        pass
