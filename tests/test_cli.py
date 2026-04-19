from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from xml.etree import ElementTree as ET

import pytest

from gtp_cli.automation import ConversionRequest, build_applescript
from gtp_cli.cli import build_parser, convert_command, lick_spec_command, lick_to_musicxml_command, main
from gtp_cli.lick_spec import lick_example
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
    assert schema["properties"]["version"]["const"] == "0.2"
    assert schema["properties"]["instrument"]["const"] == "guitar"
    assert "bend_full" in schema["$defs"]["technique"]["enum"]


def test_lick_spec_command_outputs_bass_schema(capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["lick-spec", "--instrument", "bass", "--format", "schema"])

    result = lick_spec_command(args)

    assert result == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Bass Lick JSON"
    assert schema["properties"]["instrument"]["const"] == "bass"
    assert schema["properties"]["tuning"]["enum"] == ["standard_4", "drop_d", "standard_5", "half_step_down", "custom"]
    assert schema["$defs"]["technique"]["enum"][:4] == ["finger", "pick", "slap", "pop"]


def test_lick_spec_command_outputs_drum_schema(capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["lick-spec", "--instrument", "drums", "--format", "schema"])

    result = lick_spec_command(args)

    assert result == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Drum Lick JSON"
    assert schema["properties"]["instrument"]["const"] == "drums"
    assert schema["properties"]["key"]["enum"] == ["none"]
    assert "kick" in schema["$defs"]["piece"]["enum"]
    assert "ghost" in schema["$defs"]["technique"]["enum"]


def test_lick_spec_command_outputs_llm_prompt_with_musical_constraints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = build_parser().parse_args(
        [
            "lick-spec",
            "--format",
            "prompt",
            "--instrument",
            "bass",
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
            "slide_up",
        ]
    )

    result = lick_spec_command(args)

    assert result == 0
    output = capsys.readouterr().out
    assert "Generate a bass lick as valid JSON only." in output
    assert '- instrument must be "bass"' in output
    assert "- instrument: bass" in output
    assert "- style: metal" in output
    assert "- key: D minor" in output
    assert "- bars: 4" in output
    assert "- tuning: drop_d" in output
    assert "- tempo: 140" in output
    assert "- resolution: 24" in output
    assert "- mostly use frets 3-15" in output
    assert "- include technique: palm_mute" in output
    assert "- include technique: slide_up" in output


