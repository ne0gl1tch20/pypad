"""Reusable media and image viewers hosted inside editor tabs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
except Exception:  # pragma: no cover - optional runtime dependency
    QAudioOutput = None
    QMediaPlayer = None
    QVideoWidget = None


class ImageViewerWidget(QWidget):
    """Structured image viewer with zoom and fit controls."""

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._zoom_percent = 100
        self._pixmap = QPixmap(path)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QFrame(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        self.title_label = QLabel(Path(path).name, header)
        self.meta_label = QLabel("", header)
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.meta_label)
        layout.addWidget(header)

        controls = QHBoxLayout()
        self.zoom_out_btn = QPushButton("-", self)
        self.zoom_in_btn = QPushButton("+", self)
        self.zoom_reset_btn = QPushButton("100%", self)
        self.fit_checkbox = QCheckBox("Fit to view", self)
        self.fit_checkbox.setChecked(True)
        controls.addWidget(QLabel("Zoom", self))
        controls.addWidget(self.zoom_out_btn)
        controls.addWidget(self.zoom_reset_btn)
        controls.addWidget(self.zoom_in_btn)
        controls.addSpacing(10)
        controls.addWidget(self.fit_checkbox)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.viewer = QLabel(self.scroll)
        self.viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer.setText("Loading image...")
        self.scroll.setWidget(self.viewer)
        layout.addWidget(self.scroll, 1)

        actions = QHBoxLayout()
        self.open_external_btn = QPushButton("Open in System Viewer", self)
        actions.addStretch(1)
        actions.addWidget(self.open_external_btn)
        layout.addLayout(actions)

        self.zoom_out_btn.clicked.connect(lambda: self._set_zoom(self._zoom_percent - 10))
        self.zoom_in_btn.clicked.connect(lambda: self._set_zoom(self._zoom_percent + 10))
        self.zoom_reset_btn.clicked.connect(lambda: self._set_zoom(100))
        self.fit_checkbox.toggled.connect(self._refresh_pixmap)
        self.open_external_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._path)))

        self._refresh_pixmap()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self.fit_checkbox.isChecked():
            self._refresh_pixmap()

    def _set_zoom(self, zoom: int) -> None:
        self._zoom_percent = max(10, min(400, int(zoom)))
        self.fit_checkbox.setChecked(False)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._pixmap.isNull():
            self.viewer.setText("Could not render image preview.")
            self.meta_label.setText("")
            return
        pixmap = self._pixmap
        if self.fit_checkbox.isChecked():
            size = self.scroll.viewport().size()
            pixmap = self._pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.meta_label.setText(f"{self._pixmap.width()} x {self._pixmap.height()} | Fit")
        else:
            width = max(1, int(self._pixmap.width() * (self._zoom_percent / 100.0)))
            height = max(1, int(self._pixmap.height() * (self._zoom_percent / 100.0)))
            pixmap = self._pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.meta_label.setText(f"{self._pixmap.width()} x {self._pixmap.height()} | {self._zoom_percent}%")
        self.viewer.setPixmap(pixmap)


class MediaPlayerWidget(QWidget):
    """Structured audio/video player with external fallback."""

    def __init__(self, path: str, suffix: str, *, icon_fn=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._suffix = suffix.lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QFrame(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        self.title_label = QLabel(Path(path).name, header)
        self.status_label = QLabel("", header)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.status_label)
        layout.addWidget(header)

        self.preview_host = QFrame(self)
        self.preview_layout = QVBoxLayout(self.preview_host)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.preview_host, 1)

        controls = QHBoxLayout()
        self.play_btn = QToolButton(self)
        self.pause_btn = QToolButton(self)
        self.stop_btn = QToolButton(self)
        self.play_btn.setText("Play")
        self.pause_btn.setText("Pause")
        self.stop_btn.setText("Stop")
        for button in (self.play_btn, self.pause_btn, self.stop_btn):
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setAutoRaise(False)
            button.setMinimumWidth(72)
        if callable(icon_fn):
            for button, icon_name in (
                (self.play_btn, "macro-run-multi"),
                (self.pause_btn, "macro-record-stop"),
                (self.stop_btn, "tab-close"),
            ):
                try:
                    button.setIcon(icon_fn(icon_name))
                except Exception:
                    pass
        self.elapsed_label = QLabel("00:00", self)
        self.total_label = QLabel("00:00", self)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.progress_slider.setRange(0, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.elapsed_label)
        controls.addWidget(self.progress_slider, 1)
        controls.addWidget(self.total_label)
        controls.addWidget(QLabel("Vol", self))
        controls.addWidget(self.volume_slider)
        layout.addLayout(controls)

        actions = QHBoxLayout()
        self.open_external_btn = QPushButton("Open in System Player", self)
        actions.addStretch(1)
        actions.addWidget(self.open_external_btn)
        layout.addLayout(actions)
        self.open_external_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._path)))

        self._player = None
        self._audio_output = None
        self._video_widget = None
        self._init_backend()

    def _init_backend(self) -> None:
        if QMediaPlayer is None or QAudioOutput is None:
            self.preview_layout.addWidget(QLabel("Embedded media playback is unavailable in this build.", self.preview_host), 1)
            self.status_label.setText("External playback only")
            self._set_transport_enabled(False)
            return
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        is_video = self._suffix in {".mp4", ".mkv", ".mov", ".webm", ".avi"}
        if is_video and QVideoWidget is not None:
            self._video_widget = QVideoWidget(self.preview_host)
            self._player.setVideoOutput(self._video_widget)
            self.preview_layout.addWidget(self._video_widget, 1)
            self.status_label.setText("Video")
        else:
            self.preview_layout.addWidget(QLabel("Audio player ready.", self.preview_host), 1)
            self.status_label.setText("Audio")

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self.progress_slider.sliderMoved.connect(lambda value: self._player.setPosition(int(value)))
        self.volume_slider.valueChanged.connect(
            lambda value: self._audio_output.setVolume(max(0.0, min(1.0, float(value) / 100.0)))
        )
        self.play_btn.clicked.connect(self._player.play)
        self.pause_btn.clicked.connect(self._player.pause)
        self.stop_btn.clicked.connect(self._player.stop)
        self._player.setSource(QUrl.fromLocalFile(self._path))

    def _set_transport_enabled(self, enabled: bool) -> None:
        for widget in (self.play_btn, self.pause_btn, self.stop_btn, self.progress_slider, self.volume_slider):
            widget.setEnabled(enabled)

    @staticmethod
    def _fmt(ms: int) -> str:
        sec = max(0, int(ms // 1000))
        return f"{sec // 60:02d}:{sec % 60:02d}"

    def _on_position_changed(self, ms: int) -> None:
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(int(ms))
        self.elapsed_label.setText(self._fmt(ms))

    def _on_duration_changed(self, ms: int) -> None:
        self.progress_slider.setRange(0, max(0, int(ms)))
        self.total_label.setText(self._fmt(ms))
