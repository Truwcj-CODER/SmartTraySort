# Bảng I/O và đấu dây — dùng khi ra máy thật

Phần mô phỏng không cần đọc file này.

## 1. Ngõ ra số (CPU 1214C DC/DC/DC)

| Địa chỉ | Tên | Trục | Ghi chú |
|---|---|---|---|
| `Q0.0` | X_PUL | X — chạy ngang | Kênh PTO1, tối đa **100 kHz** |
| `Q0.1` | X_DIR | X | |
| `Q0.2` | Z_PUL | Z — lên xuống | Kênh PTO2, tối đa **100 kHz** |
| `Q0.3` | Z_DIR | Z | |
| `Q0.4` | X_ENA | X | Tùy chọn, để trống driver vẫn chạy |
| `Q0.5` | Z_ENA | Z | Nên đấu: trục đứng cần chủ động cắt/cấp |
| `Q0.6` | Y_PUL | Y — lật trái phải | Kênh PTO3, **chỉ 20 kHz** |
| `Q0.7` | Y_DIR | Y | |
| `Q1.0` | Y_ENA | Y | Tùy chọn |
| `Q1.1` | — | | Còn trống |

> **Vì sao Z ở kênh nhanh, Y ở kênh chậm:** trục lên xuống chống trọng lực nên
> cần tốc độ và mô-men, còn trục lật chỉ quay ±60° mỗi chu trình. Kênh `Q0.6/Q0.7`
> bị chặn ở 20 kHz, nhường cho trục lật là hợp lý nhất.
>
> Bảng này phải **khớp với Technology Object trong TIA**: mỗi trục mở
> `Hardware interface → Pulse generator` xem đang trỏ vào PTO nào.

## 2. Ngõ vào số

| Địa chỉ | Tên | Trục | Ai đọc nó |
|---|---|---|---|
| `I0.0` | **STOP_BTN** | — | **`FC_Main`** — nút DỪNG trên tủ, đọc thẳng trong SCL |
| `I0.1` | X_MIN | X | Technology Object `Axis_X` |
| `I0.2` | X_MAX | X | Technology Object `Axis_X` |
| `I0.3` | Z_HOME | Z — lên xuống | Technology Object `Axis_Z` |
| `I0.4` | Z_MIN | Z | Technology Object `Axis_Z` |
| `I0.5` | Z_MAX | Z | Technology Object `Axis_Z` |
| `I0.6` | Y_HOME | Y — lật | Technology Object `Axis_Y` |
| `I0.7` | **ESTOP_OK** | — | **`FC_Main(HwSafeOK := ...)`** — điều kiện an toàn phần cứng |
| `I1.0` | X_HOME | X — ngang | Technology Object `Axis_X` (dời từ I0.0 sang) |

Cách đặt tên: `MIN` là đầu hành trình (phía 0), `MAX` là cuối hành trình.
`HOME` là công tắc dò gốc toạ độ. Trục Y quay nên chỉ có `HOME`.

> **Chỉ `I0.0` và `I0.7` là do chương trình SCL đọc.** Các chân còn lại không có
> dòng code nào chạm tới: chúng được khai thẳng trong Technology Object (`Homing`
> và `Position limits`), và TO tự đọc lấy. Khai trong TO thì mới có tác dụng — chỉ
> cắm dây vào PLC là chưa đủ.
>
> **`I0.0` — nút DỪNG.** `FC_Main` đọc nó qua một công tắc mềm:
> `"DB_TrayTable".UseStopBtn`. Để `FALSE` (mặc định) thì bỏ qua `I0.0` hoàn toàn,
> máy chạy như cũ — dùng khi mô phỏng hoặc khi chưa đấu nút nào. Đấu nút xong thì
> đổi sang `TRUE`, không cần biên dịch lại.
> Nút phải là tiếp điểm **thường đóng (NC)**: nhả nút → `I0.0 = 1` → cho chạy;
> nhấn nút **hoặc đứt dây** → `I0.0 = 0` → máy dừng ngay và giữ dừng suốt lúc còn
> nhấn (kể cả jog cũng bị khoá). Bật `UseStopBtn = TRUE` mà quên đấu dây thì máy
> nằm im — đó là đúng, không phải lỗi.
>
> Hiện `HomeMode = 0` (gán thẳng vị trí hiện tại làm gốc) nên **ba công tắc HOME
> chưa cần thiết**. Muốn dùng công tắc gốc thật thì đổi `HomeMode` sang 3 và khai
> công tắc trong TO.

