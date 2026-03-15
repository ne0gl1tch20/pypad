"""Background helpers for querying and installing language-tool-python without blocking the UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile

from PySide6.QtCore import QObject, Signal
from pypad.logging_utils import get_logger
from pypad.app_settings.paths import get_settings_file_path


PACKAGE_PROJECT = "language-tool-python"
PACKAGE_SPEC = "language-tool-python>=2.8,<3"
PACKAGE_JSON_URL = "https://pypi.org/pypi/language-tool-python/json"
NETWORK_TIMEOUT_SEC = 2
LOCAL_SERVER_ESTIMATE_MB = 258.0

_LOGGER = get_logger(__name__)


def _roaming_language_tool_dir() -> Path:
    """Return the app-managed roaming directory used for LanguageTool data."""
    return get_settings_file_path().parent / "language_tool_python"


def ensure_language_tool_runtime_env() -> Path:
    """Force language_tool_python to use the app roaming directory for runtime data."""
    target = _roaming_language_tool_dir()
    target.mkdir(parents=True, exist_ok=True)
    os.environ["LTP_PATH"] = str(target)
    return target


@dataclass(slots=True)
class PackageDownloadInfo:
    """Represent one downloadable distribution for installation copy."""

    version: str
    size_bytes: int
    download_url: str
    filename: str

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)


@dataclass(slots=True)
class RuntimeDownloadInfo:
    """Represent the downloadable local LanguageTool runtime bundle."""

    size_bytes: int
    download_url: str
    label: str

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)


def package_info_to_cache(info: PackageDownloadInfo) -> dict[str, object]:
    """Convert package metadata into a settings-friendly cache payload."""
    return {
        "version": info.version,
        "size_bytes": int(info.size_bytes),
        "download_url": info.download_url,
        "filename": info.filename,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }


def runtime_info_to_cache(info: RuntimeDownloadInfo) -> dict[str, object]:
    """Convert runtime metadata into a settings-friendly cache payload."""
    return {
        "size_bytes": int(info.size_bytes),
        "download_url": info.download_url,
        "label": info.label,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }


def package_info_from_cache(payload: dict | None) -> PackageDownloadInfo | None:
    """Rebuild cached package metadata when present and valid."""
    if not isinstance(payload, dict):
        return None
    try:
        version = str(payload.get("version", "") or "").strip()
        filename = str(payload.get("filename", "") or "").strip()
        download_url = str(payload.get("download_url", "") or "").strip()
        size_bytes = int(payload.get("size_bytes", 0) or 0)
    except Exception:
        return None
    if not version or not filename or not download_url or size_bytes <= 0:
        return None
    return PackageDownloadInfo(version=version, size_bytes=size_bytes, download_url=download_url, filename=filename)


def runtime_info_from_cache(payload: dict | None) -> RuntimeDownloadInfo | None:
    """Rebuild cached runtime metadata when present and valid."""
    if not isinstance(payload, dict):
        return None
    try:
        label = str(payload.get("label", "") or "").strip()
        download_url = str(payload.get("download_url", "") or "").strip()
        size_bytes = int(payload.get("size_bytes", 0) or 0)
    except Exception:
        return None
    if not label or not download_url or size_bytes <= 0:
        return None
    return RuntimeDownloadInfo(size_bytes=size_bytes, download_url=download_url, label=label)


def build_fallback_runtime_download_info() -> RuntimeDownloadInfo:
    """Build a fast fallback runtime metadata payload without a network size lookup."""
    url = "https://internal1.languagetool.org/snapshots/LanguageTool-latest-snapshot.zip"
    try:
        ensure_language_tool_runtime_env()
        download_lt = importlib.import_module("language_tool_python.download_lt")
        local_lt = download_lt.LocalLanguageTool.from_version_name("latest")
        url = str(local_lt.download_url or url)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Could not resolve runtime fallback URL from language_tool_python, using default: %s", exc)
    info = RuntimeDownloadInfo(
        size_bytes=int(LOCAL_SERVER_ESTIMATE_MB * 1024 * 1024),
        download_url=url,
        label="LanguageTool latest snapshot",
    )
    _LOGGER.info("Built runtime fallback download info: url=%s size_mb=%.1f", info.download_url, info.size_mb)
    return info


def _normalize_version_key(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", str(version or ""))
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts)


def _pick_best_distribution(files: list[dict]) -> dict | None:
    wheel = None
    sdist = None
    for row in files:
        name = str(row.get("filename", "") or "")
        if name.endswith(".whl") and "py3-none-any" in name:
            wheel = row
            break
        if str(row.get("packagetype", "") or "") == "sdist":
            sdist = row
    return wheel or sdist


def parse_package_download_info(payload: dict) -> PackageDownloadInfo:
    """Parse PyPI JSON payload and choose the best 2.x release under the current install constraint."""
    releases = payload.get("releases", {})
    if not isinstance(releases, dict):
        raise ValueError("Invalid package metadata: releases missing.")
    candidates: list[tuple[tuple[int, ...], str, dict]] = []
    for version, files in releases.items():
        text = str(version or "").strip()
        if not text or not text.startswith("2."):
            continue
        if not isinstance(files, list) or not files:
            continue
        chosen = _pick_best_distribution(files)
        if chosen is None:
            continue
        candidates.append((_normalize_version_key(text), text, chosen))
    if not candidates:
        raise ValueError("No compatible 2.x release found for language-tool-python.")
    candidates.sort(key=lambda row: row[0], reverse=True)
    _key, version, chosen = candidates[0]
    size_bytes = int(chosen.get("size", 0) or 0)
    return PackageDownloadInfo(
        version=version,
        size_bytes=max(0, size_bytes),
        download_url=str(chosen.get("url", "") or ""),
        filename=str(chosen.get("filename", "") or ""),
    )


def fetch_package_download_info() -> PackageDownloadInfo:
    """Fetch PyPI metadata for the package and return size information for the chosen release."""
    _LOGGER.info("Checking package size for %s via %s (timeout=%ss)", PACKAGE_PROJECT, PACKAGE_JSON_URL, NETWORK_TIMEOUT_SEC)
    with urlopen(PACKAGE_JSON_URL, timeout=NETWORK_TIMEOUT_SEC) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    if not isinstance(payload, dict):
        raise ValueError("Package metadata response was not a JSON object.")
    info = parse_package_download_info(payload)
    _LOGGER.info(
        "Resolved package size for %s: version=%s filename=%s size_bytes=%s size_mb=%.2f",
        PACKAGE_PROJECT,
        info.version,
        info.filename,
        info.size_bytes,
        info.size_mb,
    )
    return info


def local_language_tool_data_installed() -> bool:
    """Return whether the local LanguageTool runtime bundle is already present."""
    try:
        ensure_language_tool_runtime_env()
        download_lt = importlib.import_module("language_tool_python.download_lt")
        local_lt = download_lt.LocalLanguageTool.from_version_name("latest")
        installed = local_lt in local_lt.get_installed_versions()
        _LOGGER.info("Local LanguageTool data installed=%s", installed)
        return installed
    except Exception as exc:
        _LOGGER.warning("Could not determine whether local LanguageTool data is installed: %s", exc)
        return False


def fetch_runtime_download_info() -> RuntimeDownloadInfo:
    """Fetch the expected download size for the local LanguageTool runtime bundle."""
    try:
        ensure_language_tool_runtime_env()
        download_lt = importlib.import_module("language_tool_python.download_lt")
        local_lt = download_lt.LocalLanguageTool.from_version_name("latest")
        url = str(local_lt.download_url)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Could not resolve LanguageTool runtime download URL: %s", exc)
        raise ValueError(f"Could not resolve LanguageTool runtime download URL: {exc}") from exc
    _LOGGER.info("Checking local LanguageTool runtime size via %s (timeout=%ss)", url, NETWORK_TIMEOUT_SEC)
    size_bytes = 0
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=NETWORK_TIMEOUT_SEC) as response:  # noqa: S310
            size_bytes = int(response.headers.get("Content-Length", "0") or "0")
            _LOGGER.info("Resolved runtime HEAD size: size_bytes=%s", size_bytes)
    except Exception as exc:
        _LOGGER.warning("Runtime size HEAD request failed, using fallback estimate: %s", exc)
        size_bytes = 0
    if size_bytes <= 0:
        size_bytes = int(LOCAL_SERVER_ESTIMATE_MB * 1024 * 1024)
        _LOGGER.info("Using runtime fallback estimate: size_bytes=%s size_mb=%.1f", size_bytes, LOCAL_SERVER_ESTIMATE_MB)
    info = RuntimeDownloadInfo(size_bytes=size_bytes, download_url=url, label="LanguageTool latest snapshot")
    _LOGGER.info("Runtime download info ready: url=%s size_bytes=%s size_mb=%.2f", info.download_url, info.size_bytes, info.size_mb)
    return info


class LanguageToolMetadataWorker(QObject):
    """Fetch download metadata for language-tool-python on a background thread."""

    finished = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        """Query the package registry and emit size metadata or an error."""
        try:
            self.finished.emit(fetch_package_download_info())
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Package size check failed: %s", exc)
            self.failed.emit(str(exc))


class LanguageToolRuntimeMetadataWorker(QObject):
    """Fetch runtime-bundle size metadata for the local LanguageTool download."""

    finished = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        """Query the LanguageTool runtime URL and emit size metadata or an error."""
        try:
            self.finished.emit(fetch_runtime_download_info())
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Runtime size check failed: %s", exc)
            self.failed.emit(str(exc))


class LanguageToolInstallWorker(QObject):
    """Install language-tool-python on a background thread."""

    progress = Signal(str)
    finished = Signal()
    failed = Signal(str)

    def run(self) -> None:
        """Run pip install and stream log text back to the UI."""
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_SPEC]
        _LOGGER.info("Starting package install worker: %s", " ".join(cmd))
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                text = str(line or "").strip()
                if text:
                    _LOGGER.info("[LanguageToolInstallWorker] %s", text)
                    self.progress.emit(text)
            code = proc.wait()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Package install worker failed while reading output: %s", exc)
            proc.kill()
            self.failed.emit(str(exc))
            return
        if code != 0:
            _LOGGER.warning("Package install worker exited with code %s", code)
            self.failed.emit(f"pip install exited with code {code}.")
            return
        _LOGGER.info("Package install worker finished successfully.")
        self.finished.emit()


def import_runtime_zip(zip_path: str) -> Path:
    """Extract a manually downloaded LanguageTool ZIP into the app roaming directory."""
    return import_runtime_zip_with_progress(zip_path)


def import_runtime_zip_with_progress(zip_path: str, progress_callback=None) -> Path:
    """Extract a manually downloaded LanguageTool ZIP into the app roaming directory with optional progress callbacks."""
    ensure_language_tool_runtime_env()
    source = Path(str(zip_path or "")).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"ZIP file not found: {source}")
    if source.suffix.lower() != ".zip":
        raise ValueError("Selected file is not a .zip archive.")
    download_lt = importlib.import_module("language_tool_python.download_lt")
    local_lt = download_lt.LocalLanguageTool.from_version_name("latest")
    target_dir = _roaming_language_tool_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    _LOGGER.info("Importing manual LanguageTool ZIP from %s into %s", source, target_dir)
    with zipfile.ZipFile(source, "r") as archive:
        members = archive.infolist()
        root_name = members[0].filename if members else ""
        expected_root = f"LanguageTool-{local_lt.version_name}/"
        total_bytes = sum(max(0, int(item.file_size or 0)) for item in members) or max(1, len(members))
        processed_bytes = 0
        if root_name and root_name != expected_root:
            with tempfile.NamedTemporaryFile(suffix=".zip") as renamed_file:
                with zipfile.ZipFile(renamed_file, "w") as renamed_zip:
                    for item in members:
                        buffer = archive.read(item.filename)
                        new_name = item.filename.replace(root_name, expected_root, 1)
                        renamed_zip.writestr(new_name, buffer)
                        processed_bytes += max(1, int(item.file_size or 0))
                        if callable(progress_callback):
                            progress_callback(processed_bytes, total_bytes, f"Preparing {Path(new_name).name}")
                renamed_file.flush()
                with zipfile.ZipFile(renamed_file.name, "r") as renamed_archive:
                    renamed_members = renamed_archive.infolist()
                    renamed_total = sum(max(0, int(item.file_size or 0)) for item in renamed_members) or max(1, len(renamed_members))
                    renamed_done = 0
                    for item in renamed_members:
                        renamed_archive.extract(item, target_dir)
                        renamed_done += max(1, int(item.file_size or 0))
                        if callable(progress_callback):
                            progress_callback(renamed_done, renamed_total, f"Extracting {Path(item.filename).name}")
        else:
            for item in members:
                archive.extract(item, target_dir)
                processed_bytes += max(1, int(item.file_size or 0))
                if callable(progress_callback):
                    progress_callback(processed_bytes, total_bytes, f"Extracting {Path(item.filename).name}")
    _LOGGER.info("Manual LanguageTool ZIP import finished successfully.")
    return target_dir


class LanguageToolZipImportWorker(QObject):
    """Import a manually downloaded LanguageTool ZIP on a background thread."""

    progress = Signal(object)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, zip_path: str) -> None:
        """Store the selected ZIP path for background import."""
        super().__init__()
        self.zip_path = zip_path

    def run(self) -> None:
        """Import the ZIP and emit structured progress updates."""
        try:
            _LOGGER.info("Starting manual LanguageTool ZIP import worker for %s", self.zip_path)
            target_dir = import_runtime_zip_with_progress(
                self.zip_path,
                progress_callback=lambda done, total, status: self.progress.emit(
                    {
                        "processed_bytes": int(done),
                        "total_bytes": int(total),
                        "status": str(status),
                    }
                ),
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Manual LanguageTool ZIP import worker failed: %s", exc)
            self.failed.emit(str(exc))
            return
        _LOGGER.info("Manual LanguageTool ZIP import worker finished successfully: %s", target_dir)
        self.finished.emit(str(target_dir))


def refresh_language_tool_module() -> object | None:
    """Import or reload language_tool_python after installation."""
    try:
        return importlib.import_module("language_tool_python")
    except Exception:
        return None
