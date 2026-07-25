import sys
import json
import os
import winreg
import datetime
from PySide6.QtCore import Qt, QTimer, QRect, QStandardPaths, QUrl
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QFont, QImage, QColor, QDesktopServices
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
                               QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
                               QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QSystemTrayIcon, QMenu, QFileDialog, QCheckBox, QDoubleSpinBox)
from stock_widget_window import StockWidget

# 配置统一保存在用户目录 ~/itgeeker_widget_config/config_stock.json
_CONFIG_DIR = os.path.join(os.path.expanduser("~"), "itgeeker_widget_config")
CONFIG_FILE = os.path.join(_CONFIG_DIR, "config_stock.json")
_OLD_CONFIG_FILE = "categories.json"  # 旧版配置路径，迁移时使用
APP_VERSION = "v1.3.12.0"
APP_NAME = "ITGeeker Stock Widget"

DEFAULT_CONFIG = {
    "settings": {
        "refresh_interval": 30,
        "font_size": 11,
        "auto_start": False
    },
    "categories": [
        {"name": "新能源与智能硬件", "codes": ["002594.sz", "601127.sh", "01810.hk", "689009.sh"]},
        {"name": "航天与高科技", "codes": ["600118.sh", "003009.sz"]},
        {"name": "高息电力", "codes": ["600900.sh", "600642.sh", "000651.sz"]},
        {"name": "人力资源与其它", "codes": ["600662.sh", "300662.sz"]}
    ]
}

def load_config():
    # 优先从新路径加载
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"settings": DEFAULT_CONFIG["settings"].copy(), "categories": data}
                return data
        except:
            pass
    # 兼容迁移旧版配置文件
    if os.path.exists(_OLD_CONFIG_FILE):
        try:
            with open(_OLD_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    data = {"settings": DEFAULT_CONFIG["settings"].copy(), "categories": data}
            save_config(data)
            return data
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def create_emoji_icon(emoji, size=32):
    """Create a QIcon from an emoji character"""
    # Create a pixmap with transparent background
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    
    # Draw a circular background
    painter.setBrush(QColor(30, 30, 30, 230))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QRect(0, 0, size, size))
    
    # Draw emoji
    font = QFont("Segoe UI Emoji", size * 0.5)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    
    # Center the emoji
    fm = painter.fontMetrics()
    emoji_width = fm.horizontalAdvance(emoji)
    x = (size - emoji_width) / 2
    y = (size + fm.ascent() - fm.descent()) / 2
    painter.drawText(int(x), int(y), emoji)
    
    painter.end()
    return QIcon(pixmap)

def get_export_dir():
    """
    获取导出目录：Windows下载目录（Shell API读取）的子目录 ITGeekerWidgetExport。
    通过注册表 User Shell Folders 读取真实下载路径，fallback 到 ~/Downloads。
    目录不存在时自动创建。
    """
    downloads = None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            0, winreg.KEY_READ
        )
        # {374DE290-123F-4565-9164-39C4925E467B} 是下载文件夹的 GUID
        value, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
        winreg.CloseKey(key)
        # 展开环境变量（如 %USERPROFILE%）
        downloads = os.path.expandvars(value)
    except Exception:
        pass
    if not downloads:
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    export_dir = os.path.join(downloads, "ITGeekerWidgetExport")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir

# 注册表自启项的键名（不含空格，避免某些环境解析问题）
AUTO_START_KEY_NAME = "ITGeekerStockWidget"

def get_auto_start_path():
    """Get the registry path for auto-start"""
    return r"Software\Microsoft\Windows\CurrentVersion\Run"

def is_auto_start_enabled():
    """Check if auto-start is enabled in registry"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, get_auto_start_path(), 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, AUTO_START_KEY_NAME)
            winreg.CloseKey(key)
            return bool(value)
        except FileNotFoundError:
            # 兼容旧键名（含空格），若新键名不存在则检查旧键名
            try:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                winreg.CloseKey(key)
                return bool(value)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
    except WindowsError:
        return False

def set_auto_start(enable):
    """Enable or disable auto-start"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, get_auto_start_path(), 0, winreg.KEY_WRITE)
        if enable:
            exe_path = sys.executable
            winreg.SetValueEx(key, AUTO_START_KEY_NAME, 0, winreg.REG_SZ, exe_path)
            # 同时清理旧键名，避免残留
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        else:
            try:
                winreg.DeleteValue(key, AUTO_START_KEY_NAME)
            except FileNotFoundError:
                pass
            # 同时清理旧键名
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except WindowsError as e:
        print(f"Failed to set auto-start: {e}")
        return False

