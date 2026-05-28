from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .metadata import extract_metadata, read_dataset
from .models import (
    ConversionFailure,
    ConversionOptions,
    ConversionResult,
    DicomContentType,
    DicomMetadata,
    OutputFormat,
    WindowPreset,
)
from .overlay import build_overlay_lines

try:
    import SimpleITK as sitk
except ImportError:  # pragma: no cover - optional import path
    sitk = None  # type: ignore[assignment]


class DicomConversionError(RuntimeError):
    pass


def _installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _decoder_install_hint() -> str:
    missing: list[str] = []
    if not _installed("pylibjpeg"):
        missing.append("pylibjpeg")
    if not _installed("pylibjpeg_libjpeg"):
        missing.append("pylibjpeg-libjpeg")
    if not _installed("pylibjpeg_openjpeg"):
        missing.append("pylibjpeg-openjpeg")
    if not _installed("pylibjpeg_rle"):
        missing.append("pylibjpeg-rle")
    if not _installed("gdcm"):
        missing.append("python-gdcm")
    if not _installed("PIL"):
        missing.append("Pillow")

    if not missing:
        return (
            " Install another pixel-data decoder backend if this transfer syntax is still unsupported."
        )
    return " Install missing decoder backends: " + ", ".join(missing) + "."


def _require_cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise DicomConversionError(
            "OpenCV is not installed. Install project dependencies before converting files."
        ) from exc
    return cv2


def _invert_monochrome1_if_needed(dataset: Any, pixel_array: np.ndarray) -> np.ndarray:
    photometric = str(getattr(dataset, "PhotometricInterpretation", "")).upper()
    if photometric != "MONOCHROME1":
        return pixel_array
    if not np.issubdtype(pixel_array.dtype, np.number):
        return pixel_array
    min_value = np.min(pixel_array)
    max_value = np.max(pixel_array)
    return (max_value + min_value) - pixel_array


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
        dataset = read_dataset(source_path, stop_before_pixels=False)
        return _invert_monochrome1_if_needed(dataset, np.asarray(dataset.pixel_array))
    except Exception as exc:
        errors.append(f"pydicom: {exc}")

    joined_errors = "; ".join(errors) if errors else "Unknown DICOM loading error."
    decoder_hint = ""
    lowered_errors = joined_errors.lower()
    if any(keyword in lowered_errors for keyword in ("transfer syntax", "decoder", "decompress", "compressed")):
        decoder_hint = _decoder_install_hint()
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
    min_val_f = float(frame_float.min())
    max_val_f = float(frame_float.max())

    if max_val_f <= min_val_f:
        return np.zeros(frame.shape, dtype=np.uint8)

    scaled = (frame_float - min_val_f) * (255.0 / (max_val_f - min_val_f))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def _apply_window_center_width(frame: np.ndarray, center: float, width: float) -> np.ndarray:
    if width <= 1:
        return np.zeros(frame.shape, dtype=np.uint8)
    lower = center - (width / 2.0)
    upper = center + (width / 2.0)
    clipped = np.clip(frame.astype(np.float32, copy=False), lower, upper)
    scaled = (clipped - lower) * (255.0 / (upper - lower))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def _apply_percentile_window(frame: np.ndarray, lower_pct: float, upper_pct: float) -> np.ndarray:
    data = frame.astype(np.float32, copy=False)
    lower = float(np.percentile(data, lower_pct))
    upper = float(np.percentile(data, upper_pct))
    if upper <= lower:
        return _scale_frame_to_uint8(frame)
    clipped = np.clip(data, lower, upper)
    scaled = (clipped - lower) * (255.0 / (upper - lower))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def _is_color_like(array: np.ndarray) -> bool:
    if array.ndim >= 3 and array.shape[-1] in (3, 4):
        return True
    if array.ndim == 3 and array.shape[0] in (3, 4):
        return True
    return False


def _window_center_width_for_preset(
    metadata: DicomMetadata,
    preset: WindowPreset,
) -> tuple[float, float] | None:
    if preset is WindowPreset.AUTO:
        if metadata.window_center is not None and metadata.window_width is not None and metadata.window_width > 1:
            return (metadata.window_center, metadata.window_width)
        return None
    if preset is WindowPreset.CT_SOFT_TISSUE:
        return (40.0, 400.0)
    if preset is WindowPreset.CT_LUNG:
        return (-600.0, 1500.0)
    if preset is WindowPreset.CT_BONE:
        return (300.0, 2000.0)
    return None


def apply_window_preset(
    pixel_array: np.ndarray,
    metadata: DicomMetadata,
    preset: WindowPreset,
) -> np.ndarray:
    array = np.asarray(pixel_array)
    array = np.squeeze(array)

    if array.ndim < 2 or _is_color_like(array):
        return array

    height, width = array.shape[-2:]
    frames = array.reshape((-1, height, width))
    wc_ww = _window_center_width_for_preset(metadata, preset)
    if wc_ww is not None:
        center, window_width = wc_ww
        return np.stack(
            [_apply_window_center_width(frame, center, window_width) for frame in frames],
            axis=0,
        )

    if preset is WindowPreset.MR_BRAIN:
        return np.stack(
            [_apply_percentile_window(frame, 1.0, 99.0) for frame in frames],
            axis=0,
        )

    if preset is WindowPreset.US_GENERAL:
        return np.stack(
            [_apply_percentile_window(frame, 5.0, 98.0) for frame in frames],
            axis=0,
        )

    return array


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

    return np.stack(
        [_apply_clahe_to_color_frame(frame, clip_limit) for frame in frames], axis=0
    )


