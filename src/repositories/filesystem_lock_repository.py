"""Filesystem 기반 Lock Repository 구현체."""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

from .lock_repository import LockRepository


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

    @contextmanager
    def acquire(self, lock_key: str, timeout: float | None = None):
        """Lock을 획득합니다.

        Args:
            lock_key: Lock의 고유 키
            timeout: Lock 획득 대기 시간 (초). None이면 무한 대기

        Yields:
            lock_key: 획득한 lock의 키

        Raises:
            TimeoutError: timeout 내에 lock을 획득하지 못한 경우
        """
        lock_file = self._get_lock_file_path(lock_key)
        start_time = time.time()

        # Lock 획득 시도
        while True:
            try:
                # 파일을 생성하려고 시도 (exclusive creation)
                lock_file.touch(exist_ok=False)
                break
            except FileExistsError:
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

