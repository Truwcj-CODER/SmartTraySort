# App Android — SmartTraySort

Giao diện cầm tay cho cùng cái máy mà trang web điều khiển. Cùng server, cùng
API, cùng bộ chức năng — chỉ khác là nằm gọn trong túi và đứng ngay cạnh máy.

## Vì sao có bản app riêng

Trang web mở được trên điện thoại, nhưng nó được vẽ cho màn hình rộng: bàn phím
số của trình duyệt không có nút giữ-để-jog, camera quét mã phải qua nhiều lớp
xin phép, và mất sóng một giây là mất luôn cả trang. App gốc giải quyết đúng ba
chỗ đó — jog nhận được lúc ngón tay chạm xuống và lúc nó rời ra, camera quét mã
chạy thẳng bằng ML Kit, và đường trạng thái tự nối lại mà người dùng không thấy
gì.

## Nhận trạng thái bằng SSE, không hỏi vòng

Server đọc PLC mỗi 200 ms. Nếu app hỏi vòng theo nhịp đó thì mỗi máy là vài
nghìn request một phút trên mạng xưởng. Thay vào đó server mở một đường
`text/event-stream` tại `GET /api/events` và đẩy xuống khi có gì mới:

| Sự kiện | Khi nào gửi | Nội dung |
|---|---|---|
| `status` | mỗi vòng đọc PLC | vị trí 3 trục, bước, mã lỗi |
| `inventory` | khi bảng rổ đổi | số vật từng rổ + tổng kết |
| `layout` | khi cấu hình đổi | tọa độ rổ, quy đổi, cảnh báo |

Hai loại sau chỉ gửi khi `revision` phía server tăng, nên lúc máy đứng yên đường
truyền chỉ có vài chục byte mỗi giây. App **không** gọi REST để làm mới bất cứ
thứ gì — lệnh đi bằng REST, dữ liệu về bằng SSE, không có đường thứ ba.

Mất sóng thì `StatusStream` tự nối lại, giãn dần 1 → 10 giây. Đổi địa chỉ server
trong Cài đặt thì `flatMapLatest` cắt kết nối cũ và mở kết nối mới — không chỗ
nào còn giữ địa chỉ cũ.

## Cấu trúc

```
android_app/
├── publish.sh                    build + đặt bản mới lên server, một lệnh
├── keystore.jks                  khóa ký bản phát hành (không lên git)
├── keystore.properties           mật khẩu khóa (không lên git)
└── app/src/main/java/vn/hasaki/traysort/
    ├── MainActivity.kt           một Activity, phần còn lại là Compose
    ├── core/
    │   ├── Prefs.kt              địa chỉ server + kiểu giao diện, DataStore
    │   └── Machine.kt            mã bước PLC → chữ tiếng Việt, mô tả form
    ├── data/
    │   ├── Models.kt             hình dạng dữ liệu server trả về
    │   ├── Net.kt                một OkHttpClient cho lệnh, một cho SSE
    │   ├── TraySortApi.kt        toàn bộ REST, một chỗ bắt lỗi
    │   ├── StatusStream.kt       SSE + tự nối lại
    │   ├── Updater.kt            tự cập nhật qua WiFi
    │   └── Repository.kt         ráp ba mảnh trên lại
    └── ui/
        ├── AppViewModel.kt       nơi duy nhất giữ trạng thái và gọi lệnh
        ├── AppRoot.kt            thanh tiêu đề + 5 tab
        ├── theme/Theme.kt        bảng màu lấy từ styles.css của web
        ├── parts/                mảnh dùng lại: Panel, TrayGrid, StateCard, sơ đồ
        └── screens/              Vận hành · Sơ đồ · Cài đặt máy · Nhật ký · Hệ thống
```

Một chiều phụ thuộc: `ui → data → mạng`. Màn hình không tự gọi API bao giờ; mọi
lệnh đều đi qua `AppViewModel.command()` nên chỗ nào cũng khóa-khi-đang-chạy và
bắt lỗi giống hệt nhau.

## Năm tab

| Tab | Có gì |
|---|---|
| **Vận hành** | quét mã (gõ tay hoặc camera), lưới rổ, chạy tự động, home/park/xóa lỗi/DỪNG, sửa tồn kho |
| **Sơ đồ** | mặt cắt 2D chạy theo vị trí thật của 3 trục, bảng tọa độ từng rổ |
| **Cài đặt máy** | kích thước giàn khay, quy đổi đối chiếu TIA, chạy tay, jog |
| **Nhật ký** | mọi lệnh gửi đi và kết quả trả về |
| **Hệ thống** | địa chỉ server, sáng/tối, kiểm tra bản mới |

Nút **DỪNG** không đi qua khóa lệnh — bấm được cả khi chu trình đang chạy dở,
giống `emergency_stop` bên server.

## Tự cập nhật qua WiFi

Nhà xưởng không có Play Store, mà đi cắm cáp từng máy thì không ai làm nổi. Nên
server tự làm nơi phát bản mới.

### Quy trình phát hành — làm đúng ba bước này

**Bước 1 — tăng số hiệu.** Mở `app/build.gradle.kts`, sửa hai dòng:

```kotlin
versionCode = 4              // ← BẮT BUỘC tăng, mỗi bản +1
versionName = "1.0.3"        // ← chỉ để người đọc, đặt sao cũng được
```

