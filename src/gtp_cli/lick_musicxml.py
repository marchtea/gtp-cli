from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from gtp_cli.lick_spec import lick_schema

try:
    from jsonschema import Draft202012Validator
except ImportError as error:  # pragma: no cover - dependency issue should surface immediately in CLI usage
    raise RuntimeError("gtp-cli requires jsonschema to export lick JSON as MusicXML") from error


STANDARD_TUNINGS: dict[tuple[str, str], list[str]] = {
    ("guitar", "standard"): ["E2", "A2", "D3", "G3", "B3", "E4"],
    ("guitar", "drop_d"): ["D2", "A2", "D3", "G3", "B3", "E4"],
    ("guitar", "half_step_down"): ["Eb2", "Ab2", "Db3", "Gb3", "Bb3", "Eb4"],
    ("guitar", "open_g"): ["D2", "G2", "D3", "G3", "B3", "D4"],
    ("bass", "standard_4"): ["E1", "A1", "D2", "G2"],
    ("bass", "drop_d"): ["D1", "A1", "D2", "G2"],
    ("bass", "standard_5"): ["B0", "E1", "A1", "D2", "G2"],
    ("bass", "half_step_down"): ["Eb1", "Ab1", "Db2", "Gb2"],
}

DRUM_MIDI: dict[str, int] = {
    "kick": 36,
    "snare": 38,
    "rim": 37,
    "closed_hat": 42,
    "open_hat": 46,
    "pedal_hat": 44,
    "ride": 51,
    "ride_bell": 53,
    "crash_1": 49,
    "crash_2": 57,
    "tom_high": 50,
    "tom_mid": 47,
    "tom_floor": 43,
}


@dataclass(frozen=True)
class _NoteUnit:
    midi: int
    string: int | None = None
    fret: int | None = None
    is_unpitched: bool = False
    instrument_id: str | None = None


@dataclass(frozen=True)
class _TimelineSlot:
    start: int
    duration: int
    notes: tuple[_NoteUnit, ...]


@dataclass(frozen=True)
class _PreparedPart:
    part_id: str
    instrument: str
    title: str
    tempo: int
    beats: int
    beat_type: int
    divisions: int
    ticks_per_step: int
    bars: int
    steps_per_bar: int
    key: str
    tuning_pitches: list[int] | None
    slots_per_bar: dict[int, list[_TimelineSlot]]


def render_lick_file_to_musicxml(source: Path) -> str:
    data = json.loads(source.read_text(encoding="utf-8"))
    return render_lick_to_musicxml(data)


