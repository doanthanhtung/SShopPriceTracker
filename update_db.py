import sqlite3

# Kết nối đến cơ sở dữ liệu
conn = sqlite3.connect("price_history.db")
cursor = conn.cursor()

# Thêm cột ctaType nếu chưa tồn tại
cursor.execute("ALTER TABLE price_history ADD COLUMN ctaType TEXT")

# Lưu thay đổi và đóng kết nối
conn.commit()
conn.close()

print("Cột ctaType đã được thêm vào bảng price_history.")