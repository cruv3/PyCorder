from PyQt5.QtGui import QStandardItem, QBrush, QColor, QFont
from PyQt5.QtCore import Qt
from core.config import COL_IDX, COL_TYPE


# =====================================================
# BASIC ROW BUILDERS
# =====================================================
def append_action_row(parent, idx: int, act: dict):
    t = act.get("type", "")
    duration_str = f"{act.get('duration', 0.0):.3f}"
    details = ""

    if t in ("move", "drag") and "path" in act:
        path = act["path"]
        if isinstance(path, list):
            details = f"path={path}"
        else:
            details = f"path=[{path}]"
    elif t == "click":
        details = f"x={act.get('x', '?')}, y={act.get('y', '?')}"
    elif t == "key":
        details = f"key={act.get('key', '?')}"
    else:
        details = ", ".join(
            f"{k}={v}"
            for k, v in act.items()
            if k not in ["id", "type", "time", "duration", "screen", "comment"]
        )

    items = [
        QStandardItem(str(idx)),
        QStandardItem(t),
        QStandardItem(duration_str),
        QStandardItem(details),
        QStandardItem(act.get("comment", "")),
    ]

    for c, it in enumerate(items):
        it.setEditable(c != COL_IDX)
    items[COL_TYPE].setData("action", Qt.UserRole)
    items[COL_TYPE].setData(act, Qt.UserRole + 1)

    parent.appendRow(items)

def append_group_row(parent, name="Group", comment=""):
    items = [
        QStandardItem("—"),
        QStandardItem(name),
        QStandardItem(""),
        QStandardItem(""),
        QStandardItem(comment),
    ]
    for it in items:
        it.setFont(QFont("", weight=QFont.Bold))
        it.setBackground(QBrush(QColor(55, 65, 85, 220)))
        it.setEditable(it != items[0])
    items[COL_TYPE].setData("__group__", Qt.UserRole)
    items[COL_TYPE].setData({"name": name, "comment": comment}, Qt.UserRole + 1)
    parent.appendRow(items)
    return items[0].index()

# =====================================================
# DELETE / RENUMBER
# =====================================================

def delete_selected(model, tree):
    sel = sorted(tree.selectionModel().selectedRows(), key=lambda i: (i.parent().row(), i.row()), reverse=True)
    for idx in sel:
        model.removeRow(idx.row(), idx.parent())
    renumber_all(model)


def renumber_all(model):
    count = 1
    root = model.invisibleRootItem()
    def walk(item):
        nonlocal count
        for r in range(item.rowCount()):
            t = item.child(r, COL_TYPE)
            if not t:
                continue
            if t.data(Qt.UserRole) == "__group__":
                walk(item.child(r, 0))
            elif t.data(Qt.UserRole) == "action":
                item.child(r, COL_IDX).setText(str(count))
                count += 1
    walk(root)


# =====================================================
# SERIALIZATION
# =====================================================

def serialize_item_recursive(model, idx):
    type_idx = idx.sibling(idx.row(), COL_TYPE)
    kind = type_idx.data(Qt.UserRole)
    data = type_idx.data(Qt.UserRole + 1)
    node = {"kind": kind, "data": data, "children": []}

    if kind == "__group__":
        item = model.itemFromIndex(idx)
        for r in range(item.rowCount()):
            child_idx = item.child(r, 0).index()
            node["children"].append(serialize_item_recursive(model, child_idx))

    return node


def insert_node_recursive(parent, insert_row, node):
        kind = node["kind"]
        data = node["data"]

        if kind == "action":
            if not isinstance(data, dict) or not data.get("type"):
                return
            
            details = ", ".join([f"{k}={v}" for k, v in data.items() if k not in ["type", "duration"]])
            time_str = f'{data.get("duration", 0.0):.3f}'
            row_items = [
                QStandardItem(""),
                QStandardItem(data.get("type", "")),
                QStandardItem(time_str),
                QStandardItem(details),
                QStandardItem(data.get("comment", "")),
            ]
            for c, it in enumerate(row_items):
                if c == COL_IDX:
                    it.setEditable(False)
                    it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    it.setEditable(True)
                it.setFlags((it.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)

            row_items[COL_TYPE].setData("action", Qt.UserRole)
            row_items[COL_TYPE].setData(data, Qt.UserRole + 1)
            parent.insertRow(insert_row, row_items)

        elif kind == "__group__":
            group_items = [
                QStandardItem("—"),
                QStandardItem(data.get("name", "Group Copy")),
                QStandardItem(""),
                QStandardItem(""),
                QStandardItem(data.get("comment", "")),
            ]

            for it in group_items:
                it.setEditable(it != group_items[0])
                it.setFont(QFont("", weight=QFont.Bold))
                it.setBackground(QBrush(QColor(55, 65, 85, 220)))

            group_items[COL_TYPE].setData("__group__", Qt.UserRole)
            group_items[COL_TYPE].setData(data, Qt.UserRole + 1)

            parent.insertRow(insert_row, group_items)

            group_item = parent.child(insert_row)
            for i, child in enumerate(node.get("children", [])):
                insert_node_recursive(group_item, i, child)