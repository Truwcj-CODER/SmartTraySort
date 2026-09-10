# Kết nối Orange Pi ↔ PLC qua LAN (Modbus TCP)

## 1. Hai tầng, đừng nhầm

| Tầng | Là gì | Ở đây là |
|---|---|---|
| Vật lý | Sợi dây, đường truyền | Cáp LAN từ Orange Pi → cổng PROFINET của CPU (qua switch hoặc cắm thẳng) |
| Giao thức | Quy ước nói chuyện trên dây đó | **Modbus TCP**, cổng 502 |

Không cần module truyền thông thêm, không cần license. Cổng PROFINET sẵn có trên CPU 1214C chạy được
Modbus TCP bình thường.

## 2. Đặt địa chỉ IP

Hai thiết bị phải **cùng dải mạng**:

| Thiết bị | IP | Subnet mask |
|---|---|---|
| PLC | `192.168.0.10` | `255.255.255.0` |
| Orange Pi | `192.168.0.20` | `255.255.255.0` |

- **PLC**: TIA → *Device configuration* → click cổng PROFINET → *Ethernet addresses* → nhập IP → download.
- **Orange Pi**: sửa netplan hoặc `nmcli`, ví dụ:

```bash
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.0.20/24 ipv4.method manual
sudo nmcli con up "Wired connection 1"
```

Kiểm tra thông đường trước khi làm gì tiếp:

```bash
ping 192.168.0.10
```

Không ping được thì dừng lại xử lý mạng, đừng đụng tới code.

## 3. Bản đồ thanh ghi

Toàn bộ nằm trong `DB_Interface` (**bắt buộc bỏ Optimized block access**).
Modbus Poll đánh số từ 40001, tức `HR0 = 40001`.

### Orange Pi ghi xuống — nên ghi cả khối HR0–HR9 bằng một lệnh FC16

| HR | Tên | Kiểu | Ý nghĩa |
|---|---|---|---|
| 0 | `Command` | Word | Mã lệnh, xem bảng dưới. PLC tự xóa về 0 sau khi nhận |
| 1 | `SelPos` | Int | Số khay 1–20 |
| 2 | `CtrlBits` | Word | bit0 X+, bit1 X−, bit2 Y+, bit3 Y−, bit4 Z+, bit5 Z−,<br>**bit8 = cấp điện trục (giá trị 256)** |
| 3 | `CmdSeq` | Word | Số thứ tự lệnh, client tự tăng mỗi lần gửi |
| 4–5 | `TargetX` | Real | Tọa độ X tự do (chỉ dùng cho lệnh 8) |
| 6–7 | `TargetY` | Real | Tọa độ Y tự do |
| 8–9 | `TargetZ` | Real | Góc trục lắc (chỉ dùng cho lệnh 10) |

### PLC trả về — Orange Pi chỉ đọc

| HR | Tên | Ý nghĩa |
|---|---|---|
| 10 | `StatusBits` | bit0 Ready, bit1 Busy, bit2 Done, bit3 Homed, bit4 Error |
| 11 | `StepNo` | Bước hiện tại của máy trạng thái — rất tiện khi dò lỗi |
| 12 | `ErrorID` | Mã lỗi Motion Control |
| 13 | `AckSeq` | Echo `CmdSeq` khi PLC **đã nhận** lệnh |
| 14 | `DoneSeq` | `CmdSeq` của lệnh **đã chạy xong** |
| 15 | `Result` | 0 chưa chạy / 1 đang chạy / 2 xong / 3 bị dừng / 4 lỗi / 5 lệnh sai |
| 16–17 | `ActX` | Vị trí thực X — ngang (Real, mm) |
| 18–19 | `ActY` | Vị trí thực Y — lên xuống (Real, mm) |
| 20–21 | `ActZ` | Vị trí thực Z — trục lắc (Real, độ) |
| 22 | `CurSlot` | Khay đang chạy tới |

### Bảng mã lệnh

| Mã | Việc PLC làm |
|---|---|
| 1 | **Chạy tự động**: đi tới khay `SelPos` → đứng yên → **lắc đúng bên của khay** → về vị trí chờ |
| 2 | Chạy lấy gốc tọa độ (homing) |
| 3 | Dừng khẩn |
| 4 | Xóa lỗi |
| 5 | Teach: lưu vị trí hiện tại vào khay `SelPos` |
| 6 | Chỉ đi tới khay `SelPos`, đứng lại đó |
| 7 | Chỉ lắc tại chỗ, theo chiều của khay `SelPos` |
| 8 | Đi tới tọa độ tự do `TargetX` / `TargetY` |
| 9 | Về vị trí chờ (di chuyển, không phải homing) |
| 10 | Xoay trục lắc tới góc `TargetZ` — dùng khi căn chỉnh cơ cấu |

Lệnh 1 là lệnh gộp — Orange Pi gửi một phát, PLC lo hết. Lệnh 6/7/8/9 là lệnh lẻ, để khi bạn muốn
Orange Pi tự ghép lưu đồ riêng.

## 4. Cách bắt tay — vì sao cần `CmdSeq`

