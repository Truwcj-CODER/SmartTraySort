# Server điều khiển trên Orange Pi

Giao diện web + REST API điều khiển PLC S7-1200 qua Modbus TCP (LAN).
PLC lo chuyển động, server này lo giao diện và lưu đồ.

## Cấu trúc

```
orangepi/
├── app/
│   ├── config.py            tham số chạy, đọc từ biến môi trường — nơi duy nhất giữ mặc định
│   ├── main.py              FastAPI + lifespan, chỉ ráp mọi thứ lại
│   ├── geometry.py          kích thước thật của máy, tự suy ra số rổ và toạ độ từng rổ
│   ├── inventory.py         tồn kho từng rổ
│   ├── db.py                MySQL: kết nối, dựng bảng, kho cấu hình và bảng rổ
│   ├── plc/
│   │   ├── protocol.py      bản đồ thanh ghi, mã lệnh, mã hóa số — thuần tính toán
│   │   ├── netsetup.py      tự đặt địa chỉ cùng dải với PLC lên card mạng có dây
│   │   ├── transport.py     đóng/mở kết nối, đọc/ghi thanh ghi
│   │   └── service.py       nghiệp vụ: chạy lệnh, chờ kết quả, phát trạng thái
│   ├── api/
│   │   ├── schemas.py       kiểu dữ liệu vào/ra
│   │   ├── routes.py        REST endpoints
│   │   ├── ws.py            WebSocket phát trạng thái — trang web dùng
│   │   ├── sse.py           Server-Sent Events — app Android dùng
│   │   └── appdist.py       phát bản app Android cho điện thoại tự tải
│   ├── data/                bản JSON cũ, chỉ còn dùng để nạp lần đầu vào MySQL
│   ├── updates/             bản APK đang phát hành + latest.json
│   ├── templates/index.html cấu trúc trang, không nhúng JS/CSS
│   └── static/
│       ├── css/styles.css
│       └── js/{api,ui,app}.js   gọi API / vẽ DOM / ráp lại
├── tests/
│   ├── test_protocol.py     14 test — mã hoá, giải mã, chuỗi lệnh
│   ├── test_geometry.py     40 test — bố cục rổ, xếp vật
│   └── fake_plc.py          PLC giả lập để thử giao diện
├── android_app/             app Android, xem README riêng trong đó
├── cli.py                   điều khiển bằng dòng lệnh, dùng chung service
├── entrypoint.sh            hạ quyền xuống uid thường, giữ lại NET_ADMIN
├── Dockerfile
└── docker-compose.yml       chạy nền, tự bật lại khi máy khởi động
```

Mỗi tầng chỉ nói chuyện với tầng ngay dưới nó: `api → service → transport → protocol`.
Thêm lệnh mới thì thêm một dòng trong `protocol.Command`, một hàm trong `service`, một route
trong `routes.py` — không đụng chỗ nào khác.

## Chạy

```bash
cp .env.example .env      # điền IP của PLC và đổi mật khẩu MySQL
docker compose up -d --build
```

Compose dựng hai container: `traysort-db` (MySQL 8) và `xy-server`. Server chờ database
`healthy` rồi mới khởi động, và tự dựng bảng ở lần chạy đầu.

```bash
docker compose logs -f    # xem log
docker compose restart    # nạp lại
docker compose down       # tắt
```

Container dùng mạng của host để nói chuyện thẳng với PLC, và `restart: unless-stopped`
lo phần tự bật lại khi Pi khởi động — không cần systemd.

### Hai đường phát trạng thái

Server đọc PLC mỗi `POLL_INTERVAL` giây rồi phát bản chụp đó ra cho mọi giao
diện đang mở. Có hai đường, cùng một nguồn dữ liệu:

| Đường | Ai dùng | Vì sao |
|---|---|---|
| `WS /ws/status` | trang web | trình duyệt có sẵn WebSocket, hai chiều |
| `GET /api/events` | app Android | HTTP thường, qua được mọi proxy, tự nối lại |

Đường SSE phát ba loại sự kiện: `status` mỗi vòng đọc PLC, `inventory` khi bảng
rổ đổi, `layout` khi cấu hình đổi. Hai loại sau chỉ gửi khi số `revision` phía
server tăng — so hai số nguyên rẻ hơn nhiều so với dựng lại cả bảng mỗi vòng.
Nhờ vậy app không phải hỏi vòng lần nào, mà lúc máy đứng yên thì đường truyền
gần như trống.

Thử bằng dòng lệnh:

```bash
curl -N http://<ip>:8000/api/events
```

## App Android

Cùng bộ chức năng với trang web, gói trong một app cầm tay. Server kiêm luôn nơi
phát bản cập nhật — điện thoại tự hỏi, tự tải, tự cài, không cần cáp và không
cần Play Store.

```bash
cd android_app
./publish.sh --notes "Sửa gì đó"
```

Cài lần đầu thì mở trình duyệt trên điện thoại vào
`http://<ip-orange-pi>:8000/api/app/download`.

Chi tiết ở [`android_app/README.md`](android_app/README.md).

## Không phải đặt IP cho máy chủ

PLC ở IP cố định, còn máy chủ thì không: cắm qua USB adapter, qua cổng LAN của Pi, hay
máy khác — tên card đổi mỗi lần, và thường máy chỉ có địa chỉ DHCP của mạng văn phòng.
Không có địa chỉ nào cùng dải với PLC thì gói tin không bao giờ rơi vào đúng dây cáp.

