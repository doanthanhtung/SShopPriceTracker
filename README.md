# SShop Price Tracker

Ứng dụng desktop theo dõi giá và tình trạng hàng của sản phẩm Samsung Việt Nam. Ứng dụng lấy dữ liệu từ API Samsung, lưu lịch sử vào SQLite, hỗ trợ cảnh báo và giúp người dùng nhận diện các mức giá tốt theo dữ liệu đã ghi nhận.

## Chức năng chính

- Tải danh sách sản phẩm từ nhiều danh mục Samsung Việt Nam.
- Tìm kiếm, lọc theo danh mục và trạng thái còn/hết hàng.
- Làm mới thủ công hoặc tự động mỗi 5 phút.
- Mở nhanh trang sản phẩm để mua hàng.
- Lưu lịch sử giá và trạng thái vào SQLite.
- Xem biểu đồ lịch sử giá với giá hiện tại, mức thấp nhất, giá trung bình và tooltip khi rê chuột vào mốc dữ liệu.
- Sắp xếp theo mức giảm so với giá niêm yết hoặc giá trung bình lịch sử.
- Đăng ký thông báo có hàng theo từng sản phẩm; đăng ký được lưu qua các lần khởi động và tự hủy sau khi đã báo.
- Cảnh báo desktop/email cho sản phẩm mới, giảm giá đáng kể và sản phẩm có hàng với giá tốt.
- Đồng bộ sản phẩm biến mất khỏi API sang trạng thái hết hàng bằng script riêng.

## Yêu cầu

- Python 3.10 trở lên
- Windows, macOS hoặc Linux có môi trường đồ họa cho PyQt5/Matplotlib
- Kết nối Internet để truy cập API Samsung và SMTP nếu bật email

## Cài đặt và chạy

```powershell
git clone https://github.com/doanthanhtung/SShopPriceTracker.git
cd SShopPriceTracker

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install requests PyQt5 matplotlib

python main.py
```

Khi chạy lần đầu, ứng dụng tự tạo file `price_history.db` và các bảng cần thiết.

## Cách sử dụng

1. Bấm **Làm mới** để tải giá và trạng thái mới nhất.
2. Dùng ô tìm kiếm và bộ lọc để thu hẹp danh sách.
3. Với sản phẩm hết hàng, bấm **Thông báo khi có hàng**. Nút chuyển thành **Hủy theo dõi** khi đăng ký thành công.
4. Với sản phẩm đang có hàng, bấm **Mua ngay** để mở trang Samsung.
5. Bấm **Xem lịch sử giá** để mở biểu đồ; rê chuột gần một mốc để xem ngày, giá và trạng thái tại thời điểm đó.
6. Bật **Sắp xếp theo giảm giá so với giá trung bình** để ưu tiên các sản phẩm có giá hiện tại thấp hơn mức trung bình lịch sử.

## Dữ liệu và đồng bộ trạng thái

Database SQLite chứa hai bảng chính:

| Bảng | Mục đích |
| --- | --- |
| `price_history` | Giá và trạng thái của từng model theo ngày. |
| `availability_subscriptions` | Các sản phẩm người dùng đang theo dõi tình trạng có hàng. |

Để rà soát những model không còn xuất hiện trong API và cập nhật thành hết hàng:

```powershell
python sync_outOfStock_status.py
```

Chỉ chạy script này khi các endpoint Samsung tải thành công; lỗi mạng có thể khiến kết quả API không đầy đủ.

## Cấu hình email và bảo mật

Email được dùng để gửi bản tổng hợp cảnh báo. Cấu hình SMTP hiện nằm ở đầu file `main.py`.

Không commit mật khẩu, Gmail App Password hoặc danh sách người nhận vào repository. Nếu thông tin nhạy cảm đã từng được commit, hãy thu hồi/đổi ngay và chuyển cấu hình sang biến môi trường hoặc file `.env` được đưa vào `.gitignore`.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
python -m py_compile main.py price_history.py
```

Các kiểm thử hiện kiểm tra đăng ký thông báo có hàng, cơ chế chỉ báo một lần, sắp xếp theo giá trung bình và biểu đồ lịch sử giá.

## Cấu trúc mã nguồn

```text
main.py                       # Giao diện PyQt5, tải dữ liệu và luồng cảnh báo
price_history.py              # Truy cập SQLite và biểu đồ lịch sử giá
sync_outOfStock_status.py     # Đồng bộ model biến mất khỏi API thành hết hàng
tests/                        # Kiểm thử tự động
price_history.db              # Dữ liệu SQLite cục bộ
```

## Hướng phát triển khuyến nghị

- Chuyển cấu hình email sang biến môi trường.
- Tách tác vụ mạng/SMTP khỏi UI thread.
- Lưu snapshot theo timestamp nếu cần theo dõi biến động giá trong ngày.
- Không version-control dữ liệu SQLite vận hành; chỉ version-control schema hoặc migration.
