"""Generate and scan QR codes with a bundled decoder when available."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QFileDialog, QFormLayout, QGroupBox, QLabel, QLineEdit, QMessageBox, QPushButton

from .base_dialog import ToolDialogBase

try:
    import zxingcpp
except Exception:  # noqa: BLE001
    zxingcpp = None


def encode_matrix_payload(payload: str) -> list[list[int]]:
    """Encode text into a simple square bit matrix understood by this tool."""
    data = payload.encode("utf-8")
    header = len(data).to_bytes(2, "big")
    checksum = sum(data) % 256
    packet = header + data + bytes([checksum])
    bits = "".join(f"{byte:08b}" for byte in packet)
    size = 29
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for top, left in ((0, 0), (0, size - 7), (size - 7, 0)):
        for row in range(7):
            for col in range(7):
                border = row in {0, 6} or col in {0, 6}
                core = 2 <= row <= 4 and 2 <= col <= 4
                matrix[top + row][left + col] = 1 if border or core else 0
    cells: list[tuple[int, int]] = []
    for row in range(size):
        for col in range(size):
            if (row < 7 and col < 7) or (row < 7 and col >= size - 7) or (row >= size - 7 and col < 7):
                continue
            cells.append((row, col))
    for index, (row, col) in enumerate(cells):
        matrix[row][col] = 1 if index < len(bits) and bits[index] == "1" else 0
    return matrix


def decode_matrix_payload(matrix: list[list[int]]) -> str:
    """Decode text from a matrix produced by `encode_matrix_payload`."""
    size = len(matrix)
    cells: list[int] = []
    for row in range(size):
        for col in range(size):
            if (row < 7 and col < 7) or (row < 7 and col >= size - 7) or (row >= size - 7 and col < 7):
                continue
            cells.append(1 if matrix[row][col] else 0)
    bytes_out: list[int] = []
    for start in range(0, len(cells), 8):
        chunk = cells[start : start + 8]
        if len(chunk) < 8:
            break
        bytes_out.append(int("".join(str(bit) for bit in chunk), 2))
    data = bytes(bytes_out)
    length = int.from_bytes(data[:2], "big")
    payload = data[2 : 2 + length]
    checksum = data[2 + length] if len(data) > 2 + length else -1
    if checksum != sum(payload) % 256:
        raise ValueError("This image is not a PyPad-generated QR code.")
    return payload.decode("utf-8", errors="replace")


def matrix_to_image(matrix: list[list[int]], cell_size: int = 8) -> QImage:
    """Render the matrix into an image."""
    size = len(matrix)
    image = QImage(size * cell_size, size * cell_size, QImage.Format_RGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#000000"))
    for row, values in enumerate(matrix):
        for col, bit in enumerate(values):
            if bit:
                painter.drawRect(col * cell_size, row * cell_size, cell_size, cell_size)
    painter.end()
    return image


def image_to_matrix(image: QImage, size: int = 29) -> list[list[int]]:
    """Sample a saved image back into matrix form."""
    scaled = image.convertToFormat(QImage.Format_RGB32).scaled(size, size)
    matrix: list[list[int]] = []
    for row in range(size):
        values: list[int] = []
        for col in range(size):
            color = QColor(scaled.pixel(col, row))
            values.append(1 if color.value() < 128 else 0)
        matrix.append(values)
    return matrix


def qimage_to_zxing_buffer(image: QImage):
    """Convert a QImage into the shaped grayscale buffer expected by zxing-cpp."""
    gray = image.convertToFormat(QImage.Format_Grayscale8)
    raw = bytes(memoryview(gray.bits())[: gray.sizeInBytes()])
    packed = bytearray()
    row_width = gray.width()
    stride = gray.bytesPerLine()
    for row in range(gray.height()):
        start = row * stride
        packed.extend(raw[start : start + row_width])
    return memoryview(bytes(packed)).cast("B", shape=(gray.height(), gray.width()))


def decode_any_qr_image(image: QImage) -> str:
    """Decode a QR image using zxing-cpp when available, else fall back to PyPad format."""
    if zxingcpp is not None:
        buffer = qimage_to_zxing_buffer(image)
        result = zxingcpp.read_barcode(buffer, formats=zxingcpp.BarcodeFormat.QRCode)
        if result is not None and getattr(result, "text", ""):
            return str(result.text)
    return decode_matrix_payload(image_to_matrix(image))


class QRToolDialog(ToolDialogBase):
    """Create and scan PyPad matrix codes."""

    def __init__(self, parent, initial_text: str = "") -> None:
        super().__init__(
            parent,
            tool_id="qr_tools",
            title="QR Generator / Scanner",
            help_text=(
                "Generate privacy-friendly offline matrix codes and scan QR images locally. "
                "When the bundled zxing-cpp decoder is available, scanning works for general-purpose QR codes; "
                "otherwise the tool still scans PyPad-generated codes."
            ),
        )
        group = QGroupBox("Code", self)
        form = QFormLayout(group)
        self.payload_edit = QLineEdit(group)
        self.payload_edit.setPlaceholderText("Text, URL, or contact snippet")
        self.preview_label = QLabel(group)
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.generate_btn = QPushButton("Generate", group)
        self.scan_btn = QPushButton("Scan Image", group)
        self.save_btn.setText("Save Image...")
        self.generate_btn.clicked.connect(self.generate)
        self.scan_btn.clicked.connect(self.scan_image)
        form.addRow("Payload:", self.payload_edit)
        form.addRow("", self.generate_btn)
        form.addRow("", self.scan_btn)
        form.addRow(self.preview_label)
        self.add_section(group)
        self._current_image: QImage | None = None
        self.load_persisted_state()
        seed = str(initial_text or "").strip()
        if seed:
            self.payload_edit.setText(seed)

    def generate(self) -> None:
        matrix = encode_matrix_payload(self.payload_edit.text().strip())
        image = matrix_to_image(matrix)
        self._current_image = image
        self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.output.setPlainText(self.payload_edit.text().strip())

    def scan_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PyPad QR Image", str(Path.cwd()), "Images (*.png *.bmp *.jpg)")
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, self.windowTitle(), "Could not open the selected image.")
            return
        try:
            payload = decode_any_qr_image(image)
        except Exception as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.payload_edit.setText(payload)
        self.output.setPlainText(payload)

    def save_output(self) -> None:
        if self._current_image is None:
            self.generate()
        if self._current_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PyPad QR Image", str(Path.cwd() / "pypad-qr.png"), "PNG Images (*.png)")
        if path:
            self._current_image.save(path, "PNG")

    def state(self) -> dict[str, Any]:
        return {"payload": self.payload_edit.text()}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.payload_edit.setText(str(state.get("payload", "")))
