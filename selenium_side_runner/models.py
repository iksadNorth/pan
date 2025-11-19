from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class SideCommand:
    id: str
    command: str
    target: str = ""
    value: str = ""
    comment: str | None = None


@dataclass(slots=True)
class SideTest:
    id: str
    name: str
    commands: List[SideCommand] = field(default_factory=list)


@dataclass(slots=True)
class SideSuite:
    id: str
    name: str
    tests: List[str]
    persist_session: bool = False
    parallel: bool = False
    timeout: Optional[int] = None


@dataclass(slots=True)
class SideProject:
    id: str
    name: str
    url: str | None
    tests: Dict[str, SideTest]
    suites: List[SideSuite]

    def get_suite(self, suite_name: str | None) -> SideSuite:
        if suite_name is None:
            if not self.suites:
                raise ValueError("프로젝트에 실행 가능한 Suite가 없습니다.")
            return self.suites[0]

        for suite in self.suites:
            if suite.name == suite_name:
                return suite

        raise ValueError(f"Suite '{suite_name}' 를 찾을 수 없습니다.")

    def get_test_by_name(self, test_name: str) -> SideTest:
        for test in self.tests.values():
            if test.name == test_name:
                return test

        raise ValueError(f"테스트 '{test_name}' 를 찾을 수 없습니다.")