class EditCategoryDialog(QDialog):
    def __init__(self, category_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑分组与股票")
        self.resize(750, 450)
        self.category_data = category_data
        self.codes = list(category_data.get('codes', []))
        self.alerts = dict(category_data.get('alerts', {}))

        # 股票名称缓存：仅当 codes 集合（增/删）变化时才重新请求网络
        self._basics_cache = None
        self._basics_cache_codes = None
        
        layout = QVBoxLayout()
        
        # Name editing
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("分组名称:"))
        self.name_input = QLineEdit(category_data.get('name', '新建分组'))
        name_layout.addWidget(self.name_input)
        
        self.default_open_cb = QCheckBox("启动时自动打开")
        self.default_open_cb.setChecked(category_data.get('default_open', False))
        name_layout.addWidget(self.default_open_cb)
        
        layout.addLayout(name_layout)
        
        # Table of stocks
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "市场", "高位涨幅提醒(%)", "低位跌幅提醒(%)", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.populate_table()
        layout.addWidget(self.table)
        
        # Add stock line
        add_layout = QHBoxLayout()
        self.new_code_input = QLineEdit()
        self.new_code_input.setPlaceholderText("输入股票代码 (如 000651) 或名称 (如 格力)")
        self.new_code_input.returnPressed.connect(self.add_stock)
        add_btn = QPushButton("添加股票")
        add_btn.clicked.connect(self.add_stock)
        add_layout.addWidget(self.new_code_input)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("导入CSV")
        import_btn.clicked.connect(self.import_csv)
        export_btn = QPushButton("导出CSV")
        export_btn.clicked.connect(self.export_csv)
        
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.on_accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def on_accept(self):
        # 从 UI 中读取所有提醒值后关闭对话框
        self._capture_alerts()
        self.accept()

    def populate_table(self):
        self.table.setRowCount(0)
        if not self.codes:
            return

        from data_service import fetch_stock_basics, format_stock_code

        # 仅当代码集合发生变化（增删股票）时才重新请求名称缓存；
        # 单纯调整顺序时复用缓存，避免不必要的网络请求。
        if self._basics_cache is None or set(self._basics_cache_codes or []) != set(self.codes):
            basics = fetch_stock_basics(self.codes)
            self._basics_cache = {b['code']: b['name'] for b in basics}
            self._basics_cache_codes = list(self.codes)
        valid_map = self._basics_cache

        for idx, code in enumerate(self.codes):
            row = self.table.rowCount()
            self.table.insertRow(row)

            f_code = format_stock_code(code)  # 现在返回 600900.sh 格式
            name = valid_map.get(f_code, "未找到")
            # 从新格式获取前缀：600900.sh -> .sh -> SH
            prefix = f_code.split('.')[-1].upper() if '.' in f_code else ""

            # fill row
            self.table.setItem(row, 0, QTableWidgetItem(f_code))
            self.table.setItem(row, 1, QTableWidgetItem(name))

            prefix_item = QTableWidgetItem(prefix)
            self.table.setItem(row, 2, prefix_item)

            # Spinboxes
            high_spin = QDoubleSpinBox()
            high_spin.setRange(0, 500)
            high_spin.setValue(self.alerts.get(code, {}).get('high', 0.0))
            self.table.setCellWidget(row, 3, high_spin)

            low_spin = QDoubleSpinBox()
            low_spin.setRange(-100, 0)
            low_spin.setValue(self.alerts.get(code, {}).get('low', 0.0))
            self.table.setCellWidget(row, 4, low_spin)

            # 操作列：上移 / 下移 / 删除
            op_widget = QWidget()
            op_layout = QHBoxLayout(op_widget)
            op_layout.setContentsMargins(2, 0, 2, 0)
            op_layout.setSpacing(4)

            up_btn = QPushButton("↑")
            up_btn.setMaximumWidth(30)
            up_btn.setToolTip("上移")
            up_btn.setEnabled(idx > 0)  # 首行禁用
            up_btn.clicked.connect(lambda checked, c=code: self.move_stock(c, -1))

            down_btn = QPushButton("↓")
            down_btn.setMaximumWidth(30)
            down_btn.setToolTip("下移")
            down_btn.setEnabled(idx < len(self.codes) - 1)  # 末行禁用
            down_btn.clicked.connect(lambda checked, c=code: self.move_stock(c, +1))

            del_btn = QPushButton("删除")
            del_btn.clicked.connect(lambda checked, c=code: self.remove_stock(c))

            op_layout.addWidget(up_btn)
            op_layout.addWidget(down_btn)
            op_layout.addWidget(del_btn)
            op_layout.addStretch()

            self.table.setCellWidget(row, 5, op_widget)

    def remove_stock(self, code):
        # 删除前先保存当前 UI 中的提醒值
        self._capture_alerts()
        if code in self.codes:
            self.codes.remove(code)
            # 删除后代码集合变化，需清缓存让 populate_table 重新拉取名称
            self._basics_cache = None
            self._basics_cache_codes = None
            self.populate_table()

    def move_stock(self, code, direction):
        """调整股票顺序。direction: -1=上移, +1=下移"""
        if code not in self.codes:
            return
        idx = self.codes.index(code)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.codes):
            return
        # 移动前先把用户在 spinbox 中输入的提醒值同步到 self.alerts，
        # 避免重新渲染时被默认值 0.0 覆盖。
        self._capture_alerts()
        # 交换顺序
        self.codes[idx], self.codes[new_idx] = self.codes[new_idx], self.codes[idx]
        self.populate_table()

    def _capture_alerts(self):
        """从 UI 中读取所有 spinbox 值，保存到 self.alerts"""
        captured = {}
        for row in range(self.table.rowCount()):
            if row >= len(self.codes):
                break
            code = self.codes[row]
            high_spin = self.table.cellWidget(row, 3)
            low_spin = self.table.cellWidget(row, 4)
            if high_spin and low_spin:
                h_val = high_spin.value()
                l_val = low_spin.value()
                if h_val != 0.0 or l_val != 0.0:
                    captured[code] = {'high': h_val, 'low': l_val}
        self.alerts = captured

    def add_stock(self):
        """根据用户输入添加股票：智能识别代码或名称关键词"""
        from data_service import search_stocks
        keyword = self.new_code_input.text().strip()
        if not keyword:
            return

        # 输入像股票代码 → 直接添加
        if self._looks_like_code(keyword):
            self._try_add_stock(keyword)
            return

        # 像名称/关键词 → 走搜索
        results = search_stocks(keyword)
        if not results:
            QMessageBox.warning(
                self, "未找到",
                f"未找到匹配 '{keyword}' 的股票。\n"
                f"提示：可输入 6 位数字代码 (如 000651) 或股票名称关键词 (如 格力)。"
            )
            return

        if len(results) == 1:
            # 唯一结果，直接添加
            self._try_add_stock(results[0]['code'])
            return

        # 多个结果 → 弹窗让用户选择
        chosen = self._pick_stock(keyword, results)
        if chosen:
            self._try_add_stock(chosen)

    def _looks_like_code(self, text):
        """判断输入是否像股票代码（A 股/港股数字、美股字母数字组合）"""
        import re
        t = text.lower().strip().replace(' ', '')
        if not t:
            return False
        # 纯数字 5-6 位（A股 6、港股 5）
        if re.fullmatch(r'\d{5,6}', t):
            return True
        # sh/sz/hk/bj 前缀 + 5-6 位数字
        if re.fullmatch(r'(sh|sz|hk|bj)\d{5,6}', t):
            return True
        # us 前缀 + 字母数字组合，可能带 .oq/.nq 等交易所后缀
        if re.fullmatch(r'us[a-z0-9]+(\.[a-z]+)?', t):
            return True
        # 数字 + .sh/.sz/.hk/.bj/.us 后缀
        if re.fullmatch(r'\d{5,6}\.(sh|sz|hk|bj|us)', t):
            return True
        return False

    def _try_add_stock(self, code):
        """添加单只股票到当前分组（含缓存清理与去重检查）"""
        from data_service import format_stock_code
        code = format_stock_code(code)
        if not code:
            QMessageBox.warning(self, "提示", "无效的股票代码！")
            return
        if code in self.codes:
            QMessageBox.warning(self, "提示", f"股票 {code} 已存在于当前分组中！")
            return
        self.codes.append(code)
        self.new_code_input.clear()
        # 代码集合变化，清缓存让 populate_table 重新拉取名称
        self._basics_cache = None
        self._basics_cache_codes = None
        self.populate_table()

    def _pick_stock(self, keyword, results):
        """弹出股票选择窗口；返回用户选中的 code，未选返回 None"""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"搜索结果：{keyword}")
        dlg.resize(560, 420)

        layout = QVBoxLayout()

        info_label = QLabel(f"关键词 '{keyword}' 匹配到 {len(results)} 个股票，请选择要添加的：")
        info_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(info_label)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        MARKET_LABEL = {"sh": "沪A", "sz": "深A", "hk": "港股", "bj": "京A", "us": "美股"}
        for stock in results:
            prefix = stock['code'].split('.')[-1].upper() if '.' in stock['code'] else ''
            market_text = MARKET_LABEL.get(stock['market'], prefix)
            item_text = f"{stock['code']:<14}  {stock['name']}  [{market_text}]"
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.UserRole, stock['code'])
            list_widget.addItem(list_item)
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        # 双击直接添加
        list_widget.itemDoubleClicked.connect(lambda _item: dlg.accept())

        btn_layout = QHBoxLayout()

        def on_ok():
            if not list_widget.currentItem():
                QMessageBox.warning(dlg, "提示", "请先选择一项！")
                return
            dlg.accept()

        ok_btn = QPushButton("添加选中")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dlg.setLayout(layout)
        if dlg.exec() == QDialog.Accepted:
            item = list_widget.currentItem()
            if item:
                return item.data(Qt.UserRole)
        return None

    def import_csv(self):
        export_dir = get_export_dir()
        file, _ = QFileDialog.getOpenFileName(
            self, "选择 CSV / TXT 文件",
            export_dir,
            "Text Files (*.txt *.csv);;All Files (*)"
        )
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    QMessageBox.information(self, "提示", "文件为空")
                    return

                # 解析表头，定位列索引
                header = lines[0]
                header_cols = [c.strip().replace('\ufeff', '') for c in header.split(',')]

                # 查找必要列
                code_idx = None
                name_idx = None
                high_idx = None
                low_idx = None
                # 各列可接受的关键字（只要列名包含其中之一即匹配）
                CODE_KEYWORDS = ['代码', '股票代码', '证券代码', 'code', 'symbol', 'ticker']
                NAME_KEYWORDS = ['名称', '股票名称', '证券名称', '公司名称', '公司简称', '简称', 'name']
                HIGH_KEYWORDS = ['高位涨幅提醒', '涨幅提醒', '高位提醒', '高位', 'high']
                LOW_KEYWORDS  = ['低位跌幅提醒', '跌幅提醒', '低位提醒', '低位', 'low']

                for i, col in enumerate(header_cols):
                    col_lower = col.lower()
                    if code_idx is None and any(k.lower() in col_lower for k in CODE_KEYWORDS):
                        code_idx = i
                    elif name_idx is None and any(k.lower() in col_lower for k in NAME_KEYWORDS):
                        name_idx = i
                    elif high_idx is None and any(k.lower() in col_lower for k in HIGH_KEYWORDS):
                        high_idx = i
                    elif low_idx is None and any(k.lower() in col_lower for k in LOW_KEYWORDS):
                        low_idx = i

                # 如果找不到表头，兼容旧格式：整文件当作纯代码列表
                if code_idx is None:
                    for line in lines:
                        code = line.split(',')[0].strip()
                        if code and code not in self.codes:
                            self.codes.append(code)
                else:
                    # 有表头，按列索引读取
                    imported = 0
                    for line in lines[1:]:
                        parts = line.split(',')
                        if len(parts) <= code_idx:
                            continue
                        code = parts[code_idx].strip()
                        if not code:
                            continue
                        if code not in self.codes:
                            self.codes.append(code)
                            imported += 1
                        # 读取提醒值（如存在）
                        try:
                            if high_idx is not None and high_idx < len(parts):
                                h_val = float(parts[high_idx].strip())
                                if h_val != 0.0:
                                    self.alerts.setdefault(code, {})['high'] = h_val
                        except ValueError:
                            pass
                        try:
                            if low_idx is not None and low_idx < len(parts):
                                l_val = float(parts[low_idx].strip())
                                if l_val != 0.0:
                                    self.alerts.setdefault(code, {})['low'] = l_val
                        except ValueError:
                            pass
                    QMessageBox.information(self, "导入成功", f"成功导入 {imported} 条股票记录！")

                self.populate_table()
            except Exception as e:
                QMessageBox.warning(self, "导入失败", str(e))

    def export_csv(self):
        export_dir = get_export_dir()
        # 文件名：stock_list_{分组名}_{yyyyMMdd}_{HHmmss}.csv
        group_name = self.category_data.get('name', '未命名')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"stock_list_{group_name}_{timestamp}.csv"
        file, _ = QFileDialog.getSaveFileName(
            self, "保存 CSV 文件",
            os.path.join(export_dir, default_name),
            "CSV Files (*.csv)"
        )
        if file:
            try:
                from data_service import fetch_stock_basics, format_stock_code
                basics = fetch_stock_basics(self.codes)
                name_map = {b['code']: b['name'] for b in basics}

                with open(file, 'w', encoding='utf-8-sig') as f:
                    f.write("代码,名称,高位涨幅提醒,低位跌幅提醒\n")
                    for code in self.codes:
                        f_code = format_stock_code(code)
                        name = name_map.get(f_code, "")
                        alerts = self.alerts.get(code, {})
                        high = alerts.get('high', 0.0)
                        low = alerts.get('low', 0.0)
                        f.write(f"{f_code},{name},{high},{low}\n")
                QMessageBox.information(self, "成功", "导出成功！")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

