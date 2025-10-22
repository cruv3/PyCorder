from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QDoubleSpinBox, QSpinBox


class ControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Buttons ===
        self.btn_record = QPushButton("⏺ Record (F9)")
        self.btn_play = QPushButton("▶ Play (F10)")
        for b in (self.btn_record, self.btn_play):
            b.setFixedHeight(36)
            b.setMinimumWidth(140)
            layout.addWidget(b)

        # === Spacer ===
        layout.addStretch(1)

        # === Speed Control ===
        layout.addWidget(QLabel("Speed:"))
        self.speed_box = QDoubleSpinBox()
        self.speed_box.setRange(0.1, 10.0)
        self.speed_box.setValue(1.0)
        self.speed_box.setSingleStep(0.1)
        self.speed_box.setFixedWidth(80)
        layout.addWidget(self.speed_box)

        # === Repeat Control ===
        layout.addWidget(QLabel("Repeats (0 = ∞):"))
        self.repeat_box = QSpinBox()
        self.repeat_box.setRange(0, 9999)
        self.repeat_box.setValue(1)
        self.repeat_box.setFixedWidth(80)
        layout.addWidget(self.repeat_box)

        self.setLayout(layout)
