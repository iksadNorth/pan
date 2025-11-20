"""Side 파일 저장을 위한 Repository 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class SideRepository(ABC):
    """Side 파일 저장을 위한 Repository 인터페이스."""

    @abstractmethod
    def save(self, side_id: str, content: str) -> None:
        """Side 파일을 저장합니다.

        Args:
            side_id: Side 파일의 고유 ID
            content: Side 파일의 JSON 문자열 내용
        """
        pass

    @abstractmethod
    def get(self, side_id: str) -> str:
        """Side 파일을 조회합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Returns:
            Side 파일의 JSON 문자열 내용

        Raises:
            FileNotFoundError: Side 파일이 존재하지 않을 때
        """
        pass

    @abstractmethod
    def list_all(self) -> List[str]:
        """저장된 모든 Side 파일 ID 목록을 반환합니다.

        Returns:
            Side 파일 ID 목록
        """
        pass

    @abstractmethod
    def delete(self, side_id: str) -> None:
        """Side 파일을 삭제합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Raises:
            FileNotFoundError: Side 파일이 존재하지 않을 때
        """
        pass

    @abstractmethod
    def exists(self, side_id: str) -> bool:
        """Side 파일이 존재하는지 확인합니다.

        Args:
            side_id: Side 파일의 고유 ID

        Returns:
            존재 여부
        """
        pass