def render_lick_to_musicxml(payload: dict[str, Any]) -> str:
    tracks = _normalize_tracks(payload)
    prepared_parts = [_prepare_part(track, f"P{index}") for index, track in enumerate(tracks, start=1)]
    title = str(payload.get("title") or prepared_parts[0].title)

    score = ET.Element("score-partwise", version="2.0")
    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title

    part_list = ET.SubElement(score, "part-list")
    for prepared in prepared_parts:
        _append_score_part(part_list, prepared)

    for prepared in prepared_parts:
        _append_part(score, prepared)

    _indent_xml(score)
    xml_text = ET.tostring(score, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE score-partwise PUBLIC \'-//Recordare//DTD MusicXML 2.0 Partwise//EN\' \'http://www.musicxml.org/dtds/2.0/partwise.dtd\'>\n' + xml_text + "\n"


def _normalize_tracks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if "tracks" not in payload:
        return [payload]

    tracks = payload["tracks"]
    if not isinstance(tracks, list) or not tracks:
        raise ValueError("multi-track lick JSON must include a non-empty tracks array")
    if not all(isinstance(track, dict) for track in tracks):
        raise ValueError("multi-track lick JSON tracks must be objects")
    return tracks


def _prepare_part(lick: dict[str, Any], part_id: str) -> _PreparedPart:
    instrument = _validate(lick)
    beats, beat_type = _parse_time_signature(lick["timeSignature"])
    resolution = int(lick["resolution"])
    divisions = resolution * beat_type
    ticks_per_step = beats * 4
    bars = int(lick["bars"])
    steps_per_bar = resolution
    title = str(lick.get("title") or f"{instrument.title()} Lick")

    tuning_pitches: list[int] | None = None
    if instrument in {"guitar", "bass"}:
        tuning_pitches = _resolve_tuning_midi(lick)

    slots_per_bar: dict[int, list[_TimelineSlot]] = {index: [] for index in range(bars)}
    split_events = _split_events(lick["events"], steps_per_bar)

    for event in split_events:
        bar_index = event["start"] // steps_per_bar
        local_start = event["start"] % steps_per_bar
        duration = int(event["duration"])
        if event["type"] == "rest":
            slots_per_bar[bar_index].append(_TimelineSlot(start=local_start, duration=duration, notes=()))
            continue
        if instrument == "drums":
            piece = str(event["piece"])
            note = _NoteUnit(midi=DRUM_MIDI[piece], is_unpitched=True, instrument_id=_drum_instrument_id(part_id, piece))
            slots_per_bar[bar_index].append(_TimelineSlot(start=local_start, duration=duration, notes=(note,)))
            continue

        if event["type"] == "note":
            string = int(event["string"])
            fret = int(event["fret"])
            midi = _midi_from_string_fret(string=string, fret=fret, tuning=tuning_pitches or [])
            note = _NoteUnit(midi=midi, string=string, fret=fret)
            slots_per_bar[bar_index].append(_TimelineSlot(start=local_start, duration=duration, notes=(note,)))
            continue

        if event["type"] == "chord":
            chord_notes: list[_NoteUnit] = []
            for note_data in event["notes"]:
                string = int(note_data["string"])
                fret = int(note_data["fret"])
                midi = _midi_from_string_fret(string=string, fret=fret, tuning=tuning_pitches or [])
                chord_notes.append(_NoteUnit(midi=midi, string=string, fret=fret))
            slots_per_bar[bar_index].append(_TimelineSlot(start=local_start, duration=duration, notes=tuple(chord_notes)))
            continue

    return _PreparedPart(
        part_id=part_id,
        instrument=instrument,
        title=title,
        tempo=int(lick["tempo"]),
        beats=beats,
        beat_type=beat_type,
        divisions=divisions,
        ticks_per_step=ticks_per_step,
        bars=bars,
        steps_per_bar=steps_per_bar,
        key=str(lick.get("key", "C major")),
        tuning_pitches=tuning_pitches,
        slots_per_bar=slots_per_bar,
    )


def _append_score_part(part_list: ET.Element, prepared: _PreparedPart) -> None:
    instrument = prepared.instrument
    part_id = prepared.part_id
    score_part = ET.SubElement(part_list, "score-part", id=part_id)
    fallback_name = "Drum Set" if instrument == "drums" else ("Bass" if instrument == "bass" else "Distortion Guitar")
    ET.SubElement(score_part, "part-name").text = prepared.title or fallback_name
    ET.SubElement(score_part, "part-abbreviation").text = "drm." if instrument == "drums" else ("el.bs." if instrument == "bass" else "dist.guit.")

    if instrument == "drums":
        for piece, midi_value in DRUM_MIDI.items():
            instrument_id = _drum_instrument_id(part_id, piece)
            score_instrument = ET.SubElement(score_part, "score-instrument", id=instrument_id)
            ET.SubElement(score_instrument, "instrument-name").text = _drum_instrument_name(piece)
            midi = ET.SubElement(score_part, "midi-instrument", id=instrument_id)
            ET.SubElement(midi, "midi-channel").text = "10"
            ET.SubElement(midi, "midi-unpitched").text = str(midi_value)
            ET.SubElement(midi, "volume").text = "80"
            ET.SubElement(midi, "pan").text = "0"
        return

    midi = ET.SubElement(score_part, "midi-instrument", id=part_id)
    ET.SubElement(midi, "midi-channel").text = "5" if instrument == "bass" else "1"
    ET.SubElement(midi, "midi-bank").text = "1"
    ET.SubElement(midi, "midi-program").text = "34" if instrument == "bass" else "31"
    ET.SubElement(midi, "volume").text = "80"
    ET.SubElement(midi, "pan").text = "0"


def _append_part(score: ET.Element, prepared: _PreparedPart) -> None:
    instrument = prepared.instrument
    part = ET.SubElement(score, "part", id=prepared.part_id)
    for bar_index in range(prepared.bars):
        measure = ET.SubElement(part, "measure", number=str(bar_index + 1))
        if bar_index == 0:
            attributes = ET.SubElement(measure, "attributes")
            ET.SubElement(attributes, "divisions").text = str(prepared.divisions)
            key = ET.SubElement(attributes, "key")
            ET.SubElement(key, "fifths").text = str(_key_to_fifths(prepared.key))
            ET.SubElement(key, "mode").text = _key_to_mode(prepared.key)
            time = ET.SubElement(attributes, "time")
            ET.SubElement(time, "beats").text = str(prepared.beats)
            ET.SubElement(time, "beat-type").text = str(prepared.beat_type)
            if instrument == "drums":
                clef = ET.SubElement(attributes, "clef", number="1")
                ET.SubElement(clef, "sign").text = "percussion"
                staff_details = ET.SubElement(attributes, "staff-details", number="1")
                staff_details.append(ET.ProcessingInstruction("GP", "\n<root>\n</root>\n"))
            else:
                ET.SubElement(attributes, "staves").text = "2"
                clef_standard = ET.SubElement(attributes, "clef", number="1")
                ET.SubElement(clef_standard, "sign").text = "F" if instrument == "bass" else "G"
                ET.SubElement(clef_standard, "line").text = "2"
                clef_tab = ET.SubElement(attributes, "clef", number="2")
                ET.SubElement(clef_tab, "sign").text = "TAB"
                ET.SubElement(clef_tab, "line").text = "5"
                staff_details_standard = ET.SubElement(attributes, "staff-details", number="1")
                staff_details_standard.append(ET.ProcessingInstruction("GP", "\n<root>\n</root>\n"))
                staff_details = ET.SubElement(attributes, "staff-details", number="2")
                ET.SubElement(staff_details, "staff-lines").text = str(len(prepared.tuning_pitches or []))
                _append_staff_tuning(staff_details, prepared.tuning_pitches or [])

            _append_tempo_direction(measure, prepared.tempo)

        voice_slots = _coalesce_slots(prepared.slots_per_bar[bar_index], prepared.steps_per_bar)
        if instrument in {"guitar", "bass"}:
            _append_stringed_staff(
                parent=measure,
                slots=voice_slots,
                divisions=prepared.divisions,
                ticks_per_step=prepared.ticks_per_step,
                instrument=instrument,
                staff_number=1,
                voice="1",
                use_gp_technical=True,
                include_notehead=True,
            )
            backup = ET.SubElement(measure, "backup")
            ET.SubElement(backup, "duration").text = str(prepared.steps_per_bar * prepared.ticks_per_step)
            _append_stringed_staff(
                parent=measure,
                slots=voice_slots,
                divisions=prepared.divisions,
                ticks_per_step=prepared.ticks_per_step,
                instrument=instrument,
                staff_number=2,
                voice="5",
                use_gp_technical=False,
                include_notehead=False,
            )
            continue

        for slot in voice_slots:
            if not slot.notes:
                _append_rest(
                    parent=measure,
                    duration=slot.duration * prepared.ticks_per_step,
                    divisions=prepared.divisions,
                    instrument=instrument,
                    voice="1",
                )
                continue
            for note_index, note in enumerate(slot.notes):
                _append_note(
                    parent=measure,
                    instrument=instrument,
                    note=note,
                    duration=slot.duration * prepared.ticks_per_step,
                    divisions=prepared.divisions,
                    chord=note_index > 0,
                    voice="1",
                )


def _validate(lick: dict[str, Any]) -> str:
    instrument = str(lick.get("instrument") or "")
    if instrument not in {"guitar", "bass", "drums"}:
        raise ValueError("lick JSON must include instrument: guitar, bass, or drums")
    schema = lick_schema(instrument)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(lick), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "root"
        raise ValueError(f"lick JSON does not match spec at {path}: {first.message}")
    return instrument


def _parse_time_signature(value: str) -> tuple[int, int]:
    beats, beat_type = value.split("/", 1)
    return int(beats), int(beat_type)


def _resolve_tuning_midi(lick: dict[str, Any]) -> list[int]:
    instrument = str(lick["instrument"])
    tuning = str(lick["tuning"])
    if tuning == "custom":
        raw = lick.get("customTuning")
        if not isinstance(raw, list):
            raise ValueError("custom tuning requires customTuning array")
        names = [str(note) for note in raw]
    else:
        names = STANDARD_TUNINGS.get((instrument, tuning), [])
        if not names:
            raise ValueError(f"unsupported {instrument} tuning for MusicXML export: {tuning}")
    return [_note_name_to_midi(name) for name in names]


def _note_name_to_midi(note: str) -> int:
    steps = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    step = note[0].upper()
    if step not in steps:
        raise ValueError(f"invalid note name: {note}")
    index = 1
    alter = 0
    if index < len(note) and note[index] in {"#", "b"}:
        alter = 1 if note[index] == "#" else -1
        index += 1
    octave = int(note[index:])
    return (octave + 1) * 12 + steps[step] + alter


def _midi_from_string_fret(*, string: int, fret: int, tuning: list[int]) -> int:
    if string < 1 or string > len(tuning):
        raise ValueError(f"string {string} is invalid for tuning with {len(tuning)} strings")
    open_midi = tuning[len(tuning) - string]
    return open_midi + fret


def _split_events(events: list[dict[str, Any]], steps_per_bar: int) -> list[dict[str, Any]]:
    split: list[dict[str, Any]] = []
    for event in events:
        start = int(event["start"])
        duration = int(event["duration"])
        remaining = duration
        cursor = start
        while remaining > 0:
            local_start = cursor % steps_per_bar
            available = steps_per_bar - local_start
            take = min(available, remaining)
            chunk = dict(event)
            chunk["start"] = cursor
            chunk["duration"] = take
            split.append(chunk)
            cursor += take
            remaining -= take
    return split


def _coalesce_slots(slots: list[_TimelineSlot], steps_per_bar: int) -> list[_TimelineSlot]:
    ordered = sorted(slots, key=lambda slot: (slot.start, slot.duration))
    cursor = 0
    result: list[_TimelineSlot] = []

    while cursor < steps_per_bar:
        starting = [slot for slot in ordered if slot.start == cursor]
        if not starting:
            next_start = min([slot.start for slot in ordered if slot.start > cursor], default=steps_per_bar)
            result.append(_TimelineSlot(start=cursor, duration=next_start - cursor, notes=()))
            cursor = next_start
            continue

        durations = {slot.duration for slot in starting}
        if len(durations) != 1:
            raise ValueError(f"simultaneous events at step {cursor} must share the same duration")
        duration = durations.pop()
        if duration <= 0:
            raise ValueError(f"invalid duration at step {cursor}")
        if cursor + duration > steps_per_bar:
            raise ValueError(f"event at step {cursor} exceeds measure boundary")
        notes: list[_NoteUnit] = []
        for slot in starting:
            notes.extend(slot.notes)
        result.append(_TimelineSlot(start=cursor, duration=duration, notes=tuple(notes)))
        cursor += duration

        overlaps = [slot for slot in ordered if slot.start < cursor and slot.start >= result[-1].start and slot not in starting]
        if overlaps:
            raise ValueError(f"polyphonic overlap is not supported near step {result[-1].start}")

    return result


def _append_stringed_staff(
    *,
    parent: ET.Element,
    slots: list[_TimelineSlot],
    divisions: int,
    ticks_per_step: int,
    instrument: str,
    staff_number: int,
    voice: str,
    use_gp_technical: bool,
    include_notehead: bool,
) -> None:
    for slot in slots:
        duration = slot.duration * ticks_per_step
        if not slot.notes:
            _append_rest(
                parent=parent,
                duration=duration,
                divisions=divisions,
                instrument=instrument,
                staff_number=staff_number,
                voice=voice,
            )
            continue
        for note_index, note in enumerate(slot.notes):
            _append_note(
                parent=parent,
                instrument=instrument,
                note=note,
                duration=duration,
                divisions=divisions,
                chord=note_index > 0,
                staff_number=staff_number,
                voice=voice,
                use_gp_technical=use_gp_technical,
                include_notehead=include_notehead,
            )


def _append_rest(
    *,
    parent: ET.Element,
    duration: int,
    divisions: int,
    instrument: str,
    voice: str,
    staff_number: int | None = None,
) -> None:
    note = ET.SubElement(parent, "note")
    ET.SubElement(note, "rest")
    ET.SubElement(note, "duration").text = str(duration)
    ET.SubElement(note, "voice").text = voice
    _append_note_type(note, duration, divisions)
    if instrument != "drums":
        ET.SubElement(note, "staff").text = str(staff_number or 2)


def _append_note(
    *,
    parent: ET.Element,
    instrument: str,
    note: _NoteUnit,
    duration: int,
    divisions: int,
    chord: bool,
    voice: str,
    staff_number: int | None = None,
    use_gp_technical: bool = False,
    include_notehead: bool = False,
) -> None:
    node = ET.SubElement(parent, "note")
    if chord:
        ET.SubElement(node, "chord")

    if instrument == "drums" or note.is_unpitched:
        unpitched = ET.SubElement(node, "unpitched")
        step, octave = _midi_to_display(note.midi)
        ET.SubElement(unpitched, "display-step").text = step
        ET.SubElement(unpitched, "display-octave").text = str(octave)
    else:
        pitch = ET.SubElement(node, "pitch")
        step, alter, octave = _midi_to_pitch(note.midi)
        ET.SubElement(pitch, "step").text = step
        if alter != 0:
            ET.SubElement(pitch, "alter").text = str(alter)
        ET.SubElement(pitch, "octave").text = str(octave)

    ET.SubElement(node, "duration").text = str(duration)
    if note.instrument_id is not None:
        ET.SubElement(node, "instrument", id=note.instrument_id)
    ET.SubElement(node, "voice").text = voice
    _append_note_type(node, duration, divisions)
    if instrument == "drums":
        ET.SubElement(node, "notehead").text = "x" if note.midi in {42, 44, 46, 49, 51, 53, 57} else "normal"

    if note.string is not None and note.fret is not None:
        if include_notehead:
            ET.SubElement(node, "notehead").text = "normal"
        ET.SubElement(node, "staff").text = str(staff_number or 2)
        notations = ET.SubElement(node, "notations")
        technical = ET.SubElement(notations, "technical")
        if use_gp_technical:
            technical.append(_gp_technical_instruction(string=note.string, fret=note.fret))
        else:
            ET.SubElement(technical, "string").text = str(note.string)
            ET.SubElement(technical, "fret").text = str(note.fret)


def _gp_technical_instruction(*, string: int, fret: int) -> ET.Element:
    content = f"\n<root>\n<string>{string}</string>\n<fret>{fret}</fret>\n</root>\n"
    return ET.ProcessingInstruction("GP", content)


def _drum_instrument_id(part_id: str, piece: str) -> str:
    return f"{part_id}-I{list(DRUM_MIDI).index(piece) + 1}"


def _drum_instrument_name(piece: str) -> str:
    names = {
        "kick": "Kick (hit)",
        "snare": "Snare (hit)",
        "rim": "Snare (rim shot)",
        "closed_hat": "Hi-Hat (closed)",
        "open_hat": "Hi-Hat (open)",
        "pedal_hat": "Pedal Hi-Hat (hit)",
        "ride": "Ride (middle)",
        "ride_bell": "Ride (bell)",
        "crash_1": "Crash high (hit)",
        "crash_2": "Crash medium (hit)",
        "tom_high": "High Tom (hit)",
        "tom_mid": "Mid Tom (hit)",
        "tom_floor": "Low Tom (hit)",
    }
    return names[piece]


def _midi_to_pitch(value: int) -> tuple[str, int, int]:
    pitch_classes = {
        0: ("C", 0),
        1: ("C", 1),
        2: ("D", 0),
        3: ("D", 1),
        4: ("E", 0),
        5: ("F", 0),
        6: ("F", 1),
        7: ("G", 0),
        8: ("G", 1),
        9: ("A", 0),
        10: ("A", 1),
        11: ("B", 0),
    }
    octave = value // 12 - 1
    step, alter = pitch_classes[value % 12]
    return step, alter, octave


def _midi_to_display(value: int) -> tuple[str, int]:
    step, _, octave = _midi_to_pitch(value)
    return step, octave


def _append_tempo_direction(measure: ET.Element, tempo: int) -> None:
    direction = ET.SubElement(measure, "direction", directive="yes")
    direction_type = ET.SubElement(direction, "direction-type")
    metronome = ET.SubElement(direction_type, "metronome", parentheses="no")
    ET.SubElement(metronome, "beat-unit").text = "quarter"
    ET.SubElement(metronome, "per-minute").text = str(tempo)
    ET.SubElement(direction, "sound", tempo=str(tempo))


def _append_staff_tuning(staff_details: ET.Element, tuning_midi: list[int]) -> None:
    for line, midi in enumerate(tuning_midi, start=1):
        step, alter, octave = _midi_to_pitch(midi)
        tuning = ET.SubElement(staff_details, "staff-tuning", line=str(line))
        ET.SubElement(tuning, "tuning-step").text = step
        if alter != 0:
            ET.SubElement(tuning, "tuning-alter").text = str(alter)
        ET.SubElement(tuning, "tuning-octave").text = str(octave)


def _append_note_type(note: ET.Element, duration: int, divisions: int) -> None:
    ratio = duration / divisions
    table: list[tuple[float, str, int]] = [
        (4.0, "whole", 0),
        (3.0, "half", 1),
        (2.0, "half", 0),
        (1.5, "quarter", 1),
        (1.0, "quarter", 0),
        (0.75, "eighth", 1),
        (0.5, "eighth", 0),
        (0.375, "16th", 1),
        (0.25, "16th", 0),
        (0.125, "32nd", 0),
        (0.0625, "64th", 0),
    ]
    note_type = "quarter"
    dots = 0
    for value, label, dot_count in table:
        if abs(ratio - value) < 1e-9:
            note_type = label
            dots = dot_count
            break
    ET.SubElement(note, "type").text = note_type
    for _ in range(dots):
        ET.SubElement(note, "dot")


def _key_to_mode(key_value: str) -> str:
    lower = key_value.lower()
    return "minor" if "minor" in lower else "major"


def _key_to_fifths(key_value: str) -> int:
    mode = _key_to_mode(key_value)
    name = key_value.split(" ", 1)[0].strip()
    normalized = name.replace("♭", "b").replace("♯", "#")
    major_table = {
        "C": 0,
        "G": 1,
        "D": 2,
        "A": 3,
        "E": 4,
        "B": 5,
        "F#": 6,
        "C#": 7,
        "F": -1,
        "Bb": -2,
        "Eb": -3,
        "Ab": -4,
        "Db": -5,
        "Gb": -6,
        "Cb": -7,
    }
    minor_table = {
        "A": 0,
        "E": 1,
        "B": 2,
        "F#": 3,
        "C#": 4,
        "G#": 5,
        "D#": 6,
        "A#": 7,
        "D": -1,
        "G": -2,
        "C": -3,
        "F": -4,
        "Bb": -5,
        "Eb": -6,
        "Ab": -7,
    }
    table = minor_table if mode == "minor" else major_table
    return table.get(normalized, 0)


def _indent_xml(element: ET.Element, level: int = 0) -> None:
    prefix = "\n" + ("  " * level)
    if len(element):
        if not element.text or not element.text.strip():
            element.text = prefix + "  "
        for child in element:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = prefix
    if level and (not element.tail or not element.tail.strip()):
        element.tail = prefix
