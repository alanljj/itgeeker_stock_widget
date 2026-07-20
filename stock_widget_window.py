import sys
import os
import json
import datetime
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget, QMenu
from data_service import fetch_stock_data, is_trading_time, get_market_status

_CACHE_DIR = os.path.join(os.path.expanduser("~"), "itgeeker_widget_config", "cache")

class StockWidget(QWidget):
    def __init__(self, title, codes, settings=None, parent=None, show_main_callback=None, show_settings_callback=None, always_on_top=True):
        super().__init__(parent)
        self.settings = settings or {}
        self.title = title
        self.codes = codes
        self.stock_data = []
        self.last_fetch_time = None   # 最后成功拉取数据的时间
        self.show_main_callback = show_main_callback  # 分组管理的回调
        self.show_settings_callback = show_settings_callback  # 程序设置的回调
        self.on_closed_callback = None  # 窗口关闭时通知主窗口的回调
        self.on_top_changed_callback = None  # 置顶状态改变时通知主窗口的回调

        self.always_on_top = always_on_top

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.update_flags()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_data)
        refresh_ms = int(self.settings.get('refresh_interval', 5)) * 1000
        self.timer.start(refresh_ms)

        self._load_cache()      # 启动时先恢复缓存数据，避免休市空白
        self.fetch_data()

        self.update_size()
        self.drag_pos = None

    def _cache_path(self):
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.title)
        return os.path.join(_CACHE_DIR, f"{safe_name}.json")

    def _load_cache(self):
        path = self._cache_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                if isinstance(cached, dict):
                    self.stock_data = cached.get('stock_data', [])
                    ts = cached.get('last_fetch_time')
                    if ts:
                        self.last_fetch_time = datetime.datetime.fromisoformat(ts)
            except Exception:
                pass

    def _save_cache(self):
        path = self._cache_path()
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            payload = {
                'stock_data': self.stock_data,
                'last_fetch_time': self.last_fetch_time.isoformat() if self.last_fetch_time else None
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception:
            pass

    def update_size(self):
        self.resize(430, max(100, len(self.codes) * 60 + 50))

    def update_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def fetch_data(self):
        # 窗口未显示时不拉取数据，节省请求
        if not self.isVisible():
            return

        if not self.codes:
            self.stock_data = []
            self.update()
            return

        # 非交易时段不拉取数据，避免无效请求
        if not is_trading_time():
            self.update()   # 触发重绘以更新标题状态文字
            return

        data = fetch_stock_data(self.codes)
        if data:
            self.stock_data = data
            self.last_fetch_time = datetime.datetime.now()
            self._save_cache()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bg_brush = QBrush(QColor(30, 30, 30, 210))
        painter.setBrush(bg_brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

        font_size = int(self.settings.get('font_size', 11))

        # ── 标题 ──
        painter.setPen(QColor(255, 255, 255, 180))
        painter.setFont(QFont("Microsoft YaHei", max(10, font_size - 1), QFont.Bold))
        painter.drawText(15, 25, self.title)

        # ── 标题右侧：最后拉取时间 / 市场状态 ──
        market_status = get_market_status()
        if market_status == "":
            # 交易时段：显示最后拉取时间
            if self.last_fetch_time:
                status_text = self.last_fetch_time.strftime("%H:%M:%S")
                status_color = QColor(100, 220, 100, 200)   # 绿色
            else:
                status_text = "拉取中..."
                status_color = QColor(200, 200, 100, 180)   # 黄色
        else:
            status_text = market_status
            status_color = QColor(180, 180, 180, 160)       # 灰色

        painter.setPen(status_color)
        painter.setFont(QFont("Microsoft YaHei", max(8, font_size - 3)))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(status_text)
        painter.drawText(self.width() - tw - 12, 25, status_text)

        y_offset = 40
        row_height = 60

        for stock in self.stock_data:
            self.draw_stock_row(painter, stock, 10, y_offset, self.width() - 20, row_height)
            y_offset += row_height

    def draw_stock_row(self, painter, stock, x, y, w, h):
        painter.setBrush(QColor(255, 255, 255, 15))
        painter.drawRoundedRect(x, y, w, h - 10, 8, 8)

        is_up = stock['is_up']
        color = QColor(255, 77, 79) if is_up else QColor(82, 196, 26)

        font_size = int(self.settings.get('font_size', 11))
        painter.setPen(color)
        name_font = QFont("Microsoft YaHei", font_size, QFont.Bold)
        painter.setFont(name_font)
        
        # Handle long names by truncating to avoid overlapping
        stock_name = stock['name']
        if len(stock_name) > 7:
            stock_name = stock_name[:6] + ".."
        
        fm = painter.fontMetrics()
        name_width = fm.horizontalAdvance(stock_name)
        painter.drawText(x + 10, y + 20, stock_name)
        
        # Draw Region Block
        code_str = stock['code']  # 现在是 600900.sh 格式
        region = code_str.split('.')[-1].upper() if '.' in code_str else ""
        r_x = x + 10 + name_width + 8
        r_y = y + 7
        if region == "SH":
            r_color = QColor(220, 53, 69)
        elif region == "SZ":
            r_color = QColor(253, 126, 20)
        elif region == "HK":
            r_color = QColor(13, 110, 253)
        else:
            r_color = QColor(108, 117, 125)
            
        painter.setBrush(r_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(r_x, r_y, 22, 14, 2, 2)
        
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", max(7, font_size - 4), QFont.Bold))
        painter.drawText(r_x + 3, r_y + 12, region)

        painter.setPen(QColor(255, 255, 255, 120))
        painter.setFont(QFont("Microsoft YaHei", max(8, font_size - 3)))
        painter.drawText(x + 10, y + 38, stock['code'].upper())

        painter.setPen(color)
        painter.setFont(QFont("Arial", font_size + 3, QFont.Bold))
        price_str = f"{stock['current']:.2f}"
        painter.drawText(x + 140, y + 30, price_str)

        sign = "+" if is_up else ""
        change_str = f"{sign}{stock['change_percent']:.2f}%"
        
        change_bg = QColor(color)
        change_bg.setAlpha(50)
        painter.setBrush(change_bg)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x + 220, y + 15, 65, 22, 4, 4)
        
        painter.setPen(color)
        painter.setFont(QFont("Arial", max(10, font_size - 1), QFont.Bold))
        painter.drawText(x + 225, y + 31, change_str)

        trend = stock.get('trend', [])
        if trend and len(trend) > 1:
            self.draw_sparkline(painter, trend, color, x + 300, y + 7, w - 310, h - 24)

    def draw_sparkline(self, painter, data, color, x, y, w, h):
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1

        path = QPainterPath()
        points = []
        for i, val in enumerate(data):
            px = x + (i / (len(data) - 1)) * w
            py = y + h - ((val - min_val) / range_val) * h
            points.append((px, py))
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)

        pen = QPen(color)
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        area_path = QPainterPath(path)
        area_path.lineTo(x + w, y + h)
        area_path.lineTo(x, y + h)
        area_path.closeSubpath()

        grad = QLinearGradient(0, y, 0, y + h)
        grad_color1 = QColor(color)
        grad_color1.setAlpha(80)
        grad_color2 = QColor(color)
        grad_color2.setAlpha(0)
        grad.setColorAt(0, grad_color1)
        grad.setColorAt(1, grad_color2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)
        painter.drawPath(area_path)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            y = event.position().y()
            y_offset = 40
            row_height = 60
            if y >= y_offset:
                click_idx = int((y - y_offset) / row_height)
                if 0 <= click_idx < len(self.stock_data):
                    stock = self.stock_data[click_idx]
                    self.show_stock_detail(stock)
            event.accept()

    def show_stock_detail(self, stock):
        from stock_detail_dialog import StockDetailDialog
        dlg = StockDetailDialog(stock['code'], stock['name'], self)
        dlg.show()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'drag_pos') and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        if hasattr(self, 'on_moved_callback') and self.on_moved_callback:
            self.on_moved_callback(self.title, self.pos().x(), self.pos().y())
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        main_action = menu.addAction("📂 分组管理")
        settings_action = menu.addAction("⚙️ 程序设置")
        menu.addSeparator()
        top_action = menu.addAction("📌 取消置顶" if self.always_on_top else "📌 置顶")
        close_action = menu.addAction("❌ 关闭")

        action = menu.exec(self.mapToGlobal(event.pos()))
        if action == main_action:
            if self.show_main_callback:
                self.show_main_callback()
        elif action == settings_action:
            if self.show_settings_callback:
                self.show_settings_callback()
        elif action == top_action:
            self.always_on_top = not self.always_on_top
            self.update_flags()
            if hasattr(self, 'on_top_changed_callback') and self.on_top_changed_callback:
                self.on_top_changed_callback(self.title, self.always_on_top)
        elif action == close_action:
            self.close()

    def closeEvent(self, event):
        """窗口关闭时通知主窗口从 active_widgets 中移除"""
        if self.on_closed_callback:
            self.on_closed_callback(self)
        event.accept()
