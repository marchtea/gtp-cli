from __future__ import annotations

import json
from typing import Any

SPEC_VERSION = "0.1"

STYLES = ("rock", "blues", "blues_rock", "metal", "funk", "jazz", "country", "pop", "fusion")
TIME_SIGNATURES = ("4/4", "3/4", "6/8", "12/8")
TUNINGS = ("standard", "drop_d", "half_step_down", "open_g", "custom")
RESOLUTIONS = (16, 24)
TECHNIQUES = (
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

EXAMPLE_LICK: dict[str, Any] = {
    "version": SPEC_VERSION,
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


def guitar_lick_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Guitar Lick JSON",
        "type": "object",
        "required": [
            "version",
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
            "title": {"type": "string", "maxLength": 80},
            "style": {"enum": list(STYLES)},
            "tempo": {"type": "integer", "minimum": 40, "maximum": 240},
            "timeSignature": {"enum": list(TIME_SIGNATURES)},
            "key": {"type": "string", "maxLength": 32},
            "tuning": {"enum": list(TUNINGS)},
            "customTuning": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 6,
                "maxItems": 6,
            },
            "bars": {"type": "integer", "minimum": 1, "maximum": 8},
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
                                "string": {"type": "integer", "minimum": 1, "maximum": 6},
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
                                            "string": {"type": "integer", "minimum": 1, "maximum": 6},
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
        "$defs": {"technique": {"enum": list(TECHNIQUES)}},
        "additionalProperties": False,
    }


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_llm_prompt(
    *,
    style: str,
    key: str,
    bars: int,
    tuning: str,
    tempo: int | None = None,
    time_signature: str = "4/4",
    resolution: int = 16,
    fret_range: str | None = None,
    include_techniques: tuple[str, ...] = (),
) -> str:
    musical_requirements = [
        f"- style: {style}",
        f"- key: {key}",
        f"- bars: {bars}",
        f"- tuning: {tuning}",
    ]
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
            "- avoid impossible string jumps",
            "- make the phrase playable on guitar",
        ]
    )

    return "\n".join(
        [
            "Generate a guitar lick as valid JSON only.",
            "",
            f"Use Guitar Lick JSON Spec version {SPEC_VERSION}.",
            "",
            "Structural requirements:",
            f'- version must be "{SPEC_VERSION}"',
            "- tempo must be an integer from 40 to 240",
            f"- timeSignature must be one of: {', '.join(_quote(value) for value in TIME_SIGNATURES)}",
            f"- resolution must be one of: {', '.join(str(value) for value in RESOLUTIONS)}",
            f"- tuning must be one of: {', '.join(_quote(value) for value in TUNINGS)}",
            '- events must contain only "note", "rest", or "chord"',
            "- note events use string 1-6 and fret 0-24",
            f"- techniques must be selected only from: {', '.join(TECHNIQUES)}",
            "- output JSON only",
            "- do not include markdown",
            "- do not include comments",
            "- do not include explanatory text",
            "",
            "Musical requirements:",
            *musical_requirements,
        ]
    )


def build_summary() -> str:
    return "\n".join(
        [
            f"Guitar Lick JSON Spec v{SPEC_VERSION}",
            "",
            "Purpose: constrained JSON for LLM-generated guitar licks.",
            "",
            "Required top-level fields:",
            "version, style, tempo, timeSignature, key, tuning, bars, resolution, events",
            "",
            "Event types:",
            "note, rest, chord",
            "",
            "Allowed techniques:",
            ", ".join(TECHNIQUES),
        ]
    )


def _quote(value: str) -> str:
    return f'"{value}"'