Trong OB1, `FC_Main` phải được gọi với ngõ vào thật thay vì `TRUE`:

```pascal
"FC_Main"(HwSafeOK := "I_EstopOK");   // %I0.7 — máy thật
"FC_Main"(HwSafeOK := TRUE);          // chỉ dùng khi mô phỏng
```

Còn để `TRUE` thì E-Stop có nhấn PLC cũng không biết.

> Công tắc giới hạn nên dùng loại **thường đóng (NC)**: đứt dây là máy dừng, an toàn hơn thường mở.

## 3. Đấu tín hiệu vào driver step

Ngõ ra S7-1200 DC/DC/DC là **PNP (source) 24 V**. Cách đấu tùy loại driver:

### 3.1 Driver đầu vào 5 V (DM542, DM556, TB6600, HY-DIV268N…)

Đấu kiểu **common cathode** (chân âm chung), mỗi dây tín hiệu nối tiếp một điện trở hạn dòng:

```
   Q0.0 ──[ 2 kΩ / 0.5 W ]── PUL+
   Q0.1 ──[ 2 kΩ / 0.5 W ]── DIR+
   Q0.4 ──[ 2 kΩ / 0.5 W ]── ENA+     (nếu dùng)
   0 V (chung với 2M của PLC) ───────── PUL- , DIR- , ENA-
```

Thiếu điện trở này là **cháy opto trong driver**. Một số driver có sẵn jumper chọn 24 V — nếu có
thì gạt jumper và bỏ điện trở.

> **Dùng loại 0.5 W, đừng dùng 0.25 W.** Dòng qua trở ≈ (24 − 1.2) / 2000 ≈ 11 mA, tiêu tán
> 0.24 W. Với `PUL` thì tín hiệu chạy 50 % chu kỳ nên không sao, nhưng `DIR` và `ENA` là mức DC
> **giữ liên tục** — 0.24 W trong một con 0.25 W là chạm trần, nóng và lão hoá nhanh.

### 3.2 Driver nhận thẳng 24 V

Nối trực tiếp, không cần điện trở. Đọc nhãn hoặc datasheet để chắc chắn trước khi đấu.

### 3.3 Dùng nhiều driver khác model

Không ảnh hưởng chương trình, nhưng mỗi con phải kiểm riêng 3 thứ:

| Cần kiểm | Vì sao |
|---|---|
| Mức áp đầu vào (5 V hay 24 V) | Quyết định có cần điện trở 2 kΩ hay không |
| Tần số xung tối đa | Đặt `max velocity` trong Technology Object và `VelX`/`VelY` trong `DB_TrayTable`. TB6600 thực tế ~20–40 kHz, DM542 tới ~200 kHz |
| Vi bước cài trên DIP | Nhập vào `Pulses per motor revolution` của đúng trục đó |

Ghi lại thông số thực tế vào bảng dưới cho khỏi quên:

| Trục | Chuyển động | Model driver | Loại | Áp vào | Vi bước đặt | Tần số trần |
|---|---|---|---|---|---|---|
| X | ngang qua lại | `HBS86H v4` | hybrid servo **vòng kín**, motor 86 + encoder | 5 V → cần 2 kΩ | | 100 kHz (giới hạn PLC) |
| Y | lật trái phải ±60° | `ASD556R-LW` (Lan Wei) | bước 2 pha, motor 57/60 | 5 V → cần 2 kΩ | để **thấp**, 800–1000 | **20 kHz** (giới hạn PLC) |
| Z | lên xuống | `3DH583` | bước **3 pha** | 5 V → cần 2 kΩ | | 100 kHz (giới hạn PLC) |

