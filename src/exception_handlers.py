"""FastAPI 예외 핸들러."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from src.side_service import (
    SideFileNotFoundError,
    SideFileParseError,
    SideTemplateRenderError,
)


def register_exception_handlers(app):
    """FastAPI 앱에 예외 핸들러를 등록합니다.

    Args:
        app: FastAPI 앱 인스턴스
    """
    @app.exception_handler(SideFileNotFoundError)
    async def side_file_not_found_handler(request: Request, exc: SideFileNotFoundError):
        """Side 파일을 찾을 수 없을 때 처리."""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    @app.exception_handler(SideTemplateRenderError)
    async def side_template_render_error_handler(
        request: Request, exc: SideTemplateRenderError
    ):
        """Side 파일 템플릿 렌더링 실패 시 처리."""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(SideFileParseError)
    async def side_file_parse_error_handler(request: Request, exc: SideFileParseError):
        """Side 파일 파싱 실패 시 처리."""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
