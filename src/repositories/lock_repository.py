"""Lock 관리를 위한 Repository 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class LockRepository(ABC):
    """Lock 관리를 위한 Repository 인터페이스."""

    @abstractmethod
    def acquire(self, lock_key: str, timeout: float | None = None) -> AbstractContextManager[str]:
        """Lock을 획득합니다.

        Args:
            lock_key: Lock의 고유 키
            timeout: Lock 획득 대기 시간 (초). None이면 무한 대기

        Returns:
            Context manager. with 문에서 사용하면 자동으로 해제됩니다.

        Raises:
            TimeoutError: timeout 내에 lock을 획득하지 못한 경우
        """
        pass

