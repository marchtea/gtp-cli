from __future__ import annotations

import argparse
import sys
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from typing import Callable

from gtp_cli.automation import ConversionRequest, build_applescript, parse_menu_path, run_osascript
from gtp_cli.lick_spec import (
    EXAMPLE_LICK,
    RESOLUTIONS,
    STYLES,
    TECHNIQUES,
    TIME_SIGNATURES,
    TUNINGS,
    build_llm_prompt,
    build_summary,
    dumps_json,
    guitar_lick_schema,
)
from gtp_cli.paths import ensure_output_directories, resolve_conversion_paths

Runner = Callable[[str, int], CompletedProcess[str]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gtp-cli",
        description="Import MusicXML into Guitar Pro 8 and export Guitar Pro/PNG outputs on macOS.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="Convert one MusicXML file through Guitar Pro 8.")
    convert.add_argument("source", type=Path, help="Path to the MusicXML or XML file to import.")
    convert.add_argument("--gpx", type=Path, help="Output Guitar Pro file path. Defaults to SOURCE.gpx.")
    convert.add_argument("--png", type=Path, help="Output PNG file path. Defaults to SOURCE.png.")
    convert.add_argument("--no-gpx", action="store_true", help="Skip saving the Guitar Pro output file.")
    convert.add_argument("--no-png", action="store_true", help="Skip PNG export.")
    convert.add_argument("--gpx-extension", default="gpx", help="Default Guitar Pro output extension.")
    convert.add_argument("--app", default="Guitar Pro 8", help='macOS application name. Defaults to "Guitar Pro 8".')
    convert.add_argument("--timeout", type=int, default=120, help="Automation timeout in seconds.")
    convert.add_argument("--settle-delay", type=float, default=2.0, help="Delay after opening/saving/exporting.")
    convert.add_argument("--gpx-menu", dest="save_menu", default="File>Export>GPX...", help="Menu path used to export GPX.")
    convert.add_argument("--save-menu", dest="save_menu", help=argparse.SUPPRESS)
    convert.add_argument("--png-menu", default="File>Export>PNG...", help="Menu path used to export PNG.")
    convert.add_argument("--keep-open", action="store_true", help="Leave Guitar Pro open after conversion.")
    convert.add_argument("--force", action="store_true", help="Overwrite existing output files.")
    convert.add_argument("--dry-run", action="store_true", help="Print AppleScript instead of executing it.")
    convert.set_defaults(handler=convert_command)

    lick_spec = subparsers.add_parser("lick-spec", help="Print the LLM-facing guitar lick JSON spec.")
    lick_spec.add_argument(
        "--format",
        choices=("prompt", "schema", "summary", "example"),
        default="prompt",
        help="Output format. Defaults to prompt.",
    )
    lick_spec.add_argument("--style", choices=STYLES, default="blues_rock", help="Musical style for prompt output.")
    lick_spec.add_argument("--key", default="E minor", help='Musical key for prompt output, e.g. "E minor".')
    lick_spec.add_argument("--bars", type=int, default=2, choices=range(1, 9), help="Number of bars for prompt output.")
    lick_spec.add_argument("--tuning", choices=TUNINGS, default="standard", help="Tuning for prompt output.")
    lick_spec.add_argument("--tempo", type=int, help="Optional tempo for prompt output.")
    lick_spec.add_argument(
        "--time-signature",
        choices=TIME_SIGNATURES,
        default="4/4",
        help="Time signature for prompt output.",
    )
    lick_spec.add_argument(
        "--resolution",
        type=int,
        choices=RESOLUTIONS,
        default=16,
        help="Rhythmic grid resolution for prompt output.",
    )
    lick_spec.add_argument("--fret-range", help='Preferred fret range for prompt output, e.g. "5-12".')
    lick_spec.add_argument(
        "--include-technique",
        action="append",
        choices=TECHNIQUES,
        default=[],
        help="Technique that the generated lick should include. Can be repeated.",
    )
    lick_spec.set_defaults(handler=lick_spec_command)
    return parser


def convert_command(args: argparse.Namespace, runner: Runner = run_osascript) -> int:
    try:
        paths = resolve_conversion_paths(
            source=args.source,
            gpx=args.gpx,
            png=args.png,
            no_gpx=args.no_gpx,
            no_png=args.no_png,
            gpx_extension=args.gpx_extension,
            force=args.force,
        )
        request = ConversionRequest(
            paths=paths,
            app_name=args.app,
            timeout_seconds=args.timeout,
            settle_delay=args.settle_delay,
            save_menu=parse_menu_path(args.save_menu),
            png_menu=parse_menu_path(args.png_menu),
            keep_open=args.keep_open,
        )
        script = build_applescript(request)

        if args.dry_run:
            print(script)
            return 0

        ensure_output_directories(paths)
        result = runner(script, args.timeout + 30)
    except (FileExistsError, FileNotFoundError, TimeoutExpired, ValueError) as error:
        print(f"gtp-cli: {error}", file=sys.stderr)
        return 2

    if result.returncode != 0:
        if result.stderr:
            print(_format_osascript_error(result.stderr), file=sys.stderr)
        return result.returncode

    _print_success(paths)
    return 0


def lick_spec_command(args: argparse.Namespace) -> int:
    if args.format == "schema":
        print(dumps_json(guitar_lick_schema()))
        return 0
    if args.format == "example":
        print(dumps_json(EXAMPLE_LICK))
        return 0
    if args.format == "summary":
        print(build_summary())
        return 0

    print(
        build_llm_prompt(
            style=args.style,
            key=args.key,
            bars=args.bars,
            tuning=args.tuning,
            tempo=args.tempo,
            time_signature=args.time_signature,
            resolution=args.resolution,
            fret_range=args.fret_range,
            include_techniques=tuple(args.include_technique),
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def _print_success(paths) -> None:
    print(f"Imported: {paths.source}")
    if paths.gpx is not None:
        print(f"Saved: {paths.gpx}")
    if paths.png is not None:
        print(f"Exported: {paths.png}")


def _format_osascript_error(stderr: str) -> str:
    normalized = stderr.strip()
    if "不允许辅助访问" in normalized or "not allowed assistive access" in normalized:
        return (
            "gtp-cli: macOS blocked UI automation for osascript. "
            "Grant Accessibility permission to the terminal app that runs this command "
            "in System Settings > Privacy & Security > Accessibility, then retry.\n"
            f"Original osascript error: {normalized}"
        )
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())
