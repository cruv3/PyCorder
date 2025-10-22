import time
import uuid
from pynput import mouse, keyboard
from threading import Thread, Event
from core.screen_fetcher import ScreenFetcher


class Recorder:
    """Captures mouse and keyboard actions using pynput (no root required)."""

    def __init__(self, on_action=None, ignore_keys=None):
        self.on_action = on_action
        self.ignore_keys = ignore_keys or []
        self.is_recording = False
        self.actions = []
        self.screen_fetcher = ScreenFetcher()

        self._last_move_time = None
        self._move_buffer = None
        self._pause_threshold = 0.3
        self._stop_event = Event()
        self._move_tolerance = 3
        self._key_press_times = {}

        # listeners
        self.mouse_listener = None
        self.keyboard_listener = None
        self.flush_thread = None

    # =====================================================
    # Recording control
    # =====================================================
    def start(self):
        if self.is_recording:
            return

        self.is_recording = True
        self.actions = []
        self._stop_event.clear()
        self._last_move_time = None
        self._move_buffer = None

        # mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click
        )
        self.mouse_listener.start()

        # keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()

        # background thread to flush buffered moves
        self.flush_thread = Thread(target=self._auto_flush, daemon=True)
        self.flush_thread.start()

    def stop(self):
        """Stop recording cleanly and flush pending data."""
        if not self.is_recording:
            return self.actions

        self.is_recording = False
        self._stop_event.set()

        for listener in (self.mouse_listener, self.keyboard_listener):
            try:
                if listener:
                    listener.stop()
            except Exception:
                pass

        for listener in (self.mouse_listener, self.keyboard_listener):
            try:
                if listener and getattr(listener, "_thread", None):
                    listener._thread.join(timeout=0.5)
            except Exception:
                pass

        self.mouse_listener = None
        self.keyboard_listener = None

        if self.flush_thread and self.flush_thread.is_alive():
            self.flush_thread.join(timeout=0.5)
        self.flush_thread = None

        self._move_buffer = None
        self._flush_move()
        self._is_dragging = False
        self._drag_path = []

        return self.actions

    def _emit(self, act: dict):
        """Central emit method (appends + forwards)."""
        # Ensure every action has a duration
        if "duration" not in act:
            act["duration"] = 0.0
        self.actions.append(act)
        if self.on_action:
            self.on_action(act)

    # =====================================================
    # Mouse move and drag detection
    # =====================================================
    def _on_move(self, x, y):
        if not self.is_recording:
            return

        now = time.time()
        screen_name = self.screen_fetcher.get_name(x, y)

        # handle drag in progress
        if getattr(self, "_is_dragging", False):
            self._drag_path.append((x, y))
            self._last_move_time = now
            return

        if not self._move_buffer:
            self._move_buffer = {
                "type": "move",
                "path": [(x, y)],
                "time_start": now,
                "screen": screen_name
            }
            self._last_move_time = now
            return

        if now - self._last_move_time <= self._pause_threshold and screen_name == self._move_buffer["screen"]:
            self._move_buffer["path"].append((x, y))
            self._last_move_time = now
        else:
            self._flush_move()
            self._move_buffer = {
                "type": "move",
                "path": [(x, y)],
                "time_start": now,
                "screen": screen_name
            }
            self._last_move_time = now

    def _flush_move(self):
        """Flush a completed move path."""
        if not self._move_buffer or len(self._move_buffer["path"]) < 2:
            self._move_buffer = None
            return

        now = time.time()
        dur = round(now - self._move_buffer["time_start"], 3)
        act = {
            "id": str(uuid.uuid4()),
            "type": "move",
            "path": self._move_buffer["path"],
            "duration": dur,
            "screen": self._move_buffer["screen"]
        }
        self._emit(act)
        self._move_buffer = None

    def _auto_flush(self):
        while not self._stop_event.is_set():
            time.sleep(0.1)
            if self._move_buffer and self._last_move_time:
                if time.time() - self._last_move_time > self._pause_threshold:
                    self._flush_move()

    # =====================================================
    # Clicks and drags
    # =====================================================
    def _on_click(self, x, y, button, pressed):
        if not self.is_recording:
            return

        now = time.time()
        screen_name = self.screen_fetcher.get_name(x, y)
        self._flush_move()

        if pressed:
            self._is_dragging = True
            self._drag_start = (x, y)
            self._drag_path = [(x, y)]
            self._drag_button = str(button)
            self._drag_screen = screen_name
            self._drag_time_start = now
        else:
            if getattr(self, "_is_dragging", False):
                dur = round(now - self._drag_time_start, 3)
                dx, dy = self._drag_start
                ex, ey = x, y

                # drag or click
                if len(self._drag_path) > 1 and (abs(dx - ex) > 2 or abs(dy - ey) > 2):
                    act = {
                        "id": str(uuid.uuid4()),
                        "type": "drag",
                        "button": self._drag_button,
                        "path": self._drag_path,
                        "duration": dur,
                        "screen": self._drag_screen
                    }
                else:
                    act = {
                        "id": str(uuid.uuid4()),
                        "type": "click",
                        "button": self._drag_button,
                        "x": x,
                        "y": y,
                        "duration": dur,
                        "screen": self._drag_screen
                    }
                self._emit(act)

            self._is_dragging = False
            self._drag_path = []

    # =====================================================
    # Keyboard
    # =====================================================
    def _on_key_press(self, key):
        if not self.is_recording:
            return

        try:
            name = self._normalize_key(key)
            if name in self.ignore_keys:
                return

            # Wenn Taste schon gedrückt, ignorieren (repeats)
            if name not in self._key_press_times:
                self._key_press_times[name] = time.perf_counter()
        except Exception as e:
            print(f"[WARN] key press parse error: {e}")

    def _on_key_release(self, key):
        if not self.is_recording:
            return

        try:
            name = self._normalize_key(key)
            if name in self.ignore_keys:
                return

            press_time = self._key_press_times.pop(name, None)
            if press_time:
                dur = round(time.perf_counter() - press_time, 3)
            else:
                dur = 0.0

            act = {
                "id": str(uuid.uuid4()),
                "type": "key",
                "key": name,
                "duration": dur
            }
            self._emit(act)

        except Exception as e:
            print(f"[WARN] key release parse error: {e}")

    def _normalize_key(self, key):
        """Convert pynput key to string."""
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        elif hasattr(key, "name"):
            return key.name.lower()
        else:
            return str(key).replace("Key.", "").lower()
