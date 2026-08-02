from pathlib import Path

from eccovox.util.nvidia_runtime import nvidia_dll_directories


def test_nvidiaDllDirectories_shouldIncludeBundledLibraries_whenInstalled() -> None:
    directories = nvidia_dll_directories()

    assert all(isinstance(path, Path) and path.is_dir() for path in directories)
    if directories:
        assert any(path.name == "bin" for path in directories)