Ba lưu ý riêng cho bộ driver này:

- `3DH583` là driver **3 pha** — chỉ chạy motor bước 3 pha (3 dây). Gắn motor 2 pha thường vào là không quay.
- `HBS86H` là **vòng kín** — bắt buộc có cáp encoder từ motor về driver. Chân **ALM** của nó nên đưa
  về một DI của PLC để biết khi motor kẹt hoặc mất bước.
- **Trục Y** (không phải Z) mới là trục nằm trên kênh 20 kHz — `Q0.6`/`Q0.7`. Z ở `Q0.2`/`Q0.3`,
  chạy 100 kHz. Bản trước ghi nhầm tên trục ở dòng này.
  Với Y, tính thử cho yên tâm: tốc độ lật đang đặt `TiltVel = 200 °/s`, dẫn động trực tiếp thì
  0.56 vòng/giây. Để 6400 xung/vòng cũng chỉ ra 3.6 kHz — còn xa trần 20 kHz.
  Nên vi bước **1600–3200** là vừa: đủ mượt, chống cộng hưởng, mà vẫn thừa tốc độ.
  Chỉ khi nào có hộp giảm tốc tỷ số lớn mới phải hạ vi bước xuống.

`v_max (mm/s) = tần số trần (Hz) ÷ (xung mỗi vòng ÷ mm mỗi vòng)` — rồi đặt tốc độ vận hành khoảng
50–60 % giá trị này.

### 3.4 `ASD556R-LW` (Lan Wei) — trục Y, chép từ nhãn trên thân

Nguồn động lực ghi trên nhãn: **DC 18–50 V**. Nhãn **không ghi điện áp tín hiệu** —
xem mục 3.1 và cách đo ở cuối mục này để biết có cần điện trở 2 kΩ hay không.

> **Nhãn in sai `DLR+` / `DLR−`.** Đó là `DIR+` / `DIR−` (Direction). Đừng đi tìm cọc `DIR`.

Cọc từ trên xuống: `PWR/ALM` (đèn) · `PUL+` `PUL−` `DLR+` `DLR−` `ENA+` `ENA−` ·
`SW8`…`SW1` · `V−` `V+` `A+` `A−` `B+` `B−`.

**Bảng dòng** — chọn RMS ≤ dòng ghi trên nhãn motor:

| Peak (A) | RMS (A) | SW1 | SW2 | SW3 |
|---|---|---|---|---|
| 1.4 | 1.0 | on | on | on |
| 2.1 | 1.5 | off | on | on |
| 2.7 | 1.9 | on | off | on |
| 3.2 | 2.3 | off | off | on |
| 3.8 | 2.7 | on | on | off |
| 4.3 | 3.1 | off | on | off |
| 4.9 | 3.5 | on | off | off |
| 5.6 | 4.0 | off | off | off |

`SW4`: `on` = dòng đầy · `off` = nửa dòng. Trục Y phải giữ mâm nghiêng 60° nên để **`on`**.

**Bảng vi bước** (xung/vòng):

| MSTEP | SW5 | SW6 | SW7 | SW8 | | MSTEP | SW5 | SW6 | SW7 | SW8 |
|---|---|---|---|---|---|---|---|---|---|---|
| 200 | on | on | on | on | | 1000 | on | on | on | off |
| 400 | off | on | on | on | | 2000 | off | on | on | off |
| 800 | on | off | on | on | | 4000 | on | off | on | off |
| **1600** | **off** | **off** | **on** | **on** | | 5000 | off | off | on | off |
| 3200 | on | on | off | on | | 8000 | on | on | off | off |
| 6400 | off | on | off | on | | 10000 | off | on | off | off |
| 12800 | on | off | off | on | | 20000 | on | off | off | off |
| 25600 | off | off | off | on | | 25000 | off | off | off | off |

