"""Pan - FastAPI 기반 Selenium IDE (.side) 실행 웹 서버."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from src import SeleniumSideRunner, load_side_project
from src.models import SideProject
from src.logger_config import get_logger, log_method_call, setup_logging
from src.side_service import SideService
from src.exception_handlers import register_exception_handlers
from src.repositories import (
    FilesystemLockRepository,
    FilesystemSideRepository,
    LockRepository,
    SideRepository,
)
from src.session_pool import SessionPool
from src.websocket_manager import WSConnectionManager

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 환경 변수에서 설정 읽기
SIDE_STORAGE_DIR = Path(os.getenv("SIDE_STORAGE_DIR", "./storage/sides"))
LOCK_STORAGE_DIR = Path(os.getenv("LOCK_STORAGE_DIR", "./storage/locks"))
SELENIUM_GRID_URL = os.getenv("SELENIUM_GRID_URL", "http://localhost:4444")
SESSION_POOL_INIT_TIMEOUT = float(os.getenv("SESSION_POOL_INIT_TIMEOUT", "30.0"))

# Repository 및 Pool 초기화
side_repository: SideRepository = FilesystemSideRepository(SIDE_STORAGE_DIR)
lock_repository: LockRepository = FilesystemLockRepository(LOCK_STORAGE_DIR)
session_pool: SessionPool = SessionPool(SELENIUM_GRID_URL, init_timeout=SESSION_POOL_INIT_TIMEOUT)
side_service: SideService = SideService(side_repository)
ws_manager: WSConnectionManager = WSConnectionManager(
    lock_repository=lock_repository,
    session_pool=session_pool,
    side_service=side_service,
)


@log_method_call
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리."""
    # 시작 시 세션 풀 초기화 (백그라운드에서 비동기 실행)
    logger.info("세션 풀 초기화 시작 (백그라운드 실행)...")
    init_task = asyncio.create_task(session_pool.initialize())
    
    yield
    
    # 종료 시 세션 풀 정리
    logger.info("세션 풀 정리 중...")
    # 초기화가 아직 진행 중이면 취소 시도
    if not init_task.done():
        logger.warning("세션 풀 초기화가 아직 진행 중입니다. 취소 시도...")
        init_task.cancel()
        try:
            await init_task
        except asyncio.CancelledError:
            pass
    session_pool.cleanup()


# FastAPI 앱 생성
app = FastAPI(
    title="Pan",
    description="Selenium IDE .side 파일을 실행하는 웹 API - 양치기 신 Pan처럼 HTML을 뜯어먹고 데이터를 취합니다",
    version="0.1.0",
    lifespan=lifespan,
)

# 예외 핸들러 등록
register_exception_handlers(app)


# Pydantic 모델
class SessionExecuteRequest(BaseModel):
    """세션 실행 요청 모델."""

    side_id: str
    suite: str | None = None
    test: str | None = None
    param: dict[str, str] | None = None
    lock_uuid: str | None = None


class LockAcquireRequest(BaseModel):
    """Lock 획득 요청 모델."""

    ttl_seconds: float
    timeout: float | None = None


# Side 관련 엔드포인트
@log_method_call
@app.post("/api/v1/sides/{side_id}", status_code=status.HTTP_201_CREATED)
async def upload_side(side_id: str, file: UploadFile = File(...)) -> dict:
    """Side 파일을 업로드합니다.

    Args:
        side_id: Side 파일의 고유 ID
        file: 업로드할 Side 파일 (.side 파일)

    Returns:
        업로드 성공 메시지
    """
    try:
        # 파일 내용 읽기
        content = await file.read()
        try:
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일 인코딩 오류: UTF-8 형식의 파일만 지원합니다.",
            )
        
        # JSON 유효성 검사
        load_side_project(content_str)
        side_repository.save(side_id, content_str)
        return {"message": f"Side 파일 '{side_id}'이(가) 성공적으로 업로드되었습니다."}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 Side 파일 형식: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Side 파일 업로드 실패: {str(e)}",
        )


@log_method_call
@app.get("/api/v1/sides")
async def list_sides() -> dict:
    """저장된 모든 Side 파일 목록을 조회합니다.

    Returns:
        Side 파일 ID 목록
    """
    try:
        side_ids = side_repository.list_all()
        return {"sides": side_ids}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Side 파일 목록 조회 실패: {str(e)}",
        )


