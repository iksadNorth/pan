from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from .logger_config import log_method_call
from .models import SideCommand, SideProject, SideSuite, SideTest

BrowserFactory = Callable[[], webdriver.Remote]


@log_method_call
def execute_javascript(driver: webdriver.Remote, code: str) -> Any:
    """JavaScript 코드를 실행합니다.
    
    Args:
        driver: WebDriver 인스턴스
        code: 실행할 JavaScript 코드
    
    Returns:
        JavaScript 실행 결과
    """
    return driver.execute_script(code)


@dataclass(slots=True)
class CommandContext:
    driver: webdriver.Remote
    base_url: str | None = None


class CommandExecutor:
    LOCATOR_PREFIX_MAP = {
        "css=": By.CSS_SELECTOR,
        "xpath=": By.XPATH,
        "id=": By.ID,
        "name=": By.NAME,
        "link=": By.LINK_TEXT,
        "linkText=": By.LINK_TEXT,
        "partialLinkText=": By.PARTIAL_LINK_TEXT,
    }

    # Selenium IDE 특수 키 매핑
    KEY_MAP = {
        "${KEY_ENTER}": Keys.RETURN,
        "${KEY_TAB}": Keys.TAB,
        "${KEY_ESCAPE}": Keys.ESCAPE,
        "${KEY_BACKSPACE}": Keys.BACKSPACE,
        "${KEY_DELETE}": Keys.DELETE,
        "${KEY_UP}": Keys.UP,
        "${KEY_DOWN}": Keys.DOWN,
        "${KEY_LEFT}": Keys.LEFT,
        "${KEY_RIGHT}": Keys.RIGHT,
        "${KEY_HOME}": Keys.HOME,
        "${KEY_END}": Keys.END,
        "${KEY_PAGEUP}": Keys.PAGE_UP,
        "${KEY_PAGEDOWN}": Keys.PAGE_DOWN,
        "${KEY_SPACE}": Keys.SPACE,
        "${KEY_F1}": Keys.F1,
        "${KEY_F2}": Keys.F2,
        "${KEY_F3}": Keys.F3,
        "${KEY_F4}": Keys.F4,
        "${KEY_F5}": Keys.F5,
        "${KEY_F6}": Keys.F6,
        "${KEY_F7}": Keys.F7,
        "${KEY_F8}": Keys.F8,
        "${KEY_F9}": Keys.F9,
        "${KEY_F10}": Keys.F10,
        "${KEY_F11}": Keys.F11,
        "${KEY_F12}": Keys.F12,
    }
    
    def __init__(self, context: CommandContext):
        self.context = context
        self._handlers = {
            "open": self.handle_open,
            "click": self.handle_click,
            "clickAndWait": self.handle_clickAndWait,
            "type": self.handle_type,
            "sendKeys": self.handle_sendKeys,
            "pause": self.handle_pause,
            "mouseOver": self.handle_mouseOver,
            "setWindowSize": self.handle_setWindowSize,
            "assertText": self.handle_assertText,
            "assertElementPresent": self.handle_assertElementPresent,
            "storeText": self.handle_storeText,
        }

    @log_method_call
    def _resolve_locator(self, locator: str) -> tuple[str, str]:
        for prefix, by in self.LOCATOR_PREFIX_MAP.items():
            if locator.startswith(prefix):
                return by, locator[len(prefix) :]
        if locator.startswith("//"):
            return By.XPATH, locator
        return By.CSS_SELECTOR, locator

    @log_method_call
    def _resolve_keys(self, value: str) -> str | Keys | list[Any]:
        """Selenium IDE 특수 키 문자열을 Selenium Keys로 변환합니다.
        
        Args:
            value: 키 값 문자열 (예: "${KEY_ENTER}", "hello${KEY_ENTER}")
        
        Returns:
            변환된 키 값 (특수 키가 포함된 경우 Keys 객체, 문자열, 또는 리스트)
        """
        if not value:
            return value
        
        # 정확히 특수 키만 있는 경우
        if value in self.KEY_MAP:
            return self.KEY_MAP[value]
        
        # 특수 키가 포함된 문자열인 경우 파싱
        result: list[Any] = []
        remaining = value
        while remaining:
            # 가장 먼저 매칭되는 특수 키 찾기
            found = False
            for key_pattern, key_value in self.KEY_MAP.items():
                if key_pattern in remaining:
                    idx = remaining.index(key_pattern)
                    # 특수 키 앞의 일반 텍스트 추가
                    if idx > 0:
                        result.append(remaining[:idx])
                    # 특수 키 추가
                    result.append(key_value)
                    # 남은 부분 처리
                    remaining = remaining[idx + len(key_pattern):]
                    found = True
                    break
            
            if not found:
                # 더 이상 특수 키가 없으면 남은 부분 모두 추가
                result.append(remaining)
                break
        
        # 결과가 하나이고 Keys 객체인 경우 그대로 반환
        if len(result) == 1:
            return result[0]
        
        # 여러 개인 경우 리스트로 반환 (send_keys는 리스트도 받을 수 있음)
        return result

    @log_method_call
    def execute(self, command: SideCommand) -> None:
        handler = self._handlers.get(command.command)
        if handler is None:
            raise NotImplementedError(f"지원되지 않는 커맨드: {command.command}")
        handler(command)

    @log_method_call
    def handle_open(self, command: SideCommand) -> None:
        target = command.target.strip()
        if not target:
            return
        url = target
        if self.context.base_url and not target.startswith(("http://", "https://")):
            url = urljoin(self.context.base_url, target)
        self.context.driver.get(url)

    @log_method_call
    def handle_click(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        element.click()

    @log_method_call
    def handle_clickAndWait(self, command: SideCommand) -> None:
        self.handle_click(command)
        if command.value:
            self.handle_pause(command)

    @log_method_call
    def handle_type(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        element.clear()
        element.send_keys(command.value)

    @log_method_call
    def handle_sendKeys(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        keys = self._resolve_keys(command.value)
        # send_keys는 str, Keys, 또는 리스트를 모두 받을 수 있음
        element.send_keys(keys)  # type: ignore[arg-type]

    @log_method_call
    def handle_pause(self, command: SideCommand) -> None:
        delay_ms = float(command.value or command.target or "0")
        time.sleep(delay_ms / 1000 if delay_ms > 10 else delay_ms)

    @log_method_call
    def handle_mouseOver(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        ActionChains(self.context.driver).move_to_element(element).perform()

    @log_method_call
    def handle_setWindowSize(self, command: SideCommand) -> None:
        size_text = (command.target or command.value or "").strip().lower().replace(" ", "")
        if not size_text:
            return
        delimiter = "x" if "x" in size_text else ","
        try:
            width_str, height_str = size_text.split(delimiter, 1)
            width = int(width_str)
            height = int(height_str)
        except ValueError as exc:
            raise ValueError(f"setWindowSize 포맷 오류: '{command.target or command.value}'") from exc
        self.context.driver.set_window_size(width, height)

    @log_method_call
    def handle_assertText(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        actual = element.text.strip()
        expected = command.value.strip()
        if actual != expected:
            raise AssertionError(f"텍스트 불일치: expected '{expected}', got '{actual}'")

    @log_method_call
    def handle_assertElementPresent(self, command: SideCommand) -> None:
        self._find_element(command.target)

    @log_method_call
    def handle_storeText(self, command: SideCommand) -> None:
        # comment 필드에 JavaScript 코드가 있으면 실행
        if command.comment and command.comment.strip():
            js_code = command.comment.strip()
            self.context.driver.execute_script(js_code)
        else:
            # comment가 없으면 기존 동작 유지 (하위 호환성)
            element = self._find_element(command.target)
            _ = element.text  # 추후 확장을 위해 자리만 확보

    @log_method_call
    def _find_element(self, locator: str):
        by, value = self._resolve_locator(locator)
        try:
            return self.context.driver.find_element(by, value)
        except NoSuchElementException as exc:
            raise NoSuchElementException(f"요소를 찾을 수 없습니다: {locator}") from exc


class SeleniumSideRunner:
    def __init__(
        self,
        project: SideProject,
        driver_factory: BrowserFactory,
        implicit_wait: float = 5.0,
        base_url: str | None = None,
    ):
        self.project = project
        self.driver_factory = driver_factory
        self.implicit_wait = implicit_wait
        self.base_url = base_url or project.url

    @contextmanager
    def _driver_session(self):
        driver = self.driver_factory()
        driver.implicitly_wait(self.implicit_wait)
        try:
            yield driver
        finally:
            driver.quit()

    @log_method_call
    def run_suite(self, suite: SideSuite) -> None:
        tests = [self.project.tests[test_id] for test_id in suite.tests]
        if suite.persist_session:
            with self._driver_session() as driver:
                self._run_tests(driver, tests)
        else:
            for test in tests:
                with self._driver_session() as driver:
                    self._run_tests(driver, [test])

    @log_method_call
    def run_test(self, test: SideTest) -> None:
        with self._driver_session() as driver:
            self._run_tests(driver, [test])

    @log_method_call
    def run_test_with_driver(self, test: SideTest, driver: webdriver.Remote) -> None:
        """기존 WebDriver를 사용하여 테스트를 실행합니다.

        Args:
            test: 실행할 테스트
            driver: 사용할 WebDriver 인스턴스 (quit()하지 않음)
        """
        driver.implicitly_wait(self.implicit_wait)
        self._run_tests(driver, [test])

    @log_method_call
    def run_suite_with_driver(self, suite: SideSuite, driver: webdriver.Remote) -> None:
        """기존 WebDriver를 사용하여 Suite를 실행합니다.

        Args:
            suite: 실행할 Suite
            driver: 사용할 WebDriver 인스턴스 (quit()하지 않음)
        """
        driver.implicitly_wait(self.implicit_wait)
        tests = [self.project.tests[test_id] for test_id in suite.tests]
        self._run_tests(driver, tests)

    @log_method_call
    def _run_tests(self, driver, tests: Iterable[SideTest]) -> None:
        context = CommandContext(driver=driver, base_url=self.base_url)
        executor = CommandExecutor(context)
        for test in tests:
            for command in test.commands:
                executor.execute(command)

    @log_method_call
    def execute_side_on_driver(
        self,
        driver: webdriver.Remote,
        suite: str | None = None,
        test: str | None = None,
    ) -> str:
        """기존 WebDriver를 사용하여 Side 프로젝트를 실행합니다.
        
        Args:
            driver: 사용할 WebDriver 인스턴스 (quit()하지 않음)
            suite: 실행할 Suite 이름 (선택)
            test: 실행할 Test 이름 (선택)
        
        Returns:
            실행 후 페이지 소스
        """
        # Suite 또는 Test 실행
        if test:
            test_obj = self.project.get_test_by_name(test)
            self.run_test_with_driver(test_obj, driver)
        else:
            suite_obj = self.project.get_suite(suite)
            self.run_suite_with_driver(suite_obj, driver)
        
        # 실행 후 페이지 소스 반환
        return driver.page_source
