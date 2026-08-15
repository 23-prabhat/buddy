TERMINAL_QSS = """
QWidget#Root {
    background-color: #2a1f3d;
    color: #e8dfff;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", "Monospace";
    font-size: 13px;
}
QLabel#TitleBar {
    background-color: #241a38;
    color: #e8dfff;
    padding: 8px 12px;
    border-bottom: 1px solid #4a3a6b;
    font-weight: 600;
}
QLabel#StatusBar {
    background-color: #241a38;
    color: #a99dc4;
    padding: 6px 12px;
    border-top: 1px solid #4a3a6b;
    font-size: 12px;
}
QPlainTextEdit#Output {
    background-color: #2a1f3d;
    color: #e8dfff;
    border: none;
    padding: 10px 12px;
    selection-background-color: #5d4585;
    selection-color: #ffffff;
}
QLineEdit#Prompt {
    background-color: #2a1f3d;
    color: #c09bff;
    border: none;
    border-top: 1px solid #4a3a6b;
    padding: 10px 12px;
    selection-background-color: #5d4585;
    selection-color: #ffffff;
}
QPushButton#ModeButton {
    background-color: #241a38;
    color: #a99dc4;
    border: 1px solid #4a3a6b;
    padding: 4px 14px;
    border-radius: 3px;
    font-weight: 600;
    min-width: 64px;
}
QPushButton#ModeButton:hover {
    color: #e8dfff;
    border: 1px solid #7a5fb0;
}
QPushButton#ModeButton:checked {
    background-color: #5d4585;
    color: #ffffff;
    border: 1px solid #c09bff;
}
QScrollBar:vertical {
    background-color: #241a38;
    width: 12px;
    border: none;
    border-left: 1px solid #4a3a6b;
}
QScrollBar::handle:vertical {
    background-color: #5d4585;
    border: 2px solid #241a38;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background-color: #c09bff;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background-color: #241a38;
    height: 12px;
    border: none;
    border-top: 1px solid #4a3a6b;
}
QScrollBar::handle:horizontal {
    background-color: #5d4585;
    border: 2px solid #241a38;
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #c09bff;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
QMenu {
    background-color: #2a1f3d;
    color: #e8dfff;
    border: 1px solid #4a3a6b;
    padding: 6px;
}
QMenu::item {
    padding: 6px 24px;
}
QMenu::item:selected {
    background-color: #4a3a6b;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #4a3a6b;
    margin: 4px 8px;
}
QRubberBand {
    border: 2px solid #e040fb;
    background-color: rgba(224, 64, 251, 0.18);
    selection-background-color: #5d4585;
    selection-color: #ffffff;
}
"""