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
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os

# Cấu hình email
EMAIL_SENDER = "luongphongtrung01@gmail.com"
EMAIL_PASSWORD = "pdtu qgjf jvss igkq"
EMAIL_RECEIVERS = ["doanthanhtung.pc@gmail.com"]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# API URL
API_URL = "https://recommendationv2.api.useinsider.com/v2/most-valuable?details=true&locale=vi_VN&partnerName=10005327&size=99&campaignId=5602&strategyId=1173&clientId=nUx8daoEthUB9kf2&currency=VND&categoryList=[%22%C4%90i%E1%BB%87n%20tho%E1%BA%A1i%22%2C%20%22Samsung%22]&userId=17117706921605c7d78d185.2d92d264&shuffle=true&excludePurchaseDay=7&filter=([category][~][%C4%90i%E1%BB%87n%20tho%E1%BA%A1i]|[category][~][Samsung])&"  # Thay bằng URL thực tế


def send_email(subject, body, images=None):
    try:
        msg = MIMEMultipart('related')
        msg['From'] = EMAIL_SENDER
        msg['To'] = ", ".join(EMAIL_RECEIVERS)
        msg['Subject'] = subject

        html_body = f"""
        Tổng hợp thay đổi sản phẩm Samsung từ Hoàng Hà Mobile

        Dưới đây là các thay đổi sản phẩm mới nhất:

        {body}
        Xem chi tiết tại: hoanghamobile.com
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
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', filename)


class Product:
    def __init__(self, name, item_id, price, original_price, discount, in_stock, category, image_url, url):
        self.name = html.unescape(name)
        self.item_id = item_id
        self.price = float(price) if price else 0
        self.original_price = float(original_price) if original_price else 0
        self.discount = float(discount) if discount else 0
        self.in_stock = in_stock
        self.category = category
        self.image_url = image_url
        self.url = url

    def __eq__(self, other):
        if isinstance(other, Product):
            return (
                    self.name == other.name
                    and self.price == other.price
                    and self.get_discount_percentage() == other.get_discount_percentage()
                    and self.get_cta_display() == other.get_cta_display()
            )
        return False

    def __hash__(self):
        return hash(
            (self.name, self.price, self.get_discount_percentage(), self.get_cta_display())
        )

    def get_discount_percentage(self):
        if self.original_price > 0 and self.price > 0:
            return round((1 - self.price / self.original_price) * 100, 2)
        return 0

    def get_cta_display(self):
        return "Còn hàng" if self.in_stock else "Hết hàng"


def fetch_product_data(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Có lỗi xảy ra: {e}")
    return None


class Worker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        products = load_products()
        self.finished.emit(products)


def load_products():
    unique_products = set()
    data = fetch_product_data(API_URL)
    if data:
        for p in data.get("data", []):
            price = p.get("price", {}).get("VND", 0) or p.get("original_price", {}).get("VND", 0)
            original_price = p.get("original_price", {}).get("VND", 0)
            discount = p.get("discount", {}).get("VND", 0) if "discount" in p else 0
            product = Product(
                name=p.get("name", ""),
                item_id=p.get("item_id", ""),
                price=price,
                original_price=original_price,
                discount=discount,
                in_stock=p.get("in_stock", 0),
                category=p.get("category", []),
                image_url=p.get("image_url", ""),
                url=p.get("url", "")
            )
            unique_products.add(product)
            if product.price > 0:
                latest_price = get_latest_price(product.item_id)
                average_price = get_average_price(product.item_id)
                if latest_price is None:
                    if hasattr(ProductApp, 'instance'):
                        ProductApp.instance.show_new_product_notification(product)
                else:
                    if latest_price != product.price:
                        if average_price and product.price < average_price:
                            discount_percent = round((1 - product.price / average_price) * 100, 2)
                            if hasattr(ProductApp, 'instance'):
                                ProductApp.instance.show_price_change_notification(
                                    product, latest_price, product.price, discount_percent
                                )
                    latest_ctaType = get_latest_ctaType(product.item_id)
                    if latest_ctaType is not None and latest_ctaType != product.get_cta_display():
                        if hasattr(ProductApp, 'instance'):
                            ProductApp.instance.show_ctaType_change_notification(
                                product, latest_ctaType, product.get_cta_display()
                            )
                save_price_history(
                    product.item_id, product.name, product.price, product.get_cta_display()
                )
    return sorted(
        unique_products,
        key=lambda x: (-x.get_discount_percentage(), x.price, x.get_cta_display() != "Còn hàng"),
    )


def init_db():
    conn = sqlite3.connect("price_history_hoangha.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            item_id TEXT,
            name TEXT,
            date TEXT,
            price REAL,
            ctaType TEXT,
            PRIMARY KEY (item_id, date)
        )
        """
    )
    conn.commit()
    conn.close()


