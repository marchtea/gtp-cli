from __future__ import annotations

import json
from typing import Any

SPEC_VERSION = "0.2"

INSTRUMENTS = ("guitar", "bass", "drums")
STYLES = ("rock", "blues", "blues_rock", "metal", "funk", "jazz", "country", "pop", "fusion")
TIME_SIGNATURES = ("4/4", "3/4", "6/8", "12/8")
TUNINGS = ("standard", "drop_d", "half_step_down", "open_g", "custom")
BASS_TUNINGS = ("standard_4", "drop_d", "standard_5", "half_step_down", "custom")
RESOLUTIONS = (16, 24)
STRING_TECHNIQUES = (
    "pick",
    "legato",
    "hammer_on",
    "pull_off",
    "slide_in",
    "slide_out",
    "slide_up",
    "slide_down",
    "bend_quarter",
    "bend_half",
    "bend_full",
    "release",
    "vibrato",
    "palm_mute",
    "staccato",
    "let_ring",
    "dead_note",
    "harmonic",
    "pinch_harmonic",
)
DRUM_TECHNIQUES = (
    "normal",
    "accent",
    "ghost",
    "rimshot",
    "flam",
    "drag",
    "open",
    "closed",
    "choke",
)
BASS_TECHNIQUES = (
    "finger",
    "pick",
    "slap",
    "pop",
    "hammer_on",
    "pull_off",
    "slide_up",
    "slide_down",
    "palm_mute",
    "staccato",
    "let_ring",
    "dead_note",
    "harmonic",
)
DRUM_PIECES = (
    "kick",
    "snare",
    "rim",
    "closed_hat",
    "open_hat",
    "pedal_hat",
    "ride",
    "ride_bell",
    "crash_1",
    "crash_2",
    "tom_high",
    "tom_mid",
    "tom_floor",
)
ALL_TUNINGS = tuple(dict.fromkeys((*TUNINGS, *BASS_TUNINGS)))
ALL_TECHNIQUES = tuple(dict.fromkeys((*STRING_TECHNIQUES, *BASS_TECHNIQUES, *DRUM_TECHNIQUES)))

EXAMPLE_LICK: dict[str, Any] = {
    "version": SPEC_VERSION,
    "instrument": "guitar",
    "title": "E minor blues lick",
    "style": "blues_rock",
    "tempo": 120,
    "timeSignature": "4/4",
    "key": "E minor",
    "tuning": "standard",
    "bars": 2,
    "resolution": 16,
    "events": [
        {
            "type": "note",
            "start": 0,
            "duration": 2,
            "string": 3,
            "fret": 7,
            "velocity": 90,
            "techniques": ["pick"],
        },
        {
            "type": "note",
            "start": 2,
            "duration": 2,
            "string": 3,
            "fret": 9,
            "velocity": 92,
            "techniques": ["hammer_on"],
        },
        {
            "type": "note",
            "start": 4,
            "duration": 4,
            "string": 2,
            "fret": 8,
            "velocity": 96,
            "techniques": ["bend_half", "vibrato"],
        },
        {"type": "rest", "start": 8, "duration": 2},
        {
            "type": "note",
            "start": 10,
            "duration": 2,
            "string": 1,
            "fret": 7,
            "velocity": 88,
            "techniques": ["slide_in"],
        },
    ],
}

BASS_EXAMPLE_LICK: dict[str, Any] = {
    "version": SPEC_VERSION,
    "instrument": "bass",
    "title": "D minor bass groove",
    "style": "rock",
    "tempo": 120,
    "timeSignature": "4/4",
    "key": "D minor",
    "tuning": "standard_4",
    "bars": 2,
    "resolution": 16,
    "events": [
        {"type": "note", "start": 0, "duration": 2, "string": 4, "fret": 5, "velocity": 96, "techniques": ["finger"]},
        {"type": "note", "start": 4, "duration": 2, "string": 4, "fret": 5, "velocity": 92, "techniques": ["palm_mute"]},
        {"type": "note", "start": 6, "duration": 2, "string": 3, "fret": 3, "velocity": 88, "techniques": ["hammer_on"]},
        {"type": "rest", "start": 8, "duration": 2},
        {"type": "note", "start": 10, "duration": 2, "string": 3, "fret": 5, "velocity": 94, "techniques": ["slide_up"]},
    ],
}