Số đặt ở đây phải nhập y hệt vào `Pulses per motor revolution` của `Axis_Y`.

**Cách đo xem có cần điện trở 2 kΩ hay không** — an toàn, không cần PLC:

```
+24 V ──[ 2 kΩ ]──┬── PUL+          Đo DC volt trên HAI CHÂN con trở
                  │
  0 V ─────────────── PUL−
```

| Đo được | Trở nội | Kết luận |
|---|---|---|
| ≈ 19–20 V | ~330 Ω | Ngõ vào 5 V → **giữ điện trở 2 kΩ** |
| ≈ 10–12 V | ~2.2 kΩ | Đã tính sẵn cho 24 V → **bỏ điện trở** |

Có trở trong mạch nên đo kiểu này không hỏng gì, dù kết quả ra đằng nào.

## 4. Nguồn và an toàn

- Nguồn 24 VDC riêng cho PLC, nguồn công suất riêng cho driver (thường 24–48 VDC).
- **Mốc tham chiếu của tín hiệu xung là `0 V` của PLC, không phải `0 V` của nguồn 48 V.**
  Ba driver ở đây đều có ngõ vào kiểu cặp cách ly quang (`PUL+`/`PUL−`, `DIR+`/`DIR−`), nên vòng
  dòng khép kín ngay trong miền 24 V: `Q → điện trở → PUL+ → LED quang → PUL− → 0 V của PLC`.
  Bắt buộc phải có sợi `PUL−`/`DIR−`/`ENA−` về `0 V` của PLC.
  Nối chung `−V` của nguồn 48 V với `0 V` của nguồn 24 V là **tuỳ chọn** (chỉ để chống nhiễu), và
  nếu nối thì chỉ nối **một điểm duy nhất**. Bản trước ghi là bắt buộc — không đúng với loại
  driver cách ly quang.
  Ngoại lệ: driver rẻ tiền kiểu ngõ vào đơn (`PUL`, `DIR`, `GND` dùng chung mát với nguồn động lực)
  thì mới bắt buộc nối chung hai nguồn.
- Dây xung đi **cáp có lưới chống nhiễu**, nối đất lưới **một đầu** phía tủ điện. Không đi chung
  máng với dây động lực.
- Mạch dừng khẩn phải **cắt trực tiếp nguồn hoặc chân Enable của driver bằng phần cứng**, không đi
  qua phần mềm PLC.
- Công tắc giới hạn cứng nên vừa đưa vào DI của PLC, vừa đấu nối tiếp cắt Enable driver — phòng
  trường hợp chương trình treo.

## 5. Trục lên xuống — nguy cơ rơi tải

Trục Y chống trọng lực. Mạch dừng khẩn cắt Enable driver là motor mất mô-men giữ, đầu công tác
**rơi tự do**. Vòng kín cũng không cứu được vì nó mất điện cùng lúc. Phải có ít nhất một trong ba:

- motor có **phanh điện từ** (phanh ăn khi mất điện) — cách chuẩn nhất
- cơ cấu **tự hãm**: vít me bước nhỏ hoặc hộp số trục vít
- **đối trọng** hoặc lò xo cân bằng

## 6. Giới hạn tần số của CPU

CPU 1214C có 4 kênh PTO nhưng **chỉ Q0.0–Q0.3 chạy 100 kHz**. Kênh thứ 3 (`Q0.6`/`Q0.7`) bị giới hạn
**20 kHz**. Cả ba driver của bạn đều chịu được 200 kHz, nên nút thắt nằm ở PLC chứ không phải driver.

Muốn kênh thứ 3 nhanh hơn: gắn signal board **SB1222 DQ4x24VDC 200kHz** và trỏ kênh PTO vào ngõ ra
của board.

## 7. Mạch điều khiển trên nắp tủ — CB, đèn đỏ, nút Start, nút E-Stop

Hai file hình:

