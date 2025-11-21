"""Selenium Grid 세션 풀 관리."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from threading import Lock
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class SessionPool:
    """Selenium Grid 세션 풀을 관리하는 클래스."""

    def __init__(self, grid_url: str, pool_size: int = 4):
        """SessionPool을 초기화합니다.

        Args:
            grid_url: Selenium Grid Hub의 URL (예: http://localhost:4444)
            pool_size: 미리 생성할 세션 수
        """
        self.grid_url = grid_url.rstrip("/")
        self.pool_size = pool_size
        self._sessions: Dict[str, WebDriver] = {}
        self._lock = Lock()
        self._initialized = False

    def initialize(self) -> None:
        """세션 풀을 초기화하고 미리 세션을 생성합니다."""
        if self._initialized:
            return

        logger.info(f"세션 풀 초기화 시작 (크기: {self.pool_size})")

        # Selenium Grid Hub가 준비될 때까지 대기
        import time
        import urllib.request
        max_retries = 30
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                status_url = f"{self.grid_url}/status"
                with urllib.request.urlopen(status_url, timeout=5) as response:
                    if response.status == 200:
                        logger.info("Selenium Grid Hub 연결 확인 완료")
                        break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Selenium Grid Hub 연결 대기 중... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Selenium Grid Hub에 연결할 수 없습니다: {e}")
                    self._initialized = True
                    return

        for i in range(self.pool_size):
            try:
                driver = webdriver.Remote(
                    command_executor=self.grid_url,
                    options=webdriver.ChromeOptions(),
                )
                session_id = driver.session_id
                if session_id:
                    # 세션 warm up을 위해 www.google.com에 접속
                    try:
                        driver.get("https://www.google.com")
                        logger.info(f"세션 생성 및 warm up 완료: {session_id}")
                    except Exception as warmup_error:
                        logger.warning(f"세션 warm up 실패 ({session_id}): {warmup_error}, 세션은 생성되었습니다")
                    self._sessions[session_id] = driver
                else:
                    logger.error("세션 ID를 가져올 수 없습니다")
                    driver.quit()
            except Exception as e:
                logger.error(f"세션 생성 실패: {e}")
                # 실패한 세션은 스킵하고 계속 진행

        self._initialized = True
        logger.info(f"세션 풀 초기화 완료 (생성된 세션 수: {len(self._sessions)})")

    def get_session(self, session_id: str) -> Optional[WebDriver]:
        """세션 풀에서 특정 세션을 가져옵니다.

        Args:
            session_id: 세션 ID

        Returns:
            WebDriver 인스턴스 또는 None (세션이 존재하지 않을 때)
        """
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> list[str]:
        """세션 풀에 있는 모든 세션 ID 목록을 반환합니다.

        Returns:
            세션 ID 목록
        """
        with self._lock:
            return list(self._sessions.keys())

    def has_session(self, session_id: str) -> bool:
        """세션이 풀에 존재하는지 확인합니다.

        Args:
            session_id: 세션 ID

        Returns:
            세션 존재 여부
        """
        with self._lock:
            return session_id in self._sessions

    @contextmanager
    def acquire_session(self, session_id: str):
        """세션을 획득하고 사용 후 풀에 반환합니다.

        Args:
            session_id: 세션 ID

        Yields:
            WebDriver 인스턴스

        Raises:
            ValueError: 세션이 존재하지 않을 때
        """
        driver = self.get_session(session_id)
        if driver is None:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        # 세션 유효성 확인
        try:
            # 간단한 세션 유효성 확인 (현재 URL 조회)
            _ = driver.current_url
        except Exception:
            # 세션이 유효하지 않으면 풀에서 제거하고 새로 생성
            logger.warning(f"세션이 유효하지 않음: {session_id}, 재생성 시도")
            try:
                driver.quit()
            except Exception:
                pass
            with self._lock:
                self._sessions.pop(session_id, None)

            # 새 세션 생성 (원래 session_id 위치에 저장하여 일관성 유지)
            try:
                new_driver = webdriver.Remote(
                    command_executor=self.grid_url,
                    options=webdriver.ChromeOptions(),
                )
                new_session_id = new_driver.session_id
                if not new_session_id:
                    raise ValueError("새 세션 ID를 가져올 수 없습니다")
                with self._lock:
                    # 원래 session_id를 키로 사용하여 일관성 유지
                    # (실제로는 새 세션이지만, API 호출자는 같은 ID를 사용)
                    self._sessions[session_id] = new_driver
                    # 새 session_id도 별도로 저장 (나중에 정리할 때 사용)
                    if new_session_id != session_id:
                        self._sessions[new_session_id] = new_driver
                logger.info(f"세션 재생성 완료: {new_session_id} (요청된 ID: {session_id})")
                driver = new_driver
            except Exception as e:
                raise ValueError(f"세션 재생성 실패: {e}") from e

        try:
            # 세션을 yield하고 사용 후 자동으로 풀에 반환됨 (제거하지 않음)
            yield driver
        except Exception as e:
            logger.error(f"세션 사용 중 오류 발생: {e}")
            # 심각한 오류로 세션이 완전히 손상된 경우에만 풀에서 제거
            try:
                # 세션 상태 확인
                _ = driver.session_id
            except Exception:
                # 세션이 완전히 손상된 경우에만 제거
                logger.error(f"세션이 손상되어 풀에서 제거: {session_id}")
                try:
                    driver.quit()
                except Exception:
                    pass
                with self._lock:
                    self._sessions.pop(session_id, None)
            raise

    def cleanup(self) -> None:
        """세션 풀의 모든 세션을 정리합니다."""
        logger.info("세션 풀 정리 시작")
        with self._lock:
            for session_id, driver in list(self._sessions.items()):
                try:
                    driver.quit()
                    logger.info(f"세션 종료: {session_id}")
                except Exception as e:
                    logger.error(f"세션 종료 실패 ({session_id}): {e}")
            self._sessions.clear()
        self._initialized = False
        logger.info("세션 풀 정리 완료")

