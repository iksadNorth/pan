"""웹소켓 /ws/sessions 엔드포인트 E2E 테스트.

이 테스트는 실제 FastAPI 앱에 웹소켓으로 연결하는 클라이언트 코드 예시를 제공합니다.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
import websockets
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def mock_webdriver():
    """Mock WebDriver 인스턴스."""
    driver = Mock()
    driver.session_id = "test-session-123"
    driver.page_source = "<html><body>Test Page</body></html>"
    driver.execute_script = Mock(return_value="test-result")
    driver.current_url = "https://example.com"
    return driver


@pytest.fixture
def mock_session_pool(mock_webdriver):
    """Mock SessionPool."""
    pool = Mock()
    pool.list_sessions = Mock(return_value=["session-1", "session-2"])
    
    @contextmanager
    def acquire_session(session_id: str):
        yield mock_webdriver
    
    pool.acquire_session = Mock(side_effect=acquire_session)
    return pool


@pytest.fixture
def mock_lock_repository():
    """Mock LockRepository."""
    repository = Mock()
    
    def filter_available_sessions(session_ids: list[str]):
        for session_id in session_ids:
            yield session_id
    
    repository.filter_available_sessions = Mock(side_effect=filter_available_sessions)
    
    def _acquire_with_ttl_internal(lock_key: str, ttl_seconds: float | None = None, timeout: float = 0.1):
        from datetime import datetime, timedelta
        expires_at = None if ttl_seconds is None else datetime.now() + timedelta(seconds=ttl_seconds)
        lock_uuid = "test-lock-uuid-123"
        return expires_at, lock_uuid
    
    repository._acquire_with_ttl_internal = Mock(side_effect=_acquire_with_ttl_internal)
    repository.release = Mock()
    return repository


@pytest.fixture
def mock_side_service():
    """Mock SideService."""
    from src.models import SideCommand, SideProject, SideSuite, SideTest
    
    test = SideTest(
        id="test-1",
        name="test-1",
        commands=[SideCommand(id="cmd-1", command="open", target="/", value="")],
    )
    suite = SideSuite(id="suite-1", name="suite-1", tests=["test-1"])
    project = SideProject(
        id="test-project",
        name="Test Project",
        url="https://example.com",
        tests={"test-1": test},
        suites=[suite],
    )
    
    service = Mock()
    service.load_and_render = Mock(return_value=project)
    return service


@pytest.fixture
def mock_dependencies(mock_session_pool, mock_lock_repository, mock_side_service):
    """FastAPI 앱의 의존성을 Mock으로 교체."""
    import main
    
    # 원본 저장
    original_session_pool = main.session_pool
    original_lock_repository = main.lock_repository
    original_side_service = main.side_service
    original_ws_manager = main.ws_manager
    
    # Mock으로 교체
    main.session_pool = mock_session_pool
    main.lock_repository = mock_lock_repository
    main.side_service = mock_side_service
    
    from src.websocket_manager import WSConnectionManager
    main.ws_manager = WSConnectionManager(
        lock_repository=mock_lock_repository,
        session_pool=mock_session_pool,
        side_service=mock_side_service,
    )
    
    yield
    
    # 원본 복원
    main.session_pool = original_session_pool
    main.lock_repository = original_lock_repository
    main.side_service = original_side_service
    main.ws_manager = original_ws_manager


@pytest.fixture
async def test_server(mock_dependencies):
    """테스트용 ASGI 서버."""
    import socket
    from uvicorn import Config, Server
    
    # 사용 가능한 포트 찾기
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    
    # lifespan을 우회하기 위해 테스트용 앱 생성
    from fastapi import FastAPI
    test_app = FastAPI()
    
    # 웹소켓 엔드포인트 복사
    @test_app.websocket("/ws/sessions")
    async def websocket_session_auto(websocket):
        from fastapi import WebSocketDisconnect
        import main
        
        await websocket.accept()
        connection_id: str | None = None
        try:
            connection_id = await main.ws_manager.connect_auto(websocket)
            while True:
                try:
                    data = await websocket.receive_json()
                    result = await main.ws_manager.handle_message(connection_id, data)
                    await websocket.send_json(result)
                except WebSocketDisconnect:
                    break
        except Exception as e:
            try:
                await websocket.close(code=1011, reason=str(e))
            except Exception:
                pass
        finally:
            if connection_id:
                await main.ws_manager.disconnect(connection_id)
    
    config = Config(app=test_app, host="127.0.0.1", port=port, log_level="error")
    server = Server(config)
    
    # 서버 시작
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.5)  # 서버 시작 대기
    
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_websocket_e2e_example(test_server, mock_webdriver):
    """웹소켓 E2E 테스트 - 클라이언트 코드 예시.
    
    이 테스트는 실제 클라이언트가 웹소켓을 통해 서버에 연결하고
    명령을 전송하는 전체 흐름을 보여줍니다.
    
    사용 예시:
        ```python
        import asyncio
        import json
        import websockets
        
        async def main():
            async with websockets.connect("ws://localhost:8000/ws/sessions") as websocket:
                # JavaScript 실행
                await websocket.send(json.dumps({
                    "type": "execute_js",
                    "code": "return document.title;",
                }))
                response = json.loads(await websocket.recv())
                print(response)  # {"type": "result", "data": "..."}
                
                # 페이지 소스 조회
                await websocket.send(json.dumps({"type": "get_page_source"}))
                response = json.loads(await websocket.recv())
                print(response)  # {"type": "result", "data": "<html>..."}
                
                # Side 파일 실행
                await websocket.send(json.dumps({
                    "type": "execute_side",
                    "side_id": "my-side-file",
                    "suite": None,
                    "test": None,
                    "param": {"key": "value"},
                }))
                response = json.loads(await websocket.recv())
                print(response)  # {"type": "result", "data": "<html>..."}
        
        asyncio.run(main())
        ```
    """
    # 1. 웹소켓 연결
    async with websockets.connect(f"{test_server}/ws/sessions") as websocket:
        # 연결 성공 확인
        assert websocket is not None
        
        # 2. JavaScript 실행 명령 전송
        await websocket.send(json.dumps({
            "type": "execute_js",
            "code": "return 'Hello from JavaScript!';",
        }))
        
        # 응답 수신
        response = json.loads(await websocket.recv())
        assert response["type"] == "result"
        assert response["data"] == "test-result"
        mock_webdriver.execute_script.assert_called_once_with("return 'Hello from JavaScript!';")
        
        # 3. 페이지 소스 조회 명령 전송
        await websocket.send(json.dumps({
            "type": "get_page_source",
        }))
        
        response = json.loads(await websocket.recv())
        assert response["type"] == "result"
        assert "<html><body>Test Page</body></html>" in response["data"]
        
        # 4. Side 파일 실행 명령 전송
        with patch("src.websocket_manager.SeleniumSideRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.execute_side_on_driver = Mock(return_value="<html>Side executed</html>")
            mock_runner_class.return_value = mock_runner
            
            await websocket.send(json.dumps({
                "type": "execute_side",
                "side_id": "test-side",
                "suite": None,
                "test": None,
                "param": None,
            }))
            
            response = json.loads(await websocket.recv())
            assert response["type"] == "result"
            assert "<html>Side executed</html>" in response["data"]
        
        # 5. 연결 해제 (자동으로 Lock 해제됨)
