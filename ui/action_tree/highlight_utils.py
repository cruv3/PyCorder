# ui/action_tree/highlight_utils.py
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QBrush, QColor
from core.config import COL_TYPE

def highlight_action(tree, model, action: dict, last_highlight_index_ref):
    if not model or not isinstance(action, dict):
        return
    uid = action.get("_uid")
    if not uid:
        return

    idx = _find_index_by_uid(model, uid)
    if not idx or not idx.isValid():
        return
    _clear_previous_brush(model, last_highlight_index_ref)
    _set_row_background(model, idx, QColor(180, 220, 255))
    last_highlight_index_ref[0] = idx
    tree.scrollTo(idx, tree.EnsureVisible)

    tree.setCurrentIndex(idx)

def clear_highlight(tree, model, last_highlight_index_ref):
    _clear_previous_brush(model, last_highlight_index_ref)

def _clear_previous_brush(model, last_ref):
    idx = last_ref[0]
    if idx and idx.isValid():
        _set_row_background(model, idx, None)
    last_ref[0] = None

def _set_row_background(model, idx: QModelIndex, color: QColor = None):
    item = model.itemFromIndex(idx)
    if not item:
        return
    parent = item.parent()
    cols = range(model.columnCount()) if parent is None else range(parent.columnCount())
    brush = QBrush(color) if color else QBrush()
    for c in cols:
        it = (model.item(item.row(), c) if parent is None else parent.child(item.row(), c))
        if it:
            it.setBackground(brush)

def _find_index_by_uid(model, uid: str):
    root = model.invisibleRootItem()
    return _walk_find_uid(root, uid)

def _walk_find_uid(item, uid: str):
    for r in range(item.rowCount()):
        t_item = item.child(r, COL_TYPE)
        if not t_item:
            continue
        kind = t_item.data(Qt.UserRole)
        data = t_item.data(Qt.UserRole + 1)
        if kind == "action" and isinstance(data, dict) and data.get("_uid") == uid:
            col0 = item.child(r, 0)
            return col0.index() if col0 else QModelIndex()
        if kind == "__group__":
            res = _walk_find_uid(item.child(r, 0), uid)
            if res and res.isValid():
                return res
    return QModelIndex()