DRUM_EXAMPLE_LICK: dict[str, Any] = {
    "version": SPEC_VERSION,
    "instrument": "drums",
    "title": "Rock drum fill",
    "style": "rock",
    "tempo": 120,
    "timeSignature": "4/4",
    "key": "none",
    "bars": 1,
    "resolution": 16,
    "events": [
        {"type": "hit", "start": 0, "duration": 1, "piece": "kick", "velocity": 108, "techniques": ["normal"]},
        {"type": "hit", "start": 0, "duration": 1, "piece": "closed_hat", "velocity": 78, "techniques": ["closed"]},
        {"type": "hit", "start": 4, "duration": 1, "piece": "snare", "velocity": 112, "techniques": ["accent"]},
        {"type": "hit", "start": 8, "duration": 1, "piece": "tom_high", "velocity": 96, "techniques": ["normal"]},
        {"type": "hit", "start": 10, "duration": 1, "piece": "tom_mid", "velocity": 98, "techniques": ["normal"]},
        {"type": "hit", "start": 12, "duration": 1, "piece": "tom_floor", "velocity": 104, "techniques": ["normal"]},
        {"type": "hit", "start": 14, "duration": 1, "piece": "crash_1", "velocity": 118, "techniques": ["normal"]},
    ],
}


def lick_schema(instrument: str = "guitar") -> dict[str, Any]:
    if instrument == "drums":
        return _drum_schema()
    return _stringed_schema(instrument)


def guitar_lick_schema() -> dict[str, Any]:
    return lick_schema("guitar")


def lick_example(instrument: str = "guitar") -> dict[str, Any]:
    examples = {
        "guitar": EXAMPLE_LICK,
        "bass": BASS_EXAMPLE_LICK,
        "drums": DRUM_EXAMPLE_LICK,
    }
    return examples[instrument]


def _stringed_schema(instrument: str) -> dict[str, Any]:
    title = "Bass Lick JSON" if instrument == "bass" else "Guitar Lick JSON"
    max_string = 5 if instrument == "bass" else 6
    tunings = BASS_TUNINGS if instrument == "bass" else TUNINGS
    techniques = _techniques_for_instrument(instrument)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "required": [
            "version",
            "instrument",
            "style",
            "tempo",
            "timeSignature",
            "key",
            "tuning",
            "bars",
            "resolution",
            "events",
        ],
        "properties": {
            "version": {"const": SPEC_VERSION},
            "instrument": {"const": instrument},
            "title": {"type": "string", "maxLength": 80},
            "style": {"enum": list(STYLES)},
            "tempo": {"type": "integer", "minimum": 40, "maximum": 240},
            "timeSignature": {"enum": list(TIME_SIGNATURES)},
            "key": {"type": "string", "maxLength": 32},
            "tuning": {"enum": list(tunings)},
            "customTuning": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4 if instrument == "bass" else 6,
                "maxItems": max_string,
            },
            "bars": {"type": "integer", "minimum": 1, "maximum": 16},
            "resolution": {"enum": list(RESOLUTIONS)},
            "events": {
                "type": "array",
                "minItems": 1,
                "maxItems": 128,
                "items": {
                    "oneOf": [
                        {
                            "type": "object",
                            "required": ["type", "start", "duration", "string", "fret"],
                            "properties": {
                                "type": {"const": "note"},
                                "start": {"type": "integer", "minimum": 0},
                                "duration": {"type": "integer", "minimum": 1},
                                "string": {"type": "integer", "minimum": 1, "maximum": max_string},
                                "fret": {"type": "integer", "minimum": 0, "maximum": 24},
                                "velocity": {"type": "integer", "minimum": 1, "maximum": 127},
                                "techniques": {
                                    "type": "array",
                                    "items": {"$ref": "#/$defs/technique"},
                                    "uniqueItems": True,
                                },
                            },
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "required": ["type", "start", "duration"],
                            "properties": {
                                "type": {"const": "rest"},
                                "start": {"type": "integer", "minimum": 0},
                                "duration": {"type": "integer", "minimum": 1},
                            },
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "required": ["type", "start", "duration", "notes"],
                            "properties": {
                                "type": {"const": "chord"},
                                "start": {"type": "integer", "minimum": 0},
                                "duration": {"type": "integer", "minimum": 1},
                                "notes": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 4,
                                    "items": {
                                        "type": "object",
                                        "required": ["string", "fret"],
                                        "properties": {
                                            "string": {"type": "integer", "minimum": 1, "maximum": max_string},
                                            "fret": {"type": "integer", "minimum": 0, "maximum": 24},
                                        },
                                        "additionalProperties": False,
                                    },
                                },
                                "velocity": {"type": "integer", "minimum": 1, "maximum": 127},
                                "techniques": {
                                    "type": "array",
                                    "items": {"$ref": "#/$defs/technique"},
                                    "uniqueItems": True,
                                },
                            },
                            "additionalProperties": False,
                        },
                    ],
                },
            },
        },
        "$defs": {"technique": {"enum": list(techniques)}},
        "additionalProperties": False,
    }


