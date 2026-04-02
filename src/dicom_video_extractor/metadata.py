from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DicomMetadata


def _require_dcmread() -> Any:
    try:
        from pydicom import dcmread
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("pydicom is not installed. Install project dependencies before reading DICOM files.") from exc
    return dcmread


def read_dataset(path: str | Path, *, stop_before_pixels: bool = True) -> Any:
    dcmread = _require_dcmread()
    return dcmread(str(path), stop_before_pixels=stop_before_pixels, force=True)


def _text_value(dataset: Any, attribute: str) -> str:
    value = getattr(dataset, attribute, "")
    if value in (None, ""):
        return ""
    return str(value)


def _int_value(dataset: Any, attribute: str) -> int | None:
    value = getattr(dataset, attribute, None)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def infer_frame_rate_from_dataset(
    dataset: Any,
    *,
    default_fps: int = 15,
    fps_override: float | None = None,
) -> float:
    if fps_override is not None and fps_override > 0:
        return float(fps_override)

    for attribute in ("CineRate", "RecommendedDisplayFrameRate"):
        value = getattr(dataset, attribute, None)
        if value in (None, ""):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed

    frame_time_ms = getattr(dataset, "FrameTime", None)
    if frame_time_ms not in (None, ""):
        try:
            parsed = float(frame_time_ms)
        except (TypeError, ValueError):
            parsed = 0.0
        if parsed > 0:
            return 1000.0 / parsed

    return float(default_fps)


def extract_metadata(
    path: str | Path,
    *,
    default_fps: int = 15,
    fps_override: float | None = None,
) -> DicomMetadata:
    source_path = Path(path)
    dataset = read_dataset(source_path, stop_before_pixels=True)

    return DicomMetadata(
        source_path=source_path,
        patient_id=_text_value(dataset, "PatientID"),
        patient_name=_text_value(dataset, "PatientName"),
        patient_birth_date=_text_value(dataset, "PatientBirthDate"),
        patient_sex=_text_value(dataset, "PatientSex"),
        study_id=_text_value(dataset, "StudyID"),
        study_date=_text_value(dataset, "StudyDate"),
        study_time=_text_value(dataset, "StudyTime"),
        institution_name=_text_value(dataset, "InstitutionName"),
        manufacturer=_text_value(dataset, "Manufacturer"),
        number_of_frames=_int_value(dataset, "NumberOfFrames"),
        cine_rate=infer_frame_rate_from_dataset(
            dataset,
            default_fps=default_fps,
            fps_override=fps_override,
        ),
    )
