APP_STYLE = """
/* === Base === */
QWidget {
    background-color: #1E1E2E;
    color: #E0E0E0;
    font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
    font-size: 15px;
}

/* === Buttons === */
QPushButton {
    background-color: #2E3A4E;
    border: 1px solid #3F4B5C;
    border-radius: 6px;
    padding: 6px 12px;
    color: #E0E0E0;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #3B4B64;
    border: 1px solid #5C6B7C;
}
QPushButton:pressed {
    background-color: #4A90E2;
    border: 1px solid #4A90E2;
    color: white;
}

/* === Status Label === */
QLabel#statusLabel {
    font-size: 16px;
    font-weight: 600;
    color: #A0C4FF;
    padding: 6px;
}

/* === Spin Boxes === */
QSpinBox, QDoubleSpinBox {
    background-color: #2A2A3C;
    border: 1px solid #3A3A4C;
    color: #E0E0E0;
    border-radius: 5px;
    padding: 3px 6px;
    min-width: 80px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border: 1px solid #4A90E2;
}

/* === Table === */
QTableWidget {
    gridline-color: #3A3A4C;
    selection-background-color: #4A90E2;
    selection-color: white;
    alternate-background-color: #252535;
    font-size: 15px;
}
QHeaderView::section {
    background-color: #2A2A3C;
    color: #C8C8C8;
    padding: 6px;
    border: 1px solid #3A3A4C;
    font-weight: 600;
}

/* === Scrollbars === */
QScrollBar:vertical {
    background: #1E1E2E;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #444A5C;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #5C6B7C;
}

/* === Separators === */
QFrame[frameShape="4"] {
    color: #3A3A4C;
}

/* === Labels === */
QLabel {
    color: #E0E0E0;
}

/* === TreeView (GroupedActionEditor) === */
QTreeView {
    background-color: #1E1E2E;
    alternate-background-color: #1E1E2E;
    color: #E0E0E0;
    gridline-color: #333;
    selection-background-color: #4A90E2;
    selection-color: white;
    border: 1px solid #2A2A3C;
}
QTreeView::item {
    padding: 6px;
}
QTreeView::item:selected {
    background-color: #4A90E2;
    color: white;
}
QTreeView::item:hover {
    background-color: #2E3A4E;
}

/* Gruppe: leicht dunkler Hintergrund */
QTreeView::item:!has-children {
    background-color: #252535;
}
"""
