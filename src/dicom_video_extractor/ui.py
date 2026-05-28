from __future__ import annotations

import base64
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np

from .converter import convert_file, detect_content_type, load_dicom_frames, normalize_pixel_array
from .metadata import extract_metadata, read_dataset
from .models import ConversionFailure, ConversionOptions, ConversionResult, DicomContentType, OverlayField
from .overlay import ordered_overlay_fields


def _project_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def _frame_to_photoimage(frame: np.ndarray, max_width: int = 460, max_height: int = 320) -> tk.PhotoImage:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("OpenCV is required for preview rendering.") from exc

    if frame.ndim == 2:
        render_frame = frame
    else:
        render_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    height, width = render_frame.shape[:2]
    scale = min(max_width / max(width, 1), max_height / max(height, 1), 1.0)
    if scale < 1.0:
        scaled_width = max(1, int(width * scale))
        scaled_height = max(1, int(height * scale))
        render_frame = cv2.resize(render_frame, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA)

    success, encoded = cv2.imencode(".png", render_frame)
    if not success:
        raise RuntimeError("Could not generate preview image.")

    return tk.PhotoImage(data=base64.b64encode(encoded.tobytes()).decode("ascii"))


class WillowbendApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected_files: list[Path] = []
        self.preview_frames: np.ndarray | None = None
        self.preview_photo: tk.PhotoImage | None = None
        self.preview_after_id: str | None = None
        self.preview_frame_index = 0
        self.preview_fps = 15.0
        self.preview_content_type = DicomContentType.SINGLE_IMAGE
        self.queue_running = False
        self.queue_paused = False
        self.queue_index = 0
        self.queue_results: list[ConversionResult] = []
        self.queue_failures: list[ConversionFailure] = []
        self.queue_options: ConversionOptions | None = None
        self.queue_output_dir = ""

        self.output_dir_var = tk.StringVar(value=str(Path.cwd()))
        self.clip_limit_var = tk.StringVar(value="1.5")
        self.fps_override_var = tk.StringVar(value="")
        self.overlay_enabled_var = tk.BooleanVar(value=False)
        self.anonymize_overlay_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Select one or more DICOM files to begin.")
        self.file_count_var = tk.StringVar(value="0")
        self.preview_mode_var = tk.StringVar(value="Preview: no file selected")
        self.queue_progress_value_var = tk.DoubleVar(value=0.0)
        self.queue_progress_text_var = tk.StringVar(value="Queue progress: 0/0")
        self.queue_current_file_var = tk.StringVar(value="Current file: -")
        self.select_files_button: ttk.Button | None = None
        self.select_folder_button: ttk.Button | None = None
        self.refresh_button: ttk.Button | None = None
        self.convert_button: ttk.Button | None = None
        self.pause_queue_button: ttk.Button | None = None
        self.resume_queue_button: ttk.Button | None = None
        self.move_up_button: ttk.Button | None = None
        self.move_down_button: ttk.Button | None = None
        self.prioritize_button: ttk.Button | None = None
        self.queue_progress_bar: ttk.Progressbar | None = None
        self.overlay_field_vars = {
            field: tk.BooleanVar(
                value=field
                in (
                    OverlayField.PATIENT_NAME,
                    OverlayField.STUDY_DATE,
                    OverlayField.FPS,
                )
            )
            for field in ordered_overlay_fields()
        }
        self.metadata_vars = {
            "Patient ID": tk.StringVar(value=""),
            "Patient Name": tk.StringVar(value=""),
            "Patient Sex": tk.StringVar(value=""),
            "Birth Date": tk.StringVar(value=""),
            "Study ID": tk.StringVar(value=""),
            "Study Date": tk.StringVar(value=""),
            "Study Time": tk.StringVar(value=""),
            "Institution": tk.StringVar(value=""),
            "Manufacturer": tk.StringVar(value=""),
            "Frames": tk.StringVar(value=""),
            "FPS": tk.StringVar(value=""),
        }

        self._build_window()
        self._build_layout()
        self._set_queue_ui_state()
        self._apply_icon()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_window(self) -> None:
        self.root.title("Dicom Video Extractor")
        self.root.geometry("1080x900")
        self.root.minsize(920, 820)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _build_layout(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

        title = ttk.Label(
            frame,
            text="Dicom Video Extractor",
            font=("Segoe UI", 18, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            frame,
            text="Automatic DICOM image/video detection, preview and export workflow.",
        )
        subtitle.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))

        metadata_box = ttk.LabelFrame(frame, text="Active file metadata", padding=12)
        metadata_box.grid(row=2, column=0, sticky="nsew", padx=(0, 12))
        metadata_box.columnconfigure(1, weight=1)

        for row_index, label in enumerate(self.metadata_vars):
            ttk.Label(metadata_box, text=label).grid(
                row=row_index, column=0, sticky="w", pady=3
            )
            ttk.Label(metadata_box, textvariable=self.metadata_vars[label]).grid(
                row=row_index,
                column=1,
                sticky="w",
                pady=3,
                padx=(12, 0),
            )

        files_box = ttk.LabelFrame(frame, text="Selected files and preview", padding=12)
        files_box.grid(row=2, column=1, sticky="nsew")
        files_box.columnconfigure(0, weight=1)
        files_box.rowconfigure(0, weight=1)
        files_box.rowconfigure(2, weight=1)

        self.file_list = tk.Listbox(files_box, height=10)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.bind("<<ListboxSelect>>", self._on_list_selection_changed)

        ttk.Label(files_box, textvariable=self.preview_mode_var).grid(row=1, column=0, sticky="w", pady=(8, 4))

        self.preview_label = ttk.Label(files_box, text="No preview available", anchor="center")
        self.preview_label.grid(row=2, column=0, sticky="nsew", pady=(0, 8))

        preview_controls = ttk.Frame(files_box)
        preview_controls.grid(row=3, column=0, sticky="w")
        ttk.Button(preview_controls, text="Play", command=self.play_preview).grid(row=0, column=0)
        ttk.Button(preview_controls, text="Pause", command=self.pause_preview).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(preview_controls, text="Restart", command=self.restart_preview).grid(row=0, column=2, padx=(8, 0))

        queue_controls = ttk.Frame(files_box)
        queue_controls.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.move_up_button = ttk.Button(queue_controls, text="Move Up", command=self.move_selected_up)
        self.move_up_button.grid(row=0, column=0)
        self.move_down_button = ttk.Button(queue_controls, text="Move Down", command=self.move_selected_down)
        self.move_down_button.grid(row=0, column=1, padx=(8, 0))
        self.prioritize_button = ttk.Button(
            queue_controls, text="Prioritize Selected", command=self.prioritize_selected_file
        )
        self.prioritize_button.grid(row=0, column=2, padx=(8, 0))

        controls = ttk.LabelFrame(frame, text="Conversion options", padding=12)
        controls.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)
        controls.columnconfigure(5, weight=1)

        ttk.Label(controls, text="Output folder").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.output_dir_var).grid(
            row=0,
            column=1,
            columnspan=4,
            sticky="ew",
            padx=(8, 8),
        )
        ttk.Button(controls, text="Browse...", command=self.choose_output_folder).grid(row=0, column=5)

        ttk.Label(controls, text="Clip limit").grid(
            row=1, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(controls, width=10, textvariable=self.clip_limit_var).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 8),
            pady=(10, 0),
        )

        ttk.Label(controls, text="FPS override").grid(
            row=1, column=2, sticky="w", pady=(10, 0)
        )
        ttk.Entry(controls, width=10, textvariable=self.fps_override_var).grid(
            row=1,
            column=3,
            sticky="w",
            padx=(8, 8),
            pady=(10, 0),
        )

        ttk.Label(
            controls,
            text="Export mode: auto (single image -> PNG+JPG, moving image -> MP4+AVI)",
        ).grid(row=1, column=4, columnspan=2, sticky="w", pady=(10, 0))

        overlay_box = ttk.LabelFrame(controls, text="Video overlay", padding=10)
        overlay_box.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(14, 0))
        overlay_box.columnconfigure(0, weight=1)
        overlay_box.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            overlay_box,
            text="Embed selected metadata into exported media",
            variable=self.overlay_enabled_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            overlay_box,
            text="Anonymize personal data",
            variable=self.anonymize_overlay_var,
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))

        ttk.Label(
            overlay_box,
            text="Select which fields should be visible in the exported media:",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 6))

        for index, field in enumerate(ordered_overlay_fields()):
            row = 2 + index // 2
            column = index % 2
            ttk.Checkbutton(
                overlay_box,
                text=field.label,
                variable=self.overlay_field_vars[field],
            ).grid(row=row, column=column, sticky="w", padx=(0, 16), pady=2)

        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        actions.columnconfigure(5, weight=1)

        self.select_files_button = ttk.Button(
            actions, text="Select DICOM files...", command=self.choose_files
        )
        self.select_files_button.grid(row=0, column=0)
        self.select_folder_button = ttk.Button(
            actions, text="Select DICOM folder...", command=self.choose_folder
        )
        self.select_folder_button.grid(
            row=0,
            column=1,
            padx=(8, 0),
        )
        self.refresh_button = ttk.Button(
            actions, text="Refresh metadata", command=self.refresh_metadata
        )
        self.refresh_button.grid(
            row=0,
            column=2,
            padx=(8, 0),
        )
        self.convert_button = ttk.Button(actions, text="Convert Queue", command=self.convert)
        self.convert_button.grid(row=0, column=3, padx=(12, 0))
        self.pause_queue_button = ttk.Button(
            actions,
            text="Pause Queue",
            command=self.pause_conversion_queue,
            state="disabled",
        )
        self.pause_queue_button.grid(row=0, column=4, padx=(8, 0))
        self.resume_queue_button = ttk.Button(
            actions,
            text="Resume Queue",
            command=self.resume_conversion_queue,
            state="disabled",
        )
        self.resume_queue_button.grid(row=0, column=5, padx=(8, 0))
        ttk.Label(actions, text="Files:").grid(row=0, column=6, sticky="e")
        ttk.Label(actions, textvariable=self.file_count_var).grid(
            row=0, column=7, sticky="w", padx=(6, 0)
        )

        status = ttk.Label(frame, textvariable=self.status_var)
        status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        progress_frame = ttk.Frame(frame)
        progress_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        progress_frame.columnconfigure(0, weight=1)
        self.queue_progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=1,
            variable=self.queue_progress_value_var,
        )
        self.queue_progress_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.queue_progress_text_var).grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(progress_frame, textvariable=self.queue_current_file_var).grid(
            row=2, column=0, sticky="w", pady=(2, 0)
        )

    def _apply_icon(self) -> None:
        icon_path = _project_root() / "Original" / "Heart.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass

    def _on_close(self) -> None:
        self.pause_preview()
        self.root.destroy()

    def _set_button_state(self, button: ttk.Button | None, *, enabled: bool) -> None:
        if button is None:
            return
        button.configure(state="normal" if enabled else "disabled")

    def _set_queue_ui_state(self) -> None:
        busy = self.queue_running
        paused = self.queue_paused
        self._set_button_state(self.select_files_button, enabled=not busy)
        self._set_button_state(self.select_folder_button, enabled=not busy)
        self._set_button_state(self.refresh_button, enabled=not busy)
        self._set_button_state(self.move_up_button, enabled=not busy)
        self._set_button_state(self.move_down_button, enabled=not busy)
        self._set_button_state(self.prioritize_button, enabled=not busy)
        self._set_button_state(self.convert_button, enabled=not busy)
        self._set_button_state(self.pause_queue_button, enabled=busy and not paused)
        self._set_button_state(self.resume_queue_button, enabled=busy and paused)
        self.file_list.configure(state="disabled" if busy else "normal")

    def _selected_list_index(self) -> int | None:
        selection = self.file_list.curselection()
        if not selection:
            return None
        return int(selection[0])

    def _restore_selection(self, index: int) -> None:
        if not self.selected_files:
            return
        safe_index = max(0, min(index, len(self.selected_files) - 1))
        self.file_list.selection_clear(0, tk.END)
        self.file_list.selection_set(safe_index)
        self.file_list.activate(safe_index)
        self.file_list.see(safe_index)

    def _move_selected_file(self, target_index: int) -> None:
        if self.queue_running:
            return
        source_index = self._selected_list_index()
        if source_index is None:
            return
        if source_index < 0 or source_index >= len(self.selected_files):
            return

        clamped_target = max(0, min(target_index, len(self.selected_files) - 1))
        if source_index == clamped_target:
            return

        moved = self.selected_files.pop(source_index)
        self.selected_files.insert(clamped_target, moved)
        self.file_list.delete(0, tk.END)
        for path in self.selected_files:
            self.file_list.insert(tk.END, path.name)

        self._restore_selection(clamped_target)
        self.refresh_metadata()
        self._load_preview_for_index(clamped_target)

    def move_selected_up(self) -> None:
        selected = self._selected_list_index()
        if selected is None:
            return
        self._move_selected_file(selected - 1)

    def move_selected_down(self) -> None:
        selected = self._selected_list_index()
        if selected is None:
            return
        self._move_selected_file(selected + 1)

    def prioritize_selected_file(self) -> None:
        self._move_selected_file(0)

    def _is_dicom_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            dataset = read_dataset(path, stop_before_pixels=True)
        except Exception:
            return False
        if hasattr(dataset, "PixelData"):
            return True
        if getattr(dataset, "SOPClassUID", None):
            return True
        if getattr(dataset, "Rows", None) and getattr(dataset, "Columns", None):
            return True
        return False

    def choose_files(self) -> None:
        if self.queue_running:
            messagebox.showinfo("Queue running", "Pause or wait for the queue to finish before changing files.")
            return
        paths = filedialog.askopenfilenames(
            title="Choose DICOM files",
            filetypes=(
                ("All files (including extensionless)", "*"),
                ("DICOM files", "*.dcm *.dicom"),
                ("Files without extension", "*."),
            ),
        )
        if not paths:
            return

        raw_files = [Path(item) for item in paths]
        self._apply_dicom_selection(
            raw_files,
            output_dir_hint=raw_files[0].parent if raw_files else None,
            source_label="selection",
        )

    def choose_folder(self) -> None:
        if self.queue_running:
            messagebox.showinfo("Queue running", "Pause or wait for the queue to finish before changing files.")
            return
        folder = filedialog.askdirectory(title="Choose folder with DICOM files")
        if not folder:
            return

        root_dir = Path(folder)
        candidates = [path for path in root_dir.rglob("*") if path.is_file()]
        if not candidates:
            messagebox.showwarning("Folder is empty", "No files were found in the selected folder.")
            self.status_var.set("Selected folder contains no files.")
            return

        self.status_var.set(f"Scanning {len(candidates)} file(s) recursively for DICOM data...")
        self.root.update_idletasks()
        self._apply_dicom_selection(
            candidates,
            output_dir_hint=root_dir,
            source_label=f"folder scan ({root_dir})",
        )

    def _apply_dicom_selection(
        self,
        candidates: list[Path],
        *,
        output_dir_hint: Path | None,
        source_label: str,
    ) -> None:
        if self.queue_running:
            return
        dicom_files: list[Path] = []
        skipped_count = 0

        total = len(candidates)
        for index, path in enumerate(candidates, start=1):
            if self._is_dicom_file(path):
                dicom_files.append(path)
            else:
                skipped_count += 1

            if index % 250 == 0:
                self.status_var.set(
                    f"Scanning files... {index}/{total} checked, {len(dicom_files)} DICOM found."
                )
                self.root.update_idletasks()

        if not dicom_files:
            messagebox.showwarning("No DICOM files", "No valid DICOM files were found.")
            self.status_var.set(f"{source_label}: 0 DICOM files found in {total} checked files.")
            return

        self.selected_files = dicom_files
        self.file_list.delete(0, tk.END)
        for path in self.selected_files:
            self.file_list.insert(tk.END, path.name)

        self.file_list.selection_clear(0, tk.END)
        self.file_list.selection_set(0)
        self.file_list.activate(0)

        self.file_count_var.set(str(len(self.selected_files)))
        if output_dir_hint is not None:
            self.output_dir_var.set(str(output_dir_hint))
        else:
            self.output_dir_var.set(str(self.selected_files[0].parent))
        self.refresh_metadata()
        self._load_preview_for_index(0)
        self.status_var.set(
            f"{source_label}: {len(self.selected_files)} DICOM file(s) selected, {skipped_count} non-DICOM skipped."
        )

    def choose_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose output folder")
        if folder:
            self.output_dir_var.set(folder)

    def _selected_index(self) -> int | None:
        selection = self.file_list.curselection()
        if selection:
            return int(selection[0])
        if self.selected_files:
            return 0
        return None

    def _selected_file(self) -> Path | None:
        index = self._selected_index()
        if index is None:
            return None
        if index < 0 or index >= len(self.selected_files):
            return None
        return self.selected_files[index]

    def refresh_metadata(self) -> None:
        selected_file = self._selected_file()
        if selected_file is None:
            messagebox.showwarning("No file selected", "Choose one or more DICOM files first.")
            return

        try:
            fps_override = self._parse_optional_positive_float(
                self.fps_override_var.get()
            )
            metadata = extract_metadata(
                selected_file,
                fps_override=fps_override,
            )
        except Exception as exc:
            messagebox.showerror("Metadata error", str(exc))
            self.status_var.set("Metadata loading failed.")
            return

        for label, value in metadata.as_display_rows():
            self.metadata_vars[label].set(value)

        self.status_var.set(f"Loaded metadata for {selected_file.name}.")

    def _on_list_selection_changed(self, _: object) -> None:
        index = self._selected_index()
        if index is None:
            return
        self.refresh_metadata()
        self._load_preview_for_index(index)

    def _parse_optional_positive_float(self, raw_value: str) -> float | None:
        stripped = raw_value.strip()
        if not stripped:
            return None

        value = float(stripped)
        if value <= 0:
            raise ValueError("FPS override must be a positive number.")
        return value

    def _conversion_options(self) -> ConversionOptions:
        clip_limit = float(self.clip_limit_var.get().strip())
        if clip_limit < 0:
            raise ValueError("Clip limit must be zero or greater.")

        fps_override = self._parse_optional_positive_float(self.fps_override_var.get())
        overlay_fields = ()
        if self.overlay_enabled_var.get():
            overlay_fields = tuple(
                field
                for field, variable in self.overlay_field_vars.items()
                if variable.get()
            )

        return ConversionOptions(
            clip_limit=clip_limit,
            fps_override=fps_override,
            overlay_fields=overlay_fields,
            anonymize_overlay=self.anonymize_overlay_var.get(),
        )

    def _load_preview_for_index(self, index: int) -> None:
        if index < 0 or index >= len(self.selected_files):
            return

        path = self.selected_files[index]
        self.pause_preview()

        try:
            raw_frames = load_dicom_frames(path)
            frames = normalize_pixel_array(raw_frames)
            metadata = extract_metadata(path)
        except Exception as exc:
            self.preview_frames = None
            self.preview_photo = None
            self.preview_label.configure(text=f"Preview failed: {exc}", image="")
            self.preview_mode_var.set("Preview: unavailable")
            return

        self.preview_frames = frames
        self.preview_frame_index = 0
        self.preview_content_type = detect_content_type(metadata.number_of_frames, frames)
        self.preview_fps = metadata.cine_rate or 15.0

        if self.preview_content_type is DicomContentType.MOVING_IMAGE:
            self.preview_mode_var.set(f"Preview: moving image ({frames.shape[0]} frames, {self.preview_fps:g} FPS)")
            self.play_preview()
        else:
            self.preview_mode_var.set("Preview: single image")
            self._render_preview_frame(0)

    def _render_preview_frame(self, index: int) -> None:
        if self.preview_frames is None:
            return
        frame_count = int(self.preview_frames.shape[0])
        if frame_count <= 0:
            return
        safe_index = index % frame_count
        frame = self.preview_frames[safe_index]
        self.preview_photo = _frame_to_photoimage(frame)
        self.preview_label.configure(image=self.preview_photo, text="")
        self.preview_frame_index = safe_index

    def _preview_tick(self) -> None:
        if self.preview_frames is None:
            return
        frame_count = int(self.preview_frames.shape[0])
        if frame_count <= 1:
            self._render_preview_frame(0)
            return

        next_index = (self.preview_frame_index + 1) % frame_count
        self._render_preview_frame(next_index)
        interval_ms = max(20, int(round(1000.0 / max(self.preview_fps, 1.0))))
        self.preview_after_id = self.root.after(interval_ms, self._preview_tick)

    def play_preview(self) -> None:
        if self.preview_frames is None:
            return
        if self.preview_content_type is DicomContentType.SINGLE_IMAGE:
            self._render_preview_frame(0)
            return
        if self.preview_after_id is not None:
            return
        self._preview_tick()

    def pause_preview(self) -> None:
        if self.preview_after_id is None:
            return
        self.root.after_cancel(self.preview_after_id)
        self.preview_after_id = None

    def restart_preview(self) -> None:
        if self.preview_frames is None:
            return
        self.preview_frame_index = 0
        self._render_preview_frame(0)
        if self.preview_content_type is DicomContentType.MOVING_IMAGE:
            self.pause_preview()
            self.play_preview()

    def convert(self) -> None:
        if self.queue_running:
            messagebox.showinfo("Queue running", "A conversion queue is already running.")
            return

        if not self.selected_files:
            messagebox.showwarning(
                "No files selected", "Choose one or more DICOM files first."
            )
            return

        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showwarning("No output folder", "Choose an output folder first.")
            return

        try:
            options = self._conversion_options()
        except ValueError as exc:
            messagebox.showwarning("Invalid option", str(exc))
            return

        total = len(self.selected_files)
        self.queue_running = True
        self.queue_paused = False
        self.queue_index = 0
        self.queue_results = []
        self.queue_failures = []
        self.queue_options = options
        self.queue_output_dir = output_dir
        self.queue_progress_value_var.set(0.0)
        self.queue_progress_text_var.set(f"Queue progress: 0/{total}")
        self.queue_current_file_var.set("Current file: queue started")
        if self.queue_progress_bar is not None:
            self.queue_progress_bar.configure(maximum=max(total, 1))
        self._set_queue_ui_state()
        self.status_var.set(f"Queue started with {total} file(s).")
        self.root.update_idletasks()
        self.root.after(5, self._process_queue_step)

    def pause_conversion_queue(self) -> None:
        if not self.queue_running:
            return
        if self.queue_paused:
            return
        self.queue_paused = True
        self.status_var.set("Queue paused after current file.")
        self._set_queue_ui_state()

    def resume_conversion_queue(self) -> None:
        if not self.queue_running:
            return
        if not self.queue_paused:
            return
        self.queue_paused = False
        self.status_var.set("Queue resumed.")
        self._set_queue_ui_state()
        self.root.after(5, self._process_queue_step)

    def _process_queue_step(self) -> None:
        if not self.queue_running:
            return
        if self.queue_paused:
            return

        total = len(self.selected_files)
        if self.queue_index >= total:
            self._finish_conversion_queue()
            return

        if self.queue_options is None:
            self.queue_running = False
            self.queue_paused = False
            self._set_queue_ui_state()
            self.status_var.set("Queue stopped due to missing conversion options.")
            return

        source_path = self.selected_files[self.queue_index]
        self.queue_current_file_var.set(f"Current file: {source_path.name}")
        self.status_var.set(
            f"Converting {self.queue_index + 1}/{total}: {source_path.name}"
        )
        self.root.update_idletasks()

        try:
            result = convert_file(source_path, self.queue_output_dir, self.queue_options)
            self.queue_results.append(result)
        except Exception as exc:
            self.queue_failures.append(
                ConversionFailure(source_path=source_path, message=str(exc))
            )

        self.queue_index += 1
        self.queue_progress_value_var.set(float(self.queue_index))
        self.queue_progress_text_var.set(f"Queue progress: {self.queue_index}/{total}")

        if self.queue_index >= total:
            self._finish_conversion_queue()
            return

        if self.queue_paused:
            self.status_var.set("Queue paused.")
            self._set_queue_ui_state()
            return

        self.root.after(5, self._process_queue_step)

    def _finish_conversion_queue(self) -> None:
        self.queue_running = False
        self.queue_paused = False
        self._set_queue_ui_state()

        results = self.queue_results
        failures = self.queue_failures
        moving_count = sum(
            1
            for result in results
            if result.content_type is DicomContentType.MOVING_IMAGE
        )
        image_count = len(results) - moving_count
        self.queue_current_file_var.set("Current file: done")

        if results and not failures:
            messagebox.showinfo(
                "Conversion complete",
                (
                    f"Converted {len(results)} file(s).\n"
                    f"- Moving image DICOMs: {moving_count} (each exported as MP4 + AVI)\n"
                    f"- Single image DICOMs: {image_count} (each exported as PNG + JPG)"
                ),
            )
            self.status_var.set(f"Queue complete: converted {len(results)} file(s).")
            return

        if results and failures:
            failure_text = "\n".join(
                f"- {failure.source_path.name}: {failure.message}"
                for failure in failures[:5]
            )
            messagebox.showwarning(
                "Partial success",
                (
                    f"Converted {len(results)} file(s), but {len(failures)} failed.\n\n"
                    f"- Moving image DICOMs: {moving_count} (MP4 + AVI)\n"
                    f"- Single image DICOMs: {image_count} (PNG + JPG)\n\n"
                    f"Failures:\n{failure_text}"
                ),
            )
            self.status_var.set(
                f"Queue complete: {len(results)} converted, {len(failures)} failed."
            )
            return

        failure_text = "\n".join(
            f"- {failure.source_path.name}: {failure.message}"
            for failure in failures[:5]
        )
        messagebox.showerror(
            "Conversion failed", failure_text or "Unknown conversion error."
        )
        self.status_var.set("Queue failed: all files failed.")


def main() -> None:
    root = tk.Tk()
    WillowbendApp(root)
    root.mainloop()
