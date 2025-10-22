from PyQt5.QtWidgets import QMenu, QInputDialog, QLineEdit
from PyQt5.QtCore import Qt, QModelIndex
from core.config import COL_TYPE
from ui.action_tree.model_utils import (
    serialize_item_recursive, insert_node_recursive, delete_selected,
    append_action_row, renumber_all, append_group_row
)


class ContextMenuHandler:
    """Handles right-click context menus for actions and groups."""

    def __init__(self, tree, model, play_callback, overlay_callback=None):
        self.tree = tree
        self.model = model
        self.play_callback = play_callback
        self.overlay_callback = overlay_callback
        self.clipboard_data = []

    def open(self, pos):
        """Open context menu at mouse position."""
        idx = self.tree.indexAt(pos)
        if not idx.isValid():
            return
        kind = idx.sibling(idx.row(), COL_TYPE).data(Qt.UserRole)
        menu = QMenu(self.tree)
        if kind == "action":
            self._build_action_menu(menu, idx)
        elif kind == "__group__":
            self._build_group_menu(menu, idx)

    # ============================================================
    # MENUS
    # ============================================================
    def _build_action_menu(self, menu, idx):
        """Build context menu for action items."""
        copy = menu.addAction("📋 Copy")
        paste = menu.addAction("📥 Paste below")
        delete = menu.addAction("🗑 Delete")
        group_sel = menu.addAction("📦 Group selected")
        menu.addSeparator()
        play = menu.addAction("▶ Play from here")

        act = menu.exec_(self.tree.mapToGlobal(pos := self.tree.viewport().mapFromGlobal(self.tree.cursor().pos())))
        if not act:
            return
        if act == copy:
            self.copy_selected()
        elif act == paste:
            self.paste_below(idx)
        elif act == delete:
            self.delete_selected()
        elif act == group_sel:
            self.group_selected()
        elif act == play:
            actions = self._collect_actions_from_index(idx)
            if actions:
                self.play_callback((actions, idx))

    def _build_group_menu(self, menu, idx):
        """Build context menu for group items."""
        copy = menu.addAction("📋 Copy group")
        paste = menu.addAction("📥 Paste below")
        ungroup = menu.addAction("🧩 Ungroup")
        delete = menu.addAction("🗑 Delete group")
        menu.addSeparator()
        play_group = menu.addAction("🎬 Play group only")

        act = menu.exec_(self.tree.mapToGlobal(pos := self.tree.viewport().mapFromGlobal(self.tree.cursor().pos())))
        if not act:
            return
        if act == copy:
            self.copy_selected()
        elif act == paste:
            self.paste_below(idx)
        elif act == ungroup:
            self.ungroup(idx)
        elif act == delete:
            self.delete_selected()
        elif act == play_group:
            actions = self._collect_group_actions(idx)
            if actions:
                self.play_callback((actions, idx))

    # ============================================================
    # ACTION LOGIC
    # ============================================================
    def copy_selected(self):
        """Copy selected tree rows to internal clipboard."""
        sel = self.tree.selectionModel().selectedRows()
        if not sel:
            return
        self.clipboard_data = [serialize_item_recursive(self.model, i) for i in sel]

    def paste_below(self, idx: QModelIndex):
        """Paste clipboard content below the given index."""
        if not self.clipboard_data or not self.model:
            return
        drop_idx = idx
        if not drop_idx.isValid():
            return
        target_kind = drop_idx.sibling(drop_idx.row(), COL_TYPE).data(Qt.UserRole)
        target_parent = drop_idx.parent()
        parent_item = (
            self.model.itemFromIndex(target_parent)
            if target_parent.isValid()
            else self.model.invisibleRootItem()
        )
        insert_row = drop_idx.row() + 1
        inside_group = (
            target_kind != "__group__"
            and target_parent.isValid()
            and target_parent.sibling(target_parent.row(), COL_TYPE).data(Qt.UserRole) == "__group__"
        )
        for node in reversed(self.clipboard_data):
            kind = node.get("kind")
            if kind == "__group__" and inside_group:
                print("[WARN] Cannot paste a group inside another group.")
                continue
            insert_node_recursive(parent_item, insert_row, node)
            insert_row += 1
        renumber_all(self.model)

    def delete_selected(self):
        """Delete all selected items."""
        delete_selected(self.model, self.tree)

    def group_selected(self):
        sel = self.tree.selectionModel().selectedRows()
        if not sel:
            return
        # verschachtelte Gruppen verhindern (wie gehabt)
        for idx in sel:
            parent = idx.parent()
            if parent.isValid():
                parent_type = parent.sibling(parent.row(), COL_TYPE).data(Qt.UserRole)
                if parent_type == "__group__":
                    print("[WARN] Nested grouping not allowed.")
                    return

        name, ok = QInputDialog.getText(
            self.tree, "Create Group", "Group name:", QLineEdit.Normal,
            f"Group {self.model.rowCount()+1}"
        )
        if not ok or not name.strip():
            return

        insert_row = sel[0].row()
        group_idx = append_group_row(self.model, name=name, comment="")
        if group_idx.row() != insert_row:
            row_items = self.model.takeRow(group_idx.row())
            self.model.insertRow(insert_row, row_items)
        group_idx = self.model.index(insert_row, 0)
        group_item = self.model.itemFromIndex(group_idx)

        # ---- stabile Reihenfolge: nach Zeile sortieren (aufsteigend)
        action_rows = []
        for idx in self.tree.selectionModel().selectedRows():
            type_idx = idx.sibling(idx.row(), COL_TYPE)
            if type_idx.data(Qt.UserRole) == "action":
                action_rows.append(idx.sibling(idx.row(), 0))
        action_rows.sort(key=lambda i: (i.parent().row(), i.row()))

        # Snapshot von (parent_item, row), damit Index-Shift uns nicht zerstört
        snapshot = []
        for i in action_rows:
            p = i.parent()
            parent_item = self.model.itemFromIndex(p) if p.isValid() else self.model.invisibleRootItem()
            snapshot.append((parent_item, i.row()))

        # jetzt in Original-Reihenfolge verschieben, Row-Shift kompensieren
        moved_per_parent = {}
        for parent_item, original_row in snapshot:
            moved = moved_per_parent.get(id(parent_item), 0)
            row_items = parent_item.takeRow(original_row - moved)
            if row_items:
                group_item.appendRow(row_items)
                moved_per_parent[id(parent_item)] = moved + 1

        renumber_all(self.model)
        self.tree.expand(group_item.index())

        # Cleanup gegen leere Reste
        try:
            from ui.action_tree.editor import ActionTreeEditor
            if isinstance(self.tree.parentWidget(), ActionTreeEditor):
                self.tree.parentWidget().cleanup_empty_items()
        except Exception:
            pass
        
    def ungroup(self, group_idx):
        """Ungroup a group node and move its children one level up."""
        group_item = self.model.itemFromIndex(group_idx.sibling(group_idx.row(), 0))
        if not group_item:
            print("[ERROR] Ungroup failed: no valid group item.")
            return

        parent_index = group_idx.parent()
        parent_item = (
            self.model.itemFromIndex(parent_index)
            if parent_index.isValid()
            else self.model.invisibleRootItem()
        )

        insert_pos = group_item.row() + 1
        moved = 0

        # move all children to one level above
        for _ in range(group_item.rowCount()):
            child_row = group_item.takeRow(0)
            if child_row:
                parent_item.insertRow(insert_pos, child_row)
                insert_pos += 1
                moved += 1

        # remove the now-empty group row
        parent_item.removeRow(group_item.row())
        renumber_all(self.model)


    # ============================================================
    # PLAY LOGIC HELPERS
    # ============================================================
    def _collect_actions_from_index(self, idx):
        """Collect all actions from a given index onward."""
        actions, found = [], False
        def recurse(item):
            nonlocal found
            for r in range(item.rowCount()):
                t = item.child(r, COL_TYPE)
                if not t:
                    continue
                kind = t.data(Qt.UserRole)
                if kind == "__group__":
                    recurse(item.child(r, 0))
                elif kind == "action":
                    if not found and t.index() == idx.sibling(idx.row(), COL_TYPE):
                        found = True
                    if found:
                        actions.append(t.data(Qt.UserRole + 1))
        recurse(self.model.invisibleRootItem())
        actions = [a for a in actions if isinstance(a, dict) and a.get("type")]
        return actions

    def _collect_group_actions(self, group_idx):
        """Collect all actions inside a group (recursive)."""
        actions = []
        group_idx = group_idx.sibling(group_idx.row(), 0)
        group_item = self.model.itemFromIndex(group_idx)
        if not group_item:
            print("[ERROR] Invalid group index (no item found).")
            return actions
        def recurse(item, depth=0):
            for r in range(item.rowCount()):
                type_item = item.child(r, 1)
                if not type_item:
                    continue
                kind = type_item.data(Qt.UserRole)
                data = type_item.data(Qt.UserRole + 1)
                if kind == "action" and isinstance(data, dict):
                    actions.append(data)
                elif kind == "__group__":
                    recurse(item.child(r, 0), depth + 1)
        recurse(group_item)
        actions = [a for a in actions if isinstance(a, dict) and a.get("type")]
        return actions

    def _selected_action_rows_as_model_rows(self):
        """Return selected rows that represent actions (no duplicates)."""
        sel_rows = []
        for idx in self.tree.selectionModel().selectedRows():
            type_idx = idx.sibling(idx.row(), COL_TYPE)
            if type_idx.data(Qt.UserRole) == "action":
                sel_rows.append(idx.sibling(idx.row(), 0))
        unique, seen = [], set()
        for i in sel_rows:
            key = (i.row(), i.parent().row())
            if key not in seen:
                unique.append(i)
                seen.add(key)
        return unique
