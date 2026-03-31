"""벡터 아이콘 — 이모지 대신 QPainter로 직접 렌더링하는 아이콘 팩"""
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PySide6.QtCore import Qt, QRect, QPoint, QSize


def _make_icon(draw_func, size=24, bg="transparent") -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(bg) if bg != "transparent" else Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    draw_func(p, size)
    p.end()
    return QIcon(pix)


def _pen(color="#e0e0e0", width=2):
    return QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def icon_play():
    def draw(p: QPainter, s):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2ecc71"))
        path = QPainterPath()
        path.moveTo(s * 0.25, s * 0.15)
        path.lineTo(s * 0.8, s * 0.5)
        path.lineTo(s * 0.25, s * 0.85)
        path.closeSubpath()
        p.drawPath(path)
    return _make_icon(draw)


def icon_pause():
    def draw(p: QPainter, s):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e0e0e0"))
        p.drawRoundedRect(int(s*0.2), int(s*0.15), int(s*0.2), int(s*0.7), 2, 2)
        p.drawRoundedRect(int(s*0.6), int(s*0.15), int(s*0.2), int(s*0.7), 2, 2)
    return _make_icon(draw)


def icon_stop():
    def draw(p: QPainter, s):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e74c3c"))
        p.drawRoundedRect(int(s*0.2), int(s*0.2), int(s*0.6), int(s*0.6), 3, 3)
    return _make_icon(draw)


def icon_skip_back():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e0e0e0", 2))
        p.setBrush(QColor("#e0e0e0"))
        path = QPainterPath()
        path.moveTo(s*0.55, s*0.2)
        path.lineTo(s*0.25, s*0.5)
        path.lineTo(s*0.55, s*0.8)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(s*0.2), int(s*0.2), int(s*0.2), int(s*0.8))
    return _make_icon(draw)


def icon_skip_forward():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e0e0e0", 2))
        p.setBrush(QColor("#e0e0e0"))
        path = QPainterPath()
        path.moveTo(s*0.45, s*0.2)
        path.lineTo(s*0.75, s*0.5)
        path.lineTo(s*0.45, s*0.8)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(s*0.8), int(s*0.2), int(s*0.8), int(s*0.8))
    return _make_icon(draw)


def icon_cut():
    def draw(p: QPainter, s):
        p.setPen(_pen("#f39c12", 2))
        p.drawLine(int(s*0.3), int(s*0.2), int(s*0.5), int(s*0.5))
        p.drawLine(int(s*0.7), int(s*0.2), int(s*0.5), int(s*0.5))
        p.drawEllipse(int(s*0.15), int(s*0.6), int(s*0.25), int(s*0.25))
        p.drawEllipse(int(s*0.6), int(s*0.6), int(s*0.25), int(s*0.25))
    return _make_icon(draw)


def icon_delete():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e74c3c", 2))
        p.drawRect(int(s*0.25), int(s*0.3), int(s*0.5), int(s*0.55))
        p.drawLine(int(s*0.2), int(s*0.3), int(s*0.8), int(s*0.3))
        p.drawLine(int(s*0.35), int(s*0.15), int(s*0.65), int(s*0.15))
        p.drawLine(int(s*0.35), int(s*0.15), int(s*0.35), int(s*0.3))
        p.drawLine(int(s*0.65), int(s*0.15), int(s*0.65), int(s*0.3))
        p.drawLine(int(s*0.4), int(s*0.4), int(s*0.4), int(s*0.75))
        p.drawLine(int(s*0.6), int(s*0.4), int(s*0.6), int(s*0.75))
    return _make_icon(draw)


