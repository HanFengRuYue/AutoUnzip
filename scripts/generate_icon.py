from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assets_dir = repo_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    png_path = assets_dir / "app_icon.png"
    ico_path = assets_dir / "app_icon.ico"

    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)

    card = QPainterPath()
    card.addRoundedRect(QRectF(16, 16, 224, 224), 56, 56)
    gradient = QLinearGradient(QPointF(24, 24), QPointF(224, 232))
    gradient.setColorAt(0.0, QColor("#60a5fa"))
    gradient.setColorAt(0.52, QColor("#2563eb"))
    gradient.setColorAt(1.0, QColor("#1d4ed8"))
    painter.fillPath(card, gradient)

    glow = QPainterPath()
    glow.addEllipse(QRectF(34, 26, 140, 120))
    painter.fillPath(glow, QColor(255, 255, 255, 26))

    zipper_x = 116
    zipper_top = 54
    zipper_bottom = 194

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#eff6ff"))
    painter.drawRoundedRect(QRectF(zipper_x - 11, zipper_top, 22, zipper_bottom - zipper_top), 11, 11)

    painter.setBrush(QColor("#bfdbfe"))
    for index in range(6):
        y = zipper_top + 16 + index * 20
        painter.drawRoundedRect(QRectF(zipper_x - 23, y, 14, 8), 4, 4)
        painter.drawRoundedRect(QRectF(zipper_x + 9, y, 14, 8), 4, 4)

    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(QRectF(zipper_x - 18, 132, 36, 36))

    pull = QPainterPath()
    pull.moveTo(146, 88)
    pull.lineTo(186, 88)
    pull.lineTo(186, 72)
    pull.lineTo(210, 104)
    pull.lineTo(186, 136)
    pull.lineTo(186, 120)
    pull.lineTo(146, 120)
    pull.closeSubpath()
    painter.fillPath(pull, QColor("#eff6ff"))

    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 80), 3))
    painter.drawRoundedRect(QRectF(18, 18, 220, 220), 54, 54)

    painter.end()

    if not image.save(str(png_path)):
        raise RuntimeError(f"Failed to save PNG icon: {png_path}")
    if not image.save(str(ico_path)):
        raise RuntimeError(f"Failed to save ICO icon: {ico_path}")

    print(f"Icon written to {png_path} and {ico_path}")


if __name__ == "__main__":
    main()
