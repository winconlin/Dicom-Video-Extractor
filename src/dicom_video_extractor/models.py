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


@dataclass(slots=True)
class ConversionOptions:
    output_format: OutputFormat = OutputFormat.AVI
    clip_limit: float = 1.5
    default_fps: int = 15
    fps_override: float | None = None


@dataclass(slots=True)
class DicomMetadata:
    source_path: Path
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

    def as_display_rows(self) -> list[tuple[str, str]]:
        return [
            ("Patient ID", self.patient_id),
            ("Patient Name", self.patient_name),
            ("Patient Sex", self.patient_sex),
            ("Birth Date", self.patient_birth_date),
            ("Study ID", self.study_id),
            ("Study Date", self.study_date),
            ("Study Time", self.study_time),
            ("Institution", self.institution_name),
            ("Manufacturer", self.manufacturer),
            ("Frames", "" if self.number_of_frames is None else str(self.number_of_frames)),
            ("FPS", "" if self.cine_rate is None else f"{self.cine_rate:g}"),
        ]


@dataclass(slots=True)
class ConversionResult:
    source_path: Path
    output_path: Path
    frame_count: int
    fps: float
    output_format: OutputFormat


@dataclass(slots=True)
class ConversionFailure:
    source_path: Path
    message: str
