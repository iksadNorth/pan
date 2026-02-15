"""Selenium Grid 세션 풀 관리."""

from __future__ import annotations

import asyncio
import logging
import urllib.request
from contextlib import contextmanager
from threading import Lock
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class SessionPool:
    """Selenium Grid 세션 풀을 관리하는 클래스."""

    def __init__(self, grid_url: str, init_timeout: float = 30.0):
        """SessionPool을 초기화합니다.

        Args:
            grid_url: Selenium Grid Hub의 URL (예: http://localhost:4444)
            init_timeout: 세션 풀 초기화 최대 시간 (초). 기본값: 30초
        """
        self.grid_url = grid_url.rstrip("/")
        self.init_timeout = init_timeout
        self.max_retries = 30
        self._sessions: Dict[str, WebDriver] = {}
        self._lock = Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """세션 풀을 초기화하고 가능한 한 많은 세션을 생성합니다.
        
        세션 생성이 실패할 때까지 계속 시도하여 리소스 풀을 최대한 채웁니다.
        """
        if self._initialized: return
        logger.info("세션 풀 초기화 시작 (최대한 많은 세션 확보 시도)")
        
        for attempt in range(self.max_retries):
            try:
                status_url = f"{self.grid_url}/status"
                with urllib.request.urlopen(status_url, timeout=5) as response:
                    if response.status == 200: break
            except Exception as e:
                pass
            if attempt >= self.max_retries - 1:
                logger.error(f"Selenium Grid Hub에 연결 시도 실패")
                self._initialized = True
                return

        # 비동기로 세션 풀 초기화 실행
        await self._initialize_async()

        self._initialized = True
        logger.info(f"세션 풀 초기화 완료 (생성된 세션 수: {len(self._sessions)})")

    async def create_session_async(self) -> WebDriver:
        """비동기로 세션을 생성하는 함수."""
        loop = asyncio.get_event_loop()
        driver = await loop.run_in_executor(
            None,
            lambda: webdriver.Remote(
                command_executor=self.grid_url,
                options=webdriver.ChromeOptions(),
            )
        )
        driver.get("https://www.google.com")
        
        return driver
    
    async def _initialize_async(self) -> None:
        """비동기로 세션 풀을 초기화합니다."""
        while True:
            try:
                driver = await asyncio.wait_for(self.create_session_async(), timeout=self.init_timeout)
                
                session_id = driver.session_id
                if not session_id: break
                self._sessions[session_id] = driver
                logger.info(f"[현재 세션 수|{len(self._sessions)}]세션 생성 성공")
                
            except asyncio.TimeoutError:
                logger.info(f"[현재 세션 수|{len(self._sessions)}]시간초과로 인한 생성 중단")
                break
            except asyncio.CancelledError:
                logger.info(f"[현재 세션 수|{len(self._sessions)}]세션 생성 중단")
                break
            except Exception as e:
                logger.info(f"[현재 세션 수|{len(self._sessions)}]세션 생성에 실패하여 로직 중단: {e}")
                break

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

        # 세션 유효성 확인 (재활용을 위해 최소한의 검사만 수행)
        # session_id만 확인하고, 실제 사용 시 오류가 발생하면 그때 처리
        try:
            # session_id만 확인 (가벼운 검사)
            _ = driver.session_id
        except Exception:
            # 세션이 완전히 종료된 경우에만 재생성
            logger.warning(f"세션이 완전히 종료됨: {session_id}, 재생성 시도")
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
                new_driver.get("https://www.google.com")  # 초기 페이지 로드
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

