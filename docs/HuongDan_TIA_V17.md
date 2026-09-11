# Hướng dẫn dựng project — chạy mô phỏng trước, ra máy thật sau

Mục tiêu phần 1: mở PLCSIM lên, gõ số ô 1–20, thấy tọa độ chạy tới đúng chỗ, đứng 5 giây rồi về Home.
Chưa cần driver, chưa cần động cơ, chưa cần đấu dây.

---

## PHẦN 1 — CHẠY MÔ PHỎNG (làm được ngay hôm nay)

### Bước 1. Tạo project

1. TIA Portal V17 → *Create new project* → tên gì cũng được, ví dụ `XY_Tray`.
2. *Configure a device* → *Add new device* → **PLC → SIMATIC S7-1200 → CPU → CPU 1214C DC/DC/DC**
   → chọn mã `6ES7 214-1AG40-0XB0`, firmware **V4.5**.
3. **Bắt buộc cho mô phỏng**: chuột phải vào tên project (dòng trên cùng cây thư mục) →
   *Properties* → tab **Protection** → tick **Support simulation during block compilation**.
   Không tick cái này thì PLCSIM sẽ không chạy được.

### Bước 2. Bật kênh phát xung PTO

Mở *Device configuration* → click vào CPU → cửa sổ *Properties* bên dưới:

| Mục | Thiết lập |
|---|---|
| `Pulse generators (PTO/PWM)` → **PTO1/PWM1** | tick *Enable this pulse generator* |
| → Parameter assignment → Signal type | **PTO (pulse A and direction B)** |
| → Hardware output | Pulse = `Q0.0`, Direction = `Q0.1` |
| `Pulse generators` → **PTO2/PWM2** | tick *Enable this pulse generator* |
| → Signal type | **PTO (pulse A and direction B)** |
| → Hardware output | Pulse = `Q0.2`, Direction = `Q0.3` |

### Bước 3. Tạo 2 trục

Cây thư mục → *Technology objects* → *Add new object* → **Motion Control → TO_PositioningAxis**.
Đặt tên chính xác là **`AxisX`** (sai tên là code báo lỗi biên dịch). Rồi lặp lại cho **`AxisY`**.

Trong cửa sổ *Configuration* của mỗi trục:

| Trang | Thiết lập cho mô phỏng |
|---|---|
| **Basic parameters** | Drive = **PTO**, Unit of measurement = **mm** |
| **Hardware interface → Drive** | Pulse generator = `Pulse_1` (AxisX) / `Pulse_2` (AxisY).<br>**Bỏ tick** *Enable output* và *Ready input* — mô phỏng không có driver thật |
| **Extended parameters → Mechanics** | Pulses per motor revolution = `3200`<br>Load movement per motor revolution = `5.0` mm |
| **Position limits** | **Bỏ tick** *Enable hardware limit switches*<br>Tick *Enable software limit switches*: **AxisX** từ `0.0` đến `1300.0`; **AxisY** từ `0.0` đến `400.0` |
| **Dynamics → General** | Max velocity `150.0` mm/s, Acceleration `200.0` mm/s², Deceleration `200.0` mm/s².<br>Chỉ là giá trị khởi đầu — từ bản này server ghi đè cả ba mỗi lần khởi động, xem §3.6 |
| **Homing** | Để mặc định. Chương trình dùng `HomeMode = 0` (đặt gốc tại chỗ) nên không cần công tắc Home |

> ⚠️ Software limit phải bao trùm tọa độ trong bảng. Bảng mặc định có ô tới X = 1100 mm, Y = 300 mm.
> Nếu bạn đặt giới hạn nhỏ hơn, máy sẽ báo lỗi ngay khi chạy tới ô đó.

### Bước 4. Nạp code vào project

