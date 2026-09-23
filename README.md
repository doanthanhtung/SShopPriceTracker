# SShop Price Tracker

Ứng dụng desktop theo dõi giá và tình trạng hàng của sản phẩm Samsung Việt Nam. Ứng dụng lấy dữ liệu từ API Samsung, lưu lịch sử vào SQLite, hỗ trợ cảnh báo và giúp người dùng nhận diện các mức giá tốt theo dữ liệu đã ghi nhận.

## Chức năng chính

- Tải song song tối đa 4 danh mục Samsung; hiển thị dần theo nhóm tối đa 25 sản phẩm, không chờ toàn bộ danh sách.
- Hiển thị tiến độ tải và số lỗi; giữ dữ liệu cũ khi làm mới hoặc khi kết nối bị lỗi.
- Bảng chỉ vẽ các ô đang hiển thị, cho phép cuộn/tìm kiếm trong khi tải; việc dựng biểu đồ email và gửi SMTP chạy nền.
- Thanh tìm kiếm theo tên/mã sản phẩm, lọc tình trạng và chọn cách sắp xếp nằm cùng một khu vực.
- Bảng hiển thị giá hiện tại, giá niêm yết, mã sản phẩm và nhãn tồn kho; có số kết quả và hướng dẫn khi không tìm thấy sản phẩm.
- Làm mới thủ công hoặc tự động mỗi 5 phút.
- Mở nhanh trang sản phẩm để mua hàng.
- Lưu lịch sử giá và trạng thái vào SQLite.
- Xem biểu đồ lịch sử giá với giá hiện tại, mức thấp nhất, giá trung bình và tooltip khi rê chuột vào mốc dữ liệu.
- Sắp xếp theo mức giảm so với giá niêm yết hoặc giá trung bình lịch sử.
- Đăng ký thông báo có hàng theo từng sản phẩm; đăng ký được lưu qua các lần khởi động và tự hủy sau khi đã báo.
- Cảnh báo desktop/email cho sản phẩm mới, giảm giá đáng kể và sản phẩm có hàng với giá tốt.
- Các thay đổi tự động được gộp thành một thông báo desktop cuối lượt tải để tránh hàng loạt popup; email vẫn chứa chi tiết từng thay đổi.
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

### Tạo ứng dụng Windows dạng `.exe`

Trong PowerShell, cài PyInstaller vào môi trường ảo rồi build:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --distpath . SShopPriceTracker.spec
```

File `SShopPriceTracker.exe` được tạo ngay trong thư mục dự án và chạy không mở cửa sổ CMD. Giữ `price_history.db` cạnh file `.exe` để tiếp tục dùng lịch sử giá hiện có; nếu chưa có, ứng dụng sẽ tự tạo cơ sở dữ liệu mới.

## Cách sử dụng

1. Bấm **Làm mới** hoặc **F5** để tải giá và trạng thái mới nhất. Tùy chọn tự cập nhật nằm ngay cạnh nút làm mới.
2. Dùng **Ctrl+F** để tìm theo tên hoặc mã sản phẩm; chọn tình trạng để thu hẹp danh sách. **Xóa bộ lọc** xóa từ khóa và lọc tình trạng, giữ cách sắp xếp hiện tại.
3. Với sản phẩm hết hàng, bấm **Báo khi có hàng**. Nút chuyển thành **Hủy theo dõi** khi đăng ký thành công.
4. Với sản phẩm đang có hàng, bấm **Mua ngay** để mở trang Samsung.
5. Bấm **Lịch sử** để mở biểu đồ; rê chuột gần một mốc để xem ngày, giá và trạng thái tại thời điểm đó.
6. Trong **Sắp xếp theo**, chọn **Giảm so với giá trung bình** để ưu tiên giá tốt so với lịch sử. Cột phần trăm chuyển sang **So với TB** để khớp cách sắp xếp; sản phẩm chưa có lịch sử hiển thị dấu gạch ngang.

Bạn có thể tìm kiếm/lọc ngay trong lúc tải. Bộ lọc và vị trí cuộn được giữ khi bảng cập nhật; lượt tự động làm mới sẽ bỏ qua nếu lượt trước còn chạy. Nếu báo **Tải chưa đầy đủ**, một phần danh sách có thể là dữ liệu cũ: rê chuột vào trạng thái để xem lỗi và bấm **Làm mới** để thử lại.

## Dữ liệu và đồng bộ trạng thái

Database SQLite chứa các bảng:

| Bảng | Mục đích |
| --- | --- |
| `price_history` | Giá và trạng thái của từng model theo ngày. |
| `availability_subscriptions` | Các sản phẩm người dùng đang theo dõi tình trạng có hàng. |
| `email_outbox` | Thư chưa được SMTP xác nhận: lưu cả nội dung và ảnh, giữ lại qua lần đóng/mở app. |

Để rà soát những model không còn xuất hiện trong API và cập nhật thành hết hàng:

```powershell
python sync_outOfStock_status.py
```

Chỉ chạy script này khi các endpoint Samsung tải thành công; lỗi mạng có thể khiến kết quả API không đầy đủ.

## Cấu hình email và bảo mật

Email được dùng để gửi bản tổng hợp cảnh báo. Có thể ghi đè cấu hình mặc định bằng các biến môi trường `SMTP_HOST`, `SMTP_PORT` (STARTTLS, mặc định 587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_RECIPIENTS` (nhiều địa chỉ phân cách bằng dấu phẩy).

