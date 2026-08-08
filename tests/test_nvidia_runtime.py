from pathlib import Path
import sys

from eccovox.util.nvidia_runtime import nvidia_dll_directories


def test_nvidiaDllDirectories_shouldIncludeBundledLibraries_whenInstalled() -> None:
    directories = nvidia_dll_directories()

    assert all(isinstance(path, Path) and path.is_dir() for path in directories)
    if directories:
        assert any(path.name == "bin" for path in directories)


def test_nvidiaDllDirectories_shouldUseSitePackagesFromSysPath(
    tmp_path: Path, monkeypatch
) -> None:
    site_packages = tmp_path / "embedded" / "site-packages"
    expected = site_packages / "nvidia" / "cublas" / "bin"
    expected.mkdir(parents=True)
    monkeypatch.setattr(sys, "path", [str(site_packages), *sys.path])

    directories = nvidia_dll_directories()

    assert expected in directories
