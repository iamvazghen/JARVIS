import random

from PyQt5 import QtCore, QtGui, QtWidgets


_GLYPHS = list("アイウエオカキクケコサシスセソタチツテトナニヌネノ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")


# Override the glyph set with proper Unicode (keeps the UI looking clean even if
# the file encoding causes mojibake in the generated glyph string above).
_GLYPHS = list("アイウエオカキクケコサシスセソタチツテトナニヌネノ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")


class MatrixRainWidget(QtWidgets.QWidget):
    """
    Lightweight Matrix-style rain background.
    Draws falling glyphs in columns and repaints on a timer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)

        self._font = QtGui.QFont("Cascadia Mono", 14)
        if not self._font.exactMatch():
            self._font = QtGui.QFont("Consolas", 14)

        self._cell_w = 14
        self._cell_h = 18
        self._columns = []
        self._tails = []
        self._speeds = []
        self._head_chars = []

        self._bg = QtGui.QColor(0, 0, 0)
        # Professional look: slightly dimmer rain and a longer trail.
        self._trail = QtGui.QColor(0, 0, 0, 26)
        self._green = QtGui.QColor(0, 255, 110, 165)
        self._head = QtGui.QColor(200, 255, 210, 235)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(55)

        self._recompute_grid()

    def _recompute_grid(self):
        fm = QtGui.QFontMetrics(self._font)
        self._cell_w = max(12, fm.horizontalAdvance("W"))
        self._cell_h = max(16, fm.height())
        self._init_columns()

    def _init_columns(self):
        w = max(1, self.width())
        h = max(1, self.height())
        cols = max(8, int(w / self._cell_w))

        self._columns = [random.randint(-h, 0) for _ in range(cols)]
        self._tails = [random.randint(int(h * 0.15), int(h * 0.55)) for _ in range(cols)]
        self._speeds = [random.randint(8, 22) for _ in range(cols)]
        self._head_chars = [random.choice(_GLYPHS) for _ in range(cols)]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recompute_grid()

    def _tick(self):
        h = max(1, self.height())
        for i in range(len(self._columns)):
            self._columns[i] += self._speeds[i]
            if random.random() < 0.35:
                self._head_chars[i] = random.choice(_GLYPHS)
            if self._columns[i] - self._tails[i] > h + 50:
                self._columns[i] = random.randint(-h, 0)
                self._tails[i] = random.randint(int(h * 0.15), int(h * 0.60))
                self._speeds[i] = random.randint(8, 24)

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, False)
        painter.fillRect(self.rect(), self._bg)

        # Slight trail effect by overlaying a transparent rect
        painter.fillRect(self.rect(), self._trail)

        painter.setFont(self._font)
        col_w = self._cell_w
        row_h = self._cell_h

        for col, y in enumerate(self._columns):
            x = col * col_w
            tail = self._tails[col]

            head_char = self._head_chars[col]
            painter.setPen(self._head)
            painter.drawText(x, y, head_char)

            steps = max(6, int(tail / row_h))
            for s in range(1, steps + 1):
                cy = y - s * row_h
                if cy < -row_h:
                    break
                fade = max(0.0, 1.0 - (s / (steps + 1)))
                alpha = int(self._green.alpha() * (fade ** 1.35))
                painter.setPen(QtGui.QColor(self._green.red(), self._green.green(), self._green.blue(), alpha))
                if random.random() < 0.55:
                    ch = random.choice(_GLYPHS)
                else:
                    ch = head_char
                painter.drawText(x, cy, ch)