1. Cây thư mục → *External source files* → **Add new external file**.
2. Chọn **cả 8 file** trong `D:\PLC\src\` (giữ Ctrl chọn nhiều file cùng lúc).
3. Chọn **đúng thứ tự từ 01 đến 08**, bôi đen từng file → chuột phải → **Generate blocks from source**
   → *Yes*. Làm lần lượt 01 → 02 → … → 08, không được đảo thứ tự vì file sau tham chiếu file trước.

Sau khi xong bạn sẽ có: 3 UDT (`typXY`, `typTray`, `typIF`), các DB (`DB_TrayTable`,
`DB_Interface`, `DB_XY_Tray`, `DB_ModbusIF`) và các khối `FB_XY_Tray`, `FC_CmdDecode`,
`FC_StatusPack`, `FB_ModbusIF`, `FC_Main`.

**Nếu bước generate báo lỗi ở file 04** (không nhận diện được `MC_Power`, `MC_MoveAbsolute`…):
đây là lỗi TIA hay gặp khi import lệnh Motion Control từ file text. Cách chữa:
1. Tạo tay 1 FB mới tên `FB_XY_Tray`, ngôn ngữ SCL.
2. Mở thư viện *Instructions → Technology → Motion Control*, kéo thả lần lượt `MC_Power`,
   `MC_Reset`, `MC_Home`, `MC_MoveAbsolute`, `MC_MoveJog`, `MC_Halt` vào vùng code — TIA sẽ tự hỏi
   tên instance, đặt đúng tên như trong file (`mcPowerX`, `mcPowerY`, `mcResetX`, …).
3. Xóa các lệnh vừa kéo ra khỏi vùng code (phần khai báo Static vẫn còn lại).
4. Mở `04_FB_XY_Tray.scl` bằng Notepad, copy toàn bộ phần khai báo biến và phần thân dán vào.

### Bước 5. Gọi khối chính

Mở **OB1 (Main)** → kéo `FC_Main` từ cây thư mục vào network 1 → tại chân `Enable` gõ `TRUE`.

> Sau này ra máy thật, thay `TRUE` bằng tiếp điểm E-Stop OK (ví dụ `%I0.7`).

### Bước 6. Kiểm tra vài thiết lập DB

- `DB_Interface` → chuột phải → *Properties* → tab *Attributes* → **bỏ tick** *Optimized block access*
  (file source đã đặt sẵn, chỉ kiểm tra lại). Cần cho Modbus sau này.
- `DB_TrayTable` → mở ra → cột **Retain** → tick tất cả. Để tọa độ Teach không mất khi mất điện.
- `DB_TrayTable` → kiểm tra `UseModbus = FALSE` và `HomeMode = 0` (đúng cho mô phỏng).

### Bước 7. Biên dịch và chạy mô phỏng

1. Chọn CPU → nút **Compile** (biểu tượng bánh răng). Phải sạch lỗi mới đi tiếp.
2. Nút **Start simulation** (biểu tượng màn hình có chữ *sim*). PLCSIM mở lên.
3. Cửa sổ download hiện ra → *Load* → *Start module* → **Finish**.
4. Trong PLCSIM bấm **RUN**.

### Bước 8. Chạy thử bằng Watch table

Cây thư mục → *Watch and force tables* → *Add new watch table*, thêm các dòng:

| Name | Ghi chú |
|---|---|
| `"DB_Interface".Command` | ô để gõ lệnh vào |
| `"DB_Interface".SelPos` | số khay |
| `"DB_Interface".CmdSeq` | số thứ tự lệnh |
| `"DB_Interface".StepNo` | bước đang chạy |
| `"DB_Interface".ActX` | |
| `"DB_Interface".ActY` | |
| `"DB_Interface".Result` | kết quả lệnh |
| `"DB_Interface".DoneSeq` | |
| `"DB_XY_Tray".Homed` | |
| `"DB_XY_Tray".Ready` | |

Bấm nút kính lúp (*Monitor all*), rồi làm theo trình tự:

1. **Lấy gốc tọa độ**: cột *Modify value* của `Command` gõ `2` → bấm *Modify all*.
   → `Homed` và `Ready` chuyển TRUE, `Command` tự về `0`, `Result` = `2`.
2. **Chạy tự động tới khay 5**: `SelPos` = `5` → Modify. Rồi `Command` = `1` → Modify.
3. Nhìn `StepNo` chạy tuần tự:

```
0 → 10 (chạy X) → 20 (chạy Y) → 30 (đứng yên)
  → 100 → 110 → 120 → 110 → 120 → 110 → 120   (lắc 3 lần)
  → 190 → 200 (Y về chỗ) → 210 (X về chỗ) → 220 → 0
