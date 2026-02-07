"""Lock 관리를 위한 Repository 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from datetime import datetime


class LockInfo:
    """Lock 정보를 담는 데이터 클래스."""

    def __init__(self, exists: bool, expires_at: datetime | None = None, lock_uuid: str | None = None):
        """LockInfo를 초기화합니다.

        Args:
            exists: Lock이 존재하는지 여부
            expires_at: Lock 만료 시간 (None이면 만료 시간 없음)
            lock_uuid: Lock UUID (None이면 UUID 없음)
        """
        self.exists = exists
        self.expires_at = expires_at
        self.lock_uuid = lock_uuid

    def is_expired(self) -> bool:
        """Lock이 만료되었는지 확인합니다.

        Returns:
            Lock이 만료되었으면 True, 그렇지 않으면 False
        """
        if not self.exists:
            return False
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at


class LockRepository(ABC):
    """Lock 관리를 위한 Repository 인터페이스."""

    @abstractmethod
    def acquire(self, lock_key: str, timeout: float | None = None, ttl_seconds: float | None = None) -> AbstractContextManager[str]:
        """Lock을 획득합니다.

        Args:
            lock_key: Lock의 고유 키
            timeout: Lock 획득 대기 시간 (초). None이면 무한 대기
            ttl_seconds: Lock 유지 시간 (초). None이면 만료 시간 없음

        Returns:
            Context manager. with 문에서 사용하면 자동으로 해제됩니다.

        Raises:
            TimeoutError: timeout 내에 lock을 획득하지 못한 경우
        """
        pass

    @abstractmethod
    def release(self, lock_key: str) -> bool:
        """Lock을 해제합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock이 존재했고 해제되었으면 True, Lock이 없었으면 False
        """
        pass

    @abstractmethod
    def get_lock_info(self, lock_key: str) -> LockInfo:
        """Lock 정보를 조회합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            LockInfo 객체 (존재 여부, 만료 시간 포함)
        """
        pass

    @abstractmethod
    def is_locked(self, lock_key: str) -> bool:
        """Lock이 잠겨있는지 확인합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock이 잠겨있으면 True, 그렇지 않으면 False
        """
        pass