def test_lick_spec_command_outputs_drum_prompt(capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(
        [
            "lick-spec",
            "--instrument",
            "drums",
            "--format",
            "prompt",
            "--style",
            "funk",
            "--bars",
            "1",
            "--include-technique",
            "ghost",
        ]
    )

    result = lick_spec_command(args)

    assert result == 0
    output = capsys.readouterr().out
    assert "Generate a drum lick as valid JSON only." in output
    assert '- instrument must be "drums"' in output
    assert "- key: none" in output
    assert '- events must contain only "hit" or "rest"' in output
    assert "- hit events use piece from: kick, snare" in output
    assert "- include technique: ghost" in output
    assert "tuning must be one of" not in output


def test_lick_spec_command_rejects_unsupported_instrument_options(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = build_parser().parse_args(["lick-spec", "--instrument", "drums", "--fret-range", "5-12"])

    result = lick_spec_command(args)

    assert result == 2
    assert "--fret-range is not supported for drums" in capsys.readouterr().err


def test_lick_spec_command_rejects_wrong_instrument_tuning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = build_parser().parse_args(["lick-spec", "--instrument", "bass", "--tuning", "standard"])

    result = lick_spec_command(args)

    assert result == 2
    assert "unsupported tuning for bass: standard" in capsys.readouterr().err


def test_lick_spec_help_describes_supported_instruments(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args(["lick-spec", "--help"])

    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "--instrument {guitar,bass,drums}" in output
    assert "Supported: guitar, bass," in output
    assert "drums. Defaults to guitar." in output
    assert "--bars {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}" in output


def test_main_lick_spec_prints_default_instrument_hint(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["lick-spec"])

    assert result == 0
    output = capsys.readouterr().out
    assert "defaults to instrument=guitar" in output
    assert "Use `gtp-cli lick-spec --help`" in output
    assert 'instrument must be "guitar"' in output


def test_lick_spec_parser_accepts_12_bars() -> None:
    args = build_parser().parse_args(["lick-spec", "--bars", "12"])
    assert args.bars == 12


def test_lick_to_musicxml_command_writes_guitar_musicxml(tmp_path: Path) -> None:
    source = tmp_path / "lick.json"
    target = tmp_path / "lick.musicxml"
    source.write_text(json.dumps(lick_example("guitar")), encoding="utf-8")
    args = build_parser().parse_args(["lick-to-musicxml", str(source), "--musicxml", str(target)])

    result = lick_to_musicxml_command(args)

    assert result == 0
    assert target.exists()
    musicxml = target.read_text(encoding="utf-8")
    root = ET.fromstring(musicxml.split("\n", 2)[2])
    assert root.tag == "score-partwise"
    assert root.find("./part/measure/note/pitch") is not None
    assert root.find("./part/measure/direction/sound[@tempo='120']") is not None
    assert root.find("./part/measure/direction/direction-type/metronome/per-minute").text == "120"
    assert root.find("./part/measure/attributes/key/fifths").text == "1"
    assert root.find("./part/measure/attributes/key/mode").text == "minor"
    assert root.find("./part/measure/attributes/staves").text == "2"
    assert root.find("./part/measure/attributes/clef[@number='2']/sign").text == "TAB"
    assert root.find("./part/measure/attributes/staff-details[@number='2']/staff-tuning[@line='1']/tuning-step").text == "E"
    first_note = root.find("./part/measure/note")
    assert first_note is not None
    child_tags = [child.tag for child in first_note]
    assert first_note.find("./voice").text == "1"
    assert first_note.find("./notehead").text == "normal"
    assert child_tags.index("staff") < child_tags.index("notations")
    assert "<?GP" in musicxml
    assert root.find("./part/measure/backup/duration").text == "256"
    tab_notes = [note for note in root.findall("./part/measure/note") if note.findtext("./staff") == "2"]
    assert tab_notes
    first_tab_note = tab_notes[0]
    tab_child_tags = [child.tag for child in first_tab_note]
    assert first_tab_note.find("./voice").text == "5"
    assert tab_child_tags.index("staff") < tab_child_tags.index("notations")
    assert first_tab_note.find("./notations/technical/string").text == "3"
    assert first_tab_note.find("./notations/technical/fret").text == "7"


def test_lick_to_musicxml_command_writes_drum_musicxml(tmp_path: Path) -> None:
    source = tmp_path / "drums.json"
    source.write_text(json.dumps(lick_example("drums")), encoding="utf-8")
    args = build_parser().parse_args(["lick-to-musicxml", str(source)])

    result = lick_to_musicxml_command(args)

    assert result == 0
    target = tmp_path / "drums.musicxml"
    assert target.exists()
    root = ET.fromstring(target.read_text(encoding="utf-8").split("\n", 2)[2])
    assert root.find("./part/measure/note/unpitched") is not None
    assert root.find("./part/measure/direction/sound[@tempo='120']") is not None
    assert root.find("./part/measure/attributes/clef/sign").text == "percussion"


def test_lick_to_musicxml_command_writes_multi_track_musicxml(tmp_path: Path) -> None:
    source = tmp_path / "full-band.json"
    target = tmp_path / "full-band.musicxml"
    source.write_text(
        json.dumps(
            {
                "title": "Full Band",
                "tracks": [
                    lick_example("guitar"),
                    lick_example("drums"),
                    lick_example("bass"),
                ],
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(["lick-to-musicxml", str(source), "--musicxml", str(target)])

    result = lick_to_musicxml_command(args)

    assert result == 0
    root = ET.fromstring(target.read_text(encoding="utf-8").split("\n", 2)[2])
    assert [part.attrib["id"] for part in root.findall("./part-list/score-part")] == ["P1", "P2", "P3"]
    assert root.find("./part-list/score-part[@id='P1']/midi-instrument/midi-program").text == "31"
    assert root.find("./part-list/score-part[@id='P2']/score-instrument") is not None
    assert root.find("./part-list/score-part[@id='P2']/midi-instrument/midi-channel").text == "10"
    assert root.find("./part-list/score-part[@id='P3']/midi-instrument/midi-program").text == "34"
    assert root.find("./part[@id='P1']/measure/attributes/staves").text == "2"
    assert root.find("./part[@id='P1']/measure/backup") is not None
    assert root.find("./part[@id='P2']/measure/attributes/clef/sign").text == "percussion"
    assert root.find("./part[@id='P2']/measure/note/unpitched") is not None
    assert root.find("./part[@id='P2']/measure/note/instrument") is not None
    assert root.find("./part[@id='P3']/measure/attributes/staves").text == "2"
    assert root.find("./part[@id='P3']/measure/backup") is not None


def test_lick_to_musicxml_command_rejects_invalid_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "bad.json"
    source.write_text('{"instrument":"guitar","events":[]}', encoding="utf-8")
    args = build_parser().parse_args(["lick-to-musicxml", str(source)])

    result = lick_to_musicxml_command(args)

    assert result == 2
    assert "does not match spec" in capsys.readouterr().err
