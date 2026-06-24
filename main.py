"""Project startup entry point."""

from __future__ import annotations

import argparse

from dataclasses import replace

from douyin_academic_crawler.runtime import launch_gui, load_runtime_config, run_mock_acceptance_task


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Start the Douyin academic crawler local desktop app.",
    )
    parser.add_argument("--config", help="Path to a JSON config file.", default=None)
    parser.add_argument(
        "--mock-run",
        action="store_true",
        help="Run one fixture-backed mock collection task without opening the GUI.",
    )
    parser.add_argument(
        "--local-json",
        help="Run with a local JSON comment tree file as the offline input source.",
        default=None,
    )
    return parser


def main() -> int:
    """Run the local GUI or a mock acceptance task."""

    args = build_parser().parse_args()
    try:
        if args.mock_run:
            print("loading config", flush=True)
            config = load_runtime_config(args.config)
            if args.local_json:
                config = replace(
                    config,
                    input_mode="local_json",
                    input_json_file=args.local_json,
                    mock_mode=True,
                    allow_real_requests=False,
                )
            result = run_mock_acceptance_task(config, progress=lambda message: print(message, flush=True))
            return 0 if result.status.value == "success" else 1

        config = load_runtime_config(args.config)
        launch_gui(config)
        return 0
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
