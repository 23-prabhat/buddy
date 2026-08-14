TERMINAL_QSS = """
QWidget#Root {
    background-color: #0c0c0c;
    color: #d4d4d4;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", "Monospace";
    font-size: 13px;
}
QLabel#TitleBar {
    background-color: #111111;
    color: #e0e0e0;
    padding: 8px 12px;
    border-bottom: 1px solid #2a2a2a;
    font-weight: 600;
}
QLabel#StatusBar {
    background-color: #111111;
    color: #8a8a8a;
    padding: 6px 12px;
    border-top: 1px solid #2a2a2a;
    font-size: 12px;
}
QPlainTextEdit#Output {
    background-color: #0c0c0c;
    color: #d4d4d4;
    border: none;
    padding: 10px 12px;
    selection-background-color: #264f78;
}
QLineEdit#Prompt {
    background-color: #0c0c0c;
    color: #00ff9c;
    border: none;
    border-top: 1px solid #2a2a2a;
    padding: 10px 12px;
    selection-background-color: #264f78;
}
"""
