#!/usr/bin/env python3
"""贴边版 WiFi 开关：默认停在 virt-manager 窗口左侧黑边里。"""
import os, subprocess, sys
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QAction
from PyQt6.QtWidgets import QApplication, QWidget, QMenu

HELPER = "/usr/local/sbin/vmshield-net"
W, H = 28, 110          # 窄条，刚好塞进黑边

def helper(cmd="status"):
    try:
        r = subprocess.run(["sudo", "-n", HELPER, cmd], capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip() or "?"
    except Exception:
        return "?"

class WifiButton(QWidget):
    def __init__(self):
        super().__init__()
        # 置顶交给 KWin 脚本(vmsticky)管理，这样 qemu 窗口到后台时按钮也一起到后台
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Tool)
        self.setWindowTitle("vmwifi-btn")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(W, H)
        self.state = "?"
        self._press = None
        self._winpos = QPoint()
        self._drag = False
        self.setToolTip("点击切换 win11-malware 网络\n右键：贴边 / 退出")
        self.t = QTimer(self)
        self.t.timeout.connect(self.refresh)
        self.t.start(3000)
        self.dock()
        self.refresh()

    def dock(self):
        """贴到屏幕左侧、垂直居中——virt-manager 最大化时这里就是黑边。"""
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.left() + 4, scr.top() + (scr.height() - H) // 2)

    def refresh(self):
        s = helper("status")
        if s != self.state:
            self.state = s
            self.update()

    def toggle(self):
        self.state = helper("toggle")
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = {"up": "#1e9e6a", "down": "#c0392b"}.get(self.state, "#4a4a4a")
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 8, 8)
        p.save()
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(-90)
        p.setPen(QColor("#ffffff"))
        f = QFont()
        f.setPointSize(8)
        f.setBold(True)
        p.setFont(f)
        text = {"up": "WiFi ON", "down": "WiFi OFF"}.get(self.state, "VM OFF")
        p.drawText(-self.height() // 2, 0, self.height(), self.width(),
                   Qt.AlignmentFlag.AlignCenter, text)
        p.restore()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._winpos = self.pos()
            self._drag = False
        elif e.button() == Qt.MouseButton.RightButton:
            m = QMenu(self)
            m.addAction(QAction("贴到左侧黑边", self, triggered=self.dock))
            m.addAction(QAction("退出", self, triggered=self.close))
            m.exec(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._press is not None:
            d = e.globalPosition().toPoint() - self._press
            if d.manhattanLength() > 3:
                self._drag = True
                self.move(self._winpos + d)

    def mouseReleaseEvent(self, e):
        if self._press is not None:
            if not self._drag:
                self.toggle()
            self._press = None

app = QApplication(sys.argv)
w = WifiButton()
w.show()
sys.exit(app.exec())
