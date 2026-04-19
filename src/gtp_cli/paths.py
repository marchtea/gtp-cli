from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConversionPaths:
    source: Path
    gpx: Path | None
    png: Path | None


def resolve_conversion_paths(
    *,
    source: Path,
    gpx: Path | None,
    png: Path | None,
    no_gpx: bool = False,
    no_png: bool = False,
    gpx_extension: str = "gpx",
    force: bool = False,
) -> ConversionPaths:
    resolved_source = source.expanduser().resolve()
    if not resolved_source.exists():
        raise FileNotFoundError(f"MusicXML file does not exist: {resolved_source}")
    if not resolved_source.is_file():
        raise ValueError(f"MusicXML path is not a file: {resolved_source}")

    normalized_extension = gpx_extension.lstrip(".") or "gpx"
    resolved_gpx = None if no_gpx else _resolve_output(gpx, resolved_source.with_suffix(f".{normalized_extension}"))
    resolved_png = None if no_png else _resolve_output(png, resolved_source.with_suffix(".png"))

    if not force:
        for candidate in (resolved_gpx, resolved_png):
            if candidate is not None and candidate.exists():
                raise FileExistsError(f"Output already exists, pass --force to overwrite: {candidate}")

    return ConversionPaths(source=resolved_source, gpx=resolved_gpx, png=resolved_png)


def ensure_output_directories(paths: ConversionPaths) -> None:
    for output in (paths.gpx, paths.png):
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)


def _resolve_output(value: Path | None, default: Path) -> Path:
    return (value if value is not None else default).expanduser().resolve()