@log_method_call
@app.get("/api/v1/sides/{side_id}")
async def get_side(side_id: str) -> FileResponse:
    """특정 Side 파일을 다운로드합니다.

    Args:
        side_id: Side 파일의 고유 ID

    Returns:
        Side 파일 (.side 파일)
    """
    try:
        # 파일 시스템 저장소인 경우 파일 경로 직접 반환
        if isinstance(side_repository, FilesystemSideRepository):
            # FilesystemSideRepository의 내부 메서드를 사용하여 파일 경로 얻기
            # side_id를 안전한 파일명으로 변환
            safe_id = side_id.replace("/", "_").replace("\\", "_")
            file_path = side_repository.base_dir / f"{safe_id}.side"
            if not file_path.exists():
                raise FileNotFoundError(f"Side 파일을 찾을 수 없습니다: {side_id}")
            return FileResponse(
                path=str(file_path),
                filename=f"{side_id}.side",
                media_type="application/json",
            )
        else:
            # 다른 저장소 구현체인 경우 임시 파일 생성
            content = side_repository.get(side_id)
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".side", delete=False, encoding="utf-8") as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            return FileResponse(
                path=tmp_path,
                filename=f"{side_id}.side",
                media_type="application/json",
            )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Side 파일을 찾을 수 없습니다: {side_id}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Side 파일 조회 실패: {str(e)}",
        )


@log_method_call
@app.patch("/api/v1/sides/{side_id}")
async def update_side(side_id: str, file: UploadFile = File(...)) -> dict:
    """Side 파일을 수정합니다.

    Args:
        side_id: Side 파일의 고유 ID
        file: 수정할 Side 파일 (.side 파일)

    Returns:
        수정 성공 메시지
    """
    try:
        # 파일 존재 여부 확인
        if not side_repository.exists(side_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Side 파일을 찾을 수 없습니다: {side_id}",
            )

        # 파일 내용 읽기
        content = await file.read()
        try:
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일 인코딩 오류: UTF-8 형식의 파일만 지원합니다.",
            )

        # JSON 유효성 검사
        load_side_project(content_str)
        side_repository.save(side_id, content_str)
        return {"message": f"Side 파일 '{side_id}'이(가) 성공적으로 수정되었습니다."}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 Side 파일 형식: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Side 파일 수정 실패: {str(e)}",
        )


@log_method_call
@app.delete("/api/v1/sides/{side_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_side(side_id: str) -> None:
    """Side 파일을 삭제합니다.

    Args:
        side_id: Side 파일의 고유 ID
    """
    try:
        side_repository.delete(side_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Side 파일을 찾을 수 없습니다: {side_id}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Side 파일 삭제 실패: {str(e)}",
        )


# Session 관련 엔드포인트
@log_method_call
@app.get("/api/v1/sessions")
async def list_sessions() -> dict:
    """세션 풀에 있는 사용 가능한 세션 목록을 조회합니다.

    Returns:
        세션 ID 목록
    """
    try:
        sessions = session_pool.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 목록 조회 실패: {str(e)}",
        )


@log_method_call
async def _execute_side_on_session(
    session_id: str,
    project: SideProject,
    suite: str | None = None,
    test: str | None = None,
) -> str:
    """특정 세션에서 Side 프로젝트를 실행합니다.
    
    Args:
        session_id: Selenium Grid 세션 ID
        project: 실행할 SideProject 객체
        suite: 실행할 Suite 이름 (선택)
        test: 실행할 Test 이름 (선택)
    
    Returns:
        실행 결과 HTML 문서
    
    Raises:
        HTTPException: 세션을 찾을 수 없거나 실행 실패 시
    """
    try:
        with session_pool.acquire_session(session_id) as driver:
            # Runner 생성 및 실행
            runner = SeleniumSideRunner(
                project=project,
                driver_factory=lambda: driver,
                implicit_wait=5.0,
                base_url=project.url,
            )
            
            # Suite 또는 Test 실행 (세션은 풀에 반환됨)
            if test:
                test_obj = project.get_test_by_name(test)
                runner.run_test_with_driver(test_obj, driver)
            else:
                suite_obj = project.get_suite(suite)
                runner.run_suite_with_driver(suite_obj, driver)
            
            # 실행 후 페이지 소스 반환
            return driver.page_source
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Side 파일 실행 실패: {str(e)}",
        )


