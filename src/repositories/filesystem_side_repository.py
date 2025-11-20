"""Filesystem 기반 Side Repository 구현체."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .side_repository import SideRepository


class FilesystemSideRepository(SideRepository):
    """Filesystem을 사용한 Side Repository 구현체."""

    def __init__(self, base_dir: Path | str):
        """FilesystemSideRepository를 초기화합니다.

        Args:
            base_dir: Side 파일을 저장할 기본 디렉토리 경로
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, side_id: str) -> Path:
        """Side ID에 해당하는 파일 경로를 반환합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Returns:
            파일 경로
        """
        # side_id에 안전한 파일명으로 변환
        safe_id = side_id.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_id}.side"

    def save(self, side_id: str, content: str) -> None:
        """Side 파일을 저장합니다.

        Args:
            side_id: Side 파일의 고유 ID
            content: Side 파일의 JSON 문자열 내용
        """
        # JSON 유효성 검사
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"유효하지 않은 JSON 형식: {e}")

        file_path = self._get_file_path(side_id)
        file_path.write_text(content, encoding="utf-8")

    def get(self, side_id: str) -> str:
        """Side 파일을 조회합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Returns:
            Side 파일의 JSON 문자열 내용

        Raises:
            FileNotFoundError: Side 파일이 존재하지 않을 때
        """
        file_path = self._get_file_path(side_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Side 파일을 찾을 수 없습니다: {side_id}")
        return file_path.read_text(encoding="utf-8")

    def list_all(self) -> List[str]:
        """저장된 모든 Side 파일 ID 목록을 반환합니다.

        Returns:
            Side 파일 ID 목록
        """
        if not self.base_dir.exists():
            return []

        side_files = list(self.base_dir.glob("*.side"))
        # 파일명에서 .side 확장자를 제거하고 원래 ID로 복원
        # 실제로는 저장 시 변환된 형태이므로, 여기서는 파일명을 그대로 반환
        # 필요시 역변환 로직 추가 가능
        return [f.stem for f in side_files]

    def delete(self, side_id: str) -> None:
        """Side 파일을 삭제합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Raises:
            FileNotFoundError: Side 파일이 존재하지 않을 때
        """
        file_path = self._get_file_path(side_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Side 파일을 찾을 수 없습니다: {side_id}")
        file_path.unlink()

    def exists(self, side_id: str) -> bool:
        """Side 파일이 존재하는지 확인합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Returns:
            존재 여부
        """
        file_path = self._get_file_path(side_id)
        return file_path.exists()

