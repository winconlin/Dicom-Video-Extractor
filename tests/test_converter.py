from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from dicom_video_extractor.converter import (
    DicomConversionError,
    build_output_path,
    build_output_paths_for_content,
    detect_content_type,
    normalize_pixel_array,
)
from dicom_video_extractor.metadata import infer_frame_rate_from_dataset
from dicom_video_extractor.models import DicomContentType, OutputFormat


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

    def test_channel_first_rgb_is_reordered_to_color_last(self) -> None:
        image = np.arange(3 * 4 * 5, dtype=np.uint16).reshape(3, 4, 5)

        frames = normalize_pixel_array(image)

        self.assertEqual(frames.shape, (1, 4, 5, 3))
        self.assertEqual(frames.dtype, np.uint8)

    def test_4d_grayscale_is_flattened_to_a_frame_sequence(self) -> None:
        image = np.arange(2 * 3 * 4 * 5, dtype=np.uint16).reshape(2, 3, 4, 5)

        frames = normalize_pixel_array(image)

        self.assertEqual(frames.shape, (6, 4, 5))
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

    def test_recommended_display_frame_rate_is_used_when_cine_rate_is_missing(self) -> None:
        dataset = SimpleNamespace(RecommendedDisplayFrameRate=20)
        self.assertEqual(infer_frame_rate_from_dataset(dataset), 20.0)

    def test_frame_time_vector_is_used_when_frame_time_is_missing(self) -> None:
        dataset = SimpleNamespace(FrameTimeVector=[50, 50, 50])
        self.assertEqual(infer_frame_rate_from_dataset(dataset), 20.0)

    def test_effective_duration_and_frame_count_are_used_as_last_resort(self) -> None:
        dataset = SimpleNamespace(EffectiveDuration=2.0, NumberOfFrames=60)
        self.assertEqual(infer_frame_rate_from_dataset(dataset), 30.0)

    def test_default_is_used_when_no_metadata_exists(self) -> None:
        dataset = SimpleNamespace()
        self.assertEqual(infer_frame_rate_from_dataset(dataset, default_fps=18), 18.0)


class OutputPathTests(unittest.TestCase):
    def test_output_path_uses_selected_extension(self) -> None:
        output_path = build_output_path("scan.dcm", Path("out"), OutputFormat.MP4)
        self.assertEqual(output_path, Path("out") / "scan.mp4")

    def test_build_output_paths_for_moving_images(self) -> None:
        output_paths = build_output_paths_for_content(
            "scan.dcm",
            Path("out"),
            DicomContentType.MOVING_IMAGE,
        )
        self.assertEqual(output_paths, (Path("out") / "scan.mp4", Path("out") / "scan.avi"))

    def test_build_output_paths_for_single_images(self) -> None:
        output_paths = build_output_paths_for_content(
            "scan",
            Path("out"),
            DicomContentType.SINGLE_IMAGE,
        )
        self.assertEqual(output_paths, (Path("out") / "scan.png", Path("out") / "scan.jpg"))


class ContentTypeDetectionTests(unittest.TestCase):
    def test_detects_moving_image_from_metadata(self) -> None:
        frames = np.zeros((1, 10, 10), dtype=np.uint8)
        self.assertEqual(detect_content_type(5, frames), DicomContentType.MOVING_IMAGE)

    def test_detects_moving_image_from_frame_count_when_metadata_missing(self) -> None:
        frames = np.zeros((3, 10, 10), dtype=np.uint8)
        self.assertEqual(detect_content_type(None, frames), DicomContentType.MOVING_IMAGE)

    def test_detects_single_image(self) -> None:
        frames = np.zeros((1, 10, 10), dtype=np.uint8)
        self.assertEqual(detect_content_type(None, frames), DicomContentType.SINGLE_IMAGE)


if __name__ == "__main__":
    unittest.main()
