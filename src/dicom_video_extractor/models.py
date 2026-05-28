from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OutputFormat(str, Enum):
    AVI = "AVI"
    MP4 = "MP4"

    @property
    def suffix(self) -> str:
        if self is OutputFormat.MP4:
            return ".mp4"
        return ".avi"


class DicomContentType(str, Enum):
    SINGLE_IMAGE = "single_image"
    MOVING_IMAGE = "moving_image"


class WindowPreset(str, Enum):
    AUTO = "Auto"
    CT_SOFT_TISSUE = "CT Soft Tissue"
    CT_LUNG = "CT Lung"
    CT_BONE = "CT Bone"
    MR_BRAIN = "MR Brain"
    US_GENERAL = "US General"


class OverlayField(str, Enum):
    PATIENT_ID = "patient_id"
    PATIENT_NAME = "patient_name"
    PATIENT_SEX = "patient_sex"
    PATIENT_BIRTH_DATE = "patient_birth_date"
    STUDY_ID = "study_id"
    STUDY_DATE = "study_date"
    STUDY_TIME = "study_time"
    INSTITUTION_NAME = "institution_name"
    MANUFACTURER = "manufacturer"
    NUMBER_OF_FRAMES = "number_of_frames"
    FPS = "fps"

    @property
    def label(self) -> str:
        return {
            OverlayField.PATIENT_ID: "Patient ID",
            OverlayField.PATIENT_NAME: "Patient Name",
            OverlayField.PATIENT_SEX: "Patient Sex",
            OverlayField.PATIENT_BIRTH_DATE: "Birth Date",
            OverlayField.STUDY_ID: "Study ID",
            OverlayField.STUDY_DATE: "Study Date",
            OverlayField.STUDY_TIME: "Study Time",
            OverlayField.INSTITUTION_NAME: "Institution",
            OverlayField.MANUFACTURER: "Manufacturer",
            OverlayField.NUMBER_OF_FRAMES: "Frames",
            OverlayField.FPS: "FPS",
        }[self]


@dataclass(slots=True)
class ConversionOptions:
    output_format: OutputFormat = OutputFormat.AVI
    clip_limit: float = 1.5
    default_fps: int = 15
    fps_override: float | None = None
    window_preset: WindowPreset = WindowPreset.AUTO
    export_sidecars: bool = True
    overlay_fields: tuple[OverlayField, ...] = ()
    anonymize_overlay: bool = False

    @property
    def overlay_enabled(self) -> bool:
        return bool(self.overlay_fields)


@dataclass(slots=True)
class DicomMetadata:
    source_path: Path
    modality: str = ""
    patient_id: str = ""
    patient_name: str = ""
    patient_birth_date: str = ""
    patient_sex: str = ""
    study_id: str = ""
    study_date: str = ""
    study_time: str = ""
    institution_name: str = ""
    manufacturer: str = ""
    number_of_frames: int | None = None
    cine_rate: float | None = None
    window_center: float | None = None
    window_width: float | None = None

    def as_display_rows(self) -> list[tuple[str, str]]:
        return [
            ("Modality", self.modality),
            ("Patient ID", self.patient_id),
            ("Patient Name", self.patient_name),
            ("Patient Sex", self.patient_sex),
            ("Birth Date", self.patient_birth_date),
            ("Study ID", self.study_id),
            ("Study Date", self.study_date),
            ("Study Time", self.study_time),
            ("Institution", self.institution_name),
            ("Manufacturer", self.manufacturer),
            (
                "Frames",
                "" if self.number_of_frames is None else str(self.number_of_frames),
            ),
            ("FPS", "" if self.cine_rate is None else f"{self.cine_rate:g}"),
            ("Window Center", "" if self.window_center is None else f"{self.window_center:g}"),
            ("Window Width", "" if self.window_width is None else f"{self.window_width:g}"),
        ]

    def as_dict(self) -> dict[str, str | int | float | None]:
        return {
            "source_path": str(self.source_path),
            "modality": self.modality,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "patient_birth_date": self.patient_birth_date,
            "patient_sex": self.patient_sex,
            "study_id": self.study_id,
            "study_date": self.study_date,
            "study_time": self.study_time,
            "institution_name": self.institution_name,
            "manufacturer": self.manufacturer,
            "number_of_frames": self.number_of_frames,
            "cine_rate": self.cine_rate,
            "window_center": self.window_center,
            "window_width": self.window_width,
        }


@dataclass(slots=True)
class DicomDirSeries:
    study_instance_uid: str
    series_instance_uid: str
    study_description: str
    series_description: str
    modality: str
    files: tuple[Path, ...]

    @property
    def display_label(self) -> str:
        study_label = self.study_description or self.study_instance_uid or "Unknown Study"
        series_label = self.series_description or self.series_instance_uid or "Unknown Series"
        modality_label = self.modality or "N/A"
        return f"{study_label} | {series_label} | {modality_label} | {len(self.files)} file(s)"


@dataclass(slots=True)
class ConversionResult:
    source_path: Path
    output_paths: tuple[Path, ...]
    frame_count: int
    fps: float | None
    content_type: DicomContentType

    @property
    def output_path(self) -> Path:
        return self.output_paths[0]


@dataclass(slots=True)
class ConversionFailure:
    source_path: Path
    message: str
