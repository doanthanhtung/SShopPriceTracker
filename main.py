import requests
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, QUrl, Qt, QThread, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QTableView,
    QHBoxLayout,
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
import os
from pathlib import Path
import tempfile
from product_table import ProductTableModel, ProductActionDelegate, ProductDetailsDelegate
from ui_theme import APP_STYLESHEET
from email_delivery import DeliveryResult, EmailOutbox, send_queued_email, retry_queued_emails

# Cấu hình email
EMAIL_SENDER = "doanthanhtung.pc@gmail.com"
EMAIL_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_RECEIVERS = ["doanthanhtung.pc@gmail.com"]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Email credentials are supplied through environment variables.
EMAIL_SENDER = os.environ.get("SMTP_USERNAME", EMAIL_SENDER)
EMAIL_RECEIVERS = [address.strip() for address in os.environ.get(
    "SMTP_RECIPIENTS", ",".join(EMAIL_RECEIVERS)
).split(",") if address.strip()]
SMTP_SERVER = os.environ.get("SMTP_HOST", SMTP_SERVER)
SMTP_PORT = int(os.environ.get("SMTP_PORT", SMTP_PORT))
if SMTP_SERVER == "smtp.gmail.com":
    EMAIL_PASSWORD = EMAIL_PASSWORD.replace(" ", "")


def send_email(subject, body, images=None):
    """Lưu thư trước khi gửi, trả về kết quả thực tế để UI báo lỗi."""
    return send_queued_email(
        price_history.DB_NAME, SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD,
        EMAIL_RECEIVERS, subject, body, images,
    )


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
        self.averagePrice = price_history.get_average_price(modelCode)

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
        """Phần trăm giá hiện tại thấp hơn giá trung bình trong lịch sử."""
        if self.averagePrice and self.averagePrice > 0 and self.promotionPrice > 0:
            return round((1 - self.promotionPrice / self.averagePrice) * 100, 2)
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


