# Guitar Lick JSON Spec

Version: 0.1

This document defines a constrained JSON format for generating short guitar licks with an LLM. The format is designed to be easy for an LLM to produce, easy for code to validate, and straightforward to export to MIDI, MusicXML, or tablature-oriented formats.

## Goals

- Represent short guitar phrases using guitar-native positions: string and fret.
- Avoid ambiguous rhythmic values by using integer grid steps.
- Restrict techniques to a fixed enum so output can be validated.
- Keep the structure small enough for reliable LLM generation.
- Preserve enough information to export to MIDI first, then MusicXML or tab later.

## Non-Goals

- This is not a full replacement for MusicXML or Guitar Pro files.
- This does not attempt to represent every engraving detail.
- This does not require the LLM to calculate MIDI note numbers.
- This does not model advanced polyphonic guitar notation in version 0.1.

## Recommended Pipeline

1. Ask the LLM to generate a valid Guitar Lick JSON object.
2. Validate the object against the schema and semantic rules.
3. Convert string and fret positions into pitches.
4. Export to MIDI for playback or DAW import.
5. Optionally export to MusicXML or tablature after validation.

## Example

```json
{
  "version": "0.1",
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
      "techniques": ["pick"]
    },
    {
      "type": "note",
      "start": 2,
      "duration": 2,
      "string": 3,
      "fret": 9,
      "velocity": 92,
      "techniques": ["hammer_on"]
    },
    {
      "type": "note",
      "start": 4,
      "duration": 4,
      "string": 2,
      "fret": 8,
      "velocity": 96,
      "techniques": ["bend_half", "vibrato"]
    },
    {
      "type": "rest",
      "start": 8,
      "duration": 2
    },
    {
      "type": "note",
      "start": 10,
      "duration": 2,
      "string": 1,
      "fret": 7,
      "velocity": 88,
      "techniques": ["slide_in"]
    }
  ]
}
```

## Top-Level Fields

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `version` | Yes | string | Must be `"0.1"`. |
| `title` | No | string | Human-readable title, maximum 80 characters. |
| `style` | Yes | enum | Musical style hint. |
| `tempo` | Yes | integer | Beats per minute, from 40 to 240. |
| `timeSignature` | Yes | enum | Supported values: `"4/4"`, `"3/4"`, `"6/8"`, `"12/8"`. |
| `key` | Yes | string | Musical key, such as `"E minor"` or `"A blues"`. |
| `tuning` | Yes | enum | Supported values: `"standard"`, `"drop_d"`, `"half_step_down"`, `"open_g"`, `"custom"`. |
| `customTuning` | Conditional | string array | Required when `tuning` is `"custom"`. Strings are ordered from 6th string to 1st string. |
| `bars` | Yes | integer | Number of bars, from 1 to 8. |
| `resolution` | Yes | enum | Number of rhythmic steps per bar. Supported values: `16` and `24`. |
| `events` | Yes | array | Ordered list of note, rest, or chord events. |

## Rhythm Model

The format uses integer grid steps instead of fractional beats.

For `4/4` with `resolution: 16`:

| Musical Value | Steps |
| --- | --- |
| 1 bar | 16 |
| 1 beat / quarter note | 4 |
| eighth note | 2 |
| sixteenth note | 1 |

For `4/4` with `resolution: 24`:

| Musical Value | Steps |
| --- | --- |
| 1 bar | 24 |
| 1 beat / quarter note | 6 |
| eighth-note triplet | 2 |
| sixteenth-note triplet | 1 |

Use `resolution: 16` for straight rock, blues, pop, metal, country, and funk phrases. Use `resolution: 24` when triplets or swing-derived rhythms are required.

## Event Types

### Note Event

