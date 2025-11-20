"""FastAPI 기반 Selenium IDE (.side) 실행 웹 서버."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src import SeleniumSideRunner, create_webdriver_factory, load_side_project
from src.logger_config import get_logger, setup_logging
from src.repositories import (
    FilesystemLockRepository,
    FilesystemSideRepository,
    LockRepository,
    SideRepository,
)
from src.session_pool import SessionPool

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 환경 변수에서 설정 읽기
SIDE_STORAGE_DIR = Path(os.getenv("SIDE_STORAGE_DIR", "./storage/sides"))
LOCK_STORAGE_DIR = Path(os.getenv("LOCK_STORAGE_DIR", "./storage/locks"))
SELENIUM_GRID_URL = os.getenv("SELENIUM_GRID_URL", "http://localhost:4444")
SESSION_POOL_SIZE = int(os.getenv("SESSION_POOL_SIZE", "4"))

# Repository 및 Pool 초기화
side_repository: SideRepository = FilesystemSideRepository(SIDE_STORAGE_DIR)
lock_repository: LockRepository = FilesystemLockRepository(LOCK_STORAGE_DIR)
session_pool: SessionPool = SessionPool(SELENIUM_GRID_URL, pool_size=SESSION_POOL_SIZE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리."""
    # 시작 시 세션 풀 초기화
    logger.info("세션 풀 초기화 중...")
    session_pool.initialize()
    yield
    # 종료 시 세션 풀 정리
    logger.info("세션 풀 정리 중...")
    session_pool.cleanup()


# FastAPI 앱 생성
app = FastAPI(
    title="Selenium IDE Side Runner API",
    description="Selenium IDE .side 파일을 실행하는 웹 API",
    version="0.1.0",
    lifespan=lifespan,
)


# Pydantic 모델
class SideUploadRequest(BaseModel):
    """Side 파일 업로드 요청 모델."""

    content: str


class SideUpdateRequest(BaseModel):
    """Side 파일 수정 요청 모델."""

    content: str


class SessionExecuteRequest(BaseModel):
    """세션 실행 요청 모델."""

    side_id: str
    suite: str | None = None
    test: str | None = None


# Side 관련 엔드포인트
@app.post("/api/v1/sides/{side_id}", status_code=status.HTTP_201_CREATED)
async def upload_side(side_id: str, request: SideUploadRequest) -> dict:
    """Side 파일을 업로드합니다.

    Args:
        side_id: Side 파일의 고유 ID
        request: Side 파일의 JSON 문자열 내용

    Returns:
        업로드 성공 메시지
    """
    try:
        # JSON 유효성 검사
        load_side_project(request.content)
        side_repository.save(side_id, request.content)
        return {"message": f"Side 파일 '{side_id}'이(가) 성공적으로 업로드되었습니다."}
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


@app.get("/api/v1/sides/{side_id}")
async def get_side(side_id: str) -> dict:
    """특정 Side 파일의 내용을 조회합니다.

    Args:
        side_id: Side 파일의 고유 ID

    Returns:
        Side 파일의 JSON 내용
    """
    try:
        content = side_repository.get(side_id)
        return {"side_id": side_id, "content": content}
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


@app.patch("/api/v1/sides/{side_id}")
async def update_side(side_id: str, request: SideUpdateRequest) -> dict:
    """Side 파일을 수정합니다.

    Args:
        side_id: Side 파일의 고유 ID
        request: Side 파일의 JSON 문자열 내용

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

        # JSON 유효성 검사
        load_side_project(request.content)
        side_repository.save(side_id, request.content)
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


@app.post("/api/v1/sessions/{session_id}", response_class=HTMLResponse)
async def execute_session(session_id: str, request: SessionExecuteRequest) -> str:
    """특정 세션에서 Side 파일을 실행하고 HTML 문서를 반환합니다.

    Args:
        session_id: Selenium Grid 세션 ID
        request: 실행할 Side 파일 정보

    Returns:
        실행 결과 HTML 문서
    """
    # Lock 획득 (세션당 하나의 동작만 실행)
    lock_key = f"session_{session_id}"
    try:
        with lock_repository.acquire(lock_key, timeout=30.0):
            # Side 파일 조회
            try:
                side_content = side_repository.get(request.side_id)
            except FileNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Side 파일을 찾을 수 없습니다: {request.side_id}",
                )

            # Side 프로젝트 로드
            try:
                project = load_side_project(side_content)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Side 파일 파싱 실패: {str(e)}",
                )

            # 세션 풀에서 세션 가져오기
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
                    if request.test:
                        test = project.get_test_by_name(request.test)
                        runner.run_test_with_driver(test, driver)
                    else:
                        suite_obj = project.get_suite(request.suite)
                        runner.run_suite_with_driver(suite_obj, driver)

                    # 실행 후 페이지 소스 반환
                    html_content = driver.page_source

                    # 세션은 context manager에 의해 자동으로 풀에 반환됨
                    return html_content

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


@app.get("/")
async def root() -> dict:
    """루트 엔드포인트."""
    return {
        "message": "Selenium IDE Side Runner API",
        "version": "0.1.0",
        "docs": "/docs",
    }