Với HMI nối cứng thì chỉ cần ghi lệnh rồi PLC xóa về 0. Nhưng master ở xa qua mạng thì không nhìn được
từng vòng quét, nên dễ dính hai lỗi: gửi lệnh mà không biết PLC có nhận không, hoặc đọc `Busy` quá sớm
lúc PLC còn chưa kịp chạy nên tưởng đã xong.

Số thứ tự lệnh giải quyết cả hai:

```
Orange Pi                                PLC
    │ ghi HR0..HR7 (Command=1, SelPos=5, CmdSeq=42)
    ├──────────────────────────────────────►
    │                          nhận lệnh, AckSeq := 42, Command := 0
    │ đọc HR13 thấy AckSeq = 42  → chắc chắn PLC đã nhận
    │
    │                          chạy X → chạy Y → đứng → lắc → về chỗ
    │ đọc HR14 tới khi DoneSeq = 42
    │◄─────────────────────────────────────┤
    │ đọc HR15 Result = 2  → xong tốt
```

`Result = 3` là bị Stop cắt ngang, `= 4` là lỗi (đọc thêm `ErrorID`), `= 5` là lệnh sai hoặc máy chưa
sẵn sàng (chưa homing, chưa cấp điện trục, số khay ngoài 1–20).

Việc ghi cả khối HR0–HR7 bằng một lệnh FC16 là có chủ ý: `MB_SERVER` xử lý trọn gói yêu cầu trong một
vòng quét, nên PLC không bao giờ đọc phải trạng thái nửa vời kiểu có `Command` mới mà `SelPos` còn cũ.

## 5. Server trên Orange Pi

Toàn bộ phần mềm phía Pi nằm trong [`orangepi/`](../orangepi/README.md) — giao diện web, REST API
và thư viện điều khiển, chia tầng rõ ràng: `api → service → transport → protocol`.

```bash
cd orangepi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PLC_HOST=192.168.0.10 ./run.sh
```

Mở `http://<ip-orange-pi>:8000` là có màn hình 20 khay đúng bố cục 4 cụm, nút chạy/lắc/teach,
jog tay, ô đi tới tọa độ tự do và nhật ký lệnh. Trạng thái đẩy về qua WebSocket nên vị trí X-Y
và số bước cập nhật liên tục.

### Chưa có PLC vẫn thử được giao diện

`tests/fake_plc.py` là một PLC giả lập: nó mở cổng Modbus TCP và chạy đúng máy trạng thái của
`FB_XY_Tray` (kể cả bước lắc và chiều lắc theo cụm). Mở hai terminal:

```bash
python3 tests/fake_plc.py
```

```bash
PLC_HOST=127.0.0.1 PLC_PORT=5020 ./run.sh
```

### Gọi từ code của bạn

```python
from app.config import get_settings
from app.plc.service import PlcService

service = PlcService(get_settings())
await service.start()

await service.home()
await service.run_slot(5)        # tới khay 5, lắc sang phải, về chỗ
await service.goto_slot(12)      # chỉ đi
await service.shake_slot(12)     # rồi lắc riêng
await service.move_xy(250, 180)  # tọa độ tự do
await service.move_z(30)         # xoay trục lắc tới 30 độ
await service.park()
```

Mọi hàm đều chờ tới khi PLC báo xong và ném `PlcCommandError` nếu thất bại, nên phía lưu đồ của
bạn viết tuần tự bình thường, không phải tự quản lý polling.

## 6. Ba điểm an toàn cần biết

1. **Trục chỉ có điện khi Orange Pi bật bit 8 của `CtrlBits`** (giá trị 256). Thư viện Python tự gửi
   kèm bit này trong mọi lệnh. Nghĩa là master chưa sẵn sàng thì trục không tự nhiên chạy được.
   Riêng khi mô phỏng (`UseModbus = FALSE`) thì điều kiện này được bỏ qua cho dễ test.
2. **Jog qua mạng có giới hạn thời gian.** Giữ bit jog rồi rớt mạng là trục chạy mãi — nên PLC tự cắt
   jog sau `JogMaxTime` (mặc định 5 giây). Muốn jog tiếp phải nhả bit rồi bấm lại. Để định vị chính xác
   từ Orange Pi, dùng lệnh 8 (đi tới tọa độ) thay vì giữ jog.
3. **E-Stop vẫn phải là phần cứng.** Chân `HwSafeOK` của `FC_Main` nối vào tiếp điểm mạch dừng khẩn.
   Đừng bao giờ để việc dừng khẩn phụ thuộc vào một gói tin mạng.

## 7. Khi không kết nối được

| Hiện tượng | Chỗ cần xem |
|---|---|
| `ping` không thông | Sai IP hoặc sai subnet, dây LAN, đèn cổng |
| Ping được nhưng Modbus timeout | `DB_TrayTable.UseModbus` còn `FALSE`; hoặc đang chạy PLCSIM (không mở được cổng TCP thật) |
| Kết nối được nhưng đọc ra số vô nghĩa | `DB_Interface` chưa bỏ *Optimized block access* |
| `Result` luôn bằng 5 | Chưa chạy homing (lệnh 2), hoặc chưa cấp điện trục, hoặc `SelPos` ngoài 1–20 |
| `Status` báo `error`, `ErrorID` khác 0 | Đọc mã lỗi trong TIA (*Technology object → Diagnostics*); thường là chạy vượt software limit |