def _drum_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Drum Lick JSON",
        "type": "object",
        "required": [
            "version",
            "instrument",
            "style",
            "tempo",
            "timeSignature",
            "key",
            "bars",
            "resolution",
            "events",
        ],
        "properties": {
            "version": {"const": SPEC_VERSION},
            "instrument": {"const": "drums"},
            "title": {"type": "string", "maxLength": 80},
            "style": {"enum": list(STYLES)},
            "tempo": {"type": "integer", "minimum": 40, "maximum": 240},
            "timeSignature": {"enum": list(TIME_SIGNATURES)},
            "key": {"enum": ["none"]},
            "bars": {"type": "integer", "minimum": 1, "maximum": 16},
            "resolution": {"enum": list(RESOLUTIONS)},
            "events": {
                "type": "array",
                "minItems": 1,
                "maxItems": 256,
                "items": {
                    "oneOf": [
                        {
                            "type": "object",
                            "required": ["type", "start", "duration", "piece"],
                            "properties": {
                                "type": {"const": "hit"},
                                "start": {"type": "integer", "minimum": 0},
                                "duration": {"type": "integer", "minimum": 1},
                                "piece": {"enum": list(DRUM_PIECES)},
                                "velocity": {"type": "integer", "minimum": 1, "maximum": 127},
                                "techniques": {
                                    "type": "array",
                                    "items": {"$ref": "#/$defs/technique"},
                                    "uniqueItems": True,
                                },
                            },
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "required": ["type", "start", "duration"],
                            "properties": {
                                "type": {"const": "rest"},
                                "start": {"type": "integer", "minimum": 0},
                                "duration": {"type": "integer", "minimum": 1},
                            },
                            "additionalProperties": False,
                        },
                    ],
                },
            },
        },
        "$defs": {
            "piece": {"enum": list(DRUM_PIECES)},
            "technique": {"enum": list(DRUM_TECHNIQUES)},
        },
        "additionalProperties": False,
    }


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_llm_prompt(
    *,
    instrument: str,
    style: str,
    key: str,
    bars: int,
    tuning: str | None,
    tempo: int | None = None,
    time_signature: str = "4/4",
    resolution: int = 16,
    fret_range: str | None = None,
    include_techniques: tuple[str, ...] = (),
) -> str:
    musical_requirements = [
        f"- instrument: {instrument}",
        f"- style: {style}",
        f"- key: {key}",
        f"- bars: {bars}",
    ]
    if tuning is not None:
        musical_requirements.append(f"- tuning: {tuning}")
    if tempo is not None:
        musical_requirements.append(f"- tempo: {tempo}")
    musical_requirements.append(f"- timeSignature: {time_signature}")
    musical_requirements.append(f"- resolution: {resolution}")
    if fret_range:
        musical_requirements.append(f"- mostly use frets {fret_range}")
    for technique in include_techniques:
        musical_requirements.append(f"- include technique: {technique}")
    musical_requirements.extend(
        [
            *(_playability_lines(instrument)),
        ]
    )

    event_line = '- events must contain only "hit" or "rest"' if instrument == "drums" else '- events must contain only "note", "rest", or "chord"'
    position_line = (
        f"- hit events use piece from: {', '.join(DRUM_PIECES)}"
        if instrument == "drums"
        else f"- note events use string 1-{_max_string_for_instrument(instrument)} and fret 0-24"
    )
    tuning_line = (
        None
        if instrument == "drums"
        else f"- tuning must be one of: {', '.join(_quote(value) for value in _tunings_for_instrument(instrument))}"
    )
    techniques = _techniques_for_instrument(instrument)
    instrument_label = "drum" if instrument == "drums" else instrument

    return "\n".join(
        line for line in [
            f"Generate a {instrument_label} lick as valid JSON only.",
            "",
            f"Use Lick JSON Spec version {SPEC_VERSION}.",
            "",
            "Structural requirements:",
            f'- version must be "{SPEC_VERSION}"',
            f'- instrument must be "{instrument}"',
            "- tempo must be an integer from 40 to 240",
            f"- timeSignature must be one of: {', '.join(_quote(value) for value in TIME_SIGNATURES)}",
            f"- resolution must be one of: {', '.join(str(value) for value in RESOLUTIONS)}",
            tuning_line,
            event_line,
            position_line,
            f"- techniques must be selected only from: {', '.join(techniques)}",
            "- output JSON only",
            "- do not include markdown",
            "- do not include comments",
            "- do not include explanatory text",
            "",
            "Musical requirements:",
            *musical_requirements,
        ] if line is not None
    )