- `SoDoDauDay.svg` **Phần 4** — sơ đồ nguyên lý, để *hiểu* mạch chạy thế nào.
- `SoDoDauDayThucTe.svg` — vẽ đúng từng con trong tủ, **có số cọc**, kèm bảng
  đấu dây đánh số. Đây là tờ in ra cầm đi đấu.

### 7.1 Đồ đang có trong tủ

| Ký hiệu | Model thật | Cọc / chân |
|---|---|---|
| `CB1` | CHiNT **NXB-63 C20 2P** | `1`,`3` vào · `2`,`4` ra |
| **nguồn 24 V** | Omron **S8VK-C12024** | vào `L`,`N`,`PE` · ra `+V`,`−V` — 24 VDC 5 A |
| **nguồn 48 V** | Meanwell **LRS-600-48** | vào `AC/L`,`AC/N`,`PE` · ra `+V`,`−V` — 48 VDC |
| `PLC` | Siemens **CPU 1214C DC/DC/DC** | `L+`,`M`,`1M`,`DI a.7` |
| `K1` | CHiNT **NXJ/2Z(D) 24 VDC** | cuộn `13`/`14(+)` · khối 1 `9`-`5`-`1` · khối 2 `12`-`8`-`4` |
| `S0` | Nút nấm E-Stop Φ22 | **1** tiếp điểm NC: `11`-`12` |
| `S1` | Nút ấn START Φ22 **có đèn** | NO `13`-`14` · đèn `X1`-`X2` |
| `H1` | Đèn báo đỏ Φ22 24 VDC | `X1`-`X2` |

220 V lưới vào `CB1` trong tủ, sau `CB1` chia hai nhánh: **nguồn 24 V** nuôi PLC và mạch
điều khiển, **nguồn 48 V** nuôi ba driver. Đèn, nút, relay trên nắp tủ **đều 24 VDC**.

### 7.2 Bấm thì máy làm gì

| Thao tác | Kết quả |
|---|---|
| Bật `CB1` | **Đèn đỏ `H1` sáng** — có điện, máy chưa cho chạy |
| Ấn `START` | `K1` hút và tự giữ → đỏ **tắt**, **nút START sáng xanh**, `I0.7 = 1` |
| Ấn `E-STOP` | `K1` nhả → xanh tắt, **đỏ sáng lại**, `I0.7 = 0` → `FC_Main` dừng |
| Xoay nhả `E-STOP` | Đỏ **vẫn sáng**. Phải ấn `START` lần nữa mới chạy |

Dòng cuối là cố ý: nhả nút khẩn xong mà máy tự chạy lại là mất an toàn.

### 7.3 `K1` chỉ có 2 khối — chia thế nào cho đủ

`NXJ/2Z` là loại **2 khối chuyển mạch**, không phải 4. Chia như sau là vừa khít:

| Khối | Chân | Dùng làm gì |
|---|---|---|
| 1 | `9` (chung) → `5` (NO) | Tự giữ, đấu **song song** nút `START` |
| 2 | `12` (chung) → **0 V** | Chân chung đấu xuống 0 V |
| 2 | `4` (NC) | Đèn đỏ `H1` — K1 chưa hút thì đèn có mát → sáng |
| 2 | `8` (NO) | Kéo `DI a.7` (`I0.7`) xuống 0 V khi K1 đã hút |

Mẹo ở đây: **chân chung `12` đặt ở 0 V** nên một khối làm được cả hai việc —
phía NC thắp đèn đỏ, phía NO báo về PLC. Đặt chân chung ở +24 V là phải tốn hai
khối, mà bạn không có.

Đèn trong nút `START` **không tốn tiếp điểm nào**: đấu song song cuộn `K1` bằng
một đoạn dây cầu từ cọc `X1` sang cọc `14` ngay trên thân nút.

> **Cuộn có diode.** Bản `(D)` chống ngược, nên **đúng cực mới hút**:
> chân `14` là **(+)**, chân `13` xuống 0 V.