def _draw_overlay_box(
    frame: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
) -> np.ndarray:
    cv2 = _require_cv2()
    if frame.ndim == 2:
        output = frame.copy()
        cv2.rectangle(output, top_left, bottom_right, 0, thickness=-1)
        return output

    overlay = frame.copy()
    cv2.rectangle(overlay, top_left, bottom_right, (0, 0, 0), thickness=-1)
    return cv2.addWeighted(overlay, 0.35, frame, 0.65, 0.0)


def _overlay_frame_text(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    if not lines:
        return frame

    cv2 = _require_cv2()
    output = frame.copy()
    height, width = output.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.5, min(height, width) / 900.0)
    thickness = max(1, int(round(font_scale * 2)))
    margin = max(10, int(round(font_scale * 18)))
    line_spacing = max(8, int(round(font_scale * 12)))

    text_sizes = [
        cv2.getTextSize(line, font, font_scale, thickness)[0] for line in lines
    ]
    max_width = max(size[0] for size in text_sizes)
    line_height = max(size[1] for size in text_sizes)
    box_height = margin * 2 + len(lines) * line_height + (len(lines) - 1) * line_spacing
    box_width = margin * 2 + max_width

    output = _draw_overlay_box(output, (12, 12), (12 + box_width, 12 + box_height))
    text_color: int | tuple[int, int, int]
    if output.ndim == 2:
        text_color = 255
    else:
        text_color = (255, 255, 255)

    baseline_y = 12 + margin + line_height
    for index, line in enumerate(lines):
        y = baseline_y + index * (line_height + line_spacing)
        cv2.putText(
            output,
            line,
            (12 + margin, y),
            font,
            font_scale,
            text_color,
            thickness,
            cv2.LINE_AA,
        )
    return output


def overlay_metadata_on_frames(frames: np.ndarray, lines: list[str]) -> np.ndarray:
    if not lines:
        return frames
    return np.stack([_overlay_frame_text(frame, lines) for frame in frames], axis=0)


def build_output_path(
    source_path: str | Path,
    output_dir: str | Path,
    output_format: OutputFormat,
) -> Path:
    input_path = Path(source_path)
    directory = Path(output_dir)
    return directory / f"{input_path.stem}{output_format.suffix}"


def build_output_paths_for_content(
    source_path: str | Path,
    output_dir: str | Path,
    content_type: DicomContentType,
) -> tuple[Path, ...]:
    input_path = Path(source_path)
    directory = Path(output_dir)
    if content_type is DicomContentType.MOVING_IMAGE:
        return (
            directory / f"{input_path.stem}.mp4",
            directory / f"{input_path.stem}.avi",
        )
    return (
        directory / f"{input_path.stem}.png",
        directory / f"{input_path.stem}.jpg",
    )


def detect_content_type(metadata_number_of_frames: int | None, frames: np.ndarray) -> DicomContentType:
    if metadata_number_of_frames is not None and metadata_number_of_frames > 1:
        return DicomContentType.MOVING_IMAGE
    if int(frames.shape[0]) > 1:
        return DicomContentType.MOVING_IMAGE
    return DicomContentType.SINGLE_IMAGE


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


def write_image(frame: np.ndarray, output_path: str | Path) -> None:
    cv2 = _require_cv2()
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = _to_bgr_frame(frame) if frame.ndim == 3 else frame
    if not cv2.imwrite(str(destination), image):
        raise DicomConversionError(f"OpenCV could not write output image {destination}.")


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
    preprocessed_frames = apply_window_preset(
        raw_frames,
        metadata,
        resolved_options.window_preset,
    )
    normalized_frames = normalize_pixel_array(preprocessed_frames)
    content_type = detect_content_type(metadata.number_of_frames, normalized_frames)
    enhanced_frames = enhance_frames(normalized_frames, resolved_options.clip_limit)
    overlay_lines = build_overlay_lines(
        metadata,
        resolved_options.overlay_fields,
        anonymize=resolved_options.anonymize_overlay,
    )
    final_frames = overlay_metadata_on_frames(enhanced_frames, overlay_lines)
    output_paths = build_output_paths_for_content(source_path, output_dir, content_type)

    fps: float | None = None
    if content_type is DicomContentType.MOVING_IMAGE:
        fps = metadata.cine_rate or float(resolved_options.default_fps)
        write_video(
            final_frames,
            output_paths[0],
            fps=fps,
            output_format=OutputFormat.MP4,
        )
        write_video(
            final_frames,
            output_paths[1],
            fps=fps,
            output_format=OutputFormat.AVI,
        )
    else:
        first_frame = final_frames[0]
        write_image(first_frame, output_paths[0])
        write_image(first_frame, output_paths[1])

    return ConversionResult(
        source_path=Path(source_path),
        output_paths=output_paths,
        frame_count=int(final_frames.shape[0]),
        fps=fps,
        content_type=content_type,
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
