import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import statistics

DB_NAME = "price_history.db"


def init_db():
    """Khởi tạo dữ liệu lịch sử giá và các đăng ký thông báo có hàng."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            model_code TEXT,
            displayName TEXT,
            date TEXT,
            price INTEGER,
            ctaType TEXT,
            PRIMARY KEY (model_code, date)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS availability_subscriptions (
            model_code TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            subscribed_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def subscribe_to_availability(model_code, display_name):
    """Đăng ký nhận đúng một thông báo khi sản phẩm có hàng.

    ``model_code`` là khóa chính để cùng một sản phẩm không thể bị đăng ký
    nhiều lần, kể cả sau khi ứng dụng được khởi động lại.
    """
    now = datetime.now().isoformat(timespec="seconds")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO availability_subscriptions (model_code, display_name, subscribed_at)
        VALUES (?, ?, ?)
        ON CONFLICT(model_code) DO UPDATE SET
            display_name = excluded.display_name
        """,
        (model_code, display_name, now),
    )
    conn.commit()
    conn.close()


def unsubscribe_from_availability(model_code):
    """Hủy đăng ký thông báo có hàng cho một sản phẩm."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM availability_subscriptions WHERE model_code = ?", (model_code,)
    )
    conn.commit()
    conn.close()


def get_availability_subscriptions():
    """Trả về các mã sản phẩm đang được theo dõi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT model_code FROM availability_subscriptions")
    subscriptions = {row[0] for row in cursor.fetchall()}
    conn.close()
    return subscriptions


def consume_availability_subscription(model_code):
    """Đánh dấu một đăng ký đã được xử lý và trả về liệu nó có tồn tại.

    Xóa trước khi hiển thị thông báo giúp một sản phẩm chỉ báo một lần, kể cả
    khi có nhiều lượt làm mới gần nhau.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM availability_subscriptions WHERE model_code = ?", (model_code,)
    )
    consumed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return consumed


def save_price_history(model_code, displayName, price, ctaType):
    """
    Lưu lịch sử giá và tình trạng của sản phẩm theo model_code.
    Nếu chưa có dữ liệu của ngày hôm nay thì INSERT, còn nếu đã có:
      - Cập nhật giá nếu giá mới thấp hơn giá đã lưu.
      - Cập nhật ctaType nếu có thay đổi.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    price = int(price)  # Ép kiểu về INTEGER

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Kiểm tra xem đã có dữ liệu cho model_code và ngày hôm nay chưa
    cursor.execute(
        "SELECT price, ctaType FROM price_history WHERE model_code = ? AND date = ?",
        (model_code, today)
    )
    result = cursor.fetchone()

    if result is None:
        # Chưa có dữ liệu, thêm mới
        cursor.execute(
            "INSERT INTO price_history (model_code, displayName, date, price, ctaType) VALUES (?, ?, ?, ?, ?)",
            (model_code, displayName, today, price, ctaType)
        )
    else:
        # Đã có dữ liệu, cập nhật displayName, giá (nếu thấp hơn), và ctaType
        if price != result[0] or ctaType != result[1]:
            cursor.execute(
                "UPDATE price_history SET price = ?, displayName = ?, ctaType = ? WHERE model_code = ? AND date = ?",
                (price, displayName, ctaType, model_code, today)
            )
        else:
            cursor.execute(
                "UPDATE price_history SET displayName = ? WHERE model_code = ? AND date = ?",
                (displayName, model_code, today)
            )

    conn.commit()
    conn.close()


