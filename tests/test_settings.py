from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dicom_video_extractor.settings import (
    AppSettings,
    app_settings_path,
    default_app_settings,
    load_app_settings,
    save_app_settings,
)


class SettingsTests(unittest.TestCase):
    def test_default_settings_have_expected_values(self) -> None:
        settings = default_app_settings()
        self.assertEqual(settings.clip_limit, "1.5")
        self.assertEqual(settings.export_profile, "Custom")
        self.assertEqual(settings.window_preset, "Auto")
        self.assertTrue(settings.export_sidecars)
        self.assertIn("patient_name", settings.overlay_fields)

    def test_app_settings_path_uses_appdata_when_set(self) -> None:
        with patch.dict(os.environ, {"APPDATA": "C:/Users/Test/AppData/Roaming"}, clear=False):
            path = app_settings_path()
        self.assertEqual(
            path,
            Path("C:/Users/Test/AppData/Roaming/Dicom-Video-Extractor/settings.json"),
        )

    def test_load_missing_file_returns_defaults(self) -> None:
        with TemporaryDirectory() as tempdir:
            missing = Path(tempdir) / "missing.json"
            settings = load_app_settings(missing)
        self.assertEqual(settings.export_profile, "Custom")

    def test_load_invalid_json_returns_defaults(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            path.write_text("{invalid", encoding="utf-8")
            settings = load_app_settings(path)
        self.assertEqual(settings.window_preset, "Auto")

    def test_load_partial_payload_coerces_values(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "settings.json"
            payload = {
                "output_dir": "C:/out",
                "clip_limit": 2,
                "export_sidecars": 0,
                "overlay_fields": ["fps", 7],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            settings = load_app_settings(path)

        self.assertEqual(settings.output_dir, "C:/out")
        self.assertEqual(settings.clip_limit, "2")
        self.assertFalse(settings.export_sidecars)
        self.assertEqual(settings.overlay_fields, ["fps", "7"])

    def test_save_and_load_roundtrip(self) -> None:
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "conf" / "settings.json"
            original = AppSettings(
                output_dir="C:/export",
                last_input_dir="C:/input",
                clip_limit="1.9",
                fps_override="24",
                export_profile="Research",
                window_preset="CT Soft Tissue",
                export_sidecars=True,
                overlay_enabled=True,
                anonymize_overlay=True,
                overlay_fields=["study_date", "fps"],
            )
            written_path = save_app_settings(original, path)
            loaded = load_app_settings(path)

        self.assertEqual(written_path, path)
        self.assertEqual(loaded, original)


if __name__ == "__main__":
    unittest.main()
