import uuid
from PyQt5.QtCore import Qt
from core.config import COL_TYPE
from ui.action_tree.model_utils import append_action_row, append_group_row


def export_to_json(model):
    root = model.invisibleRootItem()

    def serialize(item):
        nodes = []
        for r in range(item.rowCount()):
            type_item = item.child(r, COL_TYPE)
            if not type_item:
                continue
            kind = type_item.data(Qt.UserRole)
            data = type_item.data(Qt.UserRole + 1)

            if kind == "__group__":
                nodes.append({
                    "kind": "__group__",
                    "data": data,
                    "children": serialize(item.child(r, 0))
                })
            elif kind == "action":
                if isinstance(data, dict) and "_uid" not in data:
                    data["_uid"] = str(uuid.uuid4())
                nodes.append({
                    "kind": "action",
                    "data": data
                })
        return nodes

    return serialize(root)


def import_from_json(model, data):
    model.removeRows(0, model.rowCount())

    def insert(parent, node):
        kind = node.get("kind")
        data = node.get("data", {}) or {}

        if kind == "action":
            if "_uid" not in data:
                data["_uid"] = str(uuid.uuid4())
            append_action_row(parent, parent.rowCount() + 1, data)

        elif kind == "__group__":
            grp_idx = append_group_row(parent, data.get("name", "Group"), data.get("comment", ""))
            g_item = model.itemFromIndex(grp_idx)
            for c in node.get("children", []):
                insert(g_item, c)

    for n in data:
        insert(model, n)
