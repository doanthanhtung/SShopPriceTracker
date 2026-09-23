"""A product table that only paints visible cells, including action buttons."""

from PyQt5 import QtCore, QtGui, QtWidgets


class ProductTableModel(QtCore.QAbstractTableModel):
    headers = ("Sản phẩm", "Giá hiện tại", "Giảm giá", "Tình trạng", "Thao tác", "Lịch sử")

    def __init__(self, action_text, parent=None):
        super().__init__(parent)
        self.products = []
        self.action_text = action_text
        self.by_average_discount = False

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.products)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal and section == 2 and self.by_average_discount:
                return "So với TB"
            return self.headers[section] if orientation == QtCore.Qt.Horizontal else section + 1
        if role == QtCore.Qt.ToolTipRole and orientation == QtCore.Qt.Horizontal and section == 2:
            return "Mức giảm so với giá trung bình lịch sử" if self.by_average_discount else "Mức giảm so với giá niêm yết"
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        product = self.products[index.row()]
        column = index.column()
        if role == QtCore.Qt.UserRole:
            return product
        if role == QtCore.Qt.DisplayRole:
            if column == 0:
                return product.displayName
            if column == 1:
                return format_price(product.promotionPrice or product.price)
            if column == 2:
                discount = product.get_discount_from_average() if self.by_average_discount else product.get_discount_percentage()
                if self.by_average_discount and not product.averagePrice:
                    return "—"
                return f"{discount:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%"
            if column == 3:
                return product.get_cta_display()
            if column == 4:
                return self.action_text(product)
            return "Lịch sử"
        if role == QtCore.Qt.ForegroundRole and column < 4:
            return QtGui.QColor("#245fe5" if column == 2 else "#243247")
        if role == QtCore.Qt.TextAlignmentRole:
            return int(QtCore.Qt.AlignVCenter | (QtCore.Qt.AlignLeft if column == 0 else QtCore.Qt.AlignHCenter))
        if role == QtCore.Qt.ToolTipRole:
            if column == 0:
                return f"{product.displayName}\n{product.modelCode}"
            if column == 1:
                return f"Giá hiện tại: {format_price(product.promotionPrice or product.price)}\nGiá niêm yết: {format_price(product.price)}"
            if column == 4 and product.get_cta_display() != "Còn hàng":
                return "Bạn sẽ nhận một thông báo khi sản phẩm có hàng."
        return None

    def set_products(self, products):
        # Compare identity: Product.__eq__ intentionally ignores some displayed fields.
        if len(products) == len(self.products) and all(a is b for a, b in zip(products, self.products)):
            return
        self.beginResetModel()
        self.products = list(products)
        self.endResetModel()

    def refresh_actions(self):
        if self.products:
            self.dataChanged.emit(self.index(0, 4), self.index(len(self.products) - 1, 4), [QtCore.Qt.DisplayRole])

    def set_discount_basis(self, by_average):
        if self.by_average_discount == bool(by_average):
            return
        self.by_average_discount = bool(by_average)
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, 2, 2)
        if self.products:
            self.dataChanged.emit(self.index(0, 2), self.index(len(self.products) - 1, 2), [QtCore.Qt.DisplayRole])


def format_price(value):
    return f"{value:,.0f} ₫".replace(",", ".") if value else "Chưa có giá"


class ProductDetailsDelegate(QtWidgets.QStyledItemDelegate):
    """Two-line product/price cells and readable stock badges, without cell widgets."""

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        product = index.data(QtCore.Qt.UserRole)
        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, option.widget)
        painter.save()
        painter.setClipRect(option.rect)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = option.rect.adjusted(12, 0, -12, 0)
        font = QtGui.QFont(option.font)

        if index.column() == 3:
            in_stock = product.get_cta_display() == "Còn hàng"
            badge = QtCore.QRect(rect.left(), rect.center().y() - 13, rect.width(), 26)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor("#e5f4ed" if in_stock else "#edf0f5"))
            painter.drawRoundedRect(badge, 6, 6)
            painter.setPen(QtGui.QColor("#21734e" if in_stock else "#627188"))
            font.setPixelSize(12)
            painter.setFont(font)
            text = QtGui.QFontMetrics(font).elidedText(product.get_cta_display(), QtCore.Qt.ElideRight, badge.width() - 8)
            painter.drawText(badge, QtCore.Qt.AlignCenter, text)
        else:
            is_price = index.column() == 1
            primary = format_price(product.promotionPrice or product.price) if is_price else product.displayName
            secondary = format_price(product.price) if is_price and product.price > product.promotionPrice > 0 else ""
            if not is_price:
                secondary = product.modelCode or ""
            font.setPixelSize(13)
            font.setWeight(QtGui.QFont.DemiBold)
            painter.setFont(font)
            painter.setPen(QtGui.QColor("#20314a"))
            primary_rect = QtCore.QRect(rect.left(), rect.center().y() - 21, rect.width(), 24) if secondary else rect
            text = QtGui.QFontMetrics(font).elidedText(primary, QtCore.Qt.ElideRight, rect.width())
            alignment = QtCore.Qt.AlignVCenter | (QtCore.Qt.AlignRight if is_price else QtCore.Qt.AlignLeft)
            painter.drawText(primary_rect, alignment, text)
            if secondary:
                font.setPixelSize(11)
                font.setWeight(QtGui.QFont.Normal)
                font.setStrikeOut(is_price)
                painter.setFont(font)
                painter.setPen(QtGui.QColor("#77879b"))
                secondary_rect = QtCore.QRect(rect.left(), rect.center().y() + 2, rect.width(), 20)
                painter.drawText(secondary_rect, alignment, QtGui.QFontMetrics(font).elidedText(secondary, QtCore.Qt.ElideRight, rect.width()))
        painter.restore()


class ProductActionDelegate(QtWidgets.QStyledItemDelegate):
    activated = QtCore.pyqtSignal(object, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pressed_index = QtCore.QPersistentModelIndex()

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, option.widget)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        button = self.button_rect(option.rect)
        primary = index.column() == 4 and index.data(QtCore.Qt.UserRole).get_cta_display() == "Còn hàng"
        hover = bool(option.state & QtWidgets.QStyle.State_MouseOver)
        painter.setBrush(QtGui.QColor("#dbe7ff" if primary and hover else "#edf3ff" if primary else "#edf1f7" if hover else "#ffffff"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#245fe5" if option.state & QtWidgets.QStyle.State_HasFocus else "#c9daf9" if primary else "#d9e1eb")))
        painter.drawRoundedRect(button, 6, 6)
        painter.setPen(QtGui.QColor("#2455b3" if primary else "#53657e"))
        font = QtGui.QFont(option.font)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(button, QtCore.Qt.AlignCenter, index.data(QtCore.Qt.DisplayRole))
        painter.restore()

    @staticmethod
    def button_rect(rect):
        return QtCore.QRect(rect.left() + 7, rect.center().y() - 16, rect.width() - 14, 32)

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton and self.button_rect(option.rect).contains(event.pos()):
                self._pressed_index = QtCore.QPersistentModelIndex(index)
                return True
            return False
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            pressed = self._pressed_index
            self._pressed_index = QtCore.QPersistentModelIndex()
            if (event.button() != QtCore.Qt.LeftButton or pressed != index
                    or not self.button_rect(option.rect).contains(event.pos())):
                return False
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() not in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) or event.isAutoRepeat():
                return False
        else:
            return False
        self.activated.emit(index.data(QtCore.Qt.UserRole), index.column())
        return True
