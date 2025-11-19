from __future__ import annotations

import argparse
import sys
from pathlib import Path

from selenium_side_runner import (
    SeleniumSideRunner,
    create_webdriver_factory,
    load_side_project,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ide-lab",
        description="Selenium IDE (.side) 실행 도구",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help=".side 파일 내 Suite/Test 확인")
    list_parser.add_argument("side_file", type=Path, help=".side 파일 경로")

    run_parser = subparsers.add_parser("run", help="Suite 또는 Test 실행")
    run_parser.add_argument("side_file", type=Path, help=".side 파일 경로")
    run_parser.add_argument("--suite", help="실행할 Suite 이름")
    run_parser.add_argument("--test", help="Suite 대신 단일 테스트 실행")
    run_parser.add_argument(
        "--browser",
        default="chrome",
        choices=("chrome", "firefox", "edge"),
        help="사용할 WebDriver",
    )
    run_parser.add_argument("--base-url", help=".side 기본 URL을 덮어쓰기")
    run_parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    run_parser.add_argument(
        "--implicit-wait",
        type=float,
        default=5.0,
        help="암묵적 대기 시간(초)",
    )

    return parser


def cmd_list(side_file: Path) -> int:
    project = load_side_project(side_file)
    print(f"프로젝트: {project.name}")
    print("Suites:")
    for suite in project.suites:
        tests = ", ".join(project.tests[test_id].name for test_id in suite.tests)
        print(f"  - {suite.name} ({tests})")
    print("Tests:")
    for test in project.tests.values():
        print(f"  - {test.name} ({len(test.commands)} commands)")
    return 0


def cmd_run(
    side_file: Path,
    suite: str | None,
    test_name: str | None,
    browser: str,
    headless: bool,
    base_url: str | None,
    implicit_wait: float,
) -> int:
    project = load_side_project(side_file)
    runner = SeleniumSideRunner(
        project=project,
        driver_factory=create_webdriver_factory(browser, headless=headless),
        implicit_wait=implicit_wait,
        base_url=base_url,
    )

    if test_name:
        test = project.get_test_by_name(test_name)
        runner.run_test(test)
    else:
        suite_obj = project.get_suite(suite)
        runner.run_suite(suite_obj)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args.side_file)
    if args.command == "run":
        return cmd_run(
            side_file=args.side_file,
            suite=args.suite,
            test_name=args.test,
            browser=args.browser,
            headless=args.headless,
            base_url=args.base_url,
            implicit_wait=args.implicit_wait,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
