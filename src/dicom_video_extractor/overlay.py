from __future__ import annotations

from datetime import datetime
from hashlib import sha1

from .models import DicomMetadata, OverlayField


def ordered_overlay_fields() -> tuple[OverlayField, ...]:
    return (
        OverlayField.PATIENT_NAME,
        OverlayField.PATIENT_ID,
        OverlayField.PATIENT_BIRTH_DATE,
        OverlayField.PATIENT_SEX,
        OverlayField.STUDY_DATE,
        OverlayField.STUDY_TIME,
        OverlayField.STUDY_ID,
        OverlayField.INSTITUTION_NAME,
        OverlayField.MANUFACTURER,
        OverlayField.NUMBER_OF_FRAMES,
        OverlayField.FPS,
    )


def _field_value(metadata: DicomMetadata, field: OverlayField) -> str:
    if field is OverlayField.PATIENT_ID:
        return metadata.patient_id
    if field is OverlayField.PATIENT_NAME:
        return metadata.patient_name
    if field is OverlayField.PATIENT_SEX:
        return metadata.patient_sex
    if field is OverlayField.PATIENT_BIRTH_DATE:
        return metadata.patient_birth_date
    if field is OverlayField.STUDY_ID:
        return metadata.study_id
    if field is OverlayField.STUDY_DATE:
        return metadata.study_date
    if field is OverlayField.STUDY_TIME:
        return metadata.study_time
    if field is OverlayField.INSTITUTION_NAME:
        return metadata.institution_name
    if field is OverlayField.MANUFACTURER:
        return metadata.manufacturer
    if field is OverlayField.NUMBER_OF_FRAMES:
        return "" if metadata.number_of_frames is None else str(metadata.number_of_frames)
    if field is OverlayField.FPS:
        return "" if metadata.cine_rate is None else f"{metadata.cine_rate:g}"
    raise ValueError(f"Unsupported overlay field: {field}")


def _placeholder_name(metadata: DicomMetadata) -> str:
    source = metadata.patient_name.strip() or metadata.patient_id.strip() or "anonymous"
    sex = metadata.patient_sex.strip().upper()
    if sex.startswith("M"):
        options = ("Max Mustermann", "John Doe")
    elif sex.startswith("F"):
        options = ("Erika Musterfrau", "Jane Doe")
    else:
        options = ("Alex Beispiel", "Jordan Doe")
    digest = int(sha1(source.encode("utf-8")).hexdigest(), 16)
    return options[digest % len(options)]


def _anonymized_patient_id(metadata: DicomMetadata) -> str:
    source = metadata.patient_id.strip() or metadata.patient_name.strip() or "anonymous"
    digest = sha1(source.encode("utf-8")).hexdigest().upper()
    return f"ANON-{digest[:8]}"


def _parse_dicom_date(raw_value: str) -> datetime | None:
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    for pattern in ("%Y%m%d", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(cleaned, pattern)
        except ValueError:
            continue
    return None


def _anonymized_birth_value(metadata: DicomMetadata) -> str:
    birth_date = _parse_dicom_date(metadata.patient_birth_date)
    study_date = _parse_dicom_date(metadata.study_date)
    if birth_date is not None and study_date is not None and study_date >= birth_date:
        years = study_date.year - birth_date.year
        before_birthday = (study_date.month, study_date.day) < (birth_date.month, birth_date.day)
        age = years - int(before_birthday)
        if age >= 0:
            return f"Age {age}"
    if birth_date is not None:
        return str(birth_date.year)

    stripped = metadata.patient_birth_date.strip()
    if len(stripped) >= 4 and stripped[:4].isdigit():
        return stripped[:4]
    return ""


def anonymized_overlay_value(metadata: DicomMetadata, field: OverlayField) -> str:
    if field is OverlayField.PATIENT_NAME:
        return _placeholder_name(metadata)
    if field is OverlayField.PATIENT_ID:
        return _anonymized_patient_id(metadata)
    if field is OverlayField.PATIENT_BIRTH_DATE:
        return _anonymized_birth_value(metadata)
    return _field_value(metadata, field)


def build_overlay_lines(
    metadata: DicomMetadata,
    fields: tuple[OverlayField, ...],
    *,
    anonymize: bool = False,
) -> list[str]:
    lines: list[str] = []
    for field in ordered_overlay_fields():
        if field not in fields:
            continue
        value = anonymized_overlay_value(metadata, field) if anonymize else _field_value(metadata, field)
        if not value:
            continue
        lines.append(f"{field.label}: {value}")
    return lines