def save_price_history(item_id, name, price, ctaType):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("price_history_hoangha.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price, ctaType FROM price_history WHERE item_id = ? AND date = ?",
        (item_id, today)
    )
    result = cursor.fetchone()
    if result is None:
        cursor.execute(
            "INSERT INTO price_history (item_id, name, date, price, ctaType) VALUES (?, ?, ?, ?, ?)",
            (item_id, name, today, price, ctaType)
        )
    else:
        if price != result[0] or ctaType != result[1]:
            cursor.execute(
                "UPDATE price_history SET price = ?, name = ?, ctaType = ? WHERE item_id = ? AND date = ?",
                (price, name, ctaType, item_id, today)
            )
        else:
            cursor.execute(
                "UPDATE price_history SET name = ? WHERE item_id = ? AND date = ?",
                (name, item_id, today)
            )
    conn.commit()
    conn.close()


def get_price_history(item_id):
    conn = sqlite3.connect("price_history_hoangha.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, date, price, ctaType FROM price_history WHERE item_id = ? ORDER BY date",
        (item_id,)
    )
    data = cursor.fetchall()
    conn.close()
    return data


def get_latest_price(item_id):
    conn = sqlite3.connect("price_history_hoangha.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price FROM price_history WHERE item_id = ? ORDER BY date DESC LIMIT 1",
        (item_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_latest_ctaType(item_id):
    conn = sqlite3.connect("price_history_hoangha.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ctaType FROM price_history WHERE item_id = ? ORDER BY date DESC LIMIT 1",
        (item_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_average_price(item_id):
    history = get_price_history(item_id)
    if not history:
        return None
    prices = [row[2] for row in history]
    return sum(prices) / len(prices)


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
        self.setWindowTitle("Danh sách sản phẩm Hoàng Hà Mobile")
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
        self.status_label = QLabel("Đang tải dữ liệu từ hoanghamobile.com...")
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
                       or (p.category and selected_category in p.category)
               )
               and (search_text in p.name.lower())
        ]

        for row, product in enumerate(filtered_products):
            self.table.insertRow(row)
            color = QtGui.QColor("green") if product.get_cta_display() == "Còn hàng" else QtGui.QColor("red")
            for col, value in enumerate(
                    [
                        product.name,
                        f"{int(product.price):,}₫".replace(",", "."),
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
            history_button.clicked.connect(lambda checked, p=product: self.show_price_history(p.item_id))
            self.table.setCellWidget(row, 5, history_button)

    def show_notification(self, product):
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Sản phẩm có hàng!",
                f"{product.name} đã có hàng. Mua ngay!",
                QSystemTrayIcon.Information,
                50000
            )

    def on_button_click(self, product, button):
        if product.get_cta_display() == "Còn hàng":
            QDesktopServices.openUrl(QUrl(product.url))
        else:
            if button.text() == "Thông báo khi có hàng":
                button.setText("Hủy thông báo")
                self.check_product_availability(product, button)
            else:
                button.setText("Thông báo khi có hàng")

    def on_refresh(self):
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Đang tải dữ liệu từ hoanghamobile.com...")
        self.status_label.setStyleSheet("color: blue;")
        self.notifications = []
        self.worker = Worker()
        self.worker.finished.connect(self.handle_load_products_result)
        self.worker.start()

    def generate_price_history_image(self, item_id):
        history = get_price_history(item_id)
        if not history:
            print(f"Không có dữ liệu lịch sử giá cho sản phẩm {item_id}")
            return None, None

        fig = plt.figure(figsize=(10, 6))
        dates = [datetime.strptime(row[1], "%Y-%m-%d") for row in history]
        prices = [row[2] for row in history]
        name = history[-1][0]

        plt.plot(dates, prices, marker='o', linestyle='-', color='b', label='Giá')
        plt.title(f"Lịch sử giá của {name} ({item_id})", fontsize=14)
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
        safe_item_id = sanitize_filename(item_id)
        image_path = f"price_history_{safe_item_id}.png"
        cid = f"price_history_{safe_item_id}"
        try:
            plt.savefig(image_path)
            plt.close(fig)
            print(f"Đã tạo biểu đồ cho {item_id} tại {image_path}")
            return image_path, cid
        except Exception as e:
            print(f"Lỗi khi lưu biểu đồ cho {item_id}: {e}")
            plt.close(fig)
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
        self.status_label.setText("Đã tải xong dữ liệu từ hoanghamobile.com")
        self.status_label.setStyleSheet("color: green;")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

        if self.notifications:
            email_subject = "Tổng hợp thay đổi sản phẩm Samsung từ Hoàng Hà Mobile"
            email_body = ""
            images = []

            price_change_notifications = [
                (message, item_id) for message, item_id in self.notifications
                if "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)" in message
            ]
            new_product_notifications = [
                (message, item_id) for message, item_id in self.notifications
                if "Sản phẩm mới" in message
            ]
            stock_and_price_notifications = [
                (message, item_id) for message, item_id in self.notifications
                if "Tình trạng sản phẩm thay đổi" in message
            ]

            price_change_notifications.sort(
                key=lambda x: float(x[0].split("Giảm giá so với giá trung bình:")[1].split("%")[0].strip()),
                reverse=True
            )

            sorted_notifications = price_change_notifications + new_product_notifications + stock_and_price_notifications

            for message, item_id in sorted_notifications:
                lines = message.split("\n")
                html_notification = "<h3>" + lines[0] + "</h3>"
                for line in lines[1:]:
                    if line and line != "-" * 50:
                        html_notification += "<p>" + line + "</p>"

                if "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)" in message or "Sản phẩm có hàng với giá tốt" in message:
                    image_path, cid = self.generate_price_history_image(item_id)
                    if image_path and cid:
                        images.append((image_path, cid))
                        html_notification += f'<p><img src="cid:{cid}" alt="Lịch sử giá {item_id}"></p>'
                    else:
                        html_notification += "<p>Không có dữ liệu lịch sử giá.</p>"

                html_notification += "<hr>"
                email_body += html_notification

            if sorted_notifications:
                send_email(email_subject, email_body, images)

                for image_path, _ in images:
                    if os.path.exists(image_path):
                        os.remove(image_path)

    def update_filters(self):
        categories = {"Tất cả"}
        statuses = {"Tất cả"}
        for p in self.products:
            if p.category:
                categories.update(p.category)
            statuses.add(p.get_cta_display())
        self.category_filter.clear()
        self.category_filter.addItems(["Tất cả"] + sorted(categories - {"Tất cả"}))
        self.cta_filter.clear()
        self.cta_filter.addItems(["Tất cả"] + sorted(statuses - {"Tất cả"}))

    def check_product_availability(self, product, button):
        if product.get_cta_display() == "Còn hàng":
            self.show_notification(product)
            button.setText("Mua ngay")

    def show_price_history(self, item_id):
        history = get_price_history(item_id)
        if not history:
            print(f"Không có dữ liệu lịch sử giá cho sản phẩm {item_id}")
            return

        fig = plt.figure(figsize=(10, 6))
        dates = [datetime.strptime(row[1], "%Y-%m-%d") for row in history]
        prices = [row[2] for row in history]
        name = history[-1][0]

        plt.plot(dates, prices, marker='o', linestyle='-', color='b', label='Giá')
        plt.title(f"Lịch sử giá của {name} ({item_id})", fontsize=14)
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
        plt.show()

    def show_ctaType_change_notification(self, product, old_ctaType, new_ctaType):
        if self.tray_icon:
            message = (
                f"{product.name}\n"
                f"Tình trạng: {new_ctaType}"
            )
            self.tray_icon.showMessage(
                "Tình trạng sản phẩm thay đổi",
                message,
                QSystemTrayIcon.Information,
                10000
            )
            notification_message = (
                f"Tình trạng sản phẩm thay đổi:\n"
                f"Sản phẩm: {product.name}\n"
                f"Tình trạng mới: {new_ctaType}\n"
                f"Link: {product.url}"
            )
            self.notifications.append((notification_message, product.item_id))

    def show_price_change_notification(self, product, old_price, new_price, discount_percent):
        if self.tray_icon:
            message = (
                f"{product.name}\n"
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
                f"Sản phẩm: {product.name}\n"
                f"Giá mới: {self.format_price(new_price)}\n"
                f"Giảm giá so với giá trung bình: {discount_percent}%\n"
                f"Link: {product.url}"
            )
            self.notifications.append((notification_message, product.item_id))

    def show_new_product_notification(self, product):
        if self.tray_icon:
            message = (
                f"Sản phẩm mới: {product.name}\n"
                f"Giá: {self.format_price(product.price)}\n"
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
                f"Sản phẩm: {product.name}\n"
                f"Giá: {self.format_price(product.price)}\n"
                f"Tình trạng: {product.get_cta_display()}\n"
                f"Link: {product.url}"
            )
            self.notifications.append((notification_message, product.item_id))

    def format_price(self, price):
        return f"{int(price):,}₫".replace(",", ".")


def main():
    import sys
    app = QApplication(sys.argv)
    main_win = ProductApp()
    main_win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    init_db()
    main()
