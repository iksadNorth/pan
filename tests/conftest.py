"""pytest 설정 및 공통 fixtures."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from unittest.mock import Mock

import pytest
from selenium.webdriver.remote.webdriver import WebDriver


@pytest.fixture
def mock_webdriver() -> Mock:
    """Mock WebDriver 인스턴스."""
    driver = Mock(spec=WebDriver)
    driver.session_id = "test-session-123"
    driver.page_source = "<html><body>Test Page</body></html>"
    driver.execute_script = Mock(return_value="test-result")
    driver.current_url = "https://example.com"
    return driver


@pytest.fixture
def mock_session_pool(mock_webdriver: Mock) -> Mock:
    """Mock SessionPool 인스턴스."""
    pool = Mock()
    pool.list_sessions = Mock(return_value=["session-1", "session-2"])
    
    @contextmanager
    def acquire_session(session_id: str):
        yield mock_webdriver
    
    pool.acquire_session = Mock(side_effect=acquire_session)
    return pool


@pytest.fixture
def mock_lock_repository() -> Mock:
    """Mock LockRepository 인스턴스."""
    repository = Mock()
    
    def filter_available_sessions(session_ids: list[str]) -> Generator[str, None, None]:
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
def mock_side_service() -> Mock:
    """Mock SideService 인스턴스."""
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
