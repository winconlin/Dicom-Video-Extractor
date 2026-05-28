from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dicom_video_extractor.ui import _prepare_retry_candidates


class UiHelpersTests(unittest.TestCase):
    def test_prepare_retry_candidates_deduplicates_and_filters_missing(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            file_a = root / "a.dcm"
            file_b = root / "b.dcm"
            missing = root / "missing.dcm"
            file_a.write_bytes(b"a")
            file_b.write_bytes(b"b")

            candidates, missing_count = _prepare_retry_candidates(
                [file_a, missing, file_a, file_b, missing]
            )

        self.assertEqual(candidates, [file_a, file_b])
        self.assertEqual(missing_count, 1)

    def test_prepare_retry_candidates_handles_empty_input(self) -> None:
        candidates, missing_count = _prepare_retry_candidates([])
        self.assertEqual(candidates, [])
        self.assertEqual(missing_count, 0)


if __name__ == "__main__":
    unittest.main()
