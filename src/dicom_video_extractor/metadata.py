from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DicomDirSeries, DicomMetadata


def _require_dcmread() -> Any:
    try:
        from pydicom import dcmread
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError(
            "pydicom is not installed. Install project dependencies before reading DICOM files."
        ) from exc
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
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _float_value(dataset: Any, attribute: str) -> float | None:
    value = getattr(dataset, attribute, None)
    if value in (None, ""):
        return None
    try:
        value = value[0]  # type: ignore[index]
    except (TypeError, IndexError, KeyError):
        pass
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _float_list_value(dataset: Any, attribute: str) -> list[float]:
    value = getattr(dataset, attribute, None)
    if value in (None, ""):
        return []

    try:
        items = list(value)  # type: ignore[arg-type]
    except TypeError:
        items = [value]

    parsed_values: list[float] = []
    for item in items:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            parsed_values.append(parsed)
    return parsed_values


def infer_frame_rate_from_dataset(
    dataset: Any,
    *,
    default_fps: int = 15,
    fps_override: float | None = None,
) -> float:
    if fps_override is not None and fps_override > 0:
        return float(fps_override)

    for attribute in ("CineRate", "RecommendedDisplayFrameRate"):
        parsed = _float_value(dataset, attribute)
        if parsed is None:
            continue
        if parsed > 0:
            return parsed

    frame_time_ms = _float_value(dataset, "FrameTime")
    if frame_time_ms is not None and frame_time_ms > 0:
        return 1000.0 / frame_time_ms

    frame_time_vector = _float_list_value(dataset, "FrameTimeVector")
    if frame_time_vector:
        average_frame_time_ms = sum(frame_time_vector) / len(frame_time_vector)
        if average_frame_time_ms > 0:
            return 1000.0 / average_frame_time_ms

    effective_duration = _float_value(dataset, "EffectiveDuration")
    number_of_frames = _int_value(dataset, "NumberOfFrames")
    if (
        effective_duration is not None
        and effective_duration > 0
        and number_of_frames
        and number_of_frames > 1
    ):
        return number_of_frames / effective_duration

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
        modality=_text_value(dataset, "Modality"),
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
        window_center=_float_value(dataset, "WindowCenter"),
        window_width=_float_value(dataset, "WindowWidth"),
    )


def _dicomdir_file_id_parts(file_id: Any) -> list[str]:
    if file_id in (None, ""):
        return []

    if isinstance(file_id, str):
        normalized = file_id.replace("\\", "/")
        return [part for part in normalized.split("/") if part]

    parts: list[str] = []
    try:
        values = list(file_id)
    except TypeError:
        values = [file_id]

    for value in values:
        text = str(value).strip()
        if not text:
            continue
        normalized = text.replace("\\", "/")
        parts.extend(part for part in normalized.split("/") if part)
    return parts


def _sort_series_key(item: DicomDirSeries) -> tuple[str, str, str, str, str]:
    return (
        item.study_description.lower(),
        item.study_instance_uid.lower(),
        item.series_description.lower(),
        item.series_instance_uid.lower(),
        item.modality.lower(),
    )


def parse_dicomdir_series(path: str | Path) -> list[DicomDirSeries]:
    source_path = Path(path)
    dataset = read_dataset(source_path, stop_before_pixels=True)
    records = getattr(dataset, "DirectoryRecordSequence", None)
    if not records:
        raise RuntimeError(f"{source_path.name} does not contain a DirectoryRecordSequence.")

    series_files: dict[
        tuple[str, str, str, str, str],
        list[Path],
    ] = {}

    current_study_uid = ""
    current_study_description = ""
    current_series_uid = ""
    current_series_description = ""
    current_modality = ""

    for record in records:
        record_type = str(getattr(record, "DirectoryRecordType", "")).upper()
        if record_type == "STUDY":
            current_study_uid = _text_value(record, "StudyInstanceUID")
            current_study_description = _text_value(record, "StudyDescription")
            current_series_uid = ""
            current_series_description = ""
            current_modality = ""
            continue

        if record_type == "SERIES":
            current_series_uid = _text_value(record, "SeriesInstanceUID")
            current_series_description = _text_value(record, "SeriesDescription")
            current_modality = _text_value(record, "Modality")
            continue

        file_parts = _dicomdir_file_id_parts(getattr(record, "ReferencedFileID", None))
        if not file_parts:
            continue

        key = (
            current_study_uid,
            current_series_uid,
            current_study_description,
            current_series_description,
            current_modality,
        )
        if key not in series_files:
            series_files[key] = []
        series_files[key].append(source_path.parent.joinpath(*file_parts))

    output: list[DicomDirSeries] = []
    for (study_uid, series_uid, study_desc, series_desc, modality), files in series_files.items():
        deduplicated = tuple(dict.fromkeys(files))
        output.append(
            DicomDirSeries(
                study_instance_uid=study_uid,
                series_instance_uid=series_uid,
                study_description=study_desc,
                series_description=series_desc,
                modality=modality,
                files=deduplicated,
            )
        )

    return sorted(output, key=_sort_series_key)
