from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import SideCommand, SideProject, SideSuite, SideTest


def _build_command(raw: Dict[str, Any]) -> SideCommand:
    return SideCommand(
        id=raw.get("id", ""),
        command=raw.get("command", ""),
        target=raw.get("target", "") or "",
        value=raw.get("value", "") or "",
        comment=raw.get("comment"),
    )


def _build_test(raw: Dict[str, Any]) -> SideTest:
    commands = [_build_command(command) for command in raw.get("commands", [])]
    return SideTest(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        commands=commands,
    )


def _build_suite(raw: Dict[str, Any]) -> SideSuite:
    return SideSuite(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        tests=list(raw.get("tests", [])),
        persist_session=bool(raw.get("persistSession", False)),
        parallel=bool(raw.get("parallel", False)),
        timeout=raw.get("timeout"),
    )


def load_side_project(path: str | Path) -> SideProject:
    """Selenium IDE .side 파일을 읽어 SideProject 객체로 반환."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f".side 파일을 찾을 수 없습니다: {file_path}")

    with file_path.open(encoding="utf-8") as fp:
        raw_project = json.load(fp)

    tests = [_build_test(test) for test in raw_project.get("tests", [])]
    test_map = {test.id: test for test in tests}

    suites = [_build_suite(suite) for suite in raw_project.get("suites", [])]

    return SideProject(
        id=raw_project.get("id", ""),
        name=raw_project.get("name", file_path.stem),
        url=raw_project.get("url"),
        tests=test_map,
        suites=suites,
    )