```

Diễn biến `ActX` phải là: lên `1100.0` → nhảy qua lại giữa `1100.0` và **`1120.0`** ba lần
(khay 5 thuộc cụm phải nên `Dir = +1`, lắc về phía **+X**) → rồi cả hai trục về `0.0`.
`Result` = `2` và `DoneSeq` bằng `CmdSeq`. Được như vậy là **logic đã chạy đạt**.

4. **Kiểm chiều lắc bên trái**: `SelPos` = `18` → `Command` = `1`.
   `ActX` phải tới `300.0` rồi lắc xuống **`280.0`** (cụm trái, `Dir = -1`), `ActY` = `100.0`.
5. **Kiểm việc chặn lệnh sai**: `SelPos` = `25` → `Command` = `1` → máy **không** chạy,
   `Result` = `5`.
6. **Thử lệnh lẻ**: `Command` = `6` (chỉ đi, không lắc, không về) → máy tới khay rồi đứng yên.
   Sau đó `Command` = `7` (lắc tại chỗ), rồi `Command` = `9` (về chỗ).

> Đổi kiểu lắc trong `DB_TrayTable`: `ShakeDist` (biên độ mm), `ShakeCount` (số lần),
> `ShakeVel` (tốc độ). Đặt `ShakeCount = 0` là bỏ hẳn bước lắc.

### Bước 9. Xem trục chạy trực quan (tùy chọn)

Mở *Technology objects → AxisX → Commissioning* trong lúc đang online — có đồng hồ vị trí,
thanh trạng thái và nút Jog. Xem trực quan hơn Watch table nhiều.

---

## PHẦN 2 — HMI (làm sau khi phần 1 chạy được)

*Add new device* → **HMI → SIMATIC Basic Panel → KTP700 Basic**. Bỏ qua wizard.

Tag HMI trỏ thẳng vào `DB_Interface`. Các phần tử cần có:

| Phần tử | Thuộc tính |
|---|---|
| Ô nhập số ô | I/O field, mode *Input*, tag `DB_Interface.SelPos`, giới hạn 1–20 |
| 20 nút chọn ô | Event *Click* → **SetValue**: tag `SelPos`, value = số ô. Sắp 4 cụm đúng như thực tế |
| Nút **Start** | Event *Click* → **SetValue**: tag `Command`, value `1` |
| Nút **Home** | → SetValue `Command` = `2` |
| Nút **Stop** | → SetValue `Command` = `3` |
| Nút **Reset** | → SetValue `Command` = `4` |
| Nút **Teach** | → SetValue `Command` = `5` |
| 4 nút Jog | Event *Press* → **SetBit** / *Release* → **ResetBit**, tag `JogBits` bit 0/1/2/3 |
| Hiển thị X, Y | I/O field mode *Output*, tag `ActX` / `ActY`, format `999.99` |
| Đèn Ready/Busy/Error | Circle, animation *Appearance* theo bit 0/1/4 của `StatusBits` |
| Số bước | I/O field *Output*, tag `StepNo` — để dò lỗi khi máy đứng giữa chừng |

> Các nút lệnh dùng **SetValue** chứ không dùng *SetBitWhileKeyPressed*: PLC tự xóa `Command` về 0
> sau khi nhận, nên một cú bấm = đúng một lệnh. Riêng nút Jog thì ngược lại, phải giữ mới chạy.

---

## PHẦN 3 — CHUYỂN SANG MÁY THẬT

Khi có driver và động cơ, chỉ đổi **thiết lập**, không sửa code:

### 3.1 Sửa trong `DB_TrayTable`
| Biến | Đổi thành | Lý do |
|---|---|---|
| `HomeMode` | `0` → **`3`** | Chạy tìm công tắc Home thật thay vì đặt gốc tại chỗ |
| `UseModbus` | `FALSE` → **`TRUE`** | Bật server cho app ngoài (CPU thật mới mở được cổng TCP) |
| `VelX`, `VelY` | theo từng driver | Driver chậm (TB6600) đặt thấp hơn driver nhanh (DM542) |

### 3.2 Sửa trong Technology Object
1. **Mechanics**: `Pulses per motor revolution` = đúng vi bước cài trên DIP driver;
   `Load movement per motor revolution` = bước vít me hoặc chu vi puly thực tế.
   Mỗi trục một giá trị riêng — dùng driver khác model thì con số khác nhau là bình thường.
2. **Hardware interface → Drive**: tick lại *Enable output* nếu driver có chân ENA.
3. **Position limits**: tick *Enable hardware limit switches*, gán DI công tắc giới hạn.
4. **Homing → Active homing**: gán DI công tắc Home, chọn chiều tìm và tốc độ tìm (chậm, 5–10 mm/s).
5. **Dynamics**: đặt max velocity theo tần số trần của **động cơ**, không phải của PLC.
   Công thức: `v_max (mm/s) = f_max (Hz) ÷ (pulse_per_rev ÷ mm_per_rev)`.
   Đo `f_max` bằng tay: cho trục chạy ở chế độ phát xung rồi tăng dần tới khi động cơ
   đuối bước. Máy này đo được **20 000 xung/s** trên cả ba trục — thấp hơn nhiều so với
   trần 100 kHz của kênh PTO, nên đây mới là con số quyết định.
   Với cơ khí hiện tại: X `20000 ÷ (3200÷32)` = **200 mm/s**, Z `20000 ÷ (2000÷54)` = **540 mm/s**.

### 3.6 Trần tốc độ đặt ở TIA, gia tốc chỉnh từ web

**Trần tốc độ — chỉ TIA đặt được.** `DynamicLimits.MaxVelocity` là read-only đối với
chương trình, viết vào là TIA báo *"The tag is read-only"*. Đặt tay một lần, cho rộng rãi:

| Trục | Max velocity | Từ đâu ra |
|---|---|---|
| `Axis_X` | `200.0` mm/s | `20000 ÷ (3200÷32)` |
| `Axis_Z` | `540.0` mm/s | `20000 ÷ (2000÷54)` |
| `Axis_Y` | `7200.0` °/s | `20000 ÷ (1000÷360)` |

Đặt xong thì thôi, vì nó sống qua lần cúp điện. Trang Cài đặt chặn sẵn không cho nhập
quá mấy con số này (`Geometry.velocity_limits()` trong `orangepi/app/geometry.py`), nên
không bao giờ chạm tới `ErrorID 16#8402` nữa.

