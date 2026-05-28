from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def app_settings_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "Dicom-Video-Extractor" / "settings.json"
    return Path.home() / ".config" / "dicom-video-extractor" / "settings.json"


@dataclass(slots=True)
class AppSettings:
    output_dir: str
    last_input_dir: str
    clip_limit: str
    fps_override: str
    export_profile: str
    window_preset: str
    export_sidecars: bool
    overlay_enabled: bool
    anonymize_overlay: bool
    overlay_fields: list[str]


def default_app_settings() -> AppSettings:
    cwd = str(Path.cwd())
    return AppSettings(
        output_dir=cwd,
        last_input_dir=cwd,
        clip_limit="1.5",
        fps_override="",
        export_profile="Custom",
        window_preset="Auto",
        export_sidecars=True,
        overlay_enabled=False,
        anonymize_overlay=False,
        overlay_fields=["patient_name", "study_date", "fps"],
    )


def _coerce_settings_payload(payload: dict[str, Any]) -> AppSettings:
    defaults = default_app_settings()
    overlay_fields_raw = payload.get("overlay_fields", defaults.overlay_fields)
    overlay_fields = [
        str(item) for item in overlay_fields_raw if isinstance(item, (str, int, float))
    ]
    return AppSettings(
        output_dir=str(payload.get("output_dir", defaults.output_dir)),
        last_input_dir=str(payload.get("last_input_dir", defaults.last_input_dir)),
        clip_limit=str(payload.get("clip_limit", defaults.clip_limit)),
        fps_override=str(payload.get("fps_override", defaults.fps_override)),
        export_profile=str(payload.get("export_profile", defaults.export_profile)),
        window_preset=str(payload.get("window_preset", defaults.window_preset)),
        export_sidecars=bool(payload.get("export_sidecars", defaults.export_sidecars)),
        overlay_enabled=bool(payload.get("overlay_enabled", defaults.overlay_enabled)),
        anonymize_overlay=bool(payload.get("anonymize_overlay", defaults.anonymize_overlay)),
        overlay_fields=overlay_fields or defaults.overlay_fields,
    )


def load_app_settings(path: str | Path | None = None) -> AppSettings:
    settings_path = Path(path) if path is not None else app_settings_path()
    if not settings_path.exists():
        return default_app_settings()

    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return default_app_settings()

    if not isinstance(payload, dict):
        return default_app_settings()
    return _coerce_settings_payload(payload)


def save_app_settings(settings: AppSettings, path: str | Path | None = None) -> Path:
    settings_path = Path(path) if path is not None else app_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return settings_path
