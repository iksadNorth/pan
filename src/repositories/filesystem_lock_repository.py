"""Filesystem 기반 Lock Repository 구현체."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from .lock_repository import LockInfo, LockRepository


class FilesystemLockRepository(LockRepository):
    """Filesystem을 사용한 Lock Repository 구현체.

    파일 시스템의 파일 존재 여부를 이용한 간단한 lock 메커니즘을 구현합니다.
    """

    def __init__(self, lock_dir: Path | str):
        """FilesystemLockRepository를 초기화합니다.

        Args:
            lock_dir: Lock 파일을 저장할 디렉토리 경로
        """
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _get_lock_file_path(self, lock_key: str) -> Path:
        """Lock 키에 해당하는 파일 경로를 반환합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock 파일 경로
        """
        # lock_key에 안전한 파일명으로 변환
        safe_key = lock_key.replace("/", "_").replace("\\", "_")
        return self.lock_dir / f"{safe_key}.lock"

    def _get_lock_info_file_path(self, lock_key: str) -> Path:
        """Lock 정보 파일 경로를 반환합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock 정보 파일 경로
        """
        safe_key = lock_key.replace("/", "_").replace("\\", "_")
        return self.lock_dir / f"{safe_key}.lock.json"

    def _load_lock_info(self, lock_key: str) -> dict | None:
        """Lock 정보를 로드합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock 정보 딕셔너리 또는 None
        """
        info_file = self._get_lock_info_file_path(lock_key)
        if not info_file.exists():
            return None
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_lock_info(self, lock_key: str, expires_at: datetime | None = None, lock_uuid: str | None = None) -> None:
        """Lock 정보를 저장합니다.

        Args:
            lock_key: Lock의 고유 키
            expires_at: 만료 시간 (None이면 만료 시간 없음)
            lock_uuid: Lock UUID (None이면 새로 생성)
        """
        info_file = self._get_lock_info_file_path(lock_key)
        if lock_uuid is None:
            lock_uuid = str(uuid.uuid4())
        info = {
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "lock_uuid": lock_uuid,
        }
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f)

    def _delete_lock_info(self, lock_key: str) -> None:
        """Lock 정보 파일을 삭제합니다.

        Args:
            lock_key: Lock의 고유 키
        """
        info_file = self._get_lock_info_file_path(lock_key)
        if info_file.exists():
            info_file.unlink()

    def _is_expired(self, lock_key: str) -> bool:
        """Lock이 만료되었는지 확인합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock이 만료되었으면 True, 그렇지 않으면 False
        """
        info = self._load_lock_info(lock_key)
        if not info:
            return False
        expires_at_str = info.get("expires_at")
        if not expires_at_str:
            return False
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            return datetime.now() >= expires_at
        except (ValueError, TypeError):
            return False

    def _cleanup_expired_lock(self, lock_key: str) -> None:
        """만료된 Lock을 정리합니다.

        Args:
            lock_key: Lock의 고유 키
        """
        lock_file = self._get_lock_file_path(lock_key)
        if lock_file.exists() and self._is_expired(lock_key):
            lock_file.unlink()
            self._delete_lock_info(lock_key)

    def _acquire_with_ttl_internal(self, lock_key: str, ttl_seconds: float | None, timeout: float | None = None) -> tuple[datetime | None, str]:
        """TTL과 함께 Lock을 획득합니다 (내부 메서드, 자동 해제하지 않음).

        Args:
            lock_key: Lock의 고유 키
            ttl_seconds: Lock 유지 시간 (초). None이면 만료 시간 없음
            timeout: Lock 획득 대기 시간 (초). None이면 무한 대기

        Returns:
            (만료 시간, lock_uuid) 튜플 (만료 시간이 None이면 만료 시간 없음)

        Raises:
            TimeoutError: timeout 내에 lock을 획득하지 못한 경우
        """
        # 만료된 Lock 정리
        self._cleanup_expired_lock(lock_key)
        
        lock_file = self._get_lock_file_path(lock_key)
        start_time = time.time()
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        lock_uuid = str(uuid.uuid4())

        # Lock 획득 시도
        while True:
            try:
                # 파일을 생성하려고 시도 (exclusive creation)
                lock_file.touch(exist_ok=False)
                # Lock 정보 저장
                self._save_lock_info(lock_key, expires_at, lock_uuid)
                return expires_at, lock_uuid
            except FileExistsError:
                # 만료된 Lock인지 확인
                self._cleanup_expired_lock(lock_key)
                if not lock_file.exists():
                    # 만료되어 정리되었으므로 다시 시도
                    continue
                
                # Lock이 이미 존재하는 경우
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(
                            f"Lock 획득 시간 초과: {lock_key} (timeout: {timeout}초)"
                        )
                # 짧은 대기 후 재시도
                time.sleep(0.1)

    @contextmanager
    def acquire(self, lock_key: str, timeout: float | None = None, ttl_seconds: float | None = None):
        """Lock을 획득합니다.

        Args:
            lock_key: Lock의 고유 키
            timeout: Lock 획득 대기 시간 (초). None이면 무한 대기
            ttl_seconds: Lock 유지 시간 (초). None이면 만료 시간 없음

        Yields:
            lock_key: 획득한 lock의 키

        Raises:
            TimeoutError: timeout 내에 lock을 획득하지 못한 경우
        """
        lock_file = self._get_lock_file_path(lock_key)
        
        # TTL이 지정된 경우
        if ttl_seconds is not None:
            self._acquire_with_ttl_internal(lock_key, ttl_seconds, timeout)
        else:
            # 기존 방식 (TTL 없음)
            # 만료된 Lock 정리
            self._cleanup_expired_lock(lock_key)
            
            start_time = time.time()
            lock_uuid = str(uuid.uuid4())

            # Lock 획득 시도
            while True:
                try:
                    # 파일을 생성하려고 시도 (exclusive creation)
                    lock_file.touch(exist_ok=False)
                    # Lock 정보 저장 (UUID 포함)
                    self._save_lock_info(lock_key, None, lock_uuid)
                    break
                except FileExistsError:
                    # 만료된 Lock인지 확인
                    self._cleanup_expired_lock(lock_key)
                    if not lock_file.exists():
                        # 만료되어 정리되었으므로 다시 시도
                        continue
                    
                    # Lock이 이미 존재하는 경우
                    if timeout is not None:
                        elapsed = time.time() - start_time
                        if elapsed >= timeout:
                            raise TimeoutError(
                                f"Lock 획득 시간 초과: {lock_key} (timeout: {timeout}초)"
                            )
                    # 짧은 대기 후 재시도
                    time.sleep(0.1)

        try:
            yield lock_key
        finally:
            # Lock 해제
            if lock_file.exists():
                lock_file.unlink()
            self._delete_lock_info(lock_key)

    def release(self, lock_key: str) -> bool:
        """Lock을 해제합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock이 존재했고 해제되었으면 True, Lock이 없었으면 False
        """
        lock_file = self._get_lock_file_path(lock_key)
        if not lock_file.exists():
            return False
        
        lock_file.unlink()
        self._delete_lock_info(lock_key)
        return True

    def is_locked(self, lock_key: str) -> bool:
        """Lock이 잠겨있는지 확인합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            Lock이 잠겨있으면 True, 그렇지 않으면 False
        """
        # 만료된 Lock 정리
        self._cleanup_expired_lock(lock_key)
        
        lock_file = self._get_lock_file_path(lock_key)
        return lock_file.exists()

    def get_lock_info(self, lock_key: str) -> LockInfo:
        """Lock 정보를 조회합니다.

        Args:
            lock_key: Lock의 고유 키

        Returns:
            LockInfo 객체 (존재 여부, 만료 시간, UUID 포함)
        """
        # is_locked를 먼저 호출하여 만료된 Lock 정리
        exists = self.is_locked(lock_key)
        
        if not exists:
            return LockInfo(exists=False)
        
        info = self._load_lock_info(lock_key)
        if not info:
            # Lock 파일은 있지만 정보 파일이 없는 경우 (기존 방식의 Lock)
            return LockInfo(exists=True, expires_at=None, lock_uuid=None)
        
        expires_at_str = info.get("expires_at")
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except (ValueError, TypeError):
                pass
        
        lock_uuid = info.get("lock_uuid")
        
        return LockInfo(exists=True, expires_at=expires_at, lock_uuid=lock_uuid)