### 7.4 Vì sao nhánh về PLC phải kéo xuống 0 V

Mục 2 đã chốt `1M = +24 V` (vì cảm biến EE-SX951 là NPN). Chân DI của S7-1200 lúc
đó ăn kiểu **sink** — nối xuống 0 V mới lên 1. Nên tiếp điểm báo trạng thái đấu
`0 V → K1 chân 12 → chân 8 → DI a.7`. Đấu ngược lên 24 V là `I0.7` không bao giờ
tích cực, dù mạch chạy đúng.

Đứt dây ở đâu trong nhánh này cũng làm `I0.7 = 0` → `FC_Main` dừng. Hỏng cũng dừng.

### 7.5 Điều còn thiếu — đọc kỹ

Nút `E-Stop` của bạn **chỉ có một tiếp điểm NC**, đã dùng hết để cắt cuộn `K1`.
`K1` cũng đã dùng hết hai khối. Nên hiện tại:

> Nhấn `E-Stop` chỉ làm `K1` nhả → đèn đỏ sáng, PLC biết qua `I0.7` rồi dừng bằng
> **phần mềm**. Nguồn 48 V của ba driver **vẫn còn**. Chương trình treo là không
> ai cắt được.

Điều này đi ngược mục 4 (*dừng khẩn phải cắt bằng phần cứng*). Vá bằng cách rẻ nhất:

1. Mua thêm **một khối tiếp điểm NC** gắn vào chính nút nấm đó (thân Φ22 thường
   lắp được 2 khối) — khoảng vài chục nghìn.
2. Mua **một contactor `K2`** chịu được cắt DC, theo dòng của `LRS-600-48`.
3. Đấu: `+24 V → khối NC thứ hai của E-Stop → cuộn K2 → 0 V`, và tiếp điểm động
   lực của `K2` nối tiếp `+V` của `LRS-600-48` đi vào ba driver.

Cách này còn hơn đi qua `K1`: nó **độc lập hoàn toàn** với relay, nên `K1` có dính
tiếp điểm thì nút khẩn vẫn cắt được.

> **Nhắc lại mục 5:** `K2` cắt là ba driver mất nguồn, motor trục Z mất mô-men giữ
> và đầu công tác **rơi tự do**. Phanh điện từ (nếu có) phải là loại **ăn khi mất
> điện**, đấu sau tiếp điểm `K2`.

Ghi chú thêm: `CB1` là **C20** — 20 A, khá lớn so với tải thật (nguồn 24 V 5 A + nguồn 48 V
600 W ≈ 3 A). Nó bảo vệ dây chứ không bảo vệ được thiết bị. Muốn chọn lọc thì thêm
cầu chì hoặc CB nhánh nhỏ cho từng bộ nguồn.

### 7.6 Bảng đấu dây

28 sợi, đánh số đầy đủ trong `SoDoDauDayThucTe.svg` khối ④. Dây điều khiển
0.75 mm², bấm đầu cốt ferrule và lồng số hai đầu đúng cột `#`.

### 7.7 Thử nguội trước khi cấp điện động lực

Cắt nhánh **nguồn 48 V** ra trước, rồi:

1. Bật `CB1` → đèn đỏ phải sáng.
2. Ấn `START` → nghe `K1` kêu "cạch", đèn đỏ tắt, nút `START` sáng xanh.
3. Ấn `E-STOP` → đèn đỏ sáng lại, nút xanh tắt.
4. Xoay nhả `E-STOP` → đèn đỏ **vẫn** sáng. Ấn `START` mới chạy lại.
5. Đo thông mạch từ `K1` chân `8` xuống 0 V ở cả hai trạng thái, **trước khi** cắm
   dây vào `DI a.7`.

Bước 2 mà `K1` không kêu: kiểm cực cuộn — chân `14` phải là **(+)**.
Bước 4 mà nút tự sáng xanh lại: đấu nhầm tự giữ sang `9`→`1` (NC) thay vì `9`→`5`.
