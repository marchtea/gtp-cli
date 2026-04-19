# Lick JSON Spec

Version: 0.2

This document defines constrained JSON formats for LLM-generated guitar, bass, and drum licks. The format is designed to be easy for an LLM to produce, easy for code to validate, and straightforward to export to MIDI, MusicXML, or tablature-oriented formats.

## Goals

- Represent short instrument phrases in a small, validated JSON structure.
- Use integer rhythm grid steps instead of ambiguous fractional beats.
- Keep each instrument's event model explicit.
- Restrict techniques and drum pieces to fixed enums.
- Preserve enough information to export to MIDI first, then MusicXML or tab later.

## Supported Instruments

| Instrument | Position Model | Event Types | Notes |
| --- | --- | --- | --- |
| `guitar` | `string` and `fret` | `note`, `rest`, `chord` | Six-string fretted phrases and chords. |
| `bass` | `string` and `fret` | `note`, `rest`, `chord` | Four- or five-string bass phrases, double-stops, and small voicings. |
| `drums` | `piece` | `hit`, `rest` | Fixed drum-piece enum for MIDI drum mapping. |

## Recommended Pipeline

1. Ask the LLM to generate a valid Lick JSON object for a specific instrument.
2. Validate the object against the instrument-specific schema and semantic rules.
3. Convert the events into pitches or drum notes.
4. Export to MIDI for playback or DAW import.
5. Optionally export guitar and bass parts to MusicXML or tablature after validation.

## CLI Access

The current schemas and prompts are exposed through `gtp-cli`. Treat the CLI output as the authoritative machine-readable spec.

Print a generation prompt:

```bash
uv run gtp-cli lick-spec --instrument guitar --format prompt
uv run gtp-cli lick-spec --instrument bass --format prompt
uv run gtp-cli lick-spec --instrument drums --format prompt
```

Print the JSON Schema for an instrument:

```bash
uv run gtp-cli lick-spec --instrument guitar --format schema
uv run gtp-cli lick-spec --instrument bass --format schema
uv run gtp-cli lick-spec --instrument drums --format schema
```

Print an example lick:

```bash
uv run gtp-cli lick-spec --instrument guitar --format example
uv run gtp-cli lick-spec --instrument bass --format example
uv run gtp-cli lick-spec --instrument drums --format example
```

Print a compact summary:

```bash
uv run gtp-cli lick-spec --instrument guitar --format summary
uv run gtp-cli lick-spec --instrument bass --format summary
uv run gtp-cli lick-spec --instrument drums --format summary
```

Prompt output can be parameterized:

```bash
uv run gtp-cli lick-spec \
  --instrument bass \
  --format prompt \
  --style funk \
  --key "E minor" \
  --bars 2 \
  --tuning standard_4 \
  --tempo 105 \
  --resolution 16 \
  --fret-range 3-9 \
  --include-technique finger \
  --include-technique palm_mute
```

```bash
uv run gtp-cli lick-spec \
  --instrument drums \
  --format prompt \
  --style rock \
  --key none \
  --bars 1 \
  --tempo 120 \
  --resolution 16 \
  --include-technique ghost \
  --include-technique accent
```

## Top-Level Fields

| Field | Guitar | Bass | Drums | Description |
| --- | --- | --- | --- | --- |
| `version` | Required | Required | Required | Must be `"0.2"`. |
| `instrument` | Required | Required | Required | Must be `"guitar"`, `"bass"`, or `"drums"`. |
| `title` | Optional | Optional | Optional | Human-readable title, maximum 80 characters. |
| `style` | Required | Required | Required | Musical style hint. |
| `tempo` | Required | Required | Required | Beats per minute, from 40 to 240. |
| `timeSignature` | Required | Required | Required | Supported values: `"4/4"`, `"3/4"`, `"6/8"`, `"12/8"`. |
| `key` | Required | Required | Required | Musical key for guitar and bass; drums use `"none"`. |
| `tuning` | Required | Required | Not used | Guitar or bass tuning enum. |
| `customTuning` | Conditional | Conditional | Not used | Required when `tuning` is `"custom"`. |
| `bars` | Required | Required | Required | Number of bars, from 1 to 16. |
| `resolution` | Required | Required | Required | Number of rhythmic steps per bar. Supported values: `16` and `24`. |
| `events` | Required | Required | Required | Ordered list of instrument events. |

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

## Guitar Events

Guitar supports `note`, `rest`, and `chord` events.

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

Guitar constraints:

- `string`: 1-6, where string 1 is high E.
- `fret`: 0-24.
- `chord.notes`: 2-4 string/fret pairs.
- `tuning`: `standard`, `drop_d`, `half_step_down`, `open_g`, or `custom`.
- `customTuning`: six pitches ordered from string 6 to string 1.

## Bass Events

Bass supports `note`, `rest`, and `chord` events with the same shape as guitar.

```json
{
  "type": "note",
  "start": 0,
  "duration": 2,
  "string": 4,
  "fret": 5,
  "velocity": 96,
  "techniques": ["finger"]
}
```

Bass constraints:

- `string`: 1-5.
- `fret`: 0-24.
- `chord.notes`: 2-4 string/fret pairs.
- `tuning`: `standard_4`, `drop_d`, `standard_5`, `half_step_down`, or `custom`.
- `customTuning`: four to five pitches ordered from lowest string to highest string.

## Drum Events

Drums support `hit` and `rest` events.

```json
{
  "type": "hit",
  "start": 4,
  "duration": 1,
  "piece": "snare",
  "velocity": 112,
  "techniques": ["accent"]
}
```

Drum constraints:

- `key` must be `"none"`.
- `piece` must come from the fixed drum-piece enum.
- Multiple `hit` events may share the same `start` to represent simultaneous kit hits.
- `duration` is usually `1`, but may be longer for cymbal or open-hat export behavior.

Supported drum pieces:

```text
kick
snare
rim
closed_hat
open_hat
pedal_hat
ride
ride_bell
crash_1
crash_2
tom_high
tom_mid
tom_floor
```

## Technique Enums

Guitar techniques:

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

Bass techniques:

```text
finger
pick
slap
pop
hammer_on
pull_off
slide_up
slide_down
palm_mute
staccato
let_ring
dead_note
harmonic
```

Drum techniques:

```text
normal
accent
ghost
rimshot
flam
drag
open
closed
choke
```

## Semantic Validation Rules

JSON Schema validation is necessary but not sufficient. The application should also enforce these semantic rules:

1. `start >= 0`.
2. `duration > 0`.
3. `start + duration <= bars * resolution`.
4. `events` are sorted by `start` ascending.
5. `velocity` is between 1 and 127 when present.
6. `techniques` contains only values allowed for the selected instrument.
7. A `rest` event must not overlap a playable event unless the caller explicitly allows it.
8. Guitar and bass `chord` events must not contain duplicate strings.
9. Guitar and bass phrases should avoid impossible string jumps unless explicitly allowed.
10. Drum phrases should remain playable by one drummer unless explicitly allowed.

## Export Notes

For MIDI export:

- Guitar and bass derive pitch from `tuning`, `string`, and `fret`.
- Drums map `piece` to MIDI drum notes.
- `start` maps to tick position.
- `duration` maps to note length.
- `velocity` maps directly to MIDI velocity.

For MusicXML export:

- Preserve guitar and bass `string`, `fret`, and `techniques`.
- Map drum `piece` values to percussion staff instruments.
- Treat advanced techniques as notation hints after the validator is stable.