**Gia tốc — server ghi đè, không phải mở TIA.** `FB_XY_Tray` nhận thêm mã tham số
**16/17/18** của lệnh 14, ghi thẳng vào `DynamicDefaults.Acceleration` cùng `Deceleration`
và `EmergencyDeceleration` của X/Y/Z. Nhánh này chỉ chạy khi `StepNo = 0`.
Server đẩy xuống mỗi lần lưu cấu hình và mỗi lần khởi động.

Giá trị lấy từ ba hằng số `ACCEL_X` / `ACCEL_Z` / `ACCEL_Y` trong
`orangepi/app/geometry.py`, không phải ô nhập trên web — đổi gia tốc là việc chỉnh một
lần khi lắp máy, không phải việc hằng ngày. Đang để 200, bằng đúng giá trị trong TIA.

Đáng nâng khi cần chu trình ngắn hơn: bước giữa hai cột là 406 mm, ở 200 mm/s với gia tốc
200 thì mất 100 mm tăng tốc + 100 mm hãm, đúng nửa quãng đường. Để 1000 thì chỉ còn 20 mm
mỗi đầu. Nâng từ từ và chạy thử — gia tốc gắt quá thì động cơ trượt bước.

⚠️ Gia tốc ghi kiểu này nằm trong DB của trục nên **cúp điện bật lại là về con số khai
trong TIA**. Bình thường không thấy vì server đẩy lại ngay khi khởi động, nhưng chạy PLC
mà không có server thì vẫn là số cũ — vậy nên §3.2 vẫn phải đặt cho đúng.

Ba chỗ đã vấp khi viết đoạn này, ghi lại kẻo quên:

- Gọi thẳng `"Axis_X"`, **không** qua tham số `IN_OUT` `#AxisX`. Kiểu `TO_PositioningAxis`
  chỉ là tham chiếu để đút vào các lệnh `MC_*`, không với tới được các ô cấu hình.
- **Không có tầng `.Config`.** Project này dùng `TO_PositioningAxis V8`, cấu trúc phẳng.
  Tầng `.Config` chỉ còn ở TO đời cũ (S7-1200 firmware V3 trở về trước).
- `MaxVelocity` read-only, như trên.

### 3.3 Hiệu chuẩn — làm trước khi teach
Dùng *Commissioning* cho trục chạy đúng 100 mm rồi lấy thước đo. Lệch thì sửa
`Pulses per motor revolution`, **không** sửa chương trình. Chỉ khi số đo khớp mới đi teach tọa độ.

### 3.4 Teach 20 ô
1. Bấm **Home**.
2. `SelPos` = 1 → dùng 4 nút Jog đưa đầu công tác vào đúng ô 1 → bấm **Teach**.
3. Lặp cho đủ 20 ô.
4. **Lưu vĩnh viễn**: online → chuột phải `DB_TrayTable` → *Snapshot of monitored values* →
   *Copy snapshot to start values* → download lại. Bỏ bước này thì lần download sau tọa độ về mặc định.

### 3.5 Test app ngoài qua Modbus
Dùng Modbus Poll hoặc `pymodbus`, kết nối IP của CPU cổng 502:
- Ghi `HR1 = 5` rồi `HR0 = 1` → máy chạy tới ô 5. `HR0` phải tự về 0.
- Đọc `HR3` xem bit trạng thái, `HR6–HR7` là tọa độ X kiểu Real.

---

## Thêm cơ cấu đẩy sau này

Mở `FB_XY_Tray`, tìm khối `CASE` ở bước **100**. Hiện tại nó chỉ có `#StepNo := 200;`.
Thay bằng chuỗi bước của bạn, ví dụ:

```pascal
100: // duoi xy-lanh day
   "Q_Day" := TRUE;
   #StepNo := 110;

110: // cho cam bien bao da duoi het
   IF "I_DayDuoi" THEN
      #StepNo := 120;
   END_IF;

120: // thu xy-lanh ve
   "Q_Day" := FALSE;
   #StepNo := 130;

130: // cho cam bien bao da thu ve
   IF "I_DayThu" THEN
      #StepNo := 200;   // xong -> ve Home
   END_IF;
```

Không phải sửa bất cứ thứ gì ở phần trước bước 100 hay sau bước 200.
Nhớ thêm timer timeout cho các bước chờ cảm biến để máy không đứng vô hạn nếu cảm biến hỏng.
