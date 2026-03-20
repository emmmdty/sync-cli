from __future__ import annotations

from pathlib import Path
import datetime
import fnmatch
import os
import tarfile

from .config import ProjectConfig


def current_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def build_remote_dir(base_dir: str, local_dir: Path | str, append_project_dir: bool = True) -> str:
    normalized_base = (base_dir or "").rstrip("/")
    project_name = Path(local_dir).resolve().name
    if append_project_dir:
        if normalized_base:
            return f"{normalized_base}/{project_name}"
        return project_name
    return normalized_base


def default_download_archive_path(local_dir: Path | str, timestamp: str) -> Path:
    project_dir = Path(local_dir).resolve()
    return project_dir / f"{project_dir.name}-{timestamp}.tar.gz"


def default_backup_archive_path(local_dir: Path | str, timestamp: str) -> Path:
    project_dir = Path(local_dir).resolve()
    return project_dir.parent / f"{project_dir.name}-backup-{timestamp}.tar.gz"


def _matches_exclude_pattern(path: Path, rel_path: str, pattern: str) -> bool:
    if pattern == ".*":
        return path.is_dir() and path.name.startswith(".")
    if fnmatch.fnmatch(path.name, pattern):
        return True
    if fnmatch.fnmatch(rel_path, pattern):
        return True
    return any(fnmatch.fnmatch(part, pattern) for part in rel_path.split("/"))


def should_exclude_backup(path: Path, base_dir: Path, exclude_patterns: tuple[str, ...]) -> bool:
    rel_path = path.relative_to(base_dir).as_posix()

    if path.is_dir() and path.name.startswith("."):
        return True

    for pattern in exclude_patterns:
        if _matches_exclude_pattern(path, rel_path, pattern):
            return True

    return False


def collect_backup_files(base_dir: Path | str, exclude_patterns: tuple[str, ...]) -> list[str]:
    root = Path(base_dir).resolve()
    results: list[str] = []

    for current_root, dirs, files in os.walk(root, topdown=True):
        current_path = Path(current_root)
        dirs[:] = [
            directory
            for directory in dirs
            if not should_exclude_backup(current_path / directory, root, exclude_patterns)
        ]

        for filename in files:
            file_path = current_path / filename
            if should_exclude_backup(file_path, root, exclude_patterns):
                continue
            results.append(file_path.relative_to(root).as_posix())

    return results


def create_tar_archive(
    base_dir: Path | str,
    files: list[str],
    output_stream,
    project_name: str | None = None,
) -> None:
    root = Path(base_dir).resolve()
    archive_root = project_name or root.name

    with tarfile.open(fileobj=output_stream, mode="w:gz", encoding="utf-8") as archive:
        for rel_path in files:
            file_path = root / rel_path
            arcname = f"{archive_root}/{rel_path}".replace("\\", "/")
            archive.add(file_path, arcname=arcname)


def create_backup_archive(*, local_dir: Path | str, output_path: Path | str, config: ProjectConfig) -> bool:
    project_dir = Path(local_dir).resolve()
    target_path = Path(output_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    files = collect_backup_files(project_dir, config.backup.excludes)
    if not files:
        print("没有可备份的文件")
        return False

    with target_path.open("wb") as handle:
        create_tar_archive(project_dir, files, handle, project_name=project_dir.name)

    print(f"备份已创建: {target_path}")
    return True