`app/plc/netsetup.py` lo việc đó lúc khởi động rồi kiểm lại mỗi 5 giây: tìm card có dây
đang có tín hiệu, gắn thêm `192.168.0.100/24` song song với địa chỉ DHCP sẵn có. Rút cắm,
đổi adapter, hay reboot đều tự nhận lại — không phải `nmcli` hay sửa `.env` gì.

Server vẫn chạy bằng uid thường; `entrypoint.sh` hạ quyền bằng `setpriv` nhưng giữ lại
đúng một quyền `NET_ADMIN` cho việc này.

Mở trình duyệt vào `http://<ip-orange-pi>:8000`. Bấm **Lấy gốc tọa độ** trước, rồi chọn khay
và bấm **Chạy tự động**.

Tài liệu API tự sinh ở `http://<ip>:8000/docs`.

Chạy thử khi chưa có PLC — mở PLC giả lập rồi trỏ server vào nó. Chạy thẳng bằng Python
thì biến ở dòng lệnh đè được `.env`:

```bash
python3 tests/fake_plc.py
```

```bash
PLC_HOST=127.0.0.1 PLC_PORT=5020 .venv/bin/uvicorn app.main:app --port 8000
```

Thử bằng Docker thì sửa `PLC_HOST` và `PLC_PORT` trong `.env`, vì `env_file` chỉ đọc file
chứ không nhận biến từ dòng lệnh.

## Chạy không cần Docker

Cho lúc phát triển, hoặc để dùng `cli.py` và chạy test:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PLC_HOST=192.168.0.10 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Kiểm tra

Chạy trong container, không cần cài gì trên máy:

```bash
docker compose run --rm --no-deps -v "$PWD/tests:/app/tests:ro" \
  --entrypoint python xy-server -m unittest discover -s tests -v
```

54 test, không cần PLC.

## Dòng lệnh

Khối `MB_SERVER` trên PLC chỉ nhận **một** kết nối Modbus TCP. Phải tắt server trước
(`docker compose stop`) rồi mới dùng được `cli.py`, không thì mọi lệnh đều bị từ chối.

```bash
python3 cli.py status
python3 cli.py home
python3 cli.py run 5
python3 cli.py xy 250 180
```

## Biến môi trường

`app/config.py` không giữ giá trị nào — nó chỉ đọc `.env` ra và ép kiểu. Thiếu một dòng
thì server dừng ngay và nói rõ thiếu dòng nào, thay vì âm thầm chạy bằng số khác.

```
cau hinh trong .env chua dung — thieu: POLL_INTERVAL, HTTP_PORT
cau hinh trong .env chua dung — sai kieu: PLC_PORT='abc' (invalid literal for int())
```

| Biến | Ý nghĩa |
|---|---|
| `PLC_HOST` | IP của PLC |
| `PLC_PORT` | Cổng Modbus TCP, chuẩn là `502` |
| `PLC_UNIT` | Unit ID |
| `PLC_CONNECT_TIMEOUT` | Tối đa chờ mở kết nối, giây |
| `NET_SETUP` | `1` để tự gán địa chỉ cùng dải với PLC, `0` để tắt |
| `PLC_LOCAL_IP` | Địa chỉ gắn cho máy chủ; để trống thì tự chọn `.100` trong dải của PLC |
| `PLC_LOCAL_PREFIX` | Độ dài prefix của dải PLC |
| `PLC_IFACE` | Ghim một card cụ thể; để trống thì tự tìm card có dây đang có tín hiệu |
| `PLC_NET_INTERVAL` | Chu kỳ kiểm lại đường mạng, giây |
| `POLL_INTERVAL` | Chu kỳ đọc trạng thái từ PLC, giây |
| `COMMAND_TIMEOUT` | Tối đa chờ một lệnh chuyển động, giây |
| `HOMING_TIMEOUT` | Homing lâu hơn vì phải dò công tắc, giây |
| `HTTP_HOST` | Địa chỉ web lắng nghe |
| `HTTP_PORT` | Cổng web |
| `MYSQL_HOST` | Địa chỉ MySQL — `127.0.0.1` vì container app dùng mạng host |
| `MYSQL_PORT` | Cổng MySQL trên máy chủ |
| `MYSQL_DATABASE` | Tên database, mặc định `traysort` |
| `MYSQL_USER` / `MYSQL_PASSWORD` | Tài khoản ứng dụng dùng |
| `MYSQL_ROOT_PASSWORD` | Chỉ container MySQL dùng lúc khởi tạo |
| `MYSQL_CONNECT_TIMEOUT` | Tối đa chờ mở kết nối, giây |
| `MYSQL_READY_TIMEOUT` | Tối đa chờ MySQL sẵn sàng lúc khởi động, giây |

## Dữ liệu

Hai bảng trong MySQL:

```sql
config  name VARCHAR(64) PK, data JSON          -- cấu hình hình học
slots   slot INT PK, code VARCHAR(128) UNIQUE,  -- mỗi rổ một mã QR
        count INT, capacity INT, updated_at DATETIME
```

`code` để `NULL` khi rổ chưa gán mã — MySQL không coi hai `NULL` là trùng nhau, nên ràng
buộc `UNIQUE` vẫn cho nhiều rổ trống mà vẫn chặn hai rổ trùng một mã QR.

Lần chạy đầu, nếu `app/data/*.json` còn đó thì server tự nạp sang MySQL rồi thôi — các
lần sau bỏ qua, không ghi đè. Giữ lại mấy file JSON đó làm bản lưu.

Số khay **không** nằm ở đây — nó suy ra từ hành trình trục X và kích thước rổ trong
`app/data/geometry.json`, sửa qua trang cấu hình.