def generate_price_history_image(model_code):
    """Tạo và lưu biểu đồ lịch sử giá dưới dạng ảnh, trả về đường dẫn file và CID."""
    fig = price_history.create_price_history_figure(model_code, headless=True)
    if fig is None:
        print(f"Không có dữ liệu lịch sử giá cho sản phẩm {model_code}")
        return None, None

    image_file = tempfile.NamedTemporaryFile(prefix="price_history_", suffix=".png", delete=False)
    image_path = image_file.name
    image_file.close()
    cid = f"price_history_{os.path.basename(image_path)}"
    try:
        fig.savefig(image_path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
        fig.clear()  # Đóng figure để giải phóng bộ nhớ
        print(f"Đã tạo biểu đồ cho {model_code} tại {image_path}")
        return image_path, cid
    except Exception as e:
        print(f"Lỗi khi lưu biểu đồ cho {model_code}: {e}")
        fig.clear()  # Đóng figure ngay cả khi có lỗi
        if os.path.exists(image_path):
            os.remove(image_path)
        return None, None


def prepare_notification_email(notifications):
    email_subject = "Tổng hợp thay đổi sản phẩm Samsung"
    email_body = ""
    images = []
    image_cache = {}

    # Lọc và sắp xếp thông báo
    price_change_notifications = [
        (message, model_code) for message, model_code in notifications
        if "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)" in message
    ]
    new_product_notifications = [
        (message, model_code) for message, model_code in notifications
        if "Sản phẩm mới" in message
    ]
    stock_and_price_notifications = [
        (message, model_code) for message, model_code in notifications
        if "Sản phẩm có hàng với giá tốt" in message
    ]
    availability_notifications = [
        (message, model_code) for message, model_code in notifications
        if "Sản phẩm đã có hàng" in message
    ]

    # Sắp xếp thông báo giảm giá theo phần trăm giảm
    price_change_notifications.sort(
        key=lambda x: float(x[0].split("Giảm giá so với giá trung bình:")[1].split("%")[0].strip()),
        reverse=True
    )

    # Gộp các thông báo đã sắp xếp
    sorted_notifications = (
        availability_notifications
        + price_change_notifications
        + stock_and_price_notifications
        + new_product_notifications
    )

    # Tạo nội dung email
    for message, model_code in sorted_notifications:
        lines = message.split("\n")
        html_notification = "<h3>" + html.escape(lines[0]) + "</h3>"
        for line in lines[1:]:
            if line and line != "-" * 50:
                html_notification += "<p>" + html.escape(line) + "</p>"

        # Thêm biểu đồ lịch sử giá cho thông báo giảm giá hoặc có hàng với giá tốt
        if "Giá sản phẩm thay đổi (Giảm dưới giá trung bình)" in message or "Sản phẩm có hàng với giá tốt" in message:
            if model_code not in image_cache:
                try:
                    image_cache[model_code] = generate_price_history_image(model_code)
                except Exception as exc:
                    print(f"Không tạo được biểu đồ email: {type(exc).__name__}")
                    image_cache[model_code] = (None, None)
                if image_cache[model_code][0]:
                    images.append(image_cache[model_code])
            image_path, cid = image_cache[model_code]
            if image_path and cid:
                html_notification += f'<p><img src="cid:{cid}" alt="Lịch sử giá {html.escape(model_code)}"></p>'
            else:
                html_notification += "<p>Không có dữ liệu lịch sử giá.</p>"

        html_notification += "<hr>"
        email_body += html_notification

    return email_subject, email_body, images


class EmailWorker(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, notifications, parent=None, retry_pending=False):
        super().__init__(parent)
        self.notifications = notifications
        self.retry_pending = retry_pending

    def run(self):
        images = []
        try:
            if self.retry_pending:
                result = retry_queued_emails(
                    price_history.DB_NAME, SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD,
                )
            else:
                subject, body, images = prepare_notification_email(self.notifications)
                result = send_email(subject, body, images)
            self.result_ready.emit(result)
        except Exception as exc:
            print(f"Không thể tạo email thông báo: {exc}")
            self.result_ready.emit(DeliveryResult(error=f"Không xử lý được email: {type(exc).__name__}"))
        finally:
            for image_path, _ in images:
                if os.path.exists(image_path):
                    os.remove(image_path)


class Worker(QThread):
    products_ready = pyqtSignal(list)
    batch_ready = pyqtSignal(list)
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)
    notification = pyqtSignal(str, tuple)

    def run(self):
        try:
            products = load_products(
                on_batch=self.batch_ready.emit,
                on_progress=self.progress.emit,
                on_error=self.error.emit,
                on_notification=self.notification.emit,
                cancelled=self.isInterruptionRequested,
            )
            self.products_ready.emit(products)
        except Exception as exc:
            self.error.emit(f"Không thể hoàn tất tải dữ liệu: {exc}")


