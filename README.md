# gtp-cli

`gtp-cli` is a macOS command line wrapper for Guitar Pro 8 workflows that are not exposed as native CLI commands.

The first supported workflow imports a MusicXML file into Guitar Pro 8, saves the opened score as a Guitar Pro output file, and exports a PNG image through macOS UI automation.

## Requirements

- macOS
- Guitar Pro 8 installed
- Accessibility permission for the terminal app that runs `gtp-cli`

Grant permission in **System Settings > Privacy & Security > Accessibility** for Terminal, iTerm, VS Code, or whichever app launches the command.

## Usage

```bash
uv run gtp-cli convert ./score.musicxml
```

By default, this writes:

- `./score.gpx`
- `./score.png`

Common options:

```bash
uv run gtp-cli convert ./score.musicxml --gpx ./out/score.gpx --png ./out/score.png --force
uv run gtp-cli convert ./score.musicxml --no-png
uv run gtp-cli convert ./score.musicxml --app "Guitar Pro 8"
uv run gtp-cli convert ./score.musicxml --dry-run
```

Use `--dry-run` to inspect the generated AppleScript without opening Guitar Pro.

## LLM Lick Spec

`gtp-cli` can print constrained JSON specs for LLM-generated guitar, bass, and drum licks:

```bash
uv run gtp-cli lick-spec --instrument guitar --format prompt
uv run gtp-cli lick-spec --instrument bass --format schema
uv run gtp-cli lick-spec --instrument drums --format example
uv run gtp-cli lick-spec --instrument guitar --format summary
```

Generate a prompt with musical constraints:

```bash
uv run gtp-cli lick-spec \
  --instrument guitar \
  --format prompt \
  --style blues_rock \
  --key "E minor" \
  --bars 2 \
  --tuning standard \
  --tempo 120 \
  --fret-range 5-12 \
  --include-technique hammer_on \
  --include-technique bend_half
```

Generate a drum prompt:

```bash
uv run gtp-cli lick-spec \
  --instrument drums \
  --format prompt \
  --style rock \
  --key none \
  --bars 1 \
  --tempo 120 \
  --include-technique ghost \
  --include-technique accent
```

## Verification

Run the unit tests:

```bash
uv run pytest
```

Verify that the generated AppleScript compiles without opening Guitar Pro:

```bash
uv run gtp-cli convert 'tests/7和弦順階連奏.xml' --force --dry-run > /tmp/gtp-cli-e2e.applescript
osacompile -o /tmp/gtp-cli-e2e.scpt /tmp/gtp-cli-e2e.applescript
```

Run the real end-to-end Guitar Pro 8 conversion:

```bash
rm -f 'tests/7和弦順階連奏.gpx' 'tests/7和弦順階連奏.png'
uv run gtp-cli convert 'tests/7和弦順階連奏.xml' --force --timeout 75 --settle-delay 1 --keep-open
file 'tests/7和弦順階連奏.gpx' 'tests/7和弦順階連奏.png'
```

## Packaging

Build the source distribution and wheel:

```bash
scripts/package.sh
```

The script runs the unit tests, verifies that the generated AppleScript compiles, and writes packages to `dist/`.

## Notes

Guitar Pro 8 does not provide a stable public command line interface on macOS, so this tool uses AppleScript and System Events to drive the normal application menus. Menu names can differ by Guitar Pro version or app language; if needed, pass custom menu paths:

```bash
uv run gtp-cli convert ./score.musicxml \
  --gpx-menu "File>Export>GPX..." \
  --png-menu "File>Export>PNG..."
```

## Docs

- [Lick JSON Spec](docs/lick-json-spec.md)
