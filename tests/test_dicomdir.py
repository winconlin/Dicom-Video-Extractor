from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dicom_video_extractor.metadata import parse_dicomdir_series


class DicomDirParsingTests(unittest.TestCase):
    def test_parse_dicomdir_series_groups_files_by_series(self) -> None:
        records = [
            SimpleNamespace(
                DirectoryRecordType="STUDY",
                StudyInstanceUID="1.2.3",
                StudyDescription="Cardio Study",
            ),
            SimpleNamespace(
                DirectoryRecordType="SERIES",
                SeriesInstanceUID="1.2.3.4",
                SeriesDescription="Echo 4CH",
                Modality="US",
            ),
            SimpleNamespace(
                DirectoryRecordType="IMAGE",
                ReferencedFileID=["P001", "S001", "SE001", "IMG0001"],
            ),
            SimpleNamespace(
                DirectoryRecordType="IMAGE",
                ReferencedFileID="P001\\S001\\SE001\\IMG0002",
            ),
        ]
        dataset = SimpleNamespace(DirectoryRecordSequence=records)
        dicomdir_path = Path("C:/data/DICOMDIR")

        with patch("dicom_video_extractor.metadata.read_dataset", return_value=dataset):
            series = parse_dicomdir_series(dicomdir_path)

        self.assertEqual(len(series), 1)
        parsed = series[0]
        self.assertEqual(parsed.study_description, "Cardio Study")
        self.assertEqual(parsed.series_description, "Echo 4CH")
        self.assertEqual(parsed.modality, "US")
        self.assertEqual(
            parsed.files,
            (
                Path("C:/data/P001/S001/SE001/IMG0001"),
                Path("C:/data/P001/S001/SE001/IMG0002"),
            ),
        )

    def test_parse_dicomdir_series_returns_sorted_series(self) -> None:
        records = [
            SimpleNamespace(
                DirectoryRecordType="STUDY",
                StudyInstanceUID="9.9.9",
                StudyDescription="Zeta",
            ),
            SimpleNamespace(
                DirectoryRecordType="SERIES",
                SeriesInstanceUID="9.9.9.2",
                SeriesDescription="Series B",
                Modality="CT",
            ),
            SimpleNamespace(
                DirectoryRecordType="IMAGE",
                ReferencedFileID=["A", "B", "C", "IMG2"],
            ),
            SimpleNamespace(
                DirectoryRecordType="SERIES",
                SeriesInstanceUID="9.9.9.1",
                SeriesDescription="Series A",
                Modality="CT",
            ),
            SimpleNamespace(
                DirectoryRecordType="IMAGE",
                ReferencedFileID=["A", "B", "C", "IMG1"],
            ),
        ]
        dataset = SimpleNamespace(DirectoryRecordSequence=records)
        dicomdir_path = Path("C:/archive/DICOMDIR")

        with patch("dicom_video_extractor.metadata.read_dataset", return_value=dataset):
            series = parse_dicomdir_series(dicomdir_path)

        self.assertEqual(len(series), 2)
        self.assertEqual(series[0].series_description, "Series A")
        self.assertEqual(series[1].series_description, "Series B")


if __name__ == "__main__":
    unittest.main()
