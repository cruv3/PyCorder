from PyQt5.QtWidgets import QTreeView, QAbstractItemView
from PyQt5.QtGui import QPainter, QPen, QColor, QDrag, QPixmap
from PyQt5.QtCore import Qt, QRect

COL_TYPE = 1


class DnDQTreeView(QTreeView):
    def __init__(self, after_move_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.after_move_callback = after_move_callback
        self._drag_rows = None
        self._drop_indicator_rect = None
        self._drop_target = None

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(False)  # wir malen selbst
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================
    def startDrag(self, supportedActions):
        rows = [(idx.parent(), idx.row()) for idx in self.selectionModel().selectedRows(0)]
        rows.sort(key=lambda t: (t[0].row(), t[1]), reverse=True)
        self._drag_rows = rows

        # --- Statt Standard-Pixmaps: transparentes Pixmap ---
        drag = QDrag(self)
        mime = self.model().mimeData(self.selectionModel().selectedRows())
        drag.setMimeData(mime)

        # Transparentes 1×1-Pixel-Pixmap → unsichtbar
        transparent_pixmap = QPixmap(1, 1)
        transparent_pixmap.fill(Qt.transparent)
        drag.setPixmap(transparent_pixmap)

        drag.exec_(Qt.MoveAction)

    def _get_kind(self, idx):
        if not idx.isValid():
            return None
        type_idx = idx.sibling(idx.row(), COL_TYPE)
        return type_idx.data(Qt.UserRole)

    def _is_descendant(self, potential_child, potential_parent):
        if not potential_child.isValid():
            return False
        parent = potential_child.parent()
        while parent.isValid():
            if parent == potential_parent:
                return True
            parent = parent.parent()
        return False

    # ============================================================
    # DROP TARGET LOGIC
    # ============================================================
    def _compute_drop_target(self, event):
        model = self.model()
        idx = self.indexAt(event.pos())

        if not idx.isValid():
            parent_item = model.invisibleRootItem()
            return parent_item, parent_item.rowCount(), None, "viewport"

        target_kind = self._get_kind(idx)
        rect: QRect = self.visualRect(idx)
        mouse_y = event.pos().y()
        top_half = mouse_y < (rect.top() + rect.height() // 2)

        # „Into“ nur bei Gruppen sinnvoll
        if target_kind == "__group__" and not top_half and mouse_y < rect.bottom():
            parent_item = model.itemFromIndex(idx.sibling(idx.row(), 0))
            insert_row = parent_item.rowCount()
            return parent_item, insert_row, target_kind, "into"

        parent_item_0 = model.itemFromIndex(idx.sibling(idx.row(), 0))
        parent_item = parent_item_0.parent() or model.invisibleRootItem()
        insert_row = idx.row() if top_half else idx.row() + 1
        return parent_item, insert_row, target_kind, ("above" if top_half else "below")

    # ============================================================
    # DRAG MOVE / DROP EVENTS
    # ============================================================
    def dragMoveEvent(self, event):
        model = self.model()
        if not model or not self._drag_rows:
            event.ignore()
            return

        parent_item, insert_row, target_kind, mode = self._compute_drop_target(event)
        self._drop_target = (parent_item, insert_row, target_kind, mode)

        # Position für Linie merken
        idx = self.indexAt(event.pos())
        if idx.isValid():
            rect = self.visualRect(idx)
            y = rect.top() if mode == "above" else rect.bottom()
            self._drop_indicator_rect = QRect(rect.left(), y - 1, rect.width(), 2)
        else:
            self._drop_indicator_rect = None

        self.viewport().update()
        event.acceptProposedAction()

    def dropEvent(self, event):
        model = self.model()
        if model is None or not self._drag_rows or not self._drop_target:
            event.ignore()
            return

        parent_item, insert_row, target_kind, mode = self._drop_target
        self._drop_indicator_rect = None
        self.viewport().update()

        # Gruppen-Logik prüfen
        def find_src_kind():
            for parent_idx, row in self._drag_rows:
                src_parent_item = model.itemFromIndex(parent_idx) if parent_idx.isValid() else model.invisibleRootItem()
                src_row_item = src_parent_item.child(row, 0)
                if src_row_item:
                    return self._get_kind(src_row_item.index())
            return None

        src_kind = find_src_kind()
        if src_kind == "__group__" and target_kind == "__group__" and mode == "into":
            event.ignore()
            return

        drop_idx = self.indexAt(event.pos())
        if drop_idx.isValid():
            for parent_idx, row in self._drag_rows:
                src_parent_item = model.itemFromIndex(parent_idx) if parent_idx.isValid() else model.invisibleRootItem()
                src_row_item = src_parent_item.child(row, 0)
                if src_row_item and self._is_descendant(drop_idx, src_row_item.index()):
                    event.ignore()
                    return

        # tatsächlicher Move
        rows_to_move = sorted(self._drag_rows, key=lambda t: (t[0].row(), t[1]), reverse=True)
        for p_idx, row in rows_to_move:
            src_parent_item = model.itemFromIndex(p_idx) if p_idx.isValid() else model.invisibleRootItem()
            if row >= src_parent_item.rowCount():
                continue
            row_items = src_parent_item.takeRow(row)
            if not row_items:
                continue
            effective_insert = insert_row
            if src_parent_item is parent_item and row < insert_row:
                effective_insert -= 1
            parent_item.insertRow(effective_insert, row_items)
            insert_row = effective_insert + 1

        self._drag_rows = None
        if callable(self.after_move_callback):
            self.after_move_callback()
        event.accept()

    # ============================================================
    # CUSTOM PAINTING
    # ============================================================
    def paintEvent(self, event):
        """Malt Drop-Linie, wenn vorhanden."""
        super().paintEvent(event)
        if self._drop_indicator_rect:
            painter = QPainter(self.viewport())
            pen = QPen(QColor(80, 140, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(
                self._drop_indicator_rect.left(),
                self._drop_indicator_rect.top(),
                self._drop_indicator_rect.right(),
                self._drop_indicator_rect.top(),
            )
            painter.end()
