import sys
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTabWidget, QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush

class KLineWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        if not self.data:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            return
            
        w, h = self.width(), self.height()
        
        lows = [d['low'] for d in self.data]
        highs = [d['high'] for d in self.data]
        min_v = min(lows)
        max_v = max(highs)
        range_v = max_v - min_v if max_v != min_v else 1
        
        padding = 20
        usable_h = h - padding * 2
        bar_w = max(1, (w - padding * 2) / len(self.data) * 0.7)
        step_x = (w - padding * 2) / len(self.data)
        
        def to_y(val):
            return h - padding - (val - min_v) / range_v * usable_h
            
        for i, d in enumerate(self.data):
            x = padding + i * step_x
            
            is_up = d['close'] >= d['open']
            color = QColor(255, 77, 79) if is_up else QColor(82, 196, 26)
            
            pen = QPen(color, 1)
            painter.setPen(pen)
            high_y = to_y(d['high'])
            low_y = to_y(d['low'])
            center_x = x + bar_w / 2
            painter.drawLine(center_x, high_y, center_x, low_y)
            
            open_y = to_y(d['open'])
            close_y = to_y(d['close'])
            top_y = min(open_y, close_y)
            rect_h = max(abs(open_y - close_y), 1)
            
            if is_up:
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x, top_y, bar_w, rect_h)
            else:
                painter.setBrush(color)
                painter.drawRect(x, top_y, bar_w, rect_h)

class TrendWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        if not self.data:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            return
            
        w, h = self.width(), self.height()
        
        min_v = min(self.data)
        max_v = max(self.data)
        range_v = max_v - min_v if max_v != min_v else 1
        
        padding = 20
        usable_h = h - padding * 2
        
        color = QColor(13, 110, 253)
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        from PySide6.QtGui import QPainterPath, QLinearGradient
        path = QPainterPath()
        
        step_x = (w - padding * 2) / (len(self.data) - 1) if len(self.data) > 1 else w
        for i, val in enumerate(self.data):
            px = padding + i * step_x
            py = h - padding - (val - min_v) / range_v * usable_h
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
                
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        
        area_path = QPainterPath(path)
        area_path.lineTo(padding + (len(self.data) - 1) * step_x, h - padding)
        area_path.lineTo(padding, h - padding)
        area_path.closeSubpath()
        
        grad = QLinearGradient(0, padding, 0, h - padding)
        c1 = QColor(color); c1.setAlpha(100)
        c2 = QColor(color); c2.setAlpha(0)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)
        painter.drawPath(area_path)


class StockDetailDialog(QDialog):
    def __init__(self, code, name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{name} ({code}) - 详情图表")
        self.resize(700, 500)
        
        # Set icon for detail window if possible
        import os
        from PySide6.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        from data_service import fetch_minute_data, fetch_daily_kline, format_stock_code
        f_code = format_stock_code(code)
        
        min_data = fetch_minute_data(f_code)
        tabs.addTab(TrendWidget(min_data), "当日分时")
        
        kline_data = fetch_daily_kline(f_code)
        tabs.addTab(KLineWidget(kline_data), "日K线 (前50天)")
