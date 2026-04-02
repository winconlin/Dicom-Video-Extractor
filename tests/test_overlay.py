from __future__ import annotations

import unittest
from pathlib import Path

from dicom_video_extractor.models import DicomMetadata, OverlayField
from dicom_video_extractor.overlay import build_overlay_lines


class OverlayLineTests(unittest.TestCase):
    def test_selected_fields_are_rendered_in_stable_order(self) -> None:
        metadata = DicomMetadata(
            source_path=Path("scan.dcm"),
            patient_name="Alice Example",
            study_date="20240101",
            cine_rate=25.0,
        )

        lines = build_overlay_lines(
            metadata,
            (
                OverlayField.FPS,
                OverlayField.STUDY_DATE,
                OverlayField.PATIENT_NAME,
            ),
        )

        self.assertEqual(
            lines,
            [
                "Patient Name: Alice Example",
                "Study Date: 20240101",
                "FPS: 25",
            ],
        )

    def test_anonymization_masks_name_id_and_birth_date(self) -> None:
        metadata = DicomMetadata(
            source_path=Path("scan.dcm"),
            patient_id="4711",
            patient_name="Erika Beispiel",
            patient_birth_date="19840615",
            patient_sex="F",
            study_date="20240101",
        )

        lines = build_overlay_lines(
            metadata,
            (
                OverlayField.PATIENT_NAME,
                OverlayField.PATIENT_ID,
                OverlayField.PATIENT_BIRTH_DATE,
            ),
            anonymize=True,
        )

        self.assertTrue(lines[0].startswith("Patient Name: "))
        self.assertNotIn("Erika Beispiel", lines[0])
        self.assertEqual(lines[1], "Patient ID: ANON-E8FED7C5")
        self.assertEqual(lines[2], "Birth Date: Age 39")

    def test_empty_values_are_skipped(self) -> None:
        metadata = DicomMetadata(source_path=Path("scan.dcm"))

        lines = build_overlay_lines(
            metadata,
            (
                OverlayField.PATIENT_NAME,
                OverlayField.INSTITUTION_NAME,
            ),
        )

        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()