def icon_copy():
    def draw(p: QPainter, s):
        p.setPen(_pen("#7ec8e3", 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(int(s*0.15), int(s*0.25), int(s*0.45), int(s*0.55), 3, 3)
        p.drawRoundedRect(int(s*0.35), int(s*0.1), int(s*0.45), int(s*0.55), 3, 3)
    return _make_icon(draw)


def icon_ripple():
    def draw(p: QPainter, s):
        p.setPen(_pen("#9b59b6", 2))
        p.drawLine(int(s*0.5), int(s*0.15), int(s*0.5), int(s*0.85))
        p.drawLine(int(s*0.35), int(s*0.3), int(s*0.5), int(s*0.15))
        p.drawLine(int(s*0.65), int(s*0.3), int(s*0.5), int(s*0.15))
        p.drawLine(int(s*0.15), int(s*0.5), int(s*0.4), int(s*0.5))
        p.drawLine(int(s*0.6), int(s*0.5), int(s*0.85), int(s*0.5))
    return _make_icon(draw)


def icon_magnet():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e74c3c", 2))
        path = QPainterPath()
        path.moveTo(s*0.2, s*0.5)
        path.cubicTo(s*0.2, s*0.15, s*0.8, s*0.15, s*0.8, s*0.5)
        p.drawPath(path)
        p.drawLine(int(s*0.2), int(s*0.5), int(s*0.2), int(s*0.8))
        p.drawLine(int(s*0.8), int(s*0.5), int(s*0.8), int(s*0.8))
        p.setPen(_pen("#4361ee", 3))
        p.drawLine(int(s*0.15), int(s*0.65), int(s*0.25), int(s*0.65))
        p.drawLine(int(s*0.75), int(s*0.65), int(s*0.85), int(s*0.65))
    return _make_icon(draw)


def icon_group():
    def draw(p: QPainter, s):
        p.setPen(_pen("#2ecc71", 1.5))
        p.setBrush(QColor("#2ecc7133"))
        p.drawRoundedRect(int(s*0.1), int(s*0.3), int(s*0.35), int(s*0.4), 3, 3)
        p.drawRoundedRect(int(s*0.55), int(s*0.3), int(s*0.35), int(s*0.4), 3, 3)
        p.setPen(_pen("#2ecc71", 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(int(s*0.05), int(s*0.15), int(s*0.9), int(s*0.7), 5, 5)
    return _make_icon(draw)


def icon_keyframe():
    def draw(p: QPainter, s):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#f1c40f"))
        path = QPainterPath()
        c = s * 0.5
        r = s * 0.3
        path.moveTo(c, c - r)
        path.lineTo(c + r, c)
        path.lineTo(c, c + r)
        path.lineTo(c - r, c)
        path.closeSubpath()
        p.drawPath(path)
    return _make_icon(draw)


def icon_zoom_in():
    def draw(p: QPainter, s):
        p.setPen(_pen("#7ec8e3", 2))
        p.drawEllipse(int(s*0.15), int(s*0.15), int(s*0.5), int(s*0.5))
        p.drawLine(int(s*0.55), int(s*0.55), int(s*0.85), int(s*0.85))
        p.drawLine(int(s*0.3), int(s*0.4), int(s*0.55), int(s*0.4))
        p.drawLine(int(s*0.42), int(s*0.28), int(s*0.42), int(s*0.52))
    return _make_icon(draw)


def icon_zoom_out():
    def draw(p: QPainter, s):
        p.setPen(_pen("#7ec8e3", 2))
        p.drawEllipse(int(s*0.15), int(s*0.15), int(s*0.5), int(s*0.5))
        p.drawLine(int(s*0.55), int(s*0.55), int(s*0.85), int(s*0.85))
        p.drawLine(int(s*0.3), int(s*0.4), int(s*0.55), int(s*0.4))
    return _make_icon(draw)


def icon_undo():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e0e0e0", 2))
        path = QPainterPath()
        path.moveTo(s*0.7, s*0.3)
        path.cubicTo(s*0.7, s*0.15, s*0.3, s*0.15, s*0.3, s*0.4)
        path.cubicTo(s*0.3, s*0.65, s*0.7, s*0.65, s*0.7, s*0.7)
        p.drawPath(path)
        p.setBrush(QColor("#e0e0e0"))
        pp = QPainterPath()
        pp.moveTo(s*0.15, s*0.35)
        pp.lineTo(s*0.35, s*0.2)
        pp.lineTo(s*0.35, s*0.5)
        pp.closeSubpath()
        p.drawPath(pp)
    return _make_icon(draw)


def icon_redo():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e0e0e0", 2))
        path = QPainterPath()
        path.moveTo(s*0.3, s*0.3)
        path.cubicTo(s*0.3, s*0.15, s*0.7, s*0.15, s*0.7, s*0.4)
        path.cubicTo(s*0.7, s*0.65, s*0.3, s*0.65, s*0.3, s*0.7)
        p.drawPath(path)
        p.setBrush(QColor("#e0e0e0"))
        pp = QPainterPath()
        pp.moveTo(s*0.85, s*0.35)
        pp.lineTo(s*0.65, s*0.2)
        pp.lineTo(s*0.65, s*0.5)
        pp.closeSubpath()
        p.drawPath(pp)
    return _make_icon(draw)


def icon_select():
    def draw(p: QPainter, s):
        p.setPen(_pen("#e0e0e0", 2))
        path = QPainterPath()
        path.moveTo(s*0.25, s*0.15)
        path.lineTo(s*0.25, s*0.75)
        path.lineTo(s*0.45, s*0.6)
        path.lineTo(s*0.6, s*0.85)
        path.lineTo(s*0.7, s*0.78)
        path.lineTo(s*0.55, s*0.55)
        path.lineTo(s*0.72, s*0.5)
        path.closeSubpath()
        p.setBrush(QColor("#e0e0e0"))
        p.drawPath(path)
    return _make_icon(draw)


def icon_trim():
    def draw(p: QPainter, s):
        p.setPen(_pen("#f39c12", 2))
        p.drawLine(int(s*0.5), int(s*0.1), int(s*0.5), int(s*0.9))
        p.setBrush(QColor("#f39c1266"))
        p.drawRect(int(s*0.15), int(s*0.25), int(s*0.3), int(s*0.5))
        p.drawRect(int(s*0.55), int(s*0.25), int(s*0.3), int(s*0.5))
    return _make_icon(draw)


def icon_export():
    def draw(p: QPainter, s):
        p.setPen(_pen("#2ecc71", 2))
        p.drawLine(int(s*0.5), int(s*0.15), int(s*0.5), int(s*0.6))
        p.setBrush(QColor("#2ecc71"))
        pp = QPainterPath()
        pp.moveTo(s*0.3, s*0.45)
        pp.lineTo(s*0.5, s*0.65)
        pp.lineTo(s*0.7, s*0.45)
        pp.closeSubpath()
        p.drawPath(pp)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(int(s*0.15), int(s*0.65), int(s*0.7), int(s*0.2), 3, 3)
    return _make_icon(draw)


def icon_ai():
    def draw(p: QPainter, s):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#4361ee"))
        p.drawEllipse(int(s*0.15), int(s*0.15), int(s*0.7), int(s*0.7))
        p.setPen(_pen("#ffffff", 2))
        f = QFont("Arial", int(s*0.3), QFont.Bold)
        p.setFont(f)
        p.drawText(QRect(0, 0, s, s), Qt.AlignCenter, "AI")
    return _make_icon(draw)
