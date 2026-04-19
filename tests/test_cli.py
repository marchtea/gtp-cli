from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from gtp_cli.automation import ConversionRequest, build_applescript
from gtp_cli.cli import build_parser, convert_command, lick_spec_command
from gtp_cli.paths import ConversionPaths, resolve_conversion_paths


def test_resolve_conversion_paths_defaults_to_input_stem(tmp_path: Path) -> None:
    source = tmp_path / "song.musicxml"
    source.write_text("<score-partwise />", encoding="utf-8")

    paths = resolve_conversion_paths(source=source, gpx=None, png=None, gpx_extension="gpx")

    assert paths == ConversionPaths(
        source=source.resolve(),
        gpx=(tmp_path / "song.gpx").resolve(),
        png=(tmp_path / "song.png").resolve(),
    )


def test_resolve_conversion_paths_can_disable_outputs(tmp_path: Path) -> None:
    source = tmp_path / "song.xml"
    source.write_text("<score-partwise />", encoding="utf-8")

    paths = resolve_conversion_paths(source=source, gpx=None, png=None, no_gpx=True, no_png=True)

    assert paths.gpx is None
    assert paths.png is None


def test_resolve_conversion_paths_requires_existing_musicxml(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_conversion_paths(source=tmp_path / "missing.musicxml", gpx=None, png=None)


def test_resolve_conversion_paths_rejects_existing_outputs_without_force(tmp_path: Path) -> None:
    source = tmp_path / "song.musicxml"
    output = tmp_path / "song.gpx"
    source.write_text("<score-partwise />", encoding="utf-8")
    output.write_text("already here", encoding="utf-8")

    with pytest.raises(FileExistsError):
        resolve_conversion_paths(source=source, gpx=output, png=None, force=False)


def test_build_applescript_contains_paths_and_menu_sequence(tmp_path: Path) -> None:
    source = tmp_path / "song.musicxml"
    gpx = tmp_path / "song.gpx"
    png = tmp_path / "song.png"
    request = ConversionRequest(
        paths=ConversionPaths(source=source, gpx=gpx, png=png),
        app_name="Guitar Pro 8",
        timeout_seconds=90,
        settle_delay=1.25,
        save_menu=("File", "Export", "GPX..."),
        png_menu=("File", "Export", "PNG..."),
        keep_open=True,
    )

    script = build_applescript(request)

    assert str(source) in script
    assert str(gpx) in script
    assert str(png) in script
    assert 'clickFirstAvailableMenuPath("Guitar Pro 8", {{"File", "Export", "GPX..."}, {"文档", "导出", "GPX..."}}, timeoutSeconds)' in script
    assert 'clickFirstAvailableMenuPath("Guitar Pro 8", {{"File", "Export", "PNG..."}, {"文档", "导出", "PNG..."}}, timeoutSeconds)' in script
    assert 'clickFirstButtonByName(appName, {"Export", "导出"})' in script
    assert "quit application appName" not in script


def test_convert_command_dry_run_prints_script_without_running_osascript(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "song.musicxml"
    source.write_text("<score-partwise />", encoding="utf-8")
    args = build_parser().parse_args(["convert", str(source), "--dry-run"])

    result = convert_command(args)

    assert result == 0
    assert "open -a" in capsys.readouterr().out


def test_convert_command_invokes_runner(tmp_path: Path) -> None:
    source = tmp_path / "song.musicxml"
    source.write_text("<score-partwise />", encoding="utf-8")
    calls: list[str] = []
    args = build_parser().parse_args(["convert", str(source), "--no-png"])

    def fake_runner(script: str, timeout: int) -> CompletedProcess[str]:
        calls.append(script)
        return CompletedProcess(args=["osascript"], returncode=0, stdout="", stderr="")

    result = convert_command(args, runner=fake_runner)

    assert result == 0
    assert len(calls) == 1
    assert "song.gpx" in calls[0]
    assert "PNG..." not in calls[0]


def test_convert_command_explains_macos_accessibility_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "song.musicxml"
    source.write_text("<score-partwise />", encoding="utf-8")
    args = build_parser().parse_args(["convert", str(source), "--no-png"])

    def fake_runner(script: str, timeout: int) -> CompletedProcess[str]:
        return CompletedProcess(args=["osascript"], returncode=1, stdout="", stderr="execution error: 不允许辅助访问。 (-1719)")

    result = convert_command(args, runner=fake_runner)

    assert result == 1
    assert "Grant Accessibility permission" in capsys.readouterr().err


def test_lick_spec_command_outputs_json_schema(capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["lick-spec", "--format", "schema"])

    result = lick_spec_command(args)

    assert result == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Guitar Lick JSON"
    assert schema["properties"]["version"]["const"] == "0.1"
    assert "bend_full" in schema["$defs"]["technique"]["enum"]


def test_lick_spec_command_outputs_llm_prompt_with_musical_constraints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = build_parser().parse_args(
        [
            "lick-spec",
            "--format",
            "prompt",
            "--style",
            "metal",
            "--key",
            "D minor",
            "--bars",
            "4",
            "--tuning",
            "drop_d",
            "--tempo",
            "140",
            "--resolution",
            "24",
            "--fret-range",
            "3-15",
            "--include-technique",
            "palm_mute",
            "--include-technique",
            "bend_full",
        ]
    )

    result = lick_spec_command(args)

    assert result == 0
    output = capsys.readouterr().out
    assert "Generate a guitar lick as valid JSON only." in output
    assert "- style: metal" in output
    assert "- key: D minor" in output
    assert "- bars: 4" in output
    assert "- tuning: drop_d" in output
    assert "- tempo: 140" in output
    assert "- resolution: 24" in output
    assert "- mostly use frets 3-15" in output
    assert "- include technique: palm_mute" in output
    assert "- include technique: bend_full" in output