```json
{
  "type": "note",
  "start": 0,
  "duration": 2,
  "string": 3,
  "fret": 7,
  "velocity": 90,
  "techniques": ["pick"]
}
```

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `type` | Yes | string | Must be `"note"`. |
| `start` | Yes | integer | Start position in grid steps. |
| `duration` | Yes | integer | Duration in grid steps. Must be greater than 0. |
| `string` | Yes | integer | Guitar string number, from 1 to 6. String 1 is the high E string. |
| `fret` | Yes | integer | Fret number, from 0 to 24. |
| `velocity` | No | integer | MIDI-style velocity, from 1 to 127. Default: 90. |
| `techniques` | No | string array | Technique enum values. |

### Rest Event

```json
{
  "type": "rest",
  "start": 8,
  "duration": 2
}
```

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `type` | Yes | string | Must be `"rest"`. |
| `start` | Yes | integer | Start position in grid steps. |
| `duration` | Yes | integer | Duration in grid steps. Must be greater than 0. |

### Chord Event

```json
{
  "type": "chord",
  "start": 0,
  "duration": 4,
  "notes": [
    { "string": 5, "fret": 7 },
    { "string": 4, "fret": 9 }
  ],
  "velocity": 96,
  "techniques": ["pick"]
}
```

Use chord events for double-stops, power chords, and small guitar voicings. Version 0.1 limits chord events to 2-4 notes.

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `type` | Yes | string | Must be `"chord"`. |
| `start` | Yes | integer | Start position in grid steps. |
| `duration` | Yes | integer | Duration in grid steps. Must be greater than 0. |
| `notes` | Yes | array | Two to four string/fret pairs. |
| `velocity` | No | integer | MIDI-style velocity, from 1 to 127. Default: 90. |
| `techniques` | No | string array | Technique enum values. |

## Technique Enum

The `techniques` array may contain only the following values:

```text
pick
legato
hammer_on
pull_off
slide_in
slide_out
slide_up
slide_down
bend_quarter
bend_half
bend_full
release
vibrato
palm_mute
staccato
let_ring
dead_note
harmonic
pinch_harmonic
```

Implementation notes:

- `hammer_on` and `pull_off` should usually connect to a previous note on the same string.
- `bend_quarter`, `bend_half`, and `bend_full` affect playback differently from notation. MIDI export may approximate them with pitch bend.
- `dead_note` should export as a muted percussive event or a low-velocity muted note.
- `let_ring` may cause overlap in playback, but should still pass structural validation.

## Semantic Validation Rules

JSON Schema validation is necessary but not sufficient. The application should also enforce these semantic rules:

1. `start >= 0`.
2. `duration > 0`.
3. `start + duration <= bars * resolution`.
4. `events` are sorted by `start` ascending.
5. `string` is between 1 and 6.
6. `fret` is between 0 and 24.
7. `velocity` is between 1 and 127 when present.
8. `techniques` contains only allowed enum values.
9. A `rest` event must not overlap a `note` or `chord` event.
10. In monophonic mode, `note` and `chord` events must not overlap unless `let_ring` is present.
11. A `chord` event must not contain duplicate strings.
12. `tuning: "custom"` requires exactly six `customTuning` entries.
13. `customTuning` entries are ordered from string 6 to string 1.
14. A generated lick should be physically playable unless the caller explicitly allows impossible positions.

## JSON Schema

