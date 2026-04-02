from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from dicom_video_extractor.converter import DicomConversionError, build_output_path, normalize_pixel_array
from dicom_video_extractor.metadata import infer_frame_rate_from_dataset
from dicom_video_extractor.models import OutputFormat


class NormalizePixelArrayTests(unittest.TestCase):
    def test_single_grayscale_image_becomes_single_frame(self) -> None:
        image = np.array([[0, 1000], [2000, 4000]], dtype=np.int16)

        frames = normalize_pixel_array(image)

        self.assertEqual(frames.shape, (1, 2, 2))
        self.assertEqual(frames.dtype, np.uint8)

    def test_rgb_multiframe_keeps_color_dimension(self) -> None:
        image = np.arange(2 * 4 * 5 * 3, dtype=np.uint16).reshape(2, 4, 5, 3)

        frames = normalize_pixel_array(image)

        self.assertEqual(frames.shape, (2, 4, 5, 3))
        self.assertEqual(frames.dtype, np.uint8)

    def test_unsupported_shape_raises(self) -> None:
        image = np.zeros((2, 3, 4, 5, 6), dtype=np.uint8)

        with self.assertRaises(DicomConversionError):
            normalize_pixel_array(image)


class FrameRateInferenceTests(unittest.TestCase):
    def test_override_wins(self) -> None:
        dataset = SimpleNamespace(CineRate=25)
        self.assertEqual(infer_frame_rate_from_dataset(dataset, fps_override=12.5), 12.5)

    def test_frame_time_is_used_as_fallback(self) -> None:
        dataset = SimpleNamespace(FrameTime=40)
        self.assertEqual(infer_frame_rate_from_dataset(dataset), 25.0)

    def test_default_is_used_when_no_metadata_exists(self) -> None:
        dataset = SimpleNamespace()
        self.assertEqual(infer_frame_rate_from_dataset(dataset, default_fps=18), 18.0)


class OutputPathTests(unittest.TestCase):
    def test_output_path_uses_selected_extension(self) -> None:
        output_path = build_output_path("scan.dcm", Path("out"), OutputFormat.MP4)
        self.assertEqual(output_path, Path("out") / "scan.mp4")


if __name__ == "__main__":
    unittest.main()
