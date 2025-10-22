from PyQt5.QtWidgets import QWidget, QVBoxLayout, QAbstractItemView
from PyQt5.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt5.QtGui import QStandardItemModel
import uuid

from ui.action_tree.context_menu import ContextMenuHandler
from ui.action_tree.model_utils import append_action_row, renumber_all
from ui.action_tree.json_io import export_to_json, import_from_json
from ui.action_tree.highlight_utils import clear_highlight, highlight_action
from ui.components.overlay import Overlay
from ui.components.dnd_qtree_view import DnDQTreeView
from core.config import COL_IDX, COL_TYPE, COL_TIME, COL_DETAILS, COL_COMMENT


class ActionTreeEditor(QWidget):
    # Dieses Signal wird im MainWindow verwendet
    play_request = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = DnDQTreeView(after_move_callback=lambda: renumber_all(self.model))
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(24)
        self.tree.setAnimated(True)
        self.tree.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setDragDropOverwriteMode(False)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.tree)

        self.model = QStandardItemModel(0, 5, self)
        self.model.setHorizontalHeaderLabels(["#", "Type / Group", "Time (s)", "Details", "Comment"])
        self.tree.setModel(self.model)
        self.tree.setColumnWidth(COL_IDX, 100)
        self.tree.setColumnWidth(COL_TYPE, 180)
        self.tree.setColumnWidth(COL_TIME, 100)
        self.tree.setColumnWidth(COL_DETAILS, 300)

        self.overlay = Overlay()
        self.tree.clicked.connect(self._on_tree_clicked)

        # Context Menu Handler
        self.context_menu = ContextMenuHandler(
            tree=self.tree,
            model=self.model,
            play_callback=self.play_request.emit
        )
        self.tree.customContextMenuRequested.connect(self.context_menu.open)

        self.tree.keyPressEvent = self._on_key_press

        self._updating_model = False
        self.model.itemChanged.connect(self._on_item_changed)

        self.last_highlight_index = [None]

    def add_action(self, action: dict):
        if "_uid" not in action or not action["_uid"]:
            action["_uid"] = str(uuid.uuid4())
        append_action_row(self.model, self.model.rowCount() + 1, action)
        self.cleanup_empty_items()
        renumber_all(self.model)

    def clear(self):
        self.model.removeRows(0, self.model.rowCount())

    def to_json(self):
        return export_to_json(self.model)

    def load_json(self, data):
        import_from_json(self.model, data)
        renumber_all(self.model)

    def set_edit_lock(self, locked: bool):
        self.tree.setDragEnabled(not locked)
        self.tree.setAcceptDrops(not locked)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers if locked else QAbstractItemView.DoubleClicked)
        self.tree.setContextMenuPolicy(Qt.NoContextMenu if locked else Qt.CustomContextMenu)
    
    def highlight_action(self, action):
        highlight_action(self.tree, self.model, action, self.last_highlight_index)
        
    def clear_highlight(self):
        clear_highlight(self.tree, self.model, self.last_highlight_index)

    def _on_tree_clicked(self, idx: QModelIndex):
        if not idx.isValid():
            return
        t_idx = idx.sibling(idx.row(), COL_TYPE)
        if t_idx.data(Qt.UserRole) != "action":
            self.overlay.hide()
            return
        act = t_idx.data(Qt.UserRole + 1) or {}
        try:
            t = act.get("type")
            if t == "move" and "path" in act:
                self.overlay.show_move(act["path"], act.get("screen", "Unknown"))
            elif t == "click":
                self.overlay.show_click(act.get("x", 0), act.get("y", 0), act.get("screen", "Unknown"))
            elif t == "drag" and "path" in act:
                self.overlay.show_drag(act["path"], act.get("screen", "Unknown"))
            else:
                self.overlay.hide()
        except Exception as e:
            print(f"[Overlay Error]: {e}")
            self.overlay.hide()

    def _on_key_press(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            from ui.action_tree.model_utils import delete_selected
            delete_selected(self.model, self.tree)
            return
        super(DnDQTreeView, self.tree).keyPressEvent(event)
    
    def get_all_actions(self):
        actions = []

        def recurse(item, depth=0):
            prefix = "  " * depth
            for row in range(item.rowCount()):
                type_item = item.child(row, COL_TYPE)
                if not type_item:
                    continue

                kind = type_item.data(Qt.UserRole)
                data = type_item.data(Qt.UserRole + 1)

                if kind == "__group__":
                    group_item = item.child(row, 0)
                    recurse(group_item, depth + 1)

                elif kind == "action":
                    if isinstance(data, dict):
                        actions.append(data)
                    else:
                        print(f"{prefix}  [WARN] Invalid action data type: {type(data)}")
                else:
                    print(f"{prefix}  [WARN] Unknown kind: {kind}")


        root = self.model.invisibleRootItem()
        recurse(root)
        return actions
        
    def get_action_index_from_model_index(self, model_index):
        def recurse(item):
            nonlocal_count = {"i": -1} 

            def walk(subitem):
                for r in range(subitem.rowCount()):
                    t_item = subitem.child(r, COL_TYPE)
                    if not t_item:
                        continue
                    kind = t_item.data(Qt.UserRole)
                    if kind == "__group__":
                        result = walk(subitem.child(r, 0))
                        if result is not None:
                            return result
                    elif kind == "action":
                        nonlocal_count["i"] += 1
                        if t_item.index() == model_index.sibling(model_index.row(), COL_TYPE):
                            return nonlocal_count["i"]
                return None

            return walk(item)

        kind = model_index.sibling(model_index.row(), COL_TYPE).data(Qt.UserRole)
        print(kind)

        if kind == "__group__":
            group_item = self.model.itemFromIndex(model_index.sibling(model_index.row(), 0))
            if not group_item:
                return 0
            if group_item.rowCount() == 0:
                return 0
            first_child = group_item.child(0, COL_TYPE)
            if not first_child:
                return 0
            return self.get_action_index_from_model_index(first_child.index())

        result = recurse(self.model.invisibleRootItem())
        return result if result is not None else 0

        
    def get_all_action_indices(self):
        indices = []

        def recurse(item):
            for r in range(item.rowCount()):
                t = item.child(r, COL_TYPE)
                if not t:
                    continue
                kind = t.data(Qt.UserRole)
                if kind == "__group__":
                    recurse(item.child(r, 0))
                elif kind == "action":
                    col0 = item.child(r, 0)
                    if col0:
                        indices.append(col0.index())

        recurse(self.model.invisibleRootItem())
        return indices
    
    def cleanup_empty_items(self):
        def recurse(item):
            to_delete = []
            for r in range(item.rowCount()):
                type_item = item.child(r, COL_TYPE)
                if not type_item:
                    to_delete.append(r)
                    continue

                kind = type_item.data(Qt.UserRole)
                data = type_item.data(Qt.UserRole + 1)

                if kind == "__group__":
                    group_item = item.child(r, 0)
                    recurse(group_item)
                    if group_item.rowCount() == 0:
                        to_delete.append(r)

                elif kind == "action":
                    if not isinstance(data, dict) or len(data) == 0:
                        to_delete.append(r)

            for r in reversed(to_delete):
                item.removeRow(r)

        recurse(self.model.invisibleRootItem())

    def _format_details(self, act: dict) -> str:
        t = act.get("type", "")
        if t in ("move", "drag") and "path" in act:
            return f"path={act.get('path', [])}"
        elif t == "click":
            return f"x={act.get('x', '?')}, y={act.get('y', '?')}"
        elif t == "key":
            return f"key={act.get('key', '?')}"
        else:
            hide = {"id", "type", "time", "duration", "screen", "comment"}
            return ", ".join(f"{k}={v}" for k, v in act.items() if k not in hide)

    def _parse_click_details(self, text: str) -> dict:
        out = {}
        for part in text.split(","):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if k in ("x", "y"):
                try:
                    out[k] = int(float(v))
                except ValueError:
                    pass
        return out

    def _parse_path_details(self, text: str):
        import ast
        text = text.strip()
        if text.startswith("path="):
            text = text[len("path="):].strip()
        try:
            val = ast.literal_eval(text)
            cleaned = []
            if isinstance(val, (list, tuple)):
                for p in val:
                    if (isinstance(p, (list, tuple)) and len(p) == 2 and
                        all(isinstance(n, (int, float)) for n in p)):
                        cleaned.append((int(p[0]), int(p[1])))
            return cleaned if cleaned else None
        except Exception:
            return None

    def _on_item_changed(self, item):
        if self._updating_model:
            return

        col = item.column()
        row = item.row()

        type_idx = item.index().sibling(row, COL_TYPE)
        kind = type_idx.data(Qt.UserRole)
        if kind != "action":
            return

        act = type_idx.data(Qt.UserRole + 1) or {}
        t = act.get("type", "")

        try:
            self._updating_model = True

            if col == COL_DETAILS:
                text = item.text()
                if t == "click":
                    upd = self._parse_click_details(text)
                    act.update(upd)
                elif t in ("move", "drag"):
                    path = self._parse_path_details(text)
                    if path is not None and len(path) >= 2:
                        act["path"] = path

                item.setText(self._format_details(act))

            elif col == COL_TIME:
                try:
                    act["time"] = float(item.text().strip())
                except ValueError:
                    pass

            elif col == COL_COMMENT:
                act["comment"] = item.text()

            type_idx.model().setData(type_idx, act, Qt.UserRole + 1)

        finally:
            self._updating_model = False

        if self.tree.selectionModel().isSelected(item.index().sibling(row, 0)):
            self._on_tree_clicked(item.index())