```json
{
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
    "events"
  ],
  "properties": {
    "version": {
      "const": "0.1"
    },
    "title": {
      "type": "string",
      "maxLength": 80
    },
    "style": {
      "enum": [
        "rock",
        "blues",
        "blues_rock",
        "metal",
        "funk",
        "jazz",
        "country",
        "pop",
        "fusion"
      ]
    },
    "tempo": {
      "type": "integer",
      "minimum": 40,
      "maximum": 240
    },
    "timeSignature": {
      "enum": ["4/4", "3/4", "6/8", "12/8"]
    },
    "key": {
      "type": "string",
      "maxLength": 32
    },
    "tuning": {
      "enum": ["standard", "drop_d", "half_step_down", "open_g", "custom"]
    },
    "customTuning": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 6,
      "maxItems": 6
    },
    "bars": {
      "type": "integer",
      "minimum": 1,
      "maximum": 8
    },
    "resolution": {
      "enum": [16, 24]
    },
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
              "type": {
                "const": "note"
              },
              "start": {
                "type": "integer",
                "minimum": 0
              },
              "duration": {
                "type": "integer",
                "minimum": 1
              },
              "string": {
                "type": "integer",
                "minimum": 1,
                "maximum": 6
              },
              "fret": {
                "type": "integer",
                "minimum": 0,
                "maximum": 24
              },
              "velocity": {
                "type": "integer",
                "minimum": 1,
                "maximum": 127
              },
              "techniques": {
                "type": "array",
                "items": {
                  "$ref": "#/$defs/technique"
                },
                "uniqueItems": true
              }
            },
            "additionalProperties": false
          },
          {
            "type": "object",
            "required": ["type", "start", "duration"],
            "properties": {
              "type": {
                "const": "rest"
              },
              "start": {
                "type": "integer",
                "minimum": 0
              },
              "duration": {
                "type": "integer",
                "minimum": 1
              }
            },
            "additionalProperties": false
          },
          {
            "type": "object",
            "required": ["type", "start", "duration", "notes"],
            "properties": {
              "type": {
                "const": "chord"
              },
              "start": {
                "type": "integer",
                "minimum": 0
              },
              "duration": {
                "type": "integer",
                "minimum": 1
              },
              "notes": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": {
                  "type": "object",
                  "required": ["string", "fret"],
                  "properties": {
                    "string": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 6
                    },
                    "fret": {
                      "type": "integer",
                      "minimum": 0,
                      "maximum": 24
                    }
                  },
                  "additionalProperties": false
                }
              },
              "velocity": {
                "type": "integer",
                "minimum": 1,
                "maximum": 127
              },
              "techniques": {
                "type": "array",
                "items": {
                  "$ref": "#/$defs/technique"
                },
                "uniqueItems": true
              }
            },
            "additionalProperties": false
          }
        ]
      }
    }
  },
  "$defs": {
    "technique": {
      "enum": [
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
        "pinch_harmonic"
      ]
    }
  },
  "additionalProperties": false
}
```

## LLM Prompt Template

```text
Generate a guitar lick as valid JSON only.

Use Guitar Lick JSON Spec version 0.1.

Structural requirements:
- version must be "0.1"
- tempo must be an integer from 40 to 240
- timeSignature must be one of: "4/4", "3/4", "6/8", "12/8"
- resolution must be 16 or 24
- tuning must be one of: "standard", "drop_d", "half_step_down", "open_g", "custom"
- events must contain only "note", "rest", or "chord"
- note events use string 1-6 and fret 0-24
- techniques must be selected only from the allowed enum
- output JSON only
- do not include markdown
- do not include comments
- do not include explanatory text

Musical requirements:
- style: blues_rock
- key: E minor
- bars: 2
- tuning: standard
- mostly use frets 5-12
- include one bend and one hammer-on
- avoid impossible string jumps
- make the phrase playable on guitar
```

## Export Notes

### MIDI

For MIDI export, derive the pitch from `tuning`, `string`, and `fret`.

Standard tuning from string 6 to string 1:

```text
E2 A2 D3 G3 B3 E4
```

MIDI export can ignore most notation-specific details at first:

- `start` maps to tick position.
- `duration` maps to note length.
- `velocity` maps directly to MIDI velocity.
- `bend_*` can be approximated with pitch-bend events.
- `palm_mute`, `dead_note`, and harmonics may require alternate channels or samples later.

### MusicXML

For MusicXML export, preserve guitar-specific fields:

- `string`
- `fret`
- `techniques`
- bend and release markings
- slide markings
- hammer-on and pull-off markings
- staccato and let-ring articulations

MusicXML export should be implemented after the JSON validator is stable.

## Versioning

Version 0.1 intentionally keeps the format small. Future versions may add:

- phrase-level metadata such as motif, call-and-response, and target notes
- scale-degree annotations
- per-note pitch cache
- fingering hints
- explicit swing feel
- per-track instrument information
- richer MusicXML articulation mapping
