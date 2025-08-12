import requests
import html
import logging
import sys
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, QUrl, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QPushButton,
    QComboBox,
    QLabel,
    QWidget,
    QCheckBox,
    QApplication,
    QSystemTrayIcon,
    QLineEdit,
    QMainWindow,
    QStatusBar,
)
import price_history

# Thiết lập logging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class Product:
    def __init__(
            self,
            displayName,
            formattedPriceSave,
            modelCode,
            originPdpUrl,
            pdpUrl,
            price,
            priceDisplay,
            promotionPrice,
            ctaType,
            pviSubtypeName,
            categorySubTypeEngName,
    ):
        try:
            self.displayName = html.unescape(displayName or "")
            self.formattedPriceSave = formattedPriceSave or ""
            self.modelCode = modelCode or ""
            self.originPdpUrl = originPdpUrl or ""
            self.pdpUrl = pdpUrl or ""
            self.price = float(price) if price else 0
            self.priceDisplay = priceDisplay or ""
            self.promotionPrice = float(promotionPrice) if promotionPrice else 0
            self.ctaType = ctaType or ""
            self.pviSubtypeName = pviSubtypeName or ""
            self.categorySubTypeEngName = categorySubTypeEngName or ""
            self.average_price = self.calculate_average_price()
            self.price_diff = 0
            logging.debug(f"Created Product: {self.modelCode}, Price: {self.promotionPrice}")
        except Exception as e:
            logging.error(f"Error in Product init: {e}")
            raise

    def __eq__(self, other):
        if isinstance(other, Product):
            return (
                    self.displayName == other.displayName
                    and self.promotionPrice == other.promotionPrice
                    and self.get_discount_percentage() == other.get_discount_percentage()
                    and self.ctaType == other.ctaType
            )
        return False

    def __hash__(self):
        return hash(
            (self.displayName, self.promotionPrice, self.get_discount_percentage(), self.ctaType)
        )

    def get_discount_percentage(self):
        if self.price > 0 and self.promotionPrice > 0:
            return round((1 - self.promotionPrice / self.price) * 100, 2)
        return 0

    def get_discount_from_average(self):
        if self.average_price > 0 and self.promotionPrice > 0:
            return round((1 - self.promotionPrice / self.average_price) * 100, 2)
        return 0

    def calculate_average_price(self):
        try:
            history = price_history.get_price_history(self.modelCode)
            if history:
                prices = [row[2] for row in history]
                return sum(prices) / len(prices)
            return self.price
        except Exception as e:
            logging.error(f"Error in calculate_average_price: {e}")
            return self.price

    def get_cta_display(self):
        if self.ctaType == "outOfStock":
            return "Hết hàng"
        elif self.ctaType in ["whereToBuy", "preOrder"]:
            return "Còn hàng"
        return self.ctaType

def fetch_product_data(url, timeout=10):
    try:
        logging.info(f"Fetching data from {url}")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching data from {url}: {e}")
        return None

URL_LIST_SRV = [
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01020000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=04010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=07010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08050000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08080000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08070000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=09010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
]

# vn_taichinhd
# sinhvien
# vn_doanhnghiepd
#vn_chinhphud
code = "vn_doanhnghiepd"
URL_LIST_LOYALTY = [
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01020000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=04010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=07010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08050000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08080000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08070000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=09010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
    (
                "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=%s&pfType=G" % code),
]

class Worker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        try:
            products = load_products()
            self.finished.emit(products)
        except Exception as e:
            logging.error(f"Error in Worker run: {e}")
            self.finished.emit([])

