# Geeker Stock Widget 项目记忆

## 项目信息
- **项目路径**: d:/git_geeker/geeker_dev/python_dev/py_fin/itgeeker_stock_widget
- **版本**: v1.3.4.0
- **技术栈**: PySide6 (Qt for Python)
- **图标**: 使用Emoji💹替代原有PNG图标
- **打包命令**: `pyinstaller ITGeekerStockWidget.spec --clean`
- **输出exe**: `dist/ITGeekerStockWidget.exe`（约 54.14 MB）
- **打包spec文件**: ITGeekerStockWidget.spec（新）和 Geeker Stock Widget.spec（旧，保留）
- **APP_NAME**: `ITGeeker Stock Widget`
- **CSV导入导出**: 导出包含表头（代码,名称,高位涨幅提醒,低位跌幅提醒）；导入支持外部表格，只要表头包含"代码"和"名称"即可
- **启动行为**: 默认隐藏到系统托盘，双击托盘图标或菜单打开

## 2026-04-30 变更记录

### v1.3.2.0
1. **新增设置界面**：创建 SettingsDialog 类，包含刷新间隔、字体大小、开机自启等设置项
2. **重构主面板**：删除内嵌设置控件，添加独立的「程序设置」按钮
3. **托盘菜单优化**：「显示主面板」→「股票分组管理」，新增「程序设置」菜单项
4. **启动隐藏**：程序启动时自动隐藏窗口，只在系统托盘运行
5. **右键菜单更新**：「打开主面板」→「股票分组管理」

### v1.3.1.0
1. 右键菜单增加「打开主面板」功能

### v1.3.0.0
1. 导入导出CSV默认路径改为 Windows 下载目录的 `ITGeekerWidgetExport` 子目录
2. 导出文件名格式：`stock_list_{分组名}_{yyyyMMdd}_{HHmmss}.csv`

## 配置结构 (categories.json)
- settings: refresh_interval, font_size, auto_start
- categories: [{name, codes, default_open, alerts, position}]

## 关键类
- ControlPanel - 主控制面板（股票分组管理）
- StockWidget - 股票显示小窗口
- SettingsDialog - 程序设置对话框（v1.3.2.0新增）
- AboutDialog - 关于对话框
- EditCategoryDialog - 分组编辑对话框

## 关键函数
- create_emoji_icon(emoji, size=32) - 创建Emoji图标
- is_auto_start_enabled() - 检查自动启动状态
- set_auto_start(enable) - 设置自动启动
- update_tray_tooltip() - 更新托盘提示
- show_settings() - 显示程序设置对话框（v1.3.2.0新增）
- _show_management_panel() - 显示股票分组管理面板（v1.3.2.0新增）
