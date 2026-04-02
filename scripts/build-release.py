from __future__ import annotations

import shutil
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


APP_NAME = "Dicom-Video-Extractor"


def _build_root(project_root: Path) -> Path:
    default_root = project_root / "release-build"
    if not default_root.exists():
        return default_root

    try:
        shutil.rmtree(default_root)
        return default_root
    except PermissionError:
        suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
        fallback_root = project_root / "release-build-fallback" / suffix
        fallback_root.mkdir(parents=True, exist_ok=True)
        return fallback_root


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    build_root = _build_root(project_root)
    dist_dir = build_root / "dist"
    work_dir = build_root / "build"
    spec_dir = build_root / "spec"
    src_dir = project_root / "src"
    entry_point = project_root / "app.py"
    icon_path = project_root / "Original" / "Heart.ico"
    title_path = project_root / "Original" / "Title.png"
    data_separator = ";" if platform.system() == "Windows" else ":"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        "--windowed",
        "--paths",
        str(src_dir),
        "--add-data",
        f"{icon_path}{data_separator}Original",
        "--add-data",
        f"{title_path}{data_separator}Original",
        str(entry_point),
    ]

    if platform.system() == "Windows" and icon_path.exists():
        command.extend(["--icon", str(icon_path)])

    subprocess.run(command, cwd=project_root, check=True)
    print(f"Build output: {dist_dir / APP_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