`versionCode` là con số **duy nhất** điện thoại dùng để so. Quên tăng nó thì
`publish.sh` vẫn chạy, server vẫn nhận file mới, nhưng điện thoại so `4 > 4` ra
sai nên **coi như không có gì mới** — và không ai biết vì sao. Đây là chỗ nhầm
duy nhất của cả quy trình.

`versionName` không tham gia so sánh. Nó chỉ là cái chữ hiện trong hộp thoại
*"Có bản 1.0.3"*.

**Bước 2 — phát hành.**

```bash
cd android_app
./publish.sh --notes "Thêm nút X, sửa lỗi Y"
```

Câu sau `--notes` hiện nguyên văn trong hộp thoại trên điện thoại, nên viết cho
người vận hành đọc, đừng viết cho lập trình viên.

Script in ra số hiệu nó **đọc được từ file APK vừa build** — không phải số bạn gõ
trong `build.gradle.kts`. Đối chiếu dòng đó là biết ngay có quên tăng hay không:

```
==> da phat hanh 1.0.3 (code 4)
    ../app/updates/smarttraysort-1.0.3.apk
    24M  sha256 64436a0a7dc12c2d…
```

**Bước 3 — không làm gì cả.** Người vận hành mở app lên là thấy hộp thoại. Không
cắm cáp, không mở trình duyệt, không Play Store.

### Bảng số hiệu đã phát hành

Ghi lại ở đây mỗi lần phát hành, để lần sau biết `versionCode` kế tiếp là bao nhiêu.

| versionCode | versionName | Ngày | Có gì |
|---|---|---|---|
| 1 | 1.0.0 | 2026-08-26 | Bản đầu tiên |
| 2 | 1.0.1 | 2026-08-26 | Sửa màu nút cho khớp thương hiệu, sơ đồ tách rõ hai dãy rổ |
| 3 | 1.0.2 | 2026-08-26 | Nút Cài đặt tự xin quyền khi máy chưa cho cài từ nguồn ngoài |

### Chỉ lần đầu mới cần trình duyệt

| Lần | Người vận hành làm gì |
|---|---|
| Cài đầu tiên | mở trình duyệt vào `http://<ip-orange-pi>:8000/api/app/download` |
| Mọi lần sau | **mở app lên** — nó tự hỏi server, tự nhắc, tự tải |

App hỏi server ngay lúc mở. Bấm *"Để sau"* thì hộp thoại tắt trong phiên đó,
nhưng tab **Hệ thống** vẫn có nút *"Kiểm tra bản mới"*, và lần mở app kế tiếp nó
lại nhắc.

Không có mạng thì app im lặng bỏ qua — không dập một dòng báo đỏ vào mặt người
đang đứng cạnh máy. Vào mạng lại thì lần mở sau nhắc tiếp.

Script build bản release đã ký, chép sang `../app/updates/`, và viết
`latest.json` bên cạnh (số hiệu bản đọc thẳng từ file APK, không đọc từ
`build.gradle.kts` — cái nằm trong APK mới là cái điện thoại nhìn thấy).

Điện thoại mở app lên:

1. hỏi `GET /api/app/latest`
2. `version_code` lớn hơn bản đang cài → hiện hộp thoại **"Có bản 1.1.0"**
3. tải APK, **đối chiếu SHA-256**, rồi gọi trình cài đặt của Android

Bước 3 không được cắt: tải qua HTTP trần trong mạng nội bộ thì không có gì bảo
đảm gói tin không bị sửa dọc đường. Mã băm không khớp là xóa file và báo lỗi.

Android vẫn hỏi xác nhận trước khi cài — app chỉ mở được màn hình cài đặt, quyết
định vẫn là của người dùng. Lần đầu máy sẽ xin bật *"cho phép cài đặt từ nguồn
này"*, app dẫn thẳng tới đúng màn hình đó.

> **Giữ kỹ `keystore.jks`.** Mất nó là mất khả năng phát bản cập nhật: Android
> từ chối cài đè một APK ký bằng khóa khác lên app đang chạy. Sao lưu ra chỗ
> khác ngay.

## Build

Cần JDK 17 và Android SDK (compileSdk 35, build-tools 35).

```bash
export JAVA_HOME=$HOME/.jdk/jdk-17.0.19+10
export ANDROID_HOME=$HOME/Android/Sdk

./gradlew :app:assembleDebug      # bản thử, cài song song được với bản chính
./gradlew :app:assembleRelease    # bản phát hành, đã ký + rút gọn
```

Bản debug có `applicationId` khác (`…​.debug`) nên cài chung máy với bản phát
hành mà không đè lên nhau.

## Cài lần đầu

Điện thoại chưa có app thì mở trình duyệt vào:

```
http://<ip-orange-pi>:8000/api/app/download
```

Cài xong, app hỏi địa chỉ máy chủ — gõ IP là đủ, nó tự thêm `http://` và cổng
`8000`. Từ lần sau app tự lo phần cập nhật.

## Quyền

| Quyền | Để làm gì | Không cấp thì sao |
|---|---|---|
| `INTERNET` | gọi API, nhận SSE | app không chạy được |
| `CAMERA` | quét mã bằng camera | vẫn gõ mã tay được |
| `REQUEST_INSTALL_PACKAGES` | tự cập nhật | phải cài tay qua trình duyệt |

Cho phép HTTP trần (`network_security_config.xml`) vì server trong mạng nội bộ
không có chứng chỉ TLS. Chỉ mở đúng chỗ đó, phần còn lại vẫn bắt buộc HTTPS.
