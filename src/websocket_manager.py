"""웹소켓 연결 및 세션 관리."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel, ValidationError

from src.logger_config import get_logger, log_method_call
from src.repositories import (
    FilesystemLockRepository,
    LockRepository,
    SideRepository,
)
from src.session_pool import SessionPool

logger = get_logger(__name__)


# Pydantic 모델
class ExecuteJSRequest(BaseModel):
    """JavaScript 실행 요청 모델."""

    code: str


class ExecuteSideRequest(BaseModel):
    """Side 파일 실행 요청 모델."""

    side_id: str
    suite: str | None = None
    test: str | None = None
    param: dict[str, str] | None = None


@dataclass
class WSConnection:
    """웹소켓 연결 정보."""

    connection_id: str
    websocket: WebSocket
    session_id: str
    lock_uuid: str | None = None


class WSConnectionManager:
    """웹소켓 연결 및 세션 관리 클래스."""

    def __init__(
        self,
        lock_repository: LockRepository,
        session_pool: SessionPool,
        side_repository: SideRepository,
    ):
        """WSConnectionManager를 초기화합니다.

        Args:
            lock_repository: Lock 관리 Repository
            session_pool: 세션 풀
            side_repository: Side 파일 Repository
        """
        self.lock_repository = lock_repository
        self.session_pool = session_pool
        self.side_repository = side_repository
        self.connections: dict[str, WSConnection] = {}
        self._handlers = {
            "execute_js": self._handle_execute_js,
            "execute_side": self._handle_execute_side,
            "get_page_source": self._handle_get_page_source,
        }

    @log_method_call
    async def connect_auto(self, websocket: WebSocket) -> str:
        """사용 가능한 세션을 자동으로 찾아 웹소켓 연결을 수락하고 락을 획득합니다.

        Args:
            websocket: 웹소켓 연결 객체

        Returns:
            connection_id: 연결 고유 ID

        Raises:
            ValueError: 사용 가능한 세션이 없거나 락 획득 실패 시
        """
        # 사용 가능한 세션 찾기 (generator 사용)
        for session_id in self.session_pool.iter_available_sessions(self.lock_repository):
            lock_key = f"session_{session_id}"
            
            # Lock이 잠겨있지 않으면 획득 시도
            if isinstance(self.lock_repository, FilesystemLockRepository):
                try:
                    # TTL 없이 락 획득 (None 전달)
                    expires_at, lock_uuid = self.lock_repository._acquire_with_ttl_internal(
                        lock_key, ttl_seconds=None, timeout=0.1
                    )
                    
                    # 락 획득 성공 - 이 세션 사용
                    connection_id = str(uuid.uuid4())
                    connection = WSConnection(
                        connection_id=connection_id,
                        websocket=websocket,
                        session_id=session_id,
                        lock_uuid=lock_uuid,
                    )
                    self.connections[connection_id] = connection

                    logger.info(f"웹소켓 자동 연결 성공: connection_id={connection_id}, session_id={session_id}, lock_uuid={lock_uuid}")
                    return connection_id
                except TimeoutError:
                    # Lock 획득 실패 (다른 프로세스가 먼저 획득), 다음 세션 시도
                    continue

        # 모든 세션이 잠겨있음
        raise ValueError("모든 세션이 사용 중입니다. 잠시 후 다시 시도해주세요.")

    @log_method_call
    async def disconnect(self, connection_id: str) -> None:
        """웹소켓 연결을 해제하고 락을 해제합니다.

        Args:
            connection_id: 연결 고유 ID
        """
        connection = self.connections.pop(connection_id, None)
        if connection is None:
            logger.warning(f"연결을 찾을 수 없습니다: {connection_id}")
            return

        # 락 해제
        lock_key = f"session_{connection.session_id}"
        try:
            self.lock_repository.release(lock_key)
            logger.info(f"웹소켓 연결 해제 및 락 해제: connection_id={connection_id}, session_id={connection.session_id}")
        except Exception as e:
            logger.error(f"락 해제 실패: {e}")

    @log_method_call
    async def handle_message(self, connection_id: str, message: dict[str, Any]) -> dict[str, Any]:
        """웹소켓 메시지를 처리합니다.

        Args:
            connection_id: 연결 고유 ID
            message: 메시지 딕셔너리

        Returns:
            응답 딕셔너리
        """
        connection = self.connections.get(connection_id)
        if connection is None:
            return {"type": "error", "message": "연결을 찾을 수 없습니다."}

        msg_type = message.get("type")
        if not msg_type:
            return {"type": "error", "message": "메시지 타입이 필요합니다."}

        handler = self._handlers.get(msg_type)
        if handler is None:
            return {"type": "error", "message": f"지원되지 않는 메시지 타입: {msg_type}"}

        try:
            return await handler(connection, message)
        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {e}", exc_info=True)
            return {"type": "error", "message": str(e)}

    async def _handle_execute_js(self, connection: WSConnection, message: dict[str, Any]) -> dict[str, Any]:
        """JavaScript 코드 실행을 처리합니다.

        Args:
            connection: 웹소켓 연결 정보
            message: 메시지 딕셔너리 (code 필드 포함)

        Returns:
            실행 결과 딕셔너리
        """
        from src.runner import execute_javascript

        # Pydantic 모델로 검증
        try:
            request = ExecuteJSRequest(**message)
        except ValidationError as e:
            return {"type": "error", "message": f"요청 검증 실패: {e.errors()[0]['msg']}"}

        # 세션 획득 및 JS 실행
        loop = asyncio.get_event_loop()
        try:
            with self.session_pool.acquire_session(connection.session_id) as driver:
                # runner.py의 execute_javascript 함수 재사용
                result = await loop.run_in_executor(
                    None,
                    lambda: execute_javascript(driver, request.code)
                )
                return {"type": "result", "data": result}
        except ValueError as e:
            return {"type": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"JS 실행 중 오류: {e}", exc_info=True)
            return {"type": "error", "message": f"JS 실행 실패: {str(e)}"}

    async def _handle_execute_side(self, connection: WSConnection, message: dict[str, Any]) -> dict[str, Any]:
        """Side 파일 실행을 처리합니다.

        Args:
            connection: 웹소켓 연결 정보
            message: 메시지 딕셔너리 (side_id, suite, test, param 필드 포함)

        Returns:
            실행 결과 딕셔너리
        """
        from src import SeleniumSideRunner, load_side_project
        from src.parser import Parser

        # Pydantic 모델로 검증
        try:
            request = ExecuteSideRequest(**message)
        except ValidationError as e:
            return {"type": "error", "message": f"요청 검증 실패: {e.errors()[0]['msg']}"}

        # Side 파일 로드 및 렌더링 (main.py의 _load_and_render_side 로직 재사용)
        try:
            side_content = self.side_repository.get(request.side_id)
        except FileNotFoundError:
            return {"type": "error", "message": f"Side 파일을 찾을 수 없습니다: {request.side_id}"}

        # jinja2 템플릿 렌더링
        if request.param:
            try:
                parser = Parser(request.param)
                side_content = parser.render(side_content)
            except Exception as e:
                return {"type": "error", "message": f"템플릿 렌더링 실패: {str(e)}"}

        # Side 프로젝트 로드
        try:
            project = load_side_project(side_content)
        except Exception as e:
            return {"type": "error", "message": f"Side 파일 파싱 실패: {str(e)}"}

        # 세션 획득 및 Side 실행 (runner.py의 execute_side_on_driver 메서드 재사용)
        loop = asyncio.get_event_loop()
        try:
            with self.session_pool.acquire_session(connection.session_id) as driver:
                runner = SeleniumSideRunner(
                    project=project,
                    driver_factory=lambda: driver,
                    implicit_wait=5.0,
                    base_url=project.url,
                )

                # runner.py의 execute_side_on_driver 메서드 재사용
                page_source = await loop.run_in_executor(
                    None,
                    lambda: runner.execute_side_on_driver(driver, suite=request.suite, test=request.test)
                )
                return {"type": "result", "data": page_source}
        except ValueError as e:
            return {"type": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Side 실행 중 오류: {e}", exc_info=True)
            return {"type": "error", "message": f"Side 실행 실패: {str(e)}"}

    async def _handle_get_page_source(self, connection: WSConnection, message: dict[str, Any]) -> dict[str, Any]:
        """페이지 소스를 조회합니다.

        Args:
            connection: 웹소켓 연결 정보
            message: 메시지 딕셔너리 (사용하지 않음, 시그니처 통일을 위해 포함)

        Returns:
            페이지 소스 딕셔너리
        """
        loop = asyncio.get_event_loop()
        try:
            with self.session_pool.acquire_session(connection.session_id) as driver:
                page_source = await loop.run_in_executor(
                    None,
                    lambda: driver.page_source
                )
                return {"type": "result", "data": page_source}
        except ValueError as e:
            return {"type": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"페이지 소스 조회 중 오류: {e}", exc_info=True)
            return {"type": "error", "message": f"페이지 소스 조회 실패: {str(e)}"}
