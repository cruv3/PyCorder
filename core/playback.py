from PyQt5.QtCore import QObject, pyqtSignal
import time
from threading import Thread
from pynput import mouse, keyboard


class Playback(QObject):
    """Handles playback of recorded mouse and keyboard actions."""

    step_signal = pyqtSignal(int, dict)
    done_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.stop_flag = False

    # =====================================================
    # Public API
    # =====================================================
    def play(self, actions, speed: float = 1.0, repeat: int = 1, on_done=None):
        """Start playing the provided action list in a background thread."""
        self.stop_flag = False
        Thread(
            target=self._run,
            args=(actions, speed, repeat, on_done),
            daemon=True,
        ).start()

    def stop(self):
        """Stop playback immediately."""
        self.stop_flag = True

    # =====================================================
    # Core logic
    # =====================================================
    def _run(self, actions, speed, repeat, on_done):
        m_ctrl = mouse.Controller()
        k_ctrl = keyboard.Controller()

        try:
            total = len(actions)
            for loop in range(repeat if repeat > 0 else 1_000_000_000):
                if self.stop_flag:
                    break

                for i, act in enumerate(actions):
                    if self.stop_flag:
                        return
                    if not isinstance(act, dict):
                        continue

                    action_type = act.get("type", "?")
                    self.step_signal.emit(i, act)

                    try:
                        if action_type == "move":
                            self._handle_move(m_ctrl, act, speed)
                        elif action_type == "drag":
                            self._handle_drag(m_ctrl, act, speed)
                        elif action_type == "click":
                            self._handle_click(m_ctrl, act)
                        elif action_type == "key":
                            self._handle_key(k_ctrl, act)
                        else:
                            # Unknown action type – ignore
                            continue
                    except Exception as e:
                        print(f"[PLAYBACK ERROR] {action_type} at step {i}: {e}")

                    time.sleep(0.02)

                # Small pause between loops (optional)
                time.sleep(0.02)

        finally:
            self.done_signal.emit()
            if on_done:
                on_done()

    # =====================================================
    # Handlers
    # =====================================================
    def _handle_move(self, m_ctrl, act, speed):
        path = act.get("path")
        if isinstance(path, list) and len(path) >= 2:
            duration = float(act.get("duration", 0.0)) / max(speed, 1e-6)
            self._play_path(m_ctrl, path, duration, speed)

    def _handle_drag(self, m_ctrl, act, speed):
        btn_name = str(act.get("button", "left")).split(".")[-1]
        btn = getattr(mouse.Button, btn_name, mouse.Button.left)
        path = act.get("path", [])
        duration = float(act.get("duration", 0.0)) / max(speed, 1e-6)
        self._play_drag(m_ctrl, btn, path, duration, speed)

    def _handle_click(self, m_ctrl, act):
        btn_name = str(act.get("button", "left")).split(".")[-1]
        btn = getattr(mouse.Button, btn_name, mouse.Button.left)
        x, y = int(act.get("x", 0)), int(act.get("y", 0))
        m_ctrl.position = (x, y)
        m_ctrl.click(btn)

    def _handle_key(self, k_ctrl, act):
        key = act.get("key")
        if not key:
            return
        try:
            k_ctrl.press(key)
            k_ctrl.release(key)
        except Exception:
            pass

    # =====================================================
    # Helpers
    # =====================================================
    def _interpolate_path(self, path, steps):
        """Smoothly interpolate a movement path."""
        n = len(path)
        if n < 2:
            return path

        res = []
        for i in range(steps):
            t = i / (steps - 1)
            t_eased = 3 * t**2 - 2 * t**3
            idx = int(t_eased * (n - 1))
            res.append(path[idx])
        return res

    def _play_path(self, m_ctrl, path, duration, speed):
        if len(path) < 2:
            return

        path = self._interpolate_path(path, len(path))
        per_step = max(duration / max(len(path) - 1, 1), 0.001 / speed)

        start = time.perf_counter()
        for i, (x, y) in enumerate(path):
            if self.stop_flag:
                return
            m_ctrl.position = (int(x), int(y))
            target = start + i * per_step
            while time.perf_counter() < target:
                time.sleep(0.0005)

        m_ctrl.position = (int(path[-1][0]), int(path[-1][1]))


    def _play_drag(self, m_ctrl, btn, path, duration, speed):
        if len(path) < 2:
            return

        path = self._interpolate_path(path, len(path))
        per_step = max(duration / max(len(path) - 1, 1), 0.005 / speed)

        m_ctrl.position = path[0]
        m_ctrl.press(btn)
        time.sleep(0.015)

        start = time.perf_counter()
        for i, (x, y) in enumerate(path[1:], start=1):
            if self.stop_flag:
                m_ctrl.release(btn)
                return
            m_ctrl.position = (int(x), int(y))
            target_time = start + i * per_step
            while time.perf_counter() < target_time:
                time.sleep(0.0005)

        time.sleep(0.010)
        m_ctrl.release(btn)