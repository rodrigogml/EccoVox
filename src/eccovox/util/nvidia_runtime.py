"""Local NVIDIA runtime discovery for Windows GPU execution."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys


_DLL_DIRECTORY_HANDLES: list[object] = []
_DLL_HANDLES: list[object] = []
_CONFIGURED_DLL_DIRECTORIES: set[Path] = set()


def configure_nvidia_dll_directories() -> tuple[Path, ...]:
    """Register CUDA/cuDNN DLL directories bundled in the active environment or toolkit."""

    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return ()
    configured_paths: list[Path] = []
    for path in nvidia_dll_directories():
        resolved_path = path.resolve()
        if resolved_path in _CONFIGURED_DLL_DIRECTORIES:
            configured_paths.append(resolved_path)
            continue
        handle = os.add_dll_directory(str(resolved_path))
        _DLL_DIRECTORY_HANDLES.append(handle)
        _CONFIGURED_DLL_DIRECTORIES.add(resolved_path)
        configured_paths.append(resolved_path)
    _prepend_process_path(configured_paths)
    _preload_core_libraries(configured_paths)
    return tuple(configured_paths)


def nvidia_dll_directories() -> tuple[Path, ...]:
    """Return existing DLL directories in deterministic priority order."""

    candidates: list[Path] = []
    candidates.extend(
        site_packages / "nvidia" / package / "bin"
        for site_packages in _site_packages_directories()
        for package in ("cublas", "cudnn", "cuda_nvrtc")
    )
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidates.append(Path(cuda_path) / "bin")
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    toolkit_root = program_files / "NVIDIA GPU Computing Toolkit" / "CUDA"
    if toolkit_root.is_dir():
        candidates.extend(
            path / "bin"
            for path in sorted(toolkit_root.glob("v12.*"), reverse=True)
        )
    unique_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for candidate in candidates:
        if candidate.is_dir() and candidate not in seen_paths:
            seen_paths.add(candidate)
            unique_paths.append(candidate)
    return tuple(unique_paths)


def _site_packages_directories() -> tuple[Path, ...]:
    """Find environment packages even when pythonservice keeps the base sys.prefix."""

    candidates = [Path(sys.prefix) / "Lib" / "site-packages"]
    candidates.extend(
        Path(entry)
        for entry in sys.path
        if entry and Path(entry).name.casefold() == "site-packages"
    )
    unique: list[Path] = []
    for candidate in candidates:
        if candidate.is_dir() and candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def _prepend_process_path(paths: list[Path]) -> None:
    current_path = os.environ.get("PATH", "")
    current_entries = current_path.split(os.pathsep) if current_path else []
    new_entries = [str(path) for path in paths if str(path) not in current_entries]
    if new_entries:
        os.environ["PATH"] = os.pathsep.join([*new_entries, *current_entries])


def _preload_core_libraries(paths: list[Path]) -> None:
    loaded_names = {
        Path(str(getattr(handle, "_name", ""))).name.casefold()
        for handle in _DLL_HANDLES
    }
    for library_name in ("cublasLt64_12.dll", "cublas64_12.dll", "cudnn64_9.dll"):
        if library_name.casefold() in loaded_names:
            continue
        library_path = next((path / library_name for path in paths if (path / library_name).is_file()), None)
        if library_path is not None:
            _DLL_HANDLES.append(ctypes.WinDLL(str(library_path)))