App không hỏi hoặc lưu mật khẩu email. Đặt `SMTP_PASSWORD` trong biến môi trường của tài khoản Windows trước khi mở app; Google yêu cầu App Password cho một số tài khoản.

Khu vực email dưới bảng chỉ xuất hiện khi có lỗi hoặc thư chưa gửi cần xử lý; bình thường và sau khi gửi thành công sẽ ẩn để dành chỗ cho danh sách. Khi gửi thất bại, app hiện thông báo desktop và giữ thư trong `email_outbox`; bấm **Gửi lại email** sau khi xử lý nguyên nhân. App tự thử tối đa 3 lần cho lỗi kết nối trước khi gửi hoặc mã SMTP 4xx. Với lỗi đăng nhập/SMTP 5xx, app giữ thư để thử lại thủ công. Người nhận đã được SMTP chấp nhận sẽ không được gửi lại trong lần thử tiếp theo.

Nếu kết nối mất trong lúc gửi và chưa rõ SMTP đã nhận thư chưa, app không tự gửi lại; nút gửi lại sẽ nhắc nguy cơ trùng thư. Lỗi khi đóng kết nối sau khi SMTP đã nhận thư không bị coi là gửi thất bại. Trạng thái SMTP đã nhận không bảo đảm thư đã vào Inbox.

Nếu gặp **SMTP 534 / WebLoginRequired**, Google yêu cầu đăng nhập và xác minh **tài khoản gửi** bằng trình duyệt trước khi thử lại. Nếu Google yêu cầu mật khẩu ứng dụng, xem [hướng dẫn App Password của Google](https://support.google.com/accounts/answer/185833).

Không commit mật khẩu, Gmail App Password hoặc danh sách người nhận vào repository. Nếu thông tin nhạy cảm đã từng được commit, hãy thu hồi/đổi ngay và chuyển cấu hình sang biến môi trường hoặc file `.env` được đưa vào `.gitignore`.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
python -m py_compile main.py price_history.py
```

Các kiểm thử kiểm tra đăng ký thông báo có hàng, cơ chế chỉ báo một lần, sắp xếp, biểu đồ, tải tăng dần khi có danh mục chậm, lỗi tải, chống tải chồng và giữ bộ lọc/dữ liệu cũ. Kiểm thử giao diện còn kiểm tra lọc 2.000 sản phẩm khi đang tải, nút thao tác sau sắp xếp/lọc và dựng ảnh email ngoài luồng giao diện. Các kiểm thử tải dùng dữ liệu giả, không gọi API hay gửi email.

## Cấu trúc mã nguồn

```text
main.py                       # Giao diện PyQt5, tải dữ liệu và luồng cảnh báo
email_delivery.py            # SMTP, hàng đợi lưu trên đĩa và gửi lại có kiểm soát
product_table.py              # Model bảng và nút thao tác chỉ vẽ khi hiển thị
ui_theme.py                   # Màu sắc và định dạng giao diện desktop
assets/                       # Biểu tượng giao diện
price_history.py              # Truy cập SQLite và biểu đồ lịch sử giá
sync_outOfStock_status.py     # Đồng bộ model biến mất khỏi API thành hết hàng
tests/                        # Kiểm thử tự động
price_history.db              # Dữ liệu SQLite cục bộ
```

## Hướng phát triển khuyến nghị

- Lưu snapshot theo timestamp nếu cần theo dõi biến động giá trong ngày.
- Không version-control dữ liệu SQLite vận hành; chỉ version-control schema hoặc migration.