def load_products():
    try:
        unique_products = {}
        # Thu thập dữ liệu từ nguồn srv
        for url in URL_LIST_SRV:
            data = fetch_product_data(url)
            if data:
                product_list = data.get("response", {}).get("resultData", {}).get("productList", [])
                for p in product_list:
                    category_subtype = p.get("categorySubTypeEngName", "")
                    if category_subtype == "Washing Machines Accessories":
                        continue
                    for model in p.get("modelList", []):
                        model_code = model.get("modelCode")
                        if model_code:
                            if model_code not in unique_products:
                                unique_products[model_code] = {'srv': None, 'loyalty': None}
                            unique_products[model_code]['srv'] = model
                        else:
                            logging.warning(f"Missing modelCode in srv data: {model}")

        # Thu thập dữ liệu từ nguồn loyalty
        for url in URL_LIST_LOYALTY:
            data = fetch_product_data(url)
            if data:
                product_list = data.get("response", {}).get("resultData", {}).get("productList", [])
                for p in product_list:
                    for model in p.get("modelList", []):
                        model_code = model.get("modelCode")
                        if model_code and model_code in unique_products:
                            unique_products[model_code]['loyalty'] = model
                        else:
                            logging.warning(f"Missing or unmatched modelCode in loyalty data: {model_code}")

        # Tạo danh sách sản phẩm
        products = set()
        for model_code, data in unique_products.items():
            if data['srv'] and data['loyalty']:
                try:
                    product_srv = Product(
                        data['srv'].get("displayName"),
                        data['srv'].get("formattedPriceSave"),
                        data['srv'].get("modelCode"),
                        data['srv'].get("originPdpUrl"),
                        data['srv'].get("pdpUrl"),
                        data['srv'].get("price"),
                        data['srv'].get("priceDisplay"),
                        data['srv'].get("promotionPrice"),
                        data['srv'].get("ctaType"),
                        data['srv'].get("pviSubtypeName"),
                        p.get("categorySubTypeEngName", ""),
                    )
                    product_loyalty_promotionPrice = float(data['loyalty'].get("promotionPrice", 0))
                    price_diff = abs(product_srv.promotionPrice - product_loyalty_promotionPrice)
                    product_srv.price_diff = price_diff
                    products.add(product_srv)
                    if product_srv.promotionPrice > 0:
                        latest_price = price_history.get_latest_price(product_srv.modelCode)
                        if latest_price is None:
                            if hasattr(ProductApp, 'instance'):
                                ProductApp.instance.show_new_product_notification(product_srv)
                        else:
                            latest_ctaType = price_history.get_latest_ctaType(product_srv.modelCode)
                            if latest_price != product_srv.promotionPrice:
                                if hasattr(ProductApp, 'instance'):
                                    ProductApp.instance.show_price_change_notification(
                                        product_srv, latest_price, product_srv.promotionPrice
                                    )
                            if latest_ctaType is not None and latest_ctaType != product_srv.ctaType:
                                if hasattr(ProductApp, 'instance'):
                                    ProductApp.instance.show_ctaType_change_notification(
                                        product_srv, latest_ctaType, product_srv.ctaType
                                    )
                        price_history.save_price_history(
                            product_srv.modelCode, product_srv.displayName, product_srv.promotionPrice, product_srv.ctaType
                        )
                except Exception as e:
                    logging.error(f"Error processing product {model_code}: {e}")
                    continue
        logging.info(f"Loaded {len(products)} products")
        return sorted(
            products,
            key=lambda x: (-x.get_discount_percentage(), x.price, x.get_cta_display() != "Còn hàng"),
        )
    except Exception as e:
        logging.error(f"Error in load_products: {e}")
        return []