def load_products(on_batch=None, on_progress=None, on_error=None,
                  on_notification=None, cancelled=lambda: False):
    """Fetch independent categories concurrently; persist and publish on one worker."""
    unique_products = {}
    subscriptions = price_history.get_availability_subscriptions()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_product_data, url): url for url in URL_LIST}
        for completed, future in enumerate(as_completed(futures), 1):
            if cancelled():
                for pending in futures:
                    pending.cancel()
                break
            batch = []
            try:
                data = future.result()
                product_list = data["response"]["resultData"]["productList"]
                if not isinstance(product_list, list):
                    raise ValueError("Danh sách sản phẩm không hợp lệ")
            except Exception as exc:
                if on_error:
                    on_error(f"Không tải được danh mục {futures[future]}: {exc}")
                if on_progress:
                    on_progress(completed, len(futures))
                continue
            for p in product_list:
                category_subtype = p.get("categorySubTypeEngName", "")
                if category_subtype == "Washing Machines Accessories":
                    continue
                for model in p.get("modelList", []):
                    code = model.get("modelCode")
                    if not code or code in unique_products:
                        continue
                    try:
                        float(model.get("price") or 0)
                        float(model.get("promotionPrice") or 0)
                    except (TypeError, ValueError):
                        if on_error:
                            on_error(f"Giá không hợp lệ: {code}")
                        continue
                    product = Product(
                        model.get("displayName") or code,
                        model.get("formattedPriceSave"),
                        model.get("modelCode"),
                        model.get("originPdpUrl"),
                        model.get("pdpUrl"),
                        model.get("price"),
                        model.get("priceDisplay") or "",
                        model.get("promotionPrice"),
                        model.get("ctaType") or "Không rõ",
                        model.get("pviSubtypeName"),
                        category_subtype,
                    )
                    unique_products[code] = product
                    batch.append(product)
                    if (on_notification and code in subscriptions and product.get_cta_display() == "Còn hàng"
                            and price_history.consume_availability_subscription(code)):
                        subscriptions.remove(code)
                        if on_notification:
                            on_notification("available", (product,))
                    if product.promotionPrice > 0:
                        latest_price = price_history.get_latest_price(product.modelCode)
                        average_price = product.averagePrice
                        if latest_price is None:
                            if on_notification:
                                on_notification("new", (product,))
                        else:
                            latest_ctaType = price_history.get_latest_ctaType(product.modelCode)
                            if latest_price != product.promotionPrice:
                                if average_price and product.promotionPrice < average_price * 0.9:  # Giảm ít nhất 10%
                                    discount_percent = round((1 - product.promotionPrice / average_price) * 100, 2)
                                    if on_notification:
                                        on_notification("price", (
                                            product, latest_price, product.promotionPrice, discount_percent
                                        ))
                            if latest_ctaType is not None and latest_ctaType != product.ctaType:
                                product.previous_min_price = price_history.get_min_price(product.modelCode)
                                if on_notification:
                                    on_notification("stock", (product, latest_ctaType, product.ctaType))
                        price_history.save_price_history(
                            product.modelCode, product.displayName, product.promotionPrice, product.ctaType
                        )
                    if len(batch) >= 25:
                        if on_batch:
                            on_batch(batch)
                        batch = []
            if batch and on_batch:
                on_batch(batch)
            if on_progress:
                on_progress(completed, len(futures))
    return sort_products(unique_products.values())


def sort_products(products, by_average_discount=False):
    """Sắp xếp danh sách mà không thay đổi thứ tự của dữ liệu gốc.

    Khi chưa có lịch sử giá, mức giảm so với trung bình là 0%, vì vậy các
    sản phẩm đó không được ưu tiên nhầm dựa trên giá niêm yết.
    """
    discount_getter = (
        lambda product: product.get_discount_from_average()
        if by_average_discount
        else product.get_discount_percentage()
    )
    return sorted(
        products,
        key=lambda product: (
            -discount_getter(product),
            product.price,
            product.get_cta_display() != "Còn hàng",
        ),
    )


