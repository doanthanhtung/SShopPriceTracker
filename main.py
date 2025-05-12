import requests
import html
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, QUrl, Qt
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
)
import price_history


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
        self.displayName = html.unescape(displayName)
        self.formattedPriceSave = formattedPriceSave
        self.modelCode = modelCode
        self.originPdpUrl = originPdpUrl
        self.pdpUrl = pdpUrl
        self.price = float(price) if price else 0
        self.priceDisplay = priceDisplay
        self.promotionPrice = float(promotionPrice) if promotionPrice else 0
        self.ctaType = ctaType
        self.pviSubtypeName = pviSubtypeName
        self.categorySubTypeEngName = categorySubTypeEngName

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

    def get_cta_display(self):
        if self.ctaType == "outOfStock":
            return "Hết hàng"
        elif self.ctaType == "whereToBuy":
            return "Còn hàng"
        return self.ctaType


def fetch_product_data(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Có lỗi xảy ra: {e}")
    return None


URL_LIST = [
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


def load_products():
    unique_products = set()
    for url in URL_LIST:
        data = fetch_product_data(url)
        if data:
            product_list = data.get("response", {}).get("resultData", {}).get("productList", [])
            for p in product_list:
                category_subtype = p.get("categorySubTypeEngName", "")
                if category_subtype == "Washing Machines Accessories":
                    continue
                for model in p.get("modelList", []):
                    product = Product(
                        model.get("displayName"),
                        model.get("formattedPriceSave"),
                        model.get("modelCode"),
                        model.get("originPdpUrl"),
                        model.get("pdpUrl"),
                        model.get("price"),
                        model.get("priceDisplay"),
                        model.get("promotionPrice"),
                        model.get("ctaType"),
                        model.get("pviSubtypeName"),
                        category_subtype,
                    )
                    unique_products.add(product)
                    if product.promotionPrice > 0:
                        # Kiểm tra sản phẩm đã tồn tại trong database chưa
                        latest_price = price_history.get_latest_price(product.modelCode)
                        if latest_price is None:  # Sản phẩm mới, chưa có trong database
                            if hasattr(ProductApp, 'instance'):
                                ProductApp.instance.show_new_product_notification(product)
                        else:  # Sản phẩm đã tồn tại, kiểm tra thay đổi giá/tình trạng
                            latest_ctaType = price_history.get_latest_ctaType(product.modelCode)
                            if latest_price != product.promotionPrice:
                                if hasattr(ProductApp, 'instance'):
                                    ProductApp.instance.show_price_change_notification(
                                        product, latest_price, product.promotionPrice
                                    )
                            if latest_ctaType is not None and latest_ctaType != product.ctaType:
                                if hasattr(ProductApp, 'instance'):
                                    ProductApp.instance.show_ctaType_change_notification(
                                        product, latest_ctaType, product.ctaType
                                    )
                        price_history.save_price_history(
                            product.modelCode, product.displayName, product.promotionPrice, product.ctaType
                        )
    return sorted(
        unique_products,
        key=lambda x: (-x.get_discount_percentage(), x.price, x.get_cta_display() != "Còn hàng"),
    )


class ProductApp(QWidget):
    instance = None

    def __init__(self):
        super().__init__()
        ProductApp.instance = self
        self.tray_icon = None
        self.init_tray_icon()
        self.init_ui()

    def init_tray_icon(self):
        tray_icon = QSystemTrayIcon(self)
        import os
        icon_path = "icon.png"
        if os.path.exists(icon_path):
            tray_icon.setIcon(QtGui.QIcon(icon_path))
        else:
            tray_icon.setIcon(QtGui.QIcon.fromTheme("info"))
        tray_icon.setVisible(True)
        self.tray_icon = tray_icon

    def init_ui(self):
        self.setWindowTitle("Danh sách sản phẩm")
        self.setGeometry(100, 100, 900, 500)
        layout = QVBoxLayout()

        # Thêm thanh tìm kiếm với debouncing
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Tìm kiếm theo tên sản phẩm...")
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.update_table)
        self.search_bar.textChanged.connect(self.start_search_timer)
        layout.addWidget(QLabel("Tìm kiếm:"))
        layout.addWidget(self.search_bar)

        # Bộ lọc theo danh mục
        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self.update_table)
        layout.addWidget(QLabel("Lọc theo danh mục:"))
        layout.addWidget(self.category_filter)

        # Bộ lọc theo tình trạng sản phẩm
        self.cta_filter = QComboBox()
        self.cta_filter.currentIndexChanged.connect(self.update_table)
        layout.addWidget(QLabel("Lọc theo tình trạng:"))
        layout.addWidget(self.cta_filter)

        # Nút làm mới dữ liệu
        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.on_refresh)
        layout.addWidget(self.refresh_button)

        # Checkbox tự động cập nhật
        self.auto_refresh_checkbox = QCheckBox("Tự động cập nhật mỗi 5 phút")
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        layout.addWidget(self.auto_refresh_checkbox)

        # Bảng hiển thị sản phẩm
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Tên sản phẩm", "Giá", "Giảm giá", "Tình trạng", "Chức năng", "Lịch sử giá"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.products = load_products()
        print(f"Số sản phẩm: {len(self.products)}")  # Kiểm tra số lượng sản phẩm
        self.update_filters()
        self.update_table()
        self.check_high_discounts(self.products)
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_refresh)

    def start_search_timer(self):
        self.search_timer.start(500)  # Chờ 500ms trước khi gọi update_table

    def toggle_auto_refresh(self, state):
        if state == Qt.Checked:
            self.timer.start(300000)
        else:
            self.timer.stop()

    def update_table(self):
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
            if (selected_cta == "Tất cả" or p.get_cta_display() == selected_cta)
               and (
                       selected_category == "Tất cả"
                       or (p.categorySubTypeEngName and p.categorySubTypeEngName == selected_category)
               )
               and (search_text in p.displayName.lower())
        ]

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

    def show_notification(self, product):
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Sản phẩm có hàng!",
                f"{product.displayName} đã có hàng. Mua ngay!",
                QSystemTrayIcon.Information,
                50000
            )

    def on_button_click(self, product, button):
        if product.get_cta_display() == "Còn hàng":
            QDesktopServices.openUrl(QUrl("http://samsung.com/" + product.pdpUrl))
        else:
            if button.text() == "Thông báo khi có hàng":
                button.setText("Hủy thông báo")
                self.check_product_availability(product, button)
            else:
                button.setText("Thông báo khi có hàng")

    def on_refresh(self):
        old_products = self.products if hasattr(self, 'products') else []
        self.products = load_products()
        new_products = [p for p in self.products if not any(op.modelCode == p.modelCode for op in old_products)]
        self.check_high_discounts(new_products)
        self.update_filters()
        self.update_table()
        for row in range(self.table.rowCount()):
            button = self.table.cellWidget(row, 4)
            if button and button.text() == "Hủy thông báo":
                product = self.products[row]
                self.check_product_availability(product, button)

    def update_filters(self):
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

    def check_product_availability(self, product, button):
        if product.get_cta_display() == "Còn hàng":
            self.show_notification(product)
            button.setText("Mua ngay")

    def show_price_history(self, model_code):
        price_history.display_price_history_chart(model_code)

    def check_high_discounts(self, products, discount_threshold=70):
        high_discount_products = [p for p in products if p.get_discount_percentage() >= discount_threshold
                                  and p.get_cta_display() == "Còn hàng"]
        for product in high_discount_products:
            self.show_discount_notification(product)

    def show_discount_notification(self, product):
        if self.tray_icon:
            discount = product.get_discount_percentage()
            message = f"{product.displayName} đang giảm giá {discount}%!\nGiá gốc: {product.priceDisplay}\nGiá khuyến mãi: {self.format_price(product.promotionPrice)}"
            self.tray_icon.showMessage(
                f"Giảm giá lớn! ({discount}%)",
                message,
                QSystemTrayIcon.Information,
                10000
            )

    def format_price(self, price):
        return f"{int(price):,}₫".replace(",", ".")

    def show_ctaType_change_notification(self, product, old_ctaType, new_ctaType):
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

    def show_price_change_notification(self, product, old_price, new_price):
        if self.tray_icon:
            change_direction = "giảm" if new_price < old_price else "tăng"
            change_amount = abs(new_price - old_price)
            message = (
                f"{product.displayName}\n"
                f"Giá cũ: {self.format_price(old_price)}\n"
                f"Giá mới: {self.format_price(new_price)}\n"
                f"Thay đổi: {change_direction} {self.format_price(change_amount)}"
            )
            self.tray_icon.showMessage(
                f"Giá sản phẩm thay đổi ({change_direction})",
                message,
                QSystemTrayIcon.Information,
                5000
            )

    def show_new_product_notification(self, product):
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


def main():
    import sys
    app = QApplication(sys.argv)
    main_win = ProductApp()
    main_win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
