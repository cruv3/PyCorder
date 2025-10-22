APP_STYLE = """
/* === Base === */
QWidget {
    background-color: #0E1014;
    color: #E5E6EB;
    font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
    font-size: 14px;
    border: none;
}

/* === Buttons === */
QPushButton {
    background-color: #1C1F26;
    border: 1px solid #2C313C;
    border-radius: 6px;
    padding: 6px 14px;
    color: #E5E6EB;
    font-weight: 500;
    letter-spacing: 0.3px;
}
QPushButton:hover {
    background-color: #252A35;
    border: 1px solid #4D9FFF;
}
QPushButton:pressed {
    background-color: #4D9FFF;
    border: 1px solid #4D9FFF;
    color: #FFFFFF;
}
QPushButton:disabled {
    background-color: #1A1C22;
    color: #5C5F66;
    border: 1px solid #262A33;
}

/* === Labels === */
QLabel {
    color: #E5E6EB;
}
QLabel#statusLabel {
    font-weight: 600;
    color: #4D9FFF;
    padding: 4px 8px;
}

/* === SpinBoxes === */
QSpinBox, QDoubleSpinBox {
    background-color: #171A1F;
    border: 1px solid #2C2F38;
    border-radius: 4px;
    color: #E5E6EB;
    padding: 3px 6px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border: 1px solid #4D9FFF;
}

/* === Table === */
QTableWidget {
    background-color: #13151B;
    border: 1px solid #22262F;
    gridline-color: #2A2E39;
    selection-background-color: #4D9FFF;
    selection-color: #FFFFFF;
    alternate-background-color: #13151B; /* no zebra */
    font-size: 14px;
}
QHeaderView::section {
    background-color: #181B22;
    color: #C7C9D0;
    padding: 6px 8px;
    border: 1px solid #2A2E39;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QTableCornerButton::section {
    background-color: #181B22;
    border: 1px solid #2A2E39;
}

/* === TreeView === */
QTreeView {
    background-color: #13151B;
    border: 1px solid #22262F;
    color: #E5E6EB;
    selection-background-color: #4D9FFF;
    selection-color: #FFFFFF;
    alternate-background-color: #13151B;
}
QTreeView::item {
    padding: 5px;
}
QTreeView::item:selected {
    background-color: #4D9FFF;
    color: #FFFFFF;
}
QTreeView::item:hover {
    background-color: #1C2028;
}

/* === Scrollbars === */
QScrollBar:vertical {
    background: #0E1014;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #2A2E39;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #4D9FFF;
}

/* === Frames / Lines === */
QFrame[frameShape="4"] {
    color: #262A33;
}
"""
