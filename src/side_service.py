"""Side 파일 로드 및 렌더링 서비스."""

from __future__ import annotations


class SideFileNotFoundError(FileNotFoundError):
    """Side 파일을 찾을 수 없을 때 발생하는 예외."""
    pass


class SideFileParseError(ValueError):
    """Side 파일 파싱 실패 시 발생하는 예외."""
    pass


class SideTemplateRenderError(ValueError):
    """Side 파일 템플릿 렌더링 실패 시 발생하는 예외."""
    pass


from src import load_side_project
from src.logger_config import get_logger, log_method_call
from src.models import SideProject
from src.parser import Parser
from src.repositories import SideRepository

logger = get_logger(__name__)


class SideService:
    """Side 파일 로드 및 렌더링을 담당하는 서비스 클래스."""

    def __init__(self, side_repository: SideRepository):
        """SideService를 초기화합니다.

        Args:
            side_repository: Side 파일 Repository
        """
        self.side_repository = side_repository

    @log_method_call
    def load_and_render(
        self, side_id: str, params: dict[str, str] | None = None
    ) -> SideProject:
        """Side 파일을 로드하고 렌더링하여 SideProject 객체를 반환합니다.

        Args:
            side_id: Side 파일 ID
            params: jinja2 템플릿 파라미터 (선택)

        Returns:
            SideProject 객체

        Raises:
            SideFileNotFoundError: 파일을 찾을 수 없을 때
            SideTemplateRenderError: 템플릿 렌더링 실패 시
            SideFileParseError: Side 파일 파싱 실패 시
        """
        # Side 파일 조회
        try:
            side_content = self.side_repository.get(side_id)
        except FileNotFoundError:
            raise SideFileNotFoundError(f"Side 파일을 찾을 수 없습니다: {side_id}")

        # jinja2 템플릿 렌더링 (param이 있는 경우)
        if params:
            try:
                parser = Parser(params)
                side_content = parser.render(side_content)
            except Exception as e:
                raise SideTemplateRenderError(f"템플릿 렌더링 실패: {str(e)}") from e

        # Side 프로젝트 로드
        try:
            return load_side_project(side_content)
        except Exception as e:
            raise SideFileParseError(f"Side 파일 파싱 실패: {str(e)}") from e
