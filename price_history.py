import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt

DB_NAME = "price_history.db"


def init_db():
    """Khởi tạo database nếu chưa tồn tại với các trường model_code, displayName, date, price và ctaType."""
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
    conn.commit()
    conn.close()


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
        if price < result[0] or ctaType != result[1]:
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


def display_price_history_chart(model_code):
    """
    Hiển thị lịch sử giá của sản phẩm theo model_code dưới dạng biểu đồ đường.
    Chỉ hiển thị giá tại các mốc giá thay đổi.
    """
    history = get_price_history(model_code)

    if not history:
        print(f"Không tìm thấy lịch sử giá cho sản phẩm có mã {model_code}")
        return

    # Tách dữ liệu thành các danh sách riêng
    dates = [datetime.strptime(row[1], "%Y-%m-%d") for row in history]
    prices = [row[2] for row in history]
    display_name = history[-1][0]  # Lấy tên sản phẩm từ bản ghi cuối cùng

    # Tạo biểu đồ
    plt.figure(figsize=(10, 6))
    plt.plot(dates, prices, marker='o', linestyle='-', color='b', label='Giá')

    # Định dạng biểu đồ
    plt.title(f"Lịch sử giá của {display_name} ({model_code})", fontsize=14)
    plt.xlabel("Ngày", fontsize=12)
    plt.ylabel("Giá (VND)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)

    # Định dạng trục y với dấu chấm phân cách hàng nghìn
    plt.gca().get_yaxis().set_major_formatter(
        plt.FuncFormatter(lambda x, loc: "{:,.0f}".format(x).replace(',', '.'))
    )

    # Xoay nhãn ngày để dễ đọc
    plt.xticks(rotation=45)

    # Hiển thị giá trị chỉ tại các điểm giá thay đổi
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


# Khởi tạo database khi chạy
init_db()