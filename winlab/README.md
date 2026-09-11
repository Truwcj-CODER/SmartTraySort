# winlab — chạy server trên Windows để debug với PLC thật

Thư mục này **không chứa bản sao code nào**. Nó trỏ thẳng vào `orangepi/app`
và chỉ thay đúng một thứ: **MySQL → SQLite**.

Bản chạy thật trên Ubuntu vẫn `docker compose up -d` như cũ, không liên quan.

## Vì sao cần

`docker-compose.yml` khai `network_mode: host` — thứ này chỉ có trên Linux.
Docker Desktop trên Windows chạy trong máy ảo nên container không với tới được
PLC ở dải LAN cắm thẳng vào máy. Cài Docker về cũng không dùng được.

Còn nếu chạy `app` trực tiếp bằng Python thì nó đòi MySQL ở `127.0.0.1:3307`,
mà Windows không có. `winlab` gỡ đúng nút thắt đó.

## Chạy

```
python winlab/run.py
python winlab/run.py --port 8080
python winlab/run.py --plc 192.168.0.10 --reload
```

Cần `fastapi`, `uvicorn`, `pymodbus`, `jinja2` (xem `orangepi/requirements.txt`).
**Không cần** `pymysql`, không cần Docker, không cần MySQL.

## Hoạt động thế nào

`run.py` làm ba việc, theo đúng thứ tự:

1. Thêm `orangepi/` vào `sys.path` — từ đây `import app.*` là code thật
2. Đổi `app.db.Database` thành lớp SQLite **trước khi** `app.main` chạy dòng
   `from .db import Database`, nên `main` nhận lớp đã đổi mà không biết gì
3. Gọi `uvicorn` với `app.main:app`

`sqlite_db.py` giữ đúng giao diện của `app.db.Database`: `endpoint`, `cursor()`,
`wait_ready()`, `setup()`, `close()`. Tầng trên — `ConfigStore`, `SlotTable`,
`migrate_json` — chạy nguyên vẹn.

SQLite không hiểu vài câu lệnh riêng của MySQL nên có một lớp dịch nhỏ:

| MySQL | SQLite |
|---|---|
| `INSERT IGNORE INTO` | `INSERT OR IGNORE INTO` |
| `ON DUPLICATE KEY UPDATE x = VALUES(x)` | `ON CONFLICT(khóa) DO UPDATE SET x = excluded.x` |
| tham số `%s` | `?` |

Bảng khai lại theo kiểu SQLite thay vì dịch `SCHEMA` của MySQL — bên kia có
`ENGINE=InnoDB`, `JSON`, `ON UPDATE CURRENT_TIMESTAMP`, dịch sang đều gãy.
Tên cột và kiểu thì khớp, nên tầng trên không phân biệt được.

`UNIQUE` trên cột `code` vẫn cho nhiều rổ cùng để trống: SQLite không coi hai
`NULL` là trùng nhau, giống hệt MySQL.

## Dữ liệu

Nằm ở `winlab/data/traysort.db`. Tách hẳn khỏi MySQL của bản chạy thật, nên
nghịch thoải mái. Muốn làm lại từ đầu thì xoá file đó rồi chạy lại.

Lần chạy đầu, nếu `orangepi/app/data/*.json` còn thì `migrate_json` tự nạp vào.

## Giới hạn

- Không tự gán IP cho card mạng (`NET_SETUP=0`). Card `Ethernet 3` phải sẵn IP
  cùng dải với PLC — hiện là `192.168.0.5/24`.
- Chỉ để debug. Máy chạy thật vẫn là Orange Pi với MySQL.