class ProductApp(QMainWindow):
    instance = None

    def __init__(self):
        super().__init__()
        ProductApp.instance = self
        self.tray_icon = None
        self.notifications = []
        self.worker = None
        self.email_workers = []
        self.email_outbox = EmailOutbox(price_history.DB_NAME)
        self._last_email_error = ""
        self._closing = False
        self._loading = False
        self.init_tray_icon()
        self.init_ui()

    def init_tray_icon(self):
        tray_icon = QSystemTrayIcon(self)
        import os
        icon_path = str(Path(__file__).resolve().parent / "icon.png")
        if os.path.exists(icon_path):
            tray_icon.setIcon(QtGui.QIcon(icon_path))
        else:
            tray_icon.setIcon(QtGui.QIcon.fromTheme("info"))
        tray_icon.setVisible(True)
        self.tray_icon = tray_icon

    def init_ui(self):
        self.setWindowTitle("Danh sách sản phẩm")
        self.setGeometry(100, 100, 1280, 780)
        self.setMinimumSize(1040, 620)
        self.setStyleSheet(APP_STYLESHEET)

        central_widget = QWidget()
        central_widget.setObjectName("appRoot")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(22, 18, 22, 6)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)
        brand = QLabel("SShop")
        brand.setObjectName("brand")
        header_layout.addWidget(brand, 0, Qt.AlignVCenter)
        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Theo dõi giá Samsung")
        title.setObjectName("pageTitle")
        subtitle = QLabel("So sánh giá, kiểm tra hàng và theo dõi sản phẩm bạn quan tâm.")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header_layout.addLayout(heading, 1)

        self.auto_refresh_checkbox = QCheckBox("Tự cập nhật mỗi 5 phút")
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        header_layout.addWidget(self.auto_refresh_checkbox)
        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.setObjectName("primaryButton")
        self.refresh_button.setMinimumWidth(110)
        self.refresh_button.setToolTip("Cập nhật giá và tình trạng hàng (F5)")
        self.refresh_button.clicked.connect(self.on_refresh)
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        filter_panel = QtWidgets.QFrame()
        filter_panel.setObjectName("filterPanel")
        filter_layout = QHBoxLayout(filter_panel)
        filter_layout.setContentsMargins(16, 12, 16, 14)
        filter_layout.setSpacing(14)

        def add_field(label_text, widget, stretch=0):
            field = QVBoxLayout()
            field.setSpacing(5)
            label = QLabel(label_text)
            label.setObjectName("fieldLabel")
            label.setBuddy(widget)
            field.addWidget(label)
            field.addWidget(widget)
            filter_layout.addLayout(field, stretch)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Nhập tên hoặc mã sản phẩm…")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setAccessibleName("Tìm theo tên hoặc mã sản phẩm")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.update_table)
        self.search_bar.textChanged.connect(self.start_search_timer)
        add_field("Tìm kiếm", self.search_bar, 1)

        self.cta_filter = QComboBox()
        self.cta_filter.addItem("Tất cả")
        self.cta_filter.setFixedWidth(154)
        self.cta_filter.setAccessibleName("Lọc tình trạng hàng")
        self.cta_filter.currentIndexChanged.connect(self.update_table)
        add_field("Tình trạng", self.cta_filter)
        self.sort_filter = QComboBox()
        self.sort_filter.addItem("Giảm giá niêm yết", False)
        self.sort_filter.addItem("Giảm so với giá trung bình", True)
        self.sort_filter.setFixedWidth(234)
        self.sort_filter.setAccessibleName("Sắp xếp sản phẩm")
        self.sort_filter.setToolTip("Sắp xếp mức giảm giá từ cao xuống thấp.")
        self.sort_filter.currentIndexChanged.connect(self.update_table)
        add_field("Sắp xếp theo", self.sort_filter)
        self.clear_filters_button = QPushButton("Xóa bộ lọc")
        self.clear_filters_button.clicked.connect(self.clear_filters)
        filter_layout.addWidget(self.clear_filters_button, 0, Qt.AlignBottom)
        layout.addWidget(filter_panel)

        table_panel = QtWidgets.QFrame()
        table_panel.setObjectName("tablePanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(1, 1, 1, 1)
        table_layout.setSpacing(0)
        table_heading = QHBoxLayout()
        table_heading.setContentsMargins(16, 12, 16, 12)
        section_title = QLabel("Danh sách sản phẩm")
        section_title.setObjectName("sectionTitle")
        table_heading.addWidget(section_title)
        table_heading.addStretch()
        self.result_count_label = QLabel("Chưa có dữ liệu")
        self.result_count_label.setObjectName("resultCount")
        table_heading.addWidget(self.result_count_label)
        table_layout.addLayout(table_heading)

        self.table = QTableView()
        self.product_model = ProductTableModel(self.get_product_action_text, self.table)
        self.table.setModel(self.product_model)
        self.action_delegate = ProductActionDelegate(self.table)
        self.action_delegate.activated.connect(self.on_table_action)
        self.table.setItemDelegateForColumn(4, self.action_delegate)
        self.table.setItemDelegateForColumn(5, self.action_delegate)
        self.table.setMouseTracking(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.details_delegate = ProductDetailsDelegate(self.table)
        for column in (0, 1, 3):
            self.table.setItemDelegateForColumn(column, self.details_delegate)
        self.configure_table_columns()
        table_layout.addWidget(self.table, 1)
        layout.addWidget(table_panel, 1)
        self.empty_state = QLabel("Đang tải sản phẩm…", self.table.viewport())
        self.empty_state.setObjectName("emptyState")
        self.empty_state.setAlignment(Qt.AlignCenter)
        self.empty_state.setWordWrap(True)
        self.empty_state.setAttribute(Qt.WA_TransparentForMouseEvents)
        empty_layout = QVBoxLayout(self.table.viewport())
        empty_layout.addWidget(self.empty_state)

        email_layout = QHBoxLayout()
        self.email_controls = QWidget()
        self.email_controls.setObjectName("emailNotice")
        self.email_controls.setLayout(email_layout)
        email_layout.setContentsMargins(14, 8, 14, 8)
        self.email_status_label = QLabel("Email: sẵn sàng")
        self.email_status_label.setWordWrap(True)
        email_layout.addWidget(self.email_status_label, 1)
        self.email_retry_button = QPushButton("Gửi lại email")
        self.email_retry_button.clicked.connect(self.retry_failed_emails)
        email_layout.addWidget(self.email_retry_button)
        self.email_controls.hide()
        layout.addWidget(self.email_controls)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Đang tải dữ liệu từ samsung.com...")
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.status_opacity = QtWidgets.QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(self.status_opacity)
        self.status_bar.addWidget(self.status_label, 1)
        self.status_fade_timer = QTimer(self)
        self.status_fade_timer.setSingleShot(True)
        self.status_fade_timer.timeout.connect(self.fade_status_message)
        self.status_fade_animation = QPropertyAnimation(self.status_opacity, b"opacity", self)
        self.status_fade_animation.setDuration(900)
        self.status_fade_animation.setStartValue(1.0)
        self.status_fade_animation.setEndValue(0.0)
        self.status_fade_animation.finished.connect(self.status_label.hide)
        self.load_progress = QtWidgets.QProgressBar()
        self.load_progress.setFixedWidth(110)
        self.load_progress.setTextVisible(False)
        self.load_progress.hide()
        self.status_bar.addPermanentWidget(self.load_progress)
        self.last_updated_label = QLabel("F5  Làm mới")
        self.status_bar.addPermanentWidget(self.last_updated_label)
        self.search_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.focus_search)
        self.refresh_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self.on_refresh)

        self.products = []
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(100)
        self.render_timer.timeout.connect(self.render_pending_products)
        self.availability_subscriptions = price_history.get_availability_subscriptions()
        self.update_email_status()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_refresh)
        self.on_refresh()

    def focus_search(self):
        self.search_bar.setFocus()
        self.search_bar.selectAll()

    def set_status_message(self, message, color=None, fade_after_ms=None):
        self.status_fade_timer.stop()
        self.status_fade_animation.stop()
        self.status_opacity.setOpacity(1.0)
        self.status_label.show()
        self.status_label.setText(message)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
        if fade_after_ms is not None:
            self.status_fade_timer.start(fade_after_ms)

    def fade_status_message(self):
        if not self._loading:
            self.status_fade_animation.start()

    def clear_filters(self):
        self.search_bar.blockSignals(True)
        self.cta_filter.blockSignals(True)
        self.search_bar.clear()
        self.cta_filter.setCurrentText("Tất cả")
        self.search_bar.blockSignals(False)
        self.cta_filter.blockSignals(False)
        self.search_timer.stop()
        self.update_table()
        self.search_bar.setFocus()

    def start_search_timer(self):
        self.search_timer.start(200)

    def toggle_auto_refresh(self, state):
        if state == Qt.Checked:
            self.timer.start(300000)
        else:
            self.timer.stop()

    def update_table(self):
        selected_cta = self.cta_filter.currentText()
        search_text = self.search_bar.text().strip().casefold()

        filtered_products = [
            p
            for p in self.products
            if (selected_cta == "Tất cả" or p.get_cta_display() == selected_cta)
            and (search_text in p.displayName.casefold() or search_text in (p.modelCode or "").casefold())
        ]
        filtered_products = sort_products(
            filtered_products,
            by_average_discount=self.sort_filter.currentData(),
        )

        scroll = self.table.verticalScrollBar().value()
        selected = self.table.currentIndex()
        selected_product = selected.data(Qt.UserRole) if selected.isValid() else None
        self.product_model.set_discount_basis(self.sort_filter.currentData())
        self.product_model.set_products(filtered_products)
        if selected_product is not None:
            for row, product in enumerate(filtered_products):
                if product.modelCode == selected_product.modelCode:
                    self.table.setCurrentIndex(self.product_model.index(row, max(selected.column(), 0)))
                    break
        self.table.verticalScrollBar().setValue(scroll)
        available = sum(p.get_cta_display() == "Còn hàng" for p in filtered_products)
        self.result_count_label.setText(f"{len(filtered_products)} / {len(self.products)} sản phẩm  ·  {available} còn hàng")
        has_filters = bool(search_text or selected_cta != "Tất cả")
        self.clear_filters_button.setEnabled(has_filters)
        self.empty_state.setVisible(not filtered_products)
        if not filtered_products:
            if has_filters:
                message = "Không tìm thấy sản phẩm phù hợp.\nThử từ khóa khác hoặc bấm Xóa bộ lọc."
            elif self._loading:
                message = "Đang tải sản phẩm…\nDanh sách sẽ hiển thị ngay khi có dữ liệu."
            else:
                message = "Chưa có sản phẩm để hiển thị.\nBấm Làm mới để tải lại danh sách."
            self.empty_state.setText(message)

    def configure_table_columns(self):
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for col in range(1, 6):
            header.setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)

        header.setMinimumSectionSize(64)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setColumnWidth(1, 148)
        self.table.setColumnWidth(2, 86)
        self.table.setColumnWidth(3, 116)
        self.table.setColumnWidth(4, 148)
        self.table.setColumnWidth(5, 108)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(58)

    def show_notification(self, product):
        message = f"{product.displayName} đã có hàng. Mua ngay!"
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Sản phẩm có hàng!",
                message,
                QSystemTrayIcon.Information,
                50000
            )
        self.notifications.append((
            "Sản phẩm đã có hàng:\n"
            f"Sản phẩm: {product.displayName}\n"
            f"Giá hiện tại: {self.format_price(product.promotionPrice)}\n"
            f"Link: http://samsung.com{product.pdpUrl}",
            product.modelCode,
        ))

    def on_table_action(self, product, column):
        if column == 4:
            self.on_button_click(product)
        elif column == 5:
            self.show_price_history(product.modelCode)

    def on_button_click(self, product, button=None):
        if product.get_cta_display() == "Còn hàng":
            QDesktopServices.openUrl(QUrl("http://samsung.com" + product.pdpUrl))
            return

        if product.modelCode in self.availability_subscriptions:
            price_history.unsubscribe_from_availability(product.modelCode)
            self.availability_subscriptions.remove(product.modelCode)
            self.set_status_message(f"Đã hủy theo dõi: {product.displayName}", "green")
        else:
            price_history.subscribe_to_availability(product.modelCode, product.displayName)
            self.availability_subscriptions.add(product.modelCode)
            self.set_status_message(f"Đã bật thông báo có hàng: {product.displayName}", "green")
        self.product_model.refresh_actions()

    def on_refresh(self):
        if self._loading or self._closing:
            return
        self._loading = True
        self.load_errors = []
        self._received_products = {}
        self._display_products = {p.modelCode: p for p in self.products}
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Đang tải…")
        self.load_progress.setRange(0, len(URL_LIST))
        self.load_progress.setValue(0)
        self.load_progress.show()
        self.update_table()
        self.set_status_message("Đang tải dữ liệu từ samsung.com...", "#245fe5")
        self.notifications = []
        self._desktop_notification_count = 0
        self.worker = Worker(self)
        self.worker.batch_ready.connect(self.handle_product_batch)
        self.worker.progress.connect(self.handle_load_progress)
        self.worker.error.connect(self.handle_load_error)
        self.worker.notification.connect(self.handle_worker_notification)
        self.worker.products_ready.connect(self.handle_load_products_result)
        self.worker.finished.connect(self.finish_loading)
        self.worker.start()

    def handle_product_batch(self, products):
        for product in products:
            self._received_products[product.modelCode] = product
            self._display_products[product.modelCode] = product
        self.products = list(self._display_products.values())
        if not self.render_timer.isActive():
            self.render_timer.start()

    def render_pending_products(self):
        self.update_filters()
        self.update_table()

    def handle_load_progress(self, completed, total):
        self.load_progress.setRange(0, total)
        self.load_progress.setValue(completed)
        self.set_status_message(
            f"Đang tải: {completed}/{total} danh mục · "
            f"{len(self._received_products)} sản phẩm · {len(self.load_errors)} lỗi"
        )

    def handle_load_error(self, message):
        self.load_errors.append(message)
        self.status_label.setToolTip("\n".join(self.load_errors))

    def handle_worker_notification(self, kind, args):
        if self._closing:
            return
        if kind == "available":
            self.availability_subscriptions.discard(args[0].modelCode)
            self.show_notification(args[0])
            self.product_model.refresh_actions()
            return
        handlers = {"new": self.show_new_product_notification,
                    "price": self.show_price_change_notification,
                    "stock": self.show_ctaType_change_notification}
        handlers[kind](*args)

    def finish_loading(self):
        self._loading = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Làm mới")
        self.load_progress.hide()
        self.render_timer.stop()
        self.render_pending_products()
        if self.load_errors:
            self.set_status_message(
                f"Tải chưa đầy đủ: {len(self._received_products)} sản phẩm mới cập nhật · "
                f"{len(self.load_errors)} lỗi. Giữ dữ liệu cũ; bấm Làm mới để thử lại.",
                "#b45309",
            )
        else:
            self.set_status_message(
                f"Đã tải xong {len(self.products)} sản phẩm",
                "#21734e",
                fade_after_ms=3000,
            )
            self.status_label.setToolTip("")
            from datetime import datetime
            self.last_updated_label.setText(f"Cập nhật lúc {datetime.now():%H:%M}")
        self.worker.deleteLater()
        self.worker = None
        count = getattr(self, "_desktop_notification_count", 0)
        if count and self.tray_icon and not self._closing:
            self.tray_icon.showMessage(
                "Cập nhật sản phẩm", f"Có {count} thay đổi sản phẩm. Xem danh sách và email tổng hợp.",
                QSystemTrayIcon.Information, 5000,
            )

    def show_desktop_message(self, title, message, icon, duration):
        if self._loading:
            # Hundreds of native tray calls can monopolize the GUI event queue.
            self._desktop_notification_count = getattr(self, "_desktop_notification_count", 0) + 1
        elif self.tray_icon and not self._closing:
            self.tray_icon.showMessage(title, message, icon, duration)

    def closeEvent(self, event):
        running = self._loading or bool(self.email_workers)
        if running:
            self._closing = True
            self.timer.stop()
            if self.worker:
                self.worker.requestInterruption()
            self.hide()
            event.ignore()
            QTimer.singleShot(100, self.close)
            return
        event.accept()

    def handle_load_products_result(self, products):
        if self._closing:
            return
        self.products = list(self._display_products.values()) if self.load_errors else products

        self.update_filters()
        self.update_table()

        if self.notifications:
            worker = EmailWorker(list(self.notifications), self)
            self.queue_email_worker(worker)

    def queue_email_worker(self, worker):
        self.email_workers.append(worker)
        worker.result_ready.connect(self.handle_email_result)
        worker.finished.connect(lambda w=worker: self.release_email_worker(w))
        self.email_retry_button.setEnabled(False)
        if len(self.email_workers) == 1:
            self.email_status_label.setText("Email: đang gửi...")
            worker.start()

    def handle_email_result(self, result):
        if result.error:
            self._last_email_error = result.error
            pending, _ = self.email_outbox.summary()
            if self.tray_icon and not self._closing:
                self.tray_icon.showMessage(
                    "Không gửi được email",
                    f"{result.error}\nThư còn trong hàng đợi ({pending} chưa hoàn tất).",
                    QSystemTrayIcon.Warning,
                    10000,
                )
        self.update_email_status(result)

    def update_email_status(self, result=None):
        pending, _ = self.email_outbox.summary()
        self.email_retry_button.setEnabled(bool(pending) and not self.email_workers)
        if pending:
            if not self._last_email_error:
                self._last_email_error = self.email_outbox.latest_error()
            text = f"Email: {pending} thư chưa gửi xong. {self._last_email_error}"
            self.email_status_label.setStyleSheet("color: #b45309;")
        elif result is not None and result.error:
            text = f"Email: {result.error}"
            self.email_status_label.setStyleSheet("color: #b45309;")
        elif result is not None and result.accepted:
            self._last_email_error = ""
            text = f"Email: SMTP đã nhận thư cho {result.accepted} người nhận."
            self.email_status_label.setStyleSheet("color: green;")
        else:
            text = "Email: sẵn sàng" if not self._last_email_error else f"Email: {self._last_email_error}"
        self.email_status_label.setText(text.strip())
        self.email_status_label.setToolTip(text.strip())
        self.email_controls.setVisible(bool(self._last_email_error or (pending and not self.email_workers)))

    def retry_failed_emails(self):
        if self.email_workers or self._closing:
            return
        pending, uncertain = self.email_outbox.summary()
        if not pending:
            return
        if uncertain and QtWidgets.QMessageBox.question(
            self, "Gửi lại email",
            "Một số thư chưa có xác nhận từ SMTP và có thể đã được gửi. Gửi lại có thể trùng thư. Tiếp tục?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No,
        ) != QtWidgets.QMessageBox.Yes:
            return
        self.queue_email_worker(EmailWorker([], self, retry_pending=True))

    def release_email_worker(self, worker):
        self.email_workers.remove(worker)
        worker.deleteLater()
        if self.email_workers:
            self.email_status_label.setText("Email: đang gửi...")
            self.email_workers[0].start()
        else:
            pending, _ = self.email_outbox.summary()
            self.email_retry_button.setEnabled(bool(pending))
            self.email_controls.setVisible(bool(pending or self._last_email_error))

    def update_filters(self):
        selected = self.cta_filter.currentText()
        statuses = {"Tất cả"}
        for p in self.products:
            statuses.add(p.get_cta_display())
        # Preserve a selected status even before its category finishes loading.
        if selected:
            statuses.add(selected)
        self.cta_filter.blockSignals(True)
        self.cta_filter.clear()
        self.cta_filter.addItems(["Tất cả"] + sorted(statuses - {"Tất cả"}))
        self.cta_filter.setCurrentText(selected or "Tất cả")
        self.cta_filter.blockSignals(False)

    def get_product_action_text(self, product):
        if product.get_cta_display() == "Còn hàng":
            return "Mua ngay"
        if product.modelCode in self.availability_subscriptions:
            return "Hủy theo dõi"
        return "Báo khi có hàng"

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
                min_price = getattr(product, "previous_min_price", None)
                average_price = product.averagePrice
                if (min_price is not None and product.promotionPrice <= min_price) and \
                        (
                                average_price is not None and product.promotionPrice <= average_price * 0.85):  # Giá hiện tại thấp hơn 15% giá trung bình
                    message = (
                        f"{product.displayName}\n"
                        f"Tình trạng: {new_status}\n"
                        f"Giá hiện tại: {self.format_price(product.promotionPrice)}\n"
                        f"Giá thấp nhất trước đây: {self.format_price(min_price)}"
                    )
                    self.show_desktop_message(
                        "Sản phẩm có hàng với giá tốt",
                        message,
                        QSystemTrayIcon.Information,
                        10000
                    )
                    notification_message = (
                        f"Sản phẩm có hàng với giá tốt:\n"
                        f"Sản phẩm: {product.displayName}\n"
                        f"Tình trạng: {new_status}\n"
                        f"Giá hiện tại: {self.format_price(product.promotionPrice)}\n"
                        f"Giá thấp nhất trước đây: {self.format_price(min_price)}\n"
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
            self.show_desktop_message(
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
            self.show_desktop_message(
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
