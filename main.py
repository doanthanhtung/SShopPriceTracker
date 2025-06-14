import requests
import html
import re
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from datetime import datetime

# Cấu hình email
EMAIL_SENDER = "luongphongtrung01@gmail.com"
EMAIL_PASSWORD = "pdtu qgjf jvss igkq"
EMAIL_RECEIVERS = ["doanthanhtung.pc@gmail.com"]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(subject, body, images=None):
    """Gửi email thông báo với nội dung HTML và ảnh nhúng inline."""
    try:
        msg = MIMEMultipart('related')
        msg['From'] = EMAIL_SENDER
        msg['To'] = ", ".join(EMAIL_RECEIVERS)
        msg['Subject'] = subject

        html_body = f"""
        Tổng hợp thay đổi sản phẩm Samsung

        Dưới đây là các thay đổi sản phẩm mới nhất:

        {body}
        Xem chi tiết tại: samsung.com
        """
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        if images:
            for image_path, cid in images:
                with open(image_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', f'<{cid}>')
                    msg.attach(img)
                print(f"Đã nhúng ảnh inline cho {cid}")

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, msg.as_string())
        server.quit()
        print(f"Đã gửi email: {subject}")
    except Exception as e:
        print(f"Lỗi khi gửi email: {e}")


def sanitize_filename(filename):
    """Loại bỏ hoặc thay thế các ký tự không hợp lệ trong tên file."""
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', filename)


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
        elif self.ctaType in ["whereToBuy", "preOrder"]:
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


