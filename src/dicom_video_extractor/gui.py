from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .converter import convert_files
from .metadata import extract_metadata
from .models import ConversionOptions, OutputFormat


def _project_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


class WillowbendApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected_files: list[Path] = []

        self.output_dir_var = tk.StringVar(value=str(Path.cwd()))
        self.clip_limit_var = tk.StringVar(value="1.5")
        self.fps_override_var = tk.StringVar(value="")
        self.output_format_var = tk.StringVar(value=OutputFormat.AVI.value)
        self.status_var = tk.StringVar(value="Select one or more DICOM files to begin.")
        self.file_count_var = tk.StringVar(value="0")
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
        self._apply_icon()

    def _build_window(self) -> None:
        self.root.title("Dicom Video Extractor")
        self.root.geometry("980x760")
        self.root.minsize(860, 680)
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
            text="Modernized standalone conversion workflow based on WillowbendDICOM.",
        )
        subtitle.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))

        metadata_box = ttk.LabelFrame(frame, text="First selected file", padding=12)
        metadata_box.grid(row=2, column=0, sticky="nsew", padx=(0, 12))
        metadata_box.columnconfigure(1, weight=1)

        for row_index, label in enumerate(self.metadata_vars):
            ttk.Label(metadata_box, text=label).grid(row=row_index, column=0, sticky="w", pady=3)
            ttk.Label(metadata_box, textvariable=self.metadata_vars[label]).grid(
                row=row_index,
                column=1,
                sticky="w",
                pady=3,
                padx=(12, 0),
            )

        files_box = ttk.LabelFrame(frame, text="Selected files", padding=12)
        files_box.grid(row=2, column=1, sticky="nsew")
        files_box.columnconfigure(0, weight=1)
        files_box.rowconfigure(0, weight=1)

        self.file_list = tk.Listbox(files_box, height=18)
        self.file_list.grid(row=0, column=0, sticky="nsew")

        controls = ttk.LabelFrame(frame, text="Conversion options", padding=12)
        controls.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Output folder").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.output_dir_var).grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(8, 8),
        )
        ttk.Button(controls, text="Browse…", command=self.choose_output_folder).grid(row=0, column=4)

        ttk.Label(controls, text="Clip limit").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(controls, width=10, textvariable=self.clip_limit_var).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 8),
            pady=(10, 0),
        )

        ttk.Label(controls, text="FPS override").grid(row=1, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(controls, width=10, textvariable=self.fps_override_var).grid(
            row=1,
            column=3,
            sticky="w",
            padx=(8, 8),
            pady=(10, 0),
        )

        ttk.Label(controls, text="Format").grid(row=1, column=4, sticky="w", pady=(10, 0))
        format_box = ttk.Combobox(
            controls,
            textvariable=self.output_format_var,
            values=[item.value for item in OutputFormat],
            state="readonly",
            width=8,
        )
        format_box.grid(row=1, column=5, sticky="w", pady=(10, 0))

        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        actions.columnconfigure(2, weight=1)

        ttk.Button(actions, text="Select DICOM files…", command=self.choose_files).grid(row=0, column=0)
        ttk.Button(actions, text="Refresh metadata", command=self.refresh_metadata).grid(
            row=0,
            column=1,
            padx=(8, 0),
        )
        ttk.Label(actions, text="Files:").grid(row=0, column=3, sticky="e")
        ttk.Label(actions, textvariable=self.file_count_var).grid(row=0, column=4, sticky="w", padx=(6, 0))
        ttk.Button(actions, text="Convert", command=self.convert).grid(row=0, column=5, padx=(12, 0))

        status = ttk.Label(frame, textvariable=self.status_var)
        status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _apply_icon(self) -> None:
        icon_path = _project_root() / "Original" / "Heart.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass

    def choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choose DICOM files",
            filetypes=(("DICOM files", "*.dcm"), ("All files", "*.*")),
        )
        if not paths:
            return

        self.selected_files = [Path(item) for item in paths]
        self.file_list.delete(0, tk.END)
        for path in self.selected_files:
            self.file_list.insert(tk.END, path.name)

        self.file_count_var.set(str(len(self.selected_files)))
        self.output_dir_var.set(str(self.selected_files[0].parent))
        self.refresh_metadata()
        self.status_var.set(f"{len(self.selected_files)} file(s) selected.")

    def choose_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose output folder")
        if folder:
            self.output_dir_var.set(folder)

    def refresh_metadata(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("No file selected", "Choose one or more DICOM files first.")
            return

        try:
            fps_override = self._parse_optional_positive_float(self.fps_override_var.get())
            metadata = extract_metadata(
                self.selected_files[0],
                fps_override=fps_override,
            )
        except Exception as exc:
            messagebox.showerror("Metadata error", str(exc))
            self.status_var.set("Metadata loading failed.")
            return

        for label, value in metadata.as_display_rows():
            self.metadata_vars[label].set(value)

        self.status_var.set(f"Loaded metadata for {self.selected_files[0].name}.")

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
        output_format = OutputFormat(self.output_format_var.get())

        return ConversionOptions(
            output_format=output_format,
            clip_limit=clip_limit,
            fps_override=fps_override,
        )

    def convert(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("No files selected", "Choose one or more DICOM files first.")
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

        self.status_var.set("Converting files...")
        self.root.update_idletasks()

        results, failures = convert_files(self.selected_files, output_dir, options)

        if results and not failures:
            messagebox.showinfo(
                "Conversion complete",
                f"Successfully converted {len(results)} file(s) to {options.output_format.value}.",
            )
            self.status_var.set(f"Converted {len(results)} file(s) successfully.")
            return

        if results and failures:
            failure_text = "\n".join(
                f"- {failure.source_path.name}: {failure.message}" for failure in failures[:5]
            )
            messagebox.showwarning(
                "Partial success",
                f"Converted {len(results)} file(s), but {len(failures)} failed:\n{failure_text}",
            )
            self.status_var.set(f"Converted {len(results)} file(s), {len(failures)} failed.")
            return

        failure_text = "\n".join(
            f"- {failure.source_path.name}: {failure.message}" for failure in failures[:5]
        )
        messagebox.showerror("Conversion failed", failure_text or "Unknown conversion error.")
        self.status_var.set("Conversion failed.")


def main() -> None:
    root = tk.Tk()
    WillowbendApp(root)
    root.mainloop()