class ProductApp(QMainWindow):
    instance = None

    def __init__(self):
        super().__init__()
        ProductApp.instance = self
        self.tray_icon = None
        self.init_tray_icon()
        self.init_ui()

    def init_tray_icon(self):
        try:
            tray_icon = QSystemTrayIcon(self)
            import os
            icon_path = "icon.png"
            if os.path.exists(icon_path):
                tray_icon.setIcon(QtGui.QIcon(icon_path))
            else:
                tray_icon.setIcon(QtGui.QIcon.fromTheme("info"))
            tray_icon.setVisible(True)
            self.tray_icon = tray_icon
            logging.info("System tray icon initialized")
        except Exception as e:
            logging.error(f"Error in init_tray_icon: {e}")

    def init_ui(self):
        try:
            self.setWindowTitle("Danh sách sản phẩm")
            self.setGeometry(100, 100, 900, 500)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)

            self.search_bar = QLineEdit()
            self.search_bar.setPlaceholderText("Tìm kiếm theo tên sản phẩm...")
            self.search_timer = QTimer()
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(self.update_table)
            self.search_bar.textChanged.connect(self.start_search_timer)
            layout.addWidget(QLabel("Tìm kiếm:"))
            layout.addWidget(self.search_bar)

            self.category_filter = QComboBox()
            self.category_filter.currentIndexChanged.connect(self.update_table)
            layout.addWidget(QLabel("Lọc theo danh mục:"))
            layout.addWidget(self.category_filter)

            self.cta_filter = QComboBox()
            self.cta_filter.currentIndexChanged.connect(self.update_table)
            layout.addWidget(QLabel("Lọc theo tình trạng:"))
            layout.addWidget(self.cta_filter)

            self.refresh_button = QPushButton("Làm mới")
            self.refresh_button.clicked.connect(self.on_refresh)
            layout.addWidget(self.refresh_button)

            self.auto_refresh_checkbox = QCheckBox("Tự động cập nhật mỗi 5 phút")
            self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
            layout.addWidget(self.auto_refresh_checkbox)

            self.sort_by_avg_discount_checkbox = QCheckBox("Sắp xếp theo giảm giá so với giá trung bình")
            self.sort_by_avg_discount_checkbox.stateChanged.connect(self.update_table)
            layout.addWidget(self.sort_by_avg_discount_checkbox)

            self.price_diff_checkbox = QCheckBox("Hiển thị sản phẩm có chênh lệch giá <= 50.000đ")
            self.price_diff_checkbox.stateChanged.connect(self.update_table)
            layout.addWidget(self.price_diff_checkbox)

            self.table = QTableWidget()
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(
                ["Tên sản phẩm", "Giá", "Giảm giá", "Tình trạng", "Chức năng", "Lịch sử giá"]
            )
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            layout.addWidget(self.table)

            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.status_label = QLabel("Đang tải dữ liệu từ samsung.com...")
            self.status_label.setStyleSheet("color: blue;")
            self.status_bar.addWidget(self.status_label)

            self.products = []
            self.on_refresh()
            self.timer = QTimer()
            self.timer.timeout.connect(self.on_refresh)
            logging.info("UI initialized")
        except Exception as e:
            logging.error(f"Error in init_ui: {e}")
            raise

    def start_search_timer(self):
        try:
            self.search_timer.start(500)
        except Exception as e:
            logging.error(f"Error in start_search_timer: {e}")

    def toggle_auto_refresh(self, state):
        try:
            if state == Qt.Checked:
                self.timer.start(300000)
            else:
                self.timer.stop()
            logging.info(f"Auto refresh {'enabled' if state == Qt.Checked else 'disabled'}")
        except Exception as e:
            logging.error(f"Error in toggle_auto_refresh: {e}")

    def update_table(self):
        try:
            self.table.setRowCount(0)
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(
                ["Tên sản phẩm", "Giá", "Giảm giá", "Tình trạng", "Chức năng", "Lịch sử giá"]
            )
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

            selected_cta = self.cta_filter.currentText()
            selected_category = self.category_filter.currentText()
            search_text = self.search_bar.text().lower()

            filtered_products = [
                p
                for p in self.products
                if (not self.price_diff_checkbox.isChecked() or p.price_diff <= 50000)
                and (selected_cta == "Tất cả" or p.get_cta_display() == selected_cta)
                and (
                        selected_category == "Tất cả"
                        or (p.categorySubTypeEngName and p.categorySubTypeEngName == selected_category)
                )
                and (search_text in p.displayName.lower())
            ]

            if self.sort_by_avg_discount_checkbox.isChecked():
                filtered_products.sort(
                    key=lambda x: (-x.get_discount_from_average(), x.price, x.get_cta_display() != "Còn hàng")
                )
            else:
                filtered_products.sort(
                    key=lambda x: (-x.get_discount_percentage(), x.price, x.get_cta_display() != "Còn hàng")
                )

            for row, product in enumerate(filtered_products):
                self.table.insertRow(row)
                color = QtGui.QColor("green") if product.get_cta_display() == "Còn hàng" else QtGui.QColor("red")
                for col, value in enumerate(
                        [
                            product.displayName,
                            product.priceDisplay,
                            f"{product.get_discount_percentage()}%",
                            product.get_cta_display(),
                        ]
                ):
                    item = QTableWidgetItem(value)
                    item.setForeground(color)
                    self.table.setItem(row, col, item)
                button_text = "Mua ngay" if product.get_cta_display() == "Còn hàng" else "Thông báo khi có hàng"
                button = QPushButton(button_text)
                button.clicked.connect(lambda checked, p=product, b=button: self.on_button_click(p, b))
                self.table.setCellWidget(row, 4, button)
                history_button = QPushButton("Xem lịch sử giá")
                history_button.clicked.connect(lambda checked, p=product: self.show_price_history(p.modelCode))
                self.table.setCellWidget(row, 5, history_button)
            logging.info(f"Table updated with {len(filtered_products)} products")
        except Exception as e:
            logging.error(f"Error in update_table: {e}")

    def show_notification(self, product):
        try:
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Sản phẩm có hàng!",
                    f"{product.displayName} đã có hàng. Mua ngay!",
                    QSystemTrayIcon.Information,
                    50000
                )
                logging.info(f"Notification shown for {product.displayName}")
        except Exception as e:
            logging.error(f"Error in show_notification: {e}")

    def on_button_click(self, product, button):
        try:
            if product.get_cta_display() == "Còn hàng":
                QDesktopServices.openUrl(QUrl("http://samsung.com/" + product.pdpUrl))
            else:
                if button.text() == "Thông báo khi có hàng":
                    button.setText("Hủy thông báo")
                    self.check_product_availability(product, button)
                else:
                    button.setText("Thông báo khi có hàng")
            logging.info(f"Button clicked for {product.displayName}: {button.text()}")
        except Exception as e:
            logging.error(f"Error in on_button_click: {e}")

    def on_refresh(self):
        try:
            self.refresh_button.setEnabled(False)
            self.status_label.setText("Đang tải dữ liệu từ samsung.com...")
            self.status_label.setStyleSheet("color: blue;")
            self.worker = Worker()
            self.worker.finished.connect(self.handle_load_products_result)
            self.worker.start()
            logging.info("Refresh initiated")
        except Exception as e:
            logging.error(f"Error in on_refresh: {e}")

    def handle_load_products_result(self, products):
        try:
            old_products = self.products if hasattr(self, 'products') else []
            self.products = products
            new_products = [p for p in self.products if not any(op.modelCode == p.modelCode for op in old_products)]
            self.check_high_discounts(new_products)
            self.update_filters()
            self.update_table()
            for row in range(self.table.rowCount()):
                button = self.table.cellWidget(row, 4)
                if button and button.text() == "Hủy thông báo":
                    product = self.products[row]
                    self.check_product_availability(product, button)
            self.refresh_button.setEnabled(True)
            self.status_label.setText("Đã tải xong dữ liệu từ samsung.com")
            self.status_label.setStyleSheet("color: green;")
            QTimer.singleShot(3000, lambda: self.status_label.setText(""))
            logging.info(f"Load products completed: {len(products)} products")
        except Exception as e:
            logging.error(f"Error in handle_load_products_result: {e}")

    def update_filters(self):
        try:
            categories = {"Tất cả"}
            statuses = {"Tất cả"}
            for p in self.products:
                if p.categorySubTypeEngName:
                    categories.add(p.categorySubTypeEngName)
                statuses.add(p.get_cta_display())
            self.category_filter.clear()
            self.category_filter.addItems(["Tất cả"] + sorted(categories - {"Tất cả"}))
            self.cta_filter.clear()
            self.cta_filter.addItems(["Tất cả"] + sorted(statuses - {"Tất cả"}))
            logging.info("Filters updated")
        except Exception as e:
            logging.error(f"Error in update_filters: {e}")

    def check_product_availability(self, product, button):
        try:
            if product.get_cta_display() == "Còn hàng":
                self.show_notification(product)
                button.setText("Mua ngay")
            logging.info(f"Checked availability for {product.displayName}")
        except Exception as e:
            logging.error(f"Error in check_product_availability: {e}")

    def show_price_history(self, model_code):
        try:
            price_history.display_price_history_chart(model_code)
            logging.info(f"Showing price history for {model_code}")
        except Exception as e:
            logging.error(f"Error in show_price_history: {e}")

    def check_high_discounts(self, products, discount_threshold=70):
        try:
            high_discount_products = [p for p in products if p.get_discount_percentage() >= discount_threshold
                                      and p.get_cta_display() == "Còn hàng"]
            for product in high_discount_products:
                self.show_discount_notification(product)
            logging.info(f"Checked high discounts: {len(high_discount_products)} products")
        except Exception as e:
            logging.error(f"Error in check_high_discounts: {e}")

    def show_discount_notification(self, product):
        try:
            if self.tray_icon:
                discount = product.get_discount_percentage()
                message = f"{product.displayName} đang giảm giá {discount}%!\nGiá gốc: {product.priceDisplay}\nGiá khuyến mãi: {self.format_price(product.promotionPrice)}"
                self.tray_icon.showMessage(
                    f"Giảm giá lớn! ({discount}%)",
                    message,
                    QSystemTrayIcon.Information,
                    10000
                )
                logging.info(f"Discount notification for {product.displayName}")
        except Exception as e:
            logging.error(f"Error in show_discount_notification: {e}")

    def format_price(self, price):
        try:
            return f"{int(price):,}₫".replace(",", ".")
        except Exception as e:
            logging.error(f"Error in format_price: {e}")
            return "0₫"

    def show_ctaType_change_notification(self, product, old_ctaType, new_ctaType):
        try:
            if self.tray_icon:
                old_status = "Còn hàng" if old_ctaType == "whereToBuy" else "Hết hàng"
                new_status = "Còn hàng" if new_ctaType == "whereToBuy" else "Hết hàng"
                message = (
                    f"{product.displayName}\n"
                    f"Tình trạng: {new_status}"
                )
                self.tray_icon.showMessage(
                    "Tình trạng sản phẩm thay đổi",
                    message,
                    QSystemTrayIcon.Information,
                    10000
                )
                logging.info(f"CTA type change notification for {product.displayName}")
        except Exception as e:
            logging.error(f"Error in show_ctaType_change_notification: {e}")

    def show_price_change_notification(self, product, old_price, new_price):
        try:
            if self.tray_icon:
                change_direction = "Giảm" if new_price < old_price else "Tăng"
                change_amount = abs(new_price - old_price)
                message = (
                    f"{product.displayName}\n"
                    f"Giá: {self.format_price(new_price)}\n"
                    f"{change_direction} {self.format_price(change_amount)}"
                )
                self.tray_icon.showMessage(
                    f"Giá sản phẩm thay đổi ({change_direction})",
                    message,
                    QSystemTrayIcon.Information,
                    5000
                )
                logging.info(f"Price change notification for {product.displayName}")
        except Exception as e:
            logging.error(f"Error in show_price_change_notification: {e}")

    def show_new_product_notification(self, product):
        try:
            if self.tray_icon:
                message = (
                    f"Sản phẩm mới: {product.displayName}\n"
                    f"Giá: {self.format_price(product.promotionPrice)}\n"
                    f"Tình trạng: {product.get_cta_display()}"
                )
                self.tray_icon.showMessage(
                    "Sản phẩm mới được thêm",
                    message,
                    QSystemTrayIcon.Information,
                    10000
                )
                logging.info(f"New product notification for {product.displayName}")
        except Exception as e:
            logging.error(f"Error in show_new_product_notification: {e}")

def main():
    try:
        app = QApplication(sys.argv)
        main_win = ProductApp()
        main_win.show()
        logging.info("Application started")
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()