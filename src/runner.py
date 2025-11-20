from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from .models import SideCommand, SideProject, SideSuite, SideTest

BrowserFactory = Callable[[], webdriver.Remote]


LOCATOR_PREFIX_MAP = {
    "css=": By.CSS_SELECTOR,
    "xpath=": By.XPATH,
    "id=": By.ID,
    "name=": By.NAME,
    "link=": By.LINK_TEXT,
    "linkText=": By.LINK_TEXT,
    "partialLinkText=": By.PARTIAL_LINK_TEXT,
}


def _resolve_locator(locator: str) -> tuple[str, str]:
    for prefix, by in LOCATOR_PREFIX_MAP.items():
        if locator.startswith(prefix):
            return by, locator[len(prefix) :]
    if locator.startswith("//"):
        return By.XPATH, locator
    return By.CSS_SELECTOR, locator


@dataclass(slots=True)
class CommandContext:
    driver: webdriver.Remote
    base_url: str | None = None


class CommandExecutor:
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

    def execute(self, command: SideCommand) -> None:
        handler = self._handlers.get(command.command)
        if handler is None:
            raise NotImplementedError(f"지원되지 않는 커맨드: {command.command}")
        handler(command)

    def handle_open(self, command: SideCommand) -> None:
        target = command.target.strip()
        if not target:
            return
        url = target
        if self.context.base_url and not target.startswith(("http://", "https://")):
            url = urljoin(self.context.base_url, target)
        self.context.driver.get(url)

    def handle_click(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        element.click()

    def handle_clickAndWait(self, command: SideCommand) -> None:
        self.handle_click(command)
        if command.value:
            self.handle_pause(command)

    def handle_type(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        element.clear()
        element.send_keys(command.value)

    def handle_sendKeys(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        element.send_keys(command.value)

    def handle_pause(self, command: SideCommand) -> None:
        delay_ms = float(command.value or command.target or "0")
        time.sleep(delay_ms / 1000 if delay_ms > 10 else delay_ms)

    def handle_mouseOver(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        ActionChains(self.context.driver).move_to_element(element).perform()

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

    def handle_assertText(self, command: SideCommand) -> None:
        element = self._find_element(command.target)
        actual = element.text.strip()
        expected = command.value.strip()
        if actual != expected:
            raise AssertionError(f"텍스트 불일치: expected '{expected}', got '{actual}'")

    def handle_assertElementPresent(self, command: SideCommand) -> None:
        self._find_element(command.target)

    def handle_storeText(self, command: SideCommand) -> None:
        # 단순 지원: storeText 는 assert 처럼 바로 출력만 수행
        element = self._find_element(command.target)
        _ = element.text  # 추후 확장을 위해 자리만 확보

    def _find_element(self, locator: str):
        by, value = _resolve_locator(locator)
        try:
            return self.context.driver.find_element(by, value)
        except NoSuchElementException as exc:
            raise NoSuchElementException(f"요소를 찾을 수 없습니다: {locator}") from exc


def create_webdriver_factory(browser: str, headless: bool = False) -> BrowserFactory:
    browser = browser.lower()

    def factory() -> webdriver.Remote:
        if browser == "chrome":
            options = ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,720")
            return webdriver.Chrome(options=options)
        if browser == "firefox":
            options = FirefoxOptions()
            if headless:
                options.add_argument("-headless")
            return webdriver.Firefox(options=options)
        if browser == "edge":
            options = EdgeOptions()
            if headless:
                options.add_argument("--headless=new")
            return webdriver.Edge(options=options)
        raise ValueError(f"지원되지 않는 브라우저: {browser}")

    return factory


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

    def run_suite(self, suite: SideSuite) -> None:
        tests = [self.project.tests[test_id] for test_id in suite.tests]
        if suite.persist_session:
            with self._driver_session() as driver:
                self._run_tests(driver, tests)
        else:
            for test in tests:
                with self._driver_session() as driver:
                    self._run_tests(driver, [test])

    def run_test(self, test: SideTest) -> None:
        with self._driver_session() as driver:
            self._run_tests(driver, [test])

    def run_test_with_driver(self, test: SideTest, driver: webdriver.Remote) -> None:
        """기존 WebDriver를 사용하여 테스트를 실행합니다.

        Args:
            test: 실행할 테스트
            driver: 사용할 WebDriver 인스턴스 (quit()하지 않음)
        """
        driver.implicitly_wait(self.implicit_wait)
        self._run_tests(driver, [test])

    def run_suite_with_driver(self, suite: SideSuite, driver: webdriver.Remote) -> None:
        """기존 WebDriver를 사용하여 Suite를 실행합니다.

        Args:
            suite: 실행할 Suite
            driver: 사용할 WebDriver 인스턴스 (quit()하지 않음)
        """
        driver.implicitly_wait(self.implicit_wait)
        tests = [self.project.tests[test_id] for test_id in suite.tests]
        self._run_tests(driver, tests)

    def _run_tests(self, driver, tests: Iterable[SideTest]) -> None:
        context = CommandContext(driver=driver, base_url=self.base_url)
        executor = CommandExecutor(context)
        for test in tests:
            for command in test.commands:
                executor.execute(command)

