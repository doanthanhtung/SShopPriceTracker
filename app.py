# from PyQt5 import QtWidgets, QtGui
# from PyQt5.QtCore import QTimer, QUrl, Qt
# from PyQt5.QtGui import QDesktopServices
# from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton, QComboBox, QLabel, QWidget, \
#     QCheckBox
# from fetch_data import load_products
#
#
# class ProductApp(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.init_ui()
#
#     def init_ui(self):
#         self.setWindowTitle("Danh sách sản phẩm")
#         self.setGeometry(100, 100, 900, 500)
#         layout = QVBoxLayout()
#
#         self.category_filter = QComboBox()
#         self.category_filter.currentIndexChanged.connect(self.update_table)
#         layout.addWidget(QLabel("Lọc theo danh mục:"))
#         layout.addWidget(self.category_filter)
#
#         self.cta_filter = QComboBox()
#         self.cta_filter.currentIndexChanged.connect(self.update_table)
#         layout.addWidget(QLabel("Lọc theo tình trạng:"))
#         layout.addWidget(self.cta_filter)
#
#         self.refresh_button = QPushButton("Làm mới")
#         self.refresh_button.clicked.connect(self.on_refresh)
#         layout.addWidget(self.refresh_button)
#
#         self.auto_refresh_checkbox = QCheckBox("Tự động cập nhật mỗi 5 phút")
#         self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
#         layout.addWidget(self.auto_refresh_checkbox)
#
#         self.table = QTableWidget()
#         self.table.setColumnCount(5)
#         self.table.setHorizontalHeaderLabels(["Tên sản phẩm", "Giá", "Giảm giá", "Tình trạng", "Chức năng"])
#         self.table.horizontalHeader().setStretchLastSection(True)
#         self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
#         layout.addWidget(self.table)
#
#         self.setLayout(layout)
#
#         self.products = load_products()
#         self.update_filters()
#         self.update_table()
#
#         self.timer = QTimer()
#         self.timer.timeout.connect(self.on_refresh)
#
#     def toggle_auto_refresh(self, state):
#         if state == Qt.Checked:
#             self.timer.start(300000)
#         else:
#             self.timer.stop()
#
#     def update_table(self):
#         self.table.setRowCount(0)
#         for row, product in enumerate(self.products):
#             self.table.insertRow(row)
#             color = QtGui.QColor("green") if product.get_cta_display() == "Còn hàng" else QtGui.QColor("red")
#
#             for col, value in enumerate([product.displayName, product.priceDisplay,
#                                          f"{product.get_discount_percentage()}%", product.get_cta_display()]):
#                 item = QTableWidgetItem(value)
#                 item.setForeground(color)
#                 self.table.setItem(row, col, item)
#
#             button = QPushButton("Mua ngay" if product.get_cta_display() == "Còn hàng" else "Thông báo khi có hàng")
#             button.clicked.connect(lambda checked, p=product, b=button: self.on_button_click(p, b))
#             self.table.setCellWidget(row, 4, button)
#
#     def on_button_click(self, product, button):
#         if product.get_cta_display() == "Còn hàng":
#             QDesktopServices.openUrl(QUrl(product.pdpUrl))
#         else:
#             button.setText("Hủy" if button.text() == "Thông báo khi có hàng" else "Thông báo khi có hàng")
#
#     def on_refresh(self):
#         self.products = load_products()
#         self.update_filters()
#         self.update_table()
#
#     def update_filters(self):
#         categories = {"Tất cả"}
#         statuses = {"Tất cả"}
#         for p in self.products:
#             if p.categorySubTypeEngName:
#                 categories.add(p.categorySubTypeEngName)
#             statuses.add(p.get_cta_display())
#
#         self.category_filter.clear()
#         self.category_filter.addItems(sorted(categories))
#         self.cta_filter.clear()
#         self.cta_filter.addItems(sorted(statuses))