class SettingsDialog(QDialog):
    """程序设置对话框"""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("程序设置")
        self.setFixedSize(400, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.settings = settings.copy()
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 刷新间隔设置
        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(QLabel("刷新间隔(秒):"))
        self.refresh_spin = QDoubleSpinBox()
        self.refresh_spin.setRange(5, 3600)
        self.refresh_spin.setValue(self.settings.get('refresh_interval', 30))
        self.refresh_spin.setSuffix(" 秒")
        self.refresh_spin.setSingleStep(5)
        refresh_layout.addWidget(self.refresh_spin)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # 字体大小设置
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体大小(px):"))
        self.font_spin = QDoubleSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setValue(self.settings.get('font_size', 11))
        self.font_spin.setSuffix(" px")
        self.font_spin.setSingleStep(1)
        font_layout.addWidget(self.font_spin)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        # 分隔线
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #ddd;")
        layout.addWidget(line)
        
        # 开机自启设置
        self.auto_start_cb = QCheckBox("开机自动启动")
        self.auto_start_cb.setChecked(self.settings.get('auto_start', False))
        self.auto_start_cb.setToolTip("程序将在Windows启动时自动运行")
        layout.addWidget(self.auto_start_cb)
        
        layout.addStretch()
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存设置")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_settings(self):
        """返回更新后的设置字典"""
        self.settings['refresh_interval'] = int(self.refresh_spin.value())
        self.settings['font_size'] = int(self.font_spin.value())
        self.settings['auto_start'] = self.auto_start_cb.isChecked()
        return self.settings

class AboutDialog(QDialog):
    """关于对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"关于 {APP_NAME}")
        self.setFixedSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(create_emoji_icon("💹", 64).pixmap(64, 64))
        layout.addWidget(icon_label)
        
        # App name and version
        title_label = QLabel(f"<h2>{APP_NAME}</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        version_label = QLabel(f"版本 {APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #666;")
        layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel("ITGeeker Stock Widget\n财务自由, 尽在掌控")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc_label)
        
        # Copyright
        copyright_label = QLabel("© 2026 ITGeeker技术奇客\nAll Rights Reserved.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(copyright_label)
        
        # Website link
        website_label = QLabel('<a href="https://www.itgeeker.net" style="color: #1a73e8; text-decoration: none;">www.itgeeker.net</a>')
        website_label.setAlignment(Qt.AlignCenter)
        website_label.setStyleSheet("font-size: 11px;")
        website_label.setOpenExternalLinks(True)
        layout.addWidget(website_label)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("关闭")
        close_btn.setMaximumWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        layout.setAlignment(close_btn, Qt.AlignCenter)
        
        self.setLayout(layout)

class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ITGeeker Stock Widget {APP_VERSION}")
        self.config_data = load_config()
        self.categories = self.config_data['categories']
        self.settings = self.config_data.get('settings', DEFAULT_CONFIG["settings"].copy())
        
        if not os.path.exists(CONFIG_FILE):
            save_config(self.config_data)

        self.active_widgets = []
        self._row_checkboxes = []  # will be populated in refresh_list
        
        # Setup Tray Icon with Emoji 💹 (64px for better visibility)
        self.tray_icon = QSystemTrayIcon(self)
        emoji_icon = create_emoji_icon("💹", 64)
        self.tray_icon.setIcon(emoji_icon)
        
        # Set tooltip with version and category count
        self.update_tray_tooltip()
        
        # 托盘菜单
        show_action = QAction("📂 分组管理", self)
        settings_action = QAction("⚙️ 程序设置", self)
        about_action = QAction("ℹ️ 关于", self)
        quit_action = QAction("🚪 退出程序", self)
        
        show_action.triggered.connect(self._show_management_panel)
        settings_action.triggered.connect(self.show_settings)
        about_action.triggered.connect(self.show_about)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(about_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        
        # Set window icon as well
        self.setWindowIcon(emoji_icon)
        
        # Start Global Alert Checker Timer
        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self.check_alerts)
        self.alert_timer.start(30000)
        self.alert_triggered = set()
        
        layout = QVBoxLayout()
        header = QLabel("<div style='text-align: center;'><span style='font-size: 18px; font-weight: bold;'>ITGeeker Stock Widget</span><br/><br/><span style='font-size: 14px; font-weight: normal; color: #888;'>财务自由, 尽在掌控</span></div>")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("padding: 10px; font-family: Microsoft YaHei;")
        layout.addWidget(header)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self.refresh_list()
        
        # Launch default open categories
        for cat in self.categories:
            if cat.get('default_open', False):
                self.open_widget(cat)
        
        btn_layout = QHBoxLayout()
        
        add_cat_btn = QPushButton("添加新分组")
        add_cat_btn.clicked.connect(self.add_category)
        btn_layout.addWidget(add_cat_btn)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setToolTip("全选 / 取消全选")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        btn_layout.addWidget(self.select_all_btn)

        launch_selected_btn = QPushButton("打开已选")
        launch_selected_btn.setToolTip("打开所有已勾选的分组")
        launch_selected_btn.clicked.connect(self.launch_selected)
        btn_layout.addWidget(launch_selected_btn)

        launch_all_btn = QPushButton("全部打开")
        launch_all_btn.clicked.connect(self.launch_all)
        btn_layout.addWidget(launch_all_btn)

        layout.addLayout(btn_layout)

        # 底部按钮区域
        bottom_layout = QHBoxLayout()
        
        settings_btn = QPushButton("程序设置")
        settings_btn.clicked.connect(self.show_settings)
        bottom_layout.addWidget(settings_btn)
        
        bottom_layout.addStretch()
        
        footer_label = QLabel(f'<a href="https://www.itgeeker.net" style="color: #999; text-decoration: none;">{APP_VERSION} | 开发者: ITGeeker技术奇客</a>')
        footer_label.setStyleSheet("font-size: 10px;")
        footer_label.setOpenExternalLinks(True)
        bottom_layout.addWidget(footer_label)
        
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.resize(850, 500)

    def show_about(self):
        """显示关于对话框"""
        dlg = AboutDialog(self)
        dlg.exec()

    def show_settings(self):
        """显示程序设置对话框"""
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            new_settings = dlg.get_settings()
            
            # 检查开机自启设置变化
            auto_start_enabled = new_settings.get('auto_start', False)
            if is_auto_start_enabled() != auto_start_enabled:
                if set_auto_start(auto_start_enabled):
                    action = "已启用" if auto_start_enabled else "已禁用"
                    QMessageBox.information(self, "提示", f"开机自动启动{action}！")
                else:
                    QMessageBox.warning(self, "错误", "设置自动启动失败！")
            
            # 保存设置
            self.settings = new_settings
            self.config_data['settings'] = self.settings
            save_config(self.config_data)
            
            QMessageBox.information(self, "提示", "设置保存成功，之后新开的窗口将采用新设置！")

    def _show_management_panel(self):
        """显示并激活股票分组管理面板"""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def update_tray_tooltip(self):
        """Update tray icon tooltip with version and category count"""
        category_count = len(self.categories)
        tooltip = f"{APP_NAME}\n{APP_VERSION}\n股票分组: {category_count} 个"
        self.tray_icon.setToolTip(tooltip)

    def _show_main_panel(self):
        """显示并激活主控制面板（供分组widget右键菜单回调）"""
        self._show_management_panel()

    def refresh_list(self):
        # 清理已被关闭的 widget（防止关闭后仍残留在列表中）
        self.active_widgets = [w for w in self.active_widgets if w.isVisible()]

        self.list_widget.clear()
        self._row_checkboxes = []  # track checkboxes per row
        # Update tooltip when categories change
        self.update_tray_tooltip()
        for idx, cat in enumerate(self.categories):
            item = QListWidgetItem()
            widget = QWidget()
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(5, 5, 5, 5)
            h_layout.setSpacing(8)

            # ── Checkbox for multi-select ──
            cb = QCheckBox()
            cb.setToolTip("勾选后可批量打开")
            cb.setFixedWidth(24)
            cb.stateChanged.connect(self._sync_select_all_btn)
            self._row_checkboxes.append(cb)
            h_layout.addWidget(cb)

            # ── Group name ──
            lbl_name = QLabel(f"{cat['name']}")
            lbl_name.setMinimumWidth(100)
            lbl_name.setStyleSheet("font-weight: bold;")
            h_layout.addWidget(lbl_name)

            # ── Open status ──
            is_open = any(w.title == cat['name'] and w.isVisible() for w in self.active_widgets)
            lbl_status = QLabel("已打开" if is_open else "未打开")
            lbl_status.setFixedWidth(48)
            lbl_status.setAlignment(Qt.AlignCenter)
            if is_open:
                lbl_status.setStyleSheet(
                    "color: #fff; background-color: #28a745; font-size: 10px; "
                    "border-radius: 4px; padding: 1px 4px;"
                )
            else:
                lbl_status.setStyleSheet(
                    "color: #fff; background-color: #adb5bd; font-size: 10px; "
                    "border-radius: 4px; padding: 1px 4px;"
                )
            h_layout.addWidget(lbl_status)

            # ── Auto-open on startup ──
            is_auto = cat.get('default_open', False)
            lbl_auto = QLabel("自动" if is_auto else "")
            lbl_auto.setFixedWidth(36)
            lbl_auto.setAlignment(Qt.AlignCenter)
            if is_auto:
                lbl_auto.setStyleSheet(
                    "color: #fff; background-color: #17a2b8; font-size: 10px; "
                    "border-radius: 4px; padding: 1px 4px;"
                )
            h_layout.addWidget(lbl_auto)

            # ── Stock codes ──
            codes_text = ",".join(cat['codes'])
            lbl_codes = QLabel(codes_text)
            lbl_codes.setStyleSheet("color: #666; font-size: 10px;")
            lbl_codes.setFixedWidth(260)
            lbl_codes.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl_codes.setToolTip(codes_text)  # 鼠标悬停显示完整内容
            h_layout.addWidget(lbl_codes)

            h_layout.addStretch()

            # ── Action buttons ──
            btn_launch = QPushButton("打开")
            btn_launch.setMaximumWidth(50)
            btn_launch.clicked.connect(lambda checked, c=cat: self.open_widget(c))

            btn_edit = QPushButton("修改")
            btn_edit.setMaximumWidth(50)
            btn_edit.clicked.connect(lambda checked, idx=idx: self.edit_category(idx))

            btn_del = QPushButton("删除")
            btn_del.setMaximumWidth(50)
            btn_del.clicked.connect(lambda checked, idx=idx: self.delete_category(idx))

            h_layout.addWidget(btn_launch)
            h_layout.addWidget(btn_edit)
            h_layout.addWidget(btn_del)

            widget.setLayout(h_layout)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def add_category(self):
        cat = {"name": "新分组", "codes": [], "default_open": False}
        dlg = EditCategoryDialog(cat, self)
        if dlg.exec():
            name = dlg.name_input.text().strip()
            codes = dlg.codes
            if name:
                self.categories.append({
                    "name": name, 
                    "codes": codes,
                    "default_open": dlg.default_open_cb.isChecked(),
                    "alerts": dlg.alerts
                })
                save_config(self.config_data)
                self.refresh_list()

    def edit_category(self, idx):
        cat = self.categories[idx]
        dlg = EditCategoryDialog(cat, self)
        if dlg.exec():
            name = dlg.name_input.text().strip()
            codes = dlg.codes
            if name:
                old_name = self.categories[idx]['name']
                self.categories[idx] = {
                    "name": name, 
                    "codes": codes,
                    "default_open": dlg.default_open_cb.isChecked(),
                    "alerts": dlg.alerts
                }
                save_config(self.config_data)
                self.refresh_list()
                
                # Check if it was open, and directly update it
                for w in self.active_widgets:
                    if w.title == old_name and w.isVisible():
                        w.title = name
                        w.codes = codes
                        w.update_size()
                        w.fetch_data()
                        w.update()

    def delete_category(self, idx):
        reply = QMessageBox.question(self, '确认', '确定要删除这个分组吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.categories.pop(idx)
            save_config(self.config_data)
            self.refresh_list()

    def open_widget(self, category):
        # 增加唯一性检查
        for w in self.active_widgets:
            if w.title == category['name'] and w.isVisible():
                w.activateWindow()
                return

        widget = StockWidget(
            category['name'], category['codes'], self.settings,
            show_main_callback=self._show_management_panel,
            show_settings_callback=self.show_settings,
            always_on_top=category.get('always_on_top', True)
        )
        widget.on_moved_callback = self.save_widget_position
        widget.on_closed_callback = self._on_widget_closed
        widget.on_top_changed_callback = self.save_widget_top
        self.active_widgets.append(widget)
        
        pos = category.get('position')
        if pos and 'x' in pos and 'y' in pos:
            widget.move(pos['x'], pos['y'])
        else:
            visible_count = len([w for w in self.active_widgets if w.isVisible()])
            offset = visible_count * 30
            widget.move(50 + offset, 50 + offset)
            
        widget.show()
        widget.fetch_data()  # 窗口刚打开时立即拉取一次数据
        self.refresh_list()  # 打开后立即刷新列表状态

    def save_widget_position(self, title, x, y):
        for cat in self.categories:
            if cat['name'] == title:
                cat['position'] = {'x': x, 'y': y}
                save_config(self.config_data)
                break

    def save_widget_top(self, title, always_on_top):
        """置顶状态改变时写入配置"""
        for cat in self.categories:
            if cat['name'] == title:
                cat['always_on_top'] = always_on_top
                save_config(self.config_data)
                break

    def _on_widget_closed(self, widget):
        """StockWidget 关闭时从 active_widgets 移除并刷新列表"""
        if widget in self.active_widgets:
            self.active_widgets.remove(widget)
        self.refresh_list()

    def check_alerts(self):
        # 非交易时段不检查提醒，避免无效请求
        from data_service import is_trading_time
        if not is_trading_time():
            return

        # 只检查已打开（可见）窗口对应分组的提醒
        open_titles = {w.title for w in self.active_widgets if w.isVisible()}

        alert_tasks = {}
        for cat in self.categories:
            if cat['name'] not in open_titles:
                continue
            alerts = cat.get('alerts', {})
            for code, limits in alerts.items():
                alert_tasks[code] = limits
        if not alert_tasks:
            return
            
        from data_service import fetch_stock_basics
        results = fetch_stock_basics(list(alert_tasks.keys()))
        for res in results:
            code = res['code'] # wait, need to match raw_code from dict keys, actually code is unformatted code
            # We'll check by matching the trailing 6 numbers because format_stock_code prepends the region
            # Quick hack: match by `code` in alert_tasks to simplify
            limits = alert_tasks.get(code)
            if not limits:
                # search for partial match
                matched = [c for c in alert_tasks.keys() if code in c or c in code]
                if matched:
                    limits = alert_tasks[matched[0]]
                    code = matched[0]
            if limits:
                cp = res.get('change_percent', 0.0)
                name = res.get('name', code)
                
                # Check High
                h_thresh = limits.get('high', 0.0)
                if h_thresh > 0.0 and cp >= h_thresh:
                    alert_id = f"{code}_HIGH_{h_thresh}"
                    if alert_id not in self.alert_triggered:
                        self.tray_icon.showMessage("股票突破高位预警", f"{name}({code}) 当前涨跌幅已达 +{cp}%！", QSystemTrayIcon.Warning, 5000)
                        self.alert_triggered.add(alert_id)
                # Check Low
                l_thresh = limits.get('low', 0.0)
                if l_thresh < 0.0 and cp <= l_thresh:
                    alert_id = f"{code}_LOW_{l_thresh}"
                    if alert_id not in self.alert_triggered:
                        self.tray_icon.showMessage("股票跌破低位预警", f"{name}({code}) 当前涨跌幅跌至 {cp}%！", QSystemTrayIcon.Warning, 5000)
                        self.alert_triggered.add(alert_id)

    def _sync_select_all_btn(self):
        """根据当前checkbox状态同步「全选」按钮的文字"""
        if not hasattr(self, 'select_all_btn'):
            return
        all_checked = bool(self._row_checkboxes) and all(cb.isChecked() for cb in self._row_checkboxes)
        self.select_all_btn.setText("取消全选" if all_checked else "全选")

    def toggle_select_all(self):
        """全选 / 取消全选所有分组的 checkbox"""
        all_checked = all(cb.isChecked() for cb in self._row_checkboxes) if self._row_checkboxes else False
        for cb in self._row_checkboxes:
            cb.setChecked(not all_checked)
        self.select_all_btn.setText("取消全选" if not all_checked else "全选")

    def launch_selected(self):
        """打开所有已勾选分组的股票组件"""
        selected_cats = [cat for cb, cat in zip(self._row_checkboxes, self.categories) if cb.isChecked()]
        if not selected_cats:
            QMessageBox.information(self, "提示", "请先勾选至少一个分组！")
            return
        for cat in selected_cats:
            self.open_widget(cat)

    def launch_all(self):
        for cat in self.categories:
            self.open_widget(cat)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("ITGeeker Stock Widget", "应用已最小化到系统托盘", QSystemTrayIcon.Information, 2000)

    def on_tray_activated(self, reason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self._show_management_panel()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    # Use Emoji icon for the application
    app.setWindowIcon(create_emoji_icon("💹", 32))
    panel = ControlPanel()
    # 启动时隐藏窗口，只在托盘运行
    panel.hide()
    sys.exit(app.exec())