@log_method_call
@app.post("/api/v1/sessions", response_class=HTMLResponse)
async def execute_session_auto(request: SessionExecuteRequest) -> str:
    """가용한 세션을 자동으로 찾아서 Side 파일을 실행하고 HTML 문서를 반환합니다.
    
    Args:
        request: 실행할 Side 파일 정보
    
    Returns:
        실행 결과 HTML 문서
    """
    # Side 파일 로드 및 렌더링
    project = side_service.load_and_render(request.side_id, request.param)
    
    # 사용 가능한 세션 찾기 (generator 사용)
    available_sessions = session_pool.list_sessions()
    for session_id in lock_repository.filter_available_sessions(available_sessions):
        lock_key = f"session_{session_id}"
        
        # Lock이 잠겨있지 않으면 획득 시도
        try:
            with lock_repository.acquire(lock_key, timeout=30.0):
                # Lock 획득 성공 - 이 세션 사용
                return await _execute_side_on_session(
                    session_id, project, request.suite, request.test
                )
        except TimeoutError:
            # Lock 획득 실패 (다른 프로세스가 먼저 획득), 다음 세션 시도
            continue
        except HTTPException:
            raise
    
    # 사용 가능한 세션이 없거나 모든 세션이 사용 중
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="사용 가능한 세션이 없습니다. 잠시 후 다시 시도해주세요.",
    )


@log_method_call
@app.post("/api/v1/sessions/{session_id}", response_class=HTMLResponse)
async def execute_session(session_id: str, request: SessionExecuteRequest) -> str:
    """특정 세션에서 Side 파일을 실행하고 HTML 문서를 반환합니다.

    Args:
        session_id: Selenium Grid 세션 ID
        request: 실행할 Side 파일 정보

    Returns:
        실행 결과 HTML 문서
    """
    # Lock 확인 및 검증
    lock_key = f"session_{session_id}"
    lock_info = lock_repository.get_lock_info(lock_key)
    
    # Lock이 존재하는 경우 UUID 검증
    if lock_info.exists:
        if request.lock_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"세션 '{session_id}'는 lock이 걸려있습니다. lock_uuid를 제공해야 합니다.",
            )
        if lock_info.lock_uuid != request.lock_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"세션 '{session_id}'에 대한 lock UUID가 일치하지 않습니다.",
            )
        # UUID가 일치하면 lock을 획득하지 않고 바로 실행
        # (이미 lock이 있으므로)
        project = side_service.load_and_render(request.side_id, request.param)
        return await _execute_side_on_session(
            session_id, project, request.suite, request.test
        )
    
    # Lock이 없는 경우 기존 방식으로 lock 획득 후 실행
    try:
        with lock_repository.acquire(lock_key, timeout=30.0):
            # Side 파일 로드 및 렌더링
            project = side_service.load_and_render(request.side_id, request.param)
            
            # 세션에서 실행
            return await _execute_side_on_session(
                session_id, project, request.suite, request.test
            )

    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"세션 '{session_id}'에 대한 lock 획득 시간 초과",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 실행 실패: {str(e)}",
        )


# Lock 관련 엔드포인트
@log_method_call
@app.post("/api/v1/locks/{session_id}", status_code=status.HTTP_201_CREATED)
async def acquire_lock(session_id: str, request: LockAcquireRequest) -> dict:
    """특정 세션에 대한 락을 획득합니다.

    Args:
        session_id: 세션 ID
        request: Lock 획득 요청 (TTL 포함)

    Returns:
        Lock 획득 성공 메시지 및 만료 시간
    """
    lock_key = f"session_{session_id}"
    try:
        # FilesystemLockRepository의 내부 메서드를 사용하여 lock을 획득 (자동 해제하지 않음)
        if isinstance(lock_repository, FilesystemLockRepository):
            expires_at, lock_uuid = lock_repository._acquire_with_ttl_internal(
                lock_key, request.ttl_seconds, request.timeout
            )
            return {
                "message": f"세션 '{session_id}'에 대한 lock을 획득했습니다.",
                "session_id": session_id,
                "lock_uuid": lock_uuid,
                "expires_at": expires_at.isoformat() if expires_at else None,
            }
        else:
            # 다른 구현체인 경우 context manager 사용 (자동 해제됨)
            with lock_repository.acquire(
                lock_key, timeout=request.timeout, ttl_seconds=request.ttl_seconds
            ):
                lock_info = lock_repository.get_lock_info(lock_key)
                return {
                    "message": f"세션 '{session_id}'에 대한 lock을 획득했습니다.",
                    "session_id": session_id,
                    "lock_uuid": lock_info.lock_uuid,
                    "expires_at": lock_info.expires_at.isoformat() if lock_info.expires_at else None,
                }
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"세션 '{session_id}'에 대한 lock 획득 시간 초과",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lock 획득 실패: {str(e)}",
        )


