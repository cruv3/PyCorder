import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFileDialog, QFrame, QHBoxLayout, QPushButton, QStyle
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QMetaObject, Qt
from PyQt5 import QtGui, QtWidgets
from pynput import keyboard

from ui.action_tree.editor import ActionTreeEditor
from ui.panels.control_panel import ControlPanel
from ui.components.gui_style import APP_STYLE
from core.recorder import Recorder
from core.playback import Playback
from core.storage import Storage
from core.config import IGNORE_KEYS, AUTOSAVE_PATH

# --- Fix für Wine & Font Rendering ---
QtWidgets.QApplication.setStyle("Fusion")
QtWidgets.QApplication.setFont(QtGui.QFont("Segoe UI", 10))

# --- Palette anpassen, damit Buttons & Labels IMMER sichtbar sind ---
palette = QtGui.QPalette()
palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#0E1014"))
palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#13151B"))
palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#1C1F26"))
palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#E5E6EB"))
palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#E5E6EB"))
palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#E5E6EB"))
QtWidgets.QApplication.setPalette(palette)

class MainWindow(QWidget):
    highlight_signal = pyqtSignal(int)
    play_done_signal = pyqtSignal()
    action_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyCorder")
        self.setGeometry(300, 150, 950, 720)
        self.setStyleSheet(APP_STYLE)

        # === Core-Komponenten ===
        self.playback = Playback()
        self.playback.step_signal.connect(self._on_playback_step)
        self.playback.done_signal.connect(self.stop_play)
        self.play_start_offset = 0
        self.recorder = Recorder(on_action=self.action_signal.emit, ignore_keys=IGNORE_KEYS)

        # === States ===
        self.actions = []
        self.is_playing = False

        # === Layout ===
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # === Action Tree ===
        self.action_tree = ActionTreeEditor()
        self.action_tree.overlay.enable(True)
        self.action_tree.play_request.connect(self._on_play_request)
        layout.addWidget(self.action_tree)

        # === Divider ===
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #333; margin: 8px 0;")
        layout.addWidget(divider)

        # === Control Panel ===
        self.controls = ControlPanel()
        layout.addWidget(self.controls)

        # === Save / Load ===
        file_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Macro")
        self.btn_save.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))

        self.btn_load = QPushButton("Load Macro")
        self.btn_load.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        for b in (self.btn_save, self.btn_load):
            b.setFixedHeight(34)
            b.setStyleSheet("font-weight: 500;")
        file_row.addWidget(self.btn_save)
        file_row.addWidget(self.btn_load)
        layout.addLayout(file_row)
        self.setLayout(layout)

        # === Signal-Verbindungen ===
        self.action_signal.connect(self._on_new_action)
        self.play_done_signal.connect(self.stop_play)
        self.controls.btn_record.clicked.connect(self.toggle_record)
        self.controls.btn_play.clicked.connect(self.toggle_play)
        self.btn_save.clicked.connect(self.save_macro)
        self.btn_load.clicked.connect(self.load_macro)

        # === Global Hotkeys ===
        self.global_listener = keyboard.Listener(on_press=self._on_global_key)
        self.global_listener.start()

        # === Autosave laden ===
        self._autoload()

    # =====================================================
    # GLOBAL HOTKEYS
    # =====================================================
    def _on_global_key(self, key):
        try:
            if key == keyboard.Key.f9:
                QMetaObject.invokeMethod(self, "toggle_record", Qt.QueuedConnection)
            elif key == keyboard.Key.f10:
                QMetaObject.invokeMethod(self, "toggle_play", Qt.QueuedConnection)
        except Exception as e:
            print(f"[HOTKEY ERROR] {e}")

    # =====================================================
    # RECORDING
    # =====================================================
    @pyqtSlot()
    def toggle_record(self):
        if self.recorder.is_recording:
            self.stop_record()
        else:
            self.start_record()

    def start_record(self):
        if self.is_playing:
            self.stop_play()

        try:
            self.recorder.start()
            self._update_ui_state(recording=True)
            self.action_tree.overlay.enable(False) 
        except Exception as e:
            print(f"[RECORD START ERROR] {e}")
            self._update_ui_state()

    def stop_record(self):
        try:
            self.recorder.stop()
        except Exception as e:
            print(f"[RECORD STOP ERROR] {e}")
        self._update_ui_state(recording=False)
        self.action_tree.overlay.enable(True) 

    def _on_new_action(self, action):
        if not self.recorder.is_recording:
            return
        if self.actions and action == self.actions[-1]:
            return
        self.action_tree.add_action(action)
        self.actions.append(action)

    # =====================================================
    # PLAYBACK
    # =====================================================
    def _on_play_request(self, payload):
        if not payload:
            return

        if isinstance(payload, tuple):
            actions, start_idx = payload
            start_offset = self.action_tree.get_action_index_from_model_index(start_idx)
        else:
            actions = payload
            start_offset = 0

        self.toggle_play(actions, start_offset)

    @pyqtSlot()
    def toggle_play(self, actions=None, start_offset=0):
        if self.is_playing:
            self.stop_play()
            return
        
        def _flatten(nodes):
            result = []
            for n in nodes:
                if isinstance(n, dict) and "kind" in n:
                    if n["kind"] == "action":
                        result.append(n["data"])
                    elif n["kind"] == "__group__":
                        result.extend(_flatten(n.get("children", [])))

                elif isinstance(n, dict) and n.get("type"):
                    result.append(n)
            return result

        if actions is None:
            actions = self.action_tree.get_all_actions()

        actions = _flatten(actions)
        actions = [a for a in actions if isinstance(a, dict) and a.get("type")]

        if not actions:
            print("[WARN] No valid actions to play (empty selection or only groups).")
            return
        
        print(f"[DEBUG] Actions to play: {len(actions)}")
        for i, act in enumerate(actions):
            if isinstance(act, dict):
                print(f"  {i:02d}: {act.get('type', 'UNKNOWN')}")
            else:
                print(f"  {i:02d}: INVALID ({type(act)})")

        self.start_play(actions, start_offset)

    def start_play(self, actions, start_offset=0):
        self.play_start_offset = start_offset
        if self.recorder.is_recording:
            self.stop_record()

        if not actions:
            print("[WARN] No actions provided to play.")
            return

        try:
            self.is_playing = True
            self._update_ui_state()

            speed = self.controls.speed_box.value()
            repeat = self.controls.repeat_box.value()
            self.action_tree.clear_highlight()

            self.playback.play(
                actions,
                speed=speed,
                repeat=repeat,
                on_done=lambda: self.play_done_signal.emit()
            )
            self.action_tree.overlay.enable(False) 
        except Exception as e:
            print(f"[PLAYBACK ERROR] {e}")
            self.stop_play()

    def stop_play(self):
        try:
            self.playback.stop()
        except Exception as e:
            print(f"[PLAY STOP ERROR] {e}")
        self.is_playing = False
        self._update_ui_state()
        self.action_tree.overlay.enable(True) 

    @pyqtSlot(int, dict)
    def _on_playback_step(self, index, action):
        self.action_tree.highlight_action(action)

    # =====================================================
    # STATE MANAGEMENT
    # =====================================================
    def _update_ui_state(self, recording=None):
        if recording is not None:
            self.recorder.is_recording = recording

        rec = self.recorder.is_recording
        play = self.is_playing

        # === Buttons ===
        self.controls.btn_record.setText("⏹ Stop (F9)" if rec else "⏺ Record (F9)")
        self.controls.btn_play.setText("⏹ Stop (F10)" if play else "▶ Play (F10)")

        # === Lock Tree ===
        locked = rec or play
        self.action_tree.set_edit_lock(locked)

    # =====================================================
    # SAVE / LOAD / AUTOSAVE
    # =====================================================
    def _autoload(self):
        if not os.path.exists(AUTOSAVE_PATH):
            return
        try:
            data = Storage.load(AUTOSAVE_PATH)
            if isinstance(data, list) and data:
                self.action_tree.load_json(data)
        except Exception as e:
            print(f"[AUTOLOAD ERROR] {e}")

    def closeEvent(self, event):
        try:
            data = self.action_tree.to_json()
            Storage.save(AUTOSAVE_PATH, data)
        except Exception as e:
            print(f"[AUTOSAVE ERROR] {e}")
        event.accept()

    def save_macro(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Macro", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            data = self.action_tree.to_json()
            Storage.save(path, data)
        except Exception as e:
            print(f"[SAVE ERROR] {e}")

    def load_macro(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Macro", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            data = Storage.load(path)
            if isinstance(data, list) and data:
                self.action_tree.load_json(data)
        except Exception as e:
            print(f"[LOAD ERROR] {e}")