def build_summary(instrument: str = "guitar") -> str:
    event_types = "hit, rest" if instrument == "drums" else "note, rest, chord"
    techniques = _techniques_for_instrument(instrument)
    return "\n".join(
        [
            f"{instrument.title()} Lick JSON Spec v{SPEC_VERSION}",
            "",
            f"Purpose: constrained JSON for LLM-generated {instrument} licks.",
            "",
            "Required top-level fields:",
            _required_field_summary(instrument),
            "",
            "Event types:",
            event_types,
            "",
            "Allowed techniques:",
            ", ".join(techniques),
        ]
    )


def techniques_for_instrument(instrument: str) -> tuple[str, ...]:
    return _techniques_for_instrument(instrument)


def tunings_for_instrument(instrument: str) -> tuple[str, ...]:
    return _tunings_for_instrument(instrument)


def _quote(value: str) -> str:
    return f'"{value}"'


def _techniques_for_instrument(instrument: str) -> tuple[str, ...]:
    if instrument == "drums":
        return DRUM_TECHNIQUES
    if instrument == "bass":
        return BASS_TECHNIQUES
    return STRING_TECHNIQUES


def _tunings_for_instrument(instrument: str) -> tuple[str, ...]:
    return BASS_TUNINGS if instrument == "bass" else TUNINGS


def _max_string_for_instrument(instrument: str) -> int:
    return 5 if instrument == "bass" else 6


def _playability_lines(instrument: str) -> tuple[str, ...]:
    if instrument == "drums":
        return ("- make the groove playable by one drummer",)
    if instrument == "bass":
        return ("- avoid impossible string jumps", "- make the phrase playable on bass")
    return ("- avoid impossible string jumps", "- make the phrase playable on guitar")


def _required_field_summary(instrument: str) -> str:
    if instrument == "drums":
        return "version, instrument, style, tempo, timeSignature, key, bars, resolution, events"
    return "version, instrument, style, tempo, timeSignature, key, tuning, bars, resolution, events"
