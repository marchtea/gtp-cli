from __future__ import annotations

import argparse
import sys
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from typing import Callable

from gtp_cli.automation import ConversionRequest, build_applescript, parse_menu_path, run_osascript
from gtp_cli.lick_spec import (
    ALL_TECHNIQUES,
    ALL_TUNINGS,
    INSTRUMENTS,
    RESOLUTIONS,
    STYLES,
    TIME_SIGNATURES,
    build_llm_prompt,
    build_summary,
    dumps_json,
    lick_example,
    lick_schema,
    techniques_for_instrument,
    tunings_for_instrument,
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

    lick_spec = subparsers.add_parser("lick-spec", help="Print the LLM-facing instrument lick JSON spec.")
    lick_spec.add_argument(
        "--format",
        choices=("prompt", "schema", "summary", "example"),
        default="prompt",
        help="Output format. Defaults to prompt.",
    )
    lick_spec.add_argument("--instrument", choices=INSTRUMENTS, default="guitar", help="Instrument spec to print.")
    lick_spec.add_argument("--style", choices=STYLES, default="blues_rock", help="Musical style for prompt output.")
    lick_spec.add_argument("--key", default="E minor", help='Musical key for prompt output, e.g. "E minor".')
    lick_spec.add_argument("--bars", type=int, default=2, choices=range(1, 9), help="Number of bars for prompt output.")
    lick_spec.add_argument("--tuning", choices=ALL_TUNINGS, help="Tuning for guitar or bass prompt output.")
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
        choices=ALL_TECHNIQUES,
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
    if args.instrument == "drums" and args.tuning is not None:
        print("gtp-cli: --tuning is not supported for drums", file=sys.stderr)
        return 2
    if args.instrument == "drums" and args.fret_range is not None:
        print("gtp-cli: --fret-range is not supported for drums", file=sys.stderr)
        return 2
    if args.instrument != "drums" and args.tuning is not None and args.tuning not in tunings_for_instrument(args.instrument):
        print(f"gtp-cli: unsupported tuning for {args.instrument}: {args.tuning}", file=sys.stderr)
        return 2

    unsupported_techniques = sorted(set(args.include_technique) - set(techniques_for_instrument(args.instrument)))
    if unsupported_techniques:
        print(
            f"gtp-cli: unsupported technique for {args.instrument}: {', '.join(unsupported_techniques)}",
            file=sys.stderr,
        )
        return 2

    if args.format == "schema":
        print(dumps_json(lick_schema(args.instrument)))
        return 0
    if args.format == "example":
        print(dumps_json(lick_example(args.instrument)))
        return 0
    if args.format == "summary":
        print(build_summary(args.instrument))
        return 0

    print(
        build_llm_prompt(
            instrument=args.instrument,
            style=args.style,
            key=_default_key(args.instrument, args.key),
            bars=args.bars,
            tuning=_default_tuning(args.instrument, args.tuning),
            tempo=args.tempo,
            time_signature=args.time_signature,
            resolution=args.resolution,
            fret_range=args.fret_range,
            include_techniques=tuple(args.include_technique),
        )
    )
    return 0


def _default_key(instrument: str, key: str) -> str:
    if instrument == "drums" and key == "E minor":
        return "none"
    return key


def _default_tuning(instrument: str, tuning: str | None) -> str | None:
    if instrument == "drums":
        return None
    if tuning is not None:
        return tuning
    if instrument == "bass":
        return "standard_4"
    return "standard"


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
