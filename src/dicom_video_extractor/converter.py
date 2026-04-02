from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .metadata import extract_metadata
from .models import ConversionFailure, ConversionOptions, ConversionResult, OutputFormat

try:
    import SimpleITK as sitk
except ImportError:  # pragma: no cover - optional import path
    sitk = None


class DicomConversionError(RuntimeError):
    pass


def _require_cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise DicomConversionError(
            "OpenCV is not installed. Install project dependencies before converting files."
        ) from exc
    return cv2


def _require_dcmread() -> Any:
    try:
        from pydicom import dcmread
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise DicomConversionError(
            "pydicom is not installed. Install project dependencies before converting files."
        ) from exc
    return dcmread


def load_dicom_frames(path: str | Path) -> np.ndarray:
    source_path = Path(path)
    errors: list[str] = []

    if sitk is not None:
        try:
            image = sitk.ReadImage(str(source_path))
            return np.asarray(sitk.GetArrayFromImage(image))
        except Exception as exc:  # pragma: no cover - depends on runtime codecs
            errors.append(f"SimpleITK: {exc}")

    try:
        dcmread = _require_dcmread()
        dataset = dcmread(str(source_path), force=True)
        return np.asarray(dataset.pixel_array)
    except Exception as exc:
        errors.append(f"pydicom: {exc}")

    joined_errors = "; ".join(errors) if errors else "Unknown DICOM loading error."
    decoder_hint = ""
    lowered_errors = joined_errors.lower()
    if any(keyword in lowered_errors for keyword in ("transfer syntax", "decoder", "decompress", "compressed")):
        decoder_hint = (
            " Install an appropriate pixel data decoder such as GDCM or pylibjpeg "
            "for compressed transfer syntaxes."
        )
    raise DicomConversionError(
        f"Could not decode pixel data from {source_path}: {joined_errors}.{decoder_hint}"
    )


def _scale_frame_to_uint8(frame: np.ndarray) -> np.ndarray:
    if frame.dtype == np.uint8:
        return frame.copy()

    if np.issubdtype(frame.dtype, np.integer):
        min_value = int(frame.min())
        max_value = int(frame.max())
        if 0 <= min_value and max_value <= 255:
            return frame.astype(np.uint8, copy=True)

    frame_float = frame.astype(np.float32, copy=False)
    min_value = float(frame_float.min())
    max_value = float(frame_float.max())

    if max_value <= min_value:
        return np.zeros(frame.shape, dtype=np.uint8)

    scaled = (frame_float - min_value) * (255.0 / (max_value - min_value))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def _flatten_grayscale_frames(array: np.ndarray) -> np.ndarray:
    height, width = array.shape[-2:]
    return array.reshape((-1, height, width))


def _flatten_color_frames(array: np.ndarray) -> np.ndarray:
    height, width, channels = array.shape[-3:]
    flattened = array.reshape((-1, height, width, channels))
    if channels == 4:
        return flattened[..., :3]
    return flattened


def normalize_pixel_array(pixel_array: np.ndarray) -> np.ndarray:
    array = np.asarray(pixel_array)
    array = np.squeeze(array)

    if array.ndim < 2:
        raise DicomConversionError(
            f"Unsupported DICOM pixel array shape {array.shape}. Expected at least two dimensions."
        )
    if array.ndim > 4:
        raise DicomConversionError(
            f"Unsupported DICOM pixel array shape {array.shape}. Expected between two and four dimensions."
        )

    if array.ndim == 2:
        normalized = array[np.newaxis, ...]
    elif array.shape[-1] in (3, 4):
        normalized = _flatten_color_frames(array)
    elif array.ndim == 3 and array.shape[0] in (3, 4):
        moved = np.moveaxis(array, -3, -1)
        normalized = _flatten_color_frames(moved)
    else:
        normalized = _flatten_grayscale_frames(array)

    return np.stack([_scale_frame_to_uint8(frame) for frame in normalized], axis=0)


def _apply_clahe_to_color_frame(frame: np.ndarray, clip_limit: float) -> np.ndarray:
    cv2 = _require_cv2()
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    enhanced_lightness = clahe.apply(lightness)
    merged = cv2.merge((enhanced_lightness, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)


def enhance_frames(frames: np.ndarray, clip_limit: float) -> np.ndarray:
    if clip_limit <= 0:
        return frames

    cv2 = _require_cv2()
    if frames.ndim == 3:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        return np.stack([clahe.apply(frame) for frame in frames], axis=0)

    return np.stack([_apply_clahe_to_color_frame(frame, clip_limit) for frame in frames], axis=0)


def build_output_path(
    source_path: str | Path,
    output_dir: str | Path,
    output_format: OutputFormat,
) -> Path:
    input_path = Path(source_path)
    directory = Path(output_dir)
    return directory / f"{input_path.stem}{output_format.suffix}"


def _video_codec(output_format: OutputFormat) -> int:
    cv2 = _require_cv2()
    if output_format is OutputFormat.MP4:
        return cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter_fourcc(*"MJPG")


def _to_bgr_frame(frame: np.ndarray) -> np.ndarray:
    cv2 = _require_cv2()
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def write_video(
    frames: np.ndarray,
    output_path: str | Path,
    *,
    fps: float,
    output_format: OutputFormat,
) -> None:
    cv2 = _require_cv2()
    if fps <= 0:
        raise DicomConversionError("FPS must be a positive number.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    first_frame = frames[0]
    height, width = first_frame.shape[:2]
    writer = cv2.VideoWriter(
        str(destination),
        _video_codec(output_format),
        float(fps),
        (width, height),
        True,
    )

    if not writer.isOpened():
        raise DicomConversionError(f"OpenCV could not open output file {destination}.")

    try:
        for frame in frames:
            writer.write(_to_bgr_frame(frame))
    finally:
        writer.release()


def convert_file(
    source_path: str | Path,
    output_dir: str | Path,
    options: ConversionOptions | None = None,
) -> ConversionResult:
    resolved_options = options or ConversionOptions()
    metadata = extract_metadata(
        source_path,
        default_fps=resolved_options.default_fps,
        fps_override=resolved_options.fps_override,
    )
    raw_frames = load_dicom_frames(source_path)
    normalized_frames = normalize_pixel_array(raw_frames)
    enhanced_frames = enhance_frames(normalized_frames, resolved_options.clip_limit)
    output_path = build_output_path(source_path, output_dir, resolved_options.output_format)

    fps = metadata.cine_rate or float(resolved_options.default_fps)
    write_video(
        enhanced_frames,
        output_path,
        fps=fps,
        output_format=resolved_options.output_format,
    )

    return ConversionResult(
        source_path=Path(source_path),
        output_path=output_path,
        frame_count=int(enhanced_frames.shape[0]),
        fps=fps,
        output_format=resolved_options.output_format,
    )


def convert_files(
    source_paths: Iterable[str | Path],
    output_dir: str | Path,
    options: ConversionOptions | None = None,
) -> tuple[list[ConversionResult], list[ConversionFailure]]:
    results: list[ConversionResult] = []
    failures: list[ConversionFailure] = []

    for source_path in source_paths:
        source = Path(source_path)
        try:
            results.append(convert_file(source, output_dir, options))
        except Exception as exc:
            failures.append(ConversionFailure(source_path=source, message=str(exc)))

    return results, failures
