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

## Notes

Guitar Pro 8 does not provide a stable public command line interface on macOS, so this tool uses AppleScript and System Events to drive the normal application menus. Menu names can differ by Guitar Pro version or app language; if needed, pass custom menu paths:

```bash
uv run gtp-cli convert ./score.musicxml \
  --gpx-menu "File>Export>GPX..." \
  --png-menu "File>Export>PNG..."
```

## Docs

- [Guitar Lick JSON Spec](docs/guitar-lick-json-spec.md)