def get_price_history(model_code):
    """Lấy lịch sử giá và tình trạng (cùng với displayName) của sản phẩm theo model_code."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT displayName, date, price, ctaType FROM price_history WHERE model_code = ? ORDER BY date",
        (model_code,)
    )
    data = cursor.fetchall()
    conn.close()
    return data  # Trả về list các tuple (displayName, date, price, ctaType)


def get_latest_price(model_code):
    """Lấy giá mới nhất của sản phẩm từ cơ sở dữ liệu theo model_code."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price FROM price_history WHERE model_code = ? ORDER BY date DESC LIMIT 1",
        (model_code,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_latest_ctaType(model_code):
    """Lấy tình trạng mới nhất của sản phẩm từ cơ sở dữ liệu theo model_code."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ctaType FROM price_history WHERE model_code = ? ORDER BY date DESC LIMIT 1",
        (model_code,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_average_price(model_code):
    """Tính giá trung bình của sản phẩm dựa trên lịch sử giá."""
    history = get_price_history(model_code)
    if not history:
        return None
    prices = [row[2] for row in history]
    return statistics.mean(prices)


def get_min_price(model_code):
    """Lấy giá thấp nhất của sản phẩm từ cơ sở dữ liệu theo model_code."""
    history = get_price_history(model_code)
    if not history:
        return None
    prices = [row[2] for row in history]
    return min(prices)


def format_price(price):
    """Định dạng giá VND nhất quán trên biểu đồ."""
    return f"{int(round(price)):,} ₫".replace(",", ".")


def create_price_history_figure(model_code):
    """Tạo biểu đồ lịch sử giá có thể dùng cho giao diện và email."""
    history = get_price_history(model_code)
    if not history:
        return None

    dates = [datetime.strptime(row[1], "%Y-%m-%d") for row in history]
    prices = [row[2] for row in history]
    display_name = history[-1][0]
    average_price = statistics.mean(prices)
    lowest_price = min(prices)
    current_price = prices[-1]
    first_price = prices[0]

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(11.5, 6.8), facecolor="#F8FAFC")
    ax.set_facecolor("#FFFFFF")

    ax.step(dates, prices, where="mid", color="#2563EB", linewidth=2.6, label="Giá ghi nhận")
    ax.fill_between(dates, prices, [min(prices)] * len(prices), step="mid", color="#DBEAFE", alpha=0.72)
    ax.axhline(
        average_price,
        color="#64748B",
        linewidth=1.4,
        linestyle=(0, (4, 3)),
        label=f"Trung bình: {format_price(average_price)}",
    )

    unique_annotation_indexes = []
    for index in (0, prices.index(lowest_price), len(prices) - 1):
        if index not in unique_annotation_indexes:
            unique_annotation_indexes.append(index)

    for index in unique_annotation_indexes:
        is_current = index == len(prices) - 1
        color = "#16A34A" if is_current else "#2563EB"
        ax.scatter(dates[index], prices[index], s=70, color=color, edgecolor="#FFFFFF", linewidth=1.8, zorder=3)
        label = "Hiện tại" if is_current else "Thấp nhất" if prices[index] == lowest_price else "Bắt đầu"
        ax.annotate(
            f"{label}\n{format_price(prices[index])}",
            (dates[index], prices[index]),
            xytext=(0, 14),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#0F172A",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "#FFFFFF", "edgecolor": "#CBD5E1"},
        )

    price_range = max(prices) - lowest_price
    vertical_padding = max(price_range * 0.18, max(current_price, 1) * 0.04)
    ax.set_ylim(max(0, lowest_price - vertical_padding), max(prices) + vertical_padding)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: format_price(value)))
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.9)
    ax.grid(axis="x", visible=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#CBD5E1")
    ax.tick_params(colors="#475569", labelsize=9)
    ax.set_ylabel("Giá bán", color="#475569", labelpad=12)
    ax.set_xlabel("Thời điểm ghi nhận", color="#475569", labelpad=10)

    title = display_name if len(display_name) <= 72 else f"{display_name[:69]}..."
    fig.suptitle(title, x=0.08, y=0.97, ha="left", fontsize=15, fontweight="bold", color="#0F172A")
    ax.set_title(
        f"Mã {model_code}  •  Hiện tại {format_price(current_price)}  •  "
        f"Thay đổi {format_price(current_price - first_price)}",
        loc="left",
        fontsize=9.5,
        color="#64748B",
        pad=18,
    )
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    fig.tight_layout(rect=(0.04, 0.04, 0.98, 0.91))

    hover_marker = ax.scatter([], [], s=110, color="#F59E0B", edgecolor="#FFFFFF", linewidth=2, zorder=4)
    hover_tooltip = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(16, -16),
        textcoords="offset points",
        fontsize=9,
        color="#FFFFFF",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#0F172A", "edgecolor": "none", "alpha": 0.95},
        arrowprops={"arrowstyle": "-", "color": "#64748B", "linewidth": 1},
        zorder=5,
    )
    hover_tooltip.set_visible(False)
    hover_marker.set_visible(False)
    date_numbers = mdates.date2num(dates)

    def on_hover(event):
        if event.inaxes != ax or event.x is None or event.y is None:
            if hover_tooltip.get_visible():
                hover_tooltip.set_visible(False)
                hover_marker.set_visible(False)
                fig.canvas.draw_idle()
            return

        point_pixels = [ax.transData.transform((date_number, price)) for date_number, price in zip(date_numbers, prices)]
        closest_index = min(
            range(len(point_pixels)),
            key=lambda index: (point_pixels[index][0] - event.x) ** 2 + (point_pixels[index][1] - event.y) ** 2,
        )
        distance = ((point_pixels[closest_index][0] - event.x) ** 2 + (point_pixels[closest_index][1] - event.y) ** 2) ** 0.5
        if distance > 18:
            if hover_tooltip.get_visible():
                hover_tooltip.set_visible(False)
                hover_marker.set_visible(False)
                fig.canvas.draw_idle()
            return

        status = "Còn hàng" if history[closest_index][3] in ["whereToBuy", "preOrder"] else "Hết hàng"
        hover_tooltip.xy = (dates[closest_index], prices[closest_index])
        hover_tooltip.set_text(
            f"{dates[closest_index].strftime('%d/%m/%Y')}\n"
            f"{format_price(prices[closest_index])}\n"
            f"{status}"
        )
        hover_tooltip.set_visible(True)
        hover_marker.set_offsets([(date_numbers[closest_index], prices[closest_index])])
        hover_marker.set_visible(True)
        fig.canvas.draw_idle()

    callback_id = fig.canvas.mpl_connect("motion_notify_event", on_hover)
    fig._price_history_hover = (hover_marker, hover_tooltip, callback_id)
    return fig


def display_price_history_chart(model_code):
    """Hiển thị biểu đồ lịch sử giá theo phong cách thống nhất."""
    fig = create_price_history_figure(model_code)
    if fig is None:
        print(f"Không tìm thấy lịch sử giá cho sản phẩm có mã {model_code}")
        return
    plt.show()


# Khởi tạo database khi chạy
init_db()