@log_method_call
@app.delete("/api/v1/locks/{session_id}")
async def release_lock(session_id: str) -> dict:
    """특정 세션에 대한 락을 해제합니다.

    Args:
        session_id: 세션 ID

    Returns:
        Lock 해제 결과 메시지
    """
    lock_key = f"session_{session_id}"
    try:
        released = lock_repository.release(lock_key)
        if released:
            return {
                "message": f"세션 '{session_id}'에 대한 lock을 해제했습니다.",
                "session_id": session_id,
            }
        else:
            return {
                "message": f"세션 '{session_id}'에 대한 lock이 이미 없습니다.",
                "session_id": session_id,
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lock 해제 실패: {str(e)}",
        )


@log_method_call
@app.get("/api/v1/locks/{session_id}")
async def get_lock_info(session_id: str) -> dict:
    """특정 세션에 대한 lock이 존재하는지 확인하고 만료 시간을 조회합니다.

    Args:
        session_id: 세션 ID

    Returns:
        Lock 정보 (존재 여부, 만료 시간)
    """
    lock_key = f"session_{session_id}"
    try:
        lock_info = lock_repository.get_lock_info(lock_key)
        return {
            "session_id": session_id,
            "exists": lock_info.exists,
            "lock_uuid": lock_info.lock_uuid,
            "expires_at": lock_info.expires_at.isoformat() if lock_info.expires_at else None,
            "is_expired": lock_info.is_expired() if lock_info.exists else False,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lock 정보 조회 실패: {str(e)}",
        )


# WebSocket 엔드포인트
@log_method_call
@app.websocket("/ws/sessions")
async def websocket_session_auto(websocket: WebSocket):
    """웹소켓을 통해 사용 가능한 세션을 자동으로 찾아 연결합니다.
    
    연결 시 자동으로 세션에 락을 걸고, 연결 해제 시 자동으로 락을 해제합니다.
    연결 중에는 JavaScript 코드 실행, Side 파일 실행, 페이지 소스 조회 등의 명령을 수행할 수 있습니다.
    
    Args:
        websocket: 웹소켓 연결 객체
    """
    await websocket.accept()
    
    connection_id: str | None = None
    try:
        # 자동으로 사용 가능한 세션 찾아서 연결 및 락 획득
        connection_id = await ws_manager.connect_auto(websocket)
        connection = ws_manager.connections.get(connection_id)
        session_id = connection.session_id if connection else "unknown"
        logger.info(f"웹소켓 자동 연결 성공: session_id={session_id}, connection_id={connection_id}")
        
        # 연결 유지 및 메시지 처리
        while True:
            try:
                # 메시지 수신
                data = await websocket.receive_json()
                
                # 메시지 처리 및 응답 전송
                result = await ws_manager.handle_message(connection_id, data)
                await websocket.send_json(result)
            except WebSocketDisconnect:
                # 정상적인 연결 해제
                break
            except Exception as e:
                # 메시지 처리 중 오류 발생
                logger.error(f"웹소켓 메시지 처리 중 오류: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": f"메시지 처리 실패: {str(e)}"
                })
    except ValueError as e:
        # 사용 가능한 세션 없음 또는 락 획득 실패
        logger.warning(f"웹소켓 자동 연결 실패: {e}")
        await websocket.close(code=1008, reason=str(e))
    except WebSocketDisconnect:
        # 연결이 이미 끊어진 경우
        pass
    except Exception as e:
        # 기타 오류
        logger.error(f"웹소켓 연결 중 오류: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        # 연결 해제 및 락 해제
        if connection_id:
            try:
                await ws_manager.disconnect(connection_id)
            except Exception as e:
                logger.error(f"웹소켓 연결 해제 중 오류: {e}", exc_info=True)


@log_method_call
@app.get("/")
async def root() -> dict:
    """루트 엔드포인트."""
    return {
        "message": "Pan - Selenium IDE Side Runner API",
        "version": "0.1.0",
        "docs": "/docs",
    }