class Worker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        products = load_products()
        self.finished.emit(products)


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
                    if product.modelCode == "SM-A556ELVAXXV":
                        print("check")
                    if product.promotionPrice > 0:
                        latest_price = price_history.get_latest_price(product.modelCode)
                        average_price = price_history.get_average_price(product.modelCode)
                        if latest_price is None:
                            if hasattr(ProductApp, 'instance'):
                                ProductApp.instance.show_new_product_notification(product)
                        else:
                            latest_ctaType = price_history.get_latest_ctaType(product.modelCode)
                            if latest_price != product.promotionPrice:
                                if average_price and product.promotionPrice < average_price:
                                    discount_percent = round((1 - product.promotionPrice / average_price) * 100, 2)
                                    if hasattr(ProductApp, 'instance'):
                                        ProductApp.instance.show_price_change_notification(
                                            product, latest_price, product.promotionPrice, discount_percent
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


class ProductApp(QMainWindow):
    instance = None

    def __init__(self):
        super().__init__()
        ProductApp.instance = self
        self.tray_icon = None
        self.notifications = []
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

    def start_search_timer(self):
        self.search_timer.start(500)

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
            QDesktopServices.openUrl(QUrl("http://samsung.com" + product.pdpUrl))
        else:
            if button.text() == "Thông báo khi có hàng":
                button.setText("Hủy thông báo")
                self.check_product_availability(product, button)
            else:
                button.setText("Thông báo khi có hàng")

    def on_refresh(self):
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Đang tải dữ liệu từ samsung.com...")
        self.status_label.setStyleSheet("color: blue;")
        self.notifications = []
        self.worker = Worker()
        self.worker.finished.connect(self.handle_load_products_result)
        self.worker.start()

    def generate_price_history_image(self, model_code):
        """Tạo và lưu biểu đồ lịch sử giá dưới dạng ảnh, trả về đường dẫn file và CID."""
        history = price_history.get_price_history(model_code)
        if not history:
            print(f"Không có dữ liệu lịch sử giá cho sản phẩm {model_code}")
            return None, None

        fig = plt.figure(figsize=(10, 6))
        dates = [datetime.strptime(row[1], "%Y-%m-%d") for row in history]
        prices = [row[2] for row in history]
        display_name = history[-1][0]

        plt.plot(dates, prices, marker='o', linestyle='-', color='b', label='Giá')
        plt.title(f"Lịch sử giá của {display_name} ({model_code})", fontsize=14)
        plt.xlabel("Ngày", fontsize=12)
        plt.ylabel("Giá (VND)", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gca().get_yaxis().set_major_formatter(
            plt.FuncFormatter(lambda x, loc: "{:,.0f}".format(x).replace(',', '.'))
        )
        plt.xticks(rotation=45)

        prev_price = None
        for i, price in enumerate(prices):
            if prev_price is None or price != prev_price:
                plt.annotate(
                    f"{price:,.0f}".replace(',', '.'),
                    (dates[i], prices[i]),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha='center'
                )
            prev_price = price

        plt.tight_layout()
        safe_model_code = sanitize_filename(model_code)  # Làm sạch model_code
        image_path = f"price_history_{safe_model_code}.png"
        cid = f"price_history_{safe_model_code}"
        try:
            plt.savefig(image_path)
            plt.close(fig)  # Đóng figure để giải phóng bộ nhớ
            print(f"Đã tạo biểu đồ cho {model_code} tại {image_path}")
            return image_path, cid
        except Exception as e:
            print(f"Lỗi khi lưu biểu đồ cho {model_code}: {e}")
            plt.close(fig)  # Đóng figure ngay cả khi có lỗi
            return None, None

    def handle_load_products_result(self, products):
        self.products = products

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

        if self.notifications:
            email_subject = "Tổng hợp thay đổi sản phẩm Samsung"
            email_body = ""
            images = []

            # Lọc và sắp xếp thông báo
            price_change_notifications = [
                (message, model_code) for message, model_code in self.notifications
                if "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)" in message
            ]
            new_product_notifications = [
                (message, model_code) for message, model_code in self.notifications
                if "Sản phẩm mới" in message
            ]
            stock_and_price_notifications = [
                (message, model_code) for message, model_code in self.notifications
                if "Tình trạng sản phẩm thay đổi" in message
            ]

            # Sắp xếp thông báo giảm giá theo phần trăm giảm
            price_change_notifications.sort(
                key=lambda x: float(x[0].split("Giảm giá so với giá trung bình:")[1].split("%")[0].strip()),
                reverse=True
            )

            # Gộp các thông báo đã sắp xếp
            sorted_notifications = price_change_notifications + new_product_notifications + stock_and_price_notifications

            # Tạo nội dung email
            for message, model_code in sorted_notifications:
                lines = message.split("\n")
                html_notification = "<h3>" + lines[0] + "</h3>"
                for line in lines[1:]:
                    if line and line != "-" * 50:
                        html_notification += "<p>" + line + "</p>"

                # Thêm biểu đồ lịch sử giá cho thông báo giảm giá hoặc có hàng với giá tốt
                if "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)" in message or "Sản phẩm có hàng với giá tốt" in message:
                    image_path, cid = self.generate_price_history_image(model_code)
                    if image_path and cid:
                        images.append((image_path, cid))
                        html_notification += f'<p><img src="cid:{cid}" alt="Lịch sử giá {model_code}"></p>'
                    else:
                        html_notification += "<p>Không có dữ liệu lịch sử giá.</p>"

                html_notification += "<hr>"
                email_body += html_notification

            # Gửi email nếu có thông báo
            if sorted_notifications:
                send_email(email_subject, email_body, images)

                # Xóa các file ảnh tạm
                for image_path, _ in images:
                    if os.path.exists(image_path):
                        os.remove(image_path)

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
            notification_message = (
                f"Giảm giá lớn ({discount}%):\n"
                f"Sản phẩm: {product.displayName}\n"
                f"Giảm giá: {discount}%\n"
                f"Giá gốc: {product.priceDisplay}\n"
                f"Giá khuyến mãi: {self.format_price(product.promotionPrice)}\n"
                f"Link: http://samsung.com{product.pdpUrl}"
            )
            self.notifications.append((notification_message, product.modelCode))

    def show_ctaType_change_notification(self, product, old_ctaType, new_ctaType):
        if self.tray_icon:
            old_status = "Còn hàng" if old_ctaType in ["whereToBuy", "preOrder"] else "Hết hàng"
            new_status = "Còn hàng" if new_ctaType in ["whereToBuy", "preOrder"] else "Hết hàng"
            if new_status == "Còn hàng":
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
                notification_message = (
                    f"Tình trạng sản phẩm thay đổi:\n"
                    f"Sản phẩm: {product.displayName}\n"
                    f"Tình trạng mới: {new_status}\n"
                    f"Link: http://samsung.com{product.pdpUrl}"
                )
                self.notifications.append((notification_message, product.modelCode))

    def show_price_change_notification(self, product, old_price, new_price, discount_percent):
        if self.tray_icon:
            message = (
                f"{product.displayName}\n"
                f"Giá mới: {self.format_price(new_price)}\n"
                f"Giảm giá so với giá trung bình: {discount_percent}%"
            )
            self.tray_icon.showMessage(
                "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)",
                message,
                QSystemTrayIcon.Information,
                5000
            )
            notification_message = (
                f"Giá sản phẩm thay đổi (Giảm dưới giá trung bình):\n"
                f"Sản phẩm: {product.displayName}\n"
                f"Giá mới: {self.format_price(new_price)}\n"
                f"Giảm giá so với giá trung bình: {discount_percent}%\n"
                f"Link: http://samsung.com{product.pdpUrl}"
            )
            self.notifications.append((notification_message, product.modelCode))

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
            notification_message = (
                f"Sản phẩm mới:\n"
                f"Sản phẩm: {product.displayName}\n"
                f"Giá: {self.format_price(product.promotionPrice)}\n"
                f"Tình trạng: {product.get_cta_display()}\n"
                f"Link: http://samsung.com{product.pdpUrl}"
            )
            self.notifications.append((notification_message, product.modelCode))

    def format_price(self, price):
        return f"{int(price):,}₫".replace(",", ".")


def main():
    import sys
    app = QApplication(sys.argv)
    main_win = ProductApp()
    main_win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
