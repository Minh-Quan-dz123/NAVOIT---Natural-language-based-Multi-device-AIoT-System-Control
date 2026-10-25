# DEVICE REGISTRY API — TÀI LIỆU MÔ TẢ

**Phiên bản tài liệu:** 1.0 — phân tích source ngày 24/10/2026  
**Công nghệ:** ASP.NET Core Web API, EF Core, PostgreSQL, JWT Bearer  
**Đối tượng sử dụng:** Frontend/Web và NLP Server trong hệ thống điều khiển thiết bị bằng giọng nói.

> **Trạng thái:** Đây là tài liệu **theo source được cung cấp**, không phải kết quả chạy/test API. Có **39 route** được khai báo trong 10 Controller thực sự chứa action. Một số Service trong ZIP chưa được triển khai hoặc không khớp Controller/DTO nên dự án **chưa đủ căn cứ để khẳng định biên dịch/chạy được**. Ký hiệu **[Thiết kế/chưa sẵn sàng]** nghĩa là route có trong Controller nhưng chưa có triển khai Service phù hợp trong source; **[501]** nghĩa là Controller chủ động trả 501; **[Có xử lý]** nghĩa là thấy logic xử lý tương ứng, nhưng chưa được kiểm thử runtime.

## 1. Tổng quan

Registry lưu và quản lý:

- `User`: tài khoản người dùng.
- `Microcontroller`: thông tin ESP32/ESP8266 thuộc User.
- `DeviceType`: loại thiết bị và tập trạng thái cho phép.
- `Device`: thiết bị logic, có thể chưa gắn MCU/GPIO.
- `Schedule`: tối đa một lịch đang lưu cho mỗi Device.
- `Tag`, `TagGroup`, `DeviceTagGroup`: các nhãn và nhóm từ đồng nghĩa phục vụ NLP nhận diện thiết bị.

**Phân công trách nhiệm:**

1. **Web/Frontend** gọi API xác thực, cấu hình thiết bị, MCU, lịch và tag.
2. **Device Registry Server** lưu cấu hình, giữ bản ghi các trạng thái và liên kết dữ liệu.
3. **NLP Server** xử lý câu lệnh/ngữ nghĩa, điều phối MQTT tới ESP32, xử lý phản hồi và dùng **Internal API** để cập nhật lại Registry.
4. **ESP32** thực thi lệnh và cung cấp kết quả thực tế.

**Quan trọng:** `201 Created` khi tạo Device và `200 OK` khi lưu Schedule **chỉ khẳng định thao tác lưu Registry**; chúng **không xác nhận** ESP32 đã nhận hay thực thi lệnh. Các Internal API bản thân chúng cũng **không publish MQTT**.

## 2. Quy ước chung

- Base URL: `https://<YOUR-HOST>` (địa chỉ thực tế **chưa được cung cấp**).
- Kiểu dữ liệu request/response: `application/json`.
- JSON property được minh họa theo **camelCase** của thiết lập mặc định ASP.NET Core; không thấy cấu hình serializer riêng trong `Program.cs`.
- Các giá trị `id`, `deviceId`, `mcuId`: số nguyên (route có ràng buộc `:int`).
- Thời gian `.NET DateTime` được trả dưới dạng chuỗi ISO 8601 theo JSON serializer; thời gian Unix cho Schedule là **số giây**, không phải mili-giây.
- `null` có nghĩa không có giá trị; một số DTO dùng `null` để biểu thị *không sửa trường đó* trong PATCH.
- `204 No Content`: response body rỗng.
- `400 Bad Request`: dữ liệu không hợp lệ; `401 Unauthorized`: không xác thực; `404 Not Found`: không tìm thấy; `409 Conflict`: xung đột/ràng buộc nghiệp vụ; `501 Not Implemented`: chưa triển khai.
- Lỗi validation từ `[ApiController]` có thể được ASP.NET Core tự trả `400` theo định dạng `ValidationProblemDetails`, **khác** với lỗi nghiệp vụ `{ "message": "..." }` mà Controller tự tạo.
- Response JSON mô tả bên dưới là **ví dụ minh họa cấu trúc**, không phải dữ liệu lấy từ database thật.

### 2.1. Xác thực JWT dành cho Public API

Tất cả endpoint trừ `/api/auth/register`, `/api/auth/login` và nhóm `/api/internal/*` đều có `[Authorize]`. Gửi:

```http
Authorization: Bearer <accessToken>
Content-Type: application/json
```

- Đăng nhập/đăng ký trả `accessToken`, `expiresAt`, `userId`, `username`.
- Token được ký **HS256**, hiệu lực **1 giờ**, chứa claim User ID và Username.
- Server xác minh Issuer, Audience, SigningKey, Lifetime và cho phép chênh lệch thời gian 30 giây.
- Nhiều API User/Device/Microcontroller/Schedule/Tag lấy User ID từ claim JWT; client không cần đưa `userId` trong body của những API đó.

### 2.2. Xác thực giữa NLP Server và Registry

Toàn bộ `/api/internal/*` sử dụng:

```http
X-Internal-Key: <InternalApiKey>
Content-Type: application/json
```

- **Không dùng JWT người dùng** cho 5 Internal API.
- Cấu hình `InternalApiKey` bắt buộc và dài ít nhất **32 byte UTF-8** lúc khởi động (theo `Program.cs`).
- Header được so khớp với key cấu hình bằng phép so sánh constant-time.
- Body Internal API có `userId` và server xác minh quyền sở hữu bản ghi cho user đó.
- **Tuyệt đối không đưa key này vào trình duyệt/Frontend**; chỉ NLP Server/trusted backend giữ key.

## 3. Danh mục API (39 endpoints)

Ký hiệu: `JWT` = Bearer Token; `KEY` = `X-Internal-Key`; `—` = public không xác thực.

| Nhóm | Method | Endpoint | Xác thực | Mục đích / tình trạng |
|---|---|---|---|---|
| Auth | POST | `/api/auth/register` | — | Đăng ký, trả JWT; có xử lý |
| Auth | POST | `/api/auth/login` | — | Đăng nhập, trả JWT; có xử lý |
| User | POST | `/api/user` | JWT | Tạo người dùng; có xử lý |
| User | GET | `/api/user` | JWT | Lấy tất cả User; có xử lý |
| User | GET | `/api/user/{id}` | JWT | Chi tiết User; có xử lý |
| User | GET | `/api/user/username/{username}` | JWT | Tìm User theo username; có xử lý |
| User | PUT | `/api/user/{id}` | JWT | Sửa tên và số điện thoại; có xử lý |
| User | PUT | `/api/user/{id}/password` | JWT | Đổi mật khẩu; có xử lý |
| User | DELETE | `/api/user/{id}` | JWT | Xóa tài khoản; có xử lý |
| DeviceType | GET | `/api/devicetype` | JWT | Danh sách loại; có xử lý nhưng DTO không khớp Service |
| DeviceType | GET | `/api/devicetype/{id}` | JWT | Chi tiết loại; có xử lý nhưng DTO không khớp Service |
| DeviceType | POST | `/api/devicetype` | JWT | Tạo loại; thiết kế/chưa sẵn sàng |
| DeviceType | PATCH | `/api/devicetype/{id}` | JWT | Sửa loại; thiết kế/chưa sẵn sàng |
| DeviceType | DELETE | `/api/devicetype/{id}` | JWT | Xóa loại; có xử lý |
| Microcontroller | POST | `/api/microcontroller` | JWT | Đăng ký MCU; thiết kế/chưa sẵn sàng |
| Microcontroller | GET | `/api/microcontroller` | JWT | MCU của User; thiết kế/chưa sẵn sàng |
| Microcontroller | GET | `/api/microcontroller/{id}` | JWT | Chi tiết MCU; thiết kế/chưa sẵn sàng |
| Microcontroller | PATCH | `/api/microcontroller/{id}` | JWT | Đổi Type/MAC; thiết kế/chưa sẵn sàng |
| Microcontroller | DELETE | `/api/microcontroller/{id}` | JWT | Xóa MCU; thiết kế/chưa sẵn sàng |
| Microcontroller | GET | `/api/microcontroller/{id}/devices` | JWT | Device gắn MCU; thiết kế/chưa sẵn sàng |
| Device | POST | `/api/device` | JWT | Tạo Device; thiết kế/chưa sẵn sàng |
| Device | GET | `/api/device` | JWT | Danh sách Device; có logic đọc, trả Entity |
| Device | GET | `/api/device/unassigned` | JWT | Device chưa gắn MCU; thiết kế/chưa sẵn sàng |
| Device | GET | `/api/device/{id}` | JWT | Chi tiết Device; có logic đọc, trả Entity |
| Device | PATCH | `/api/device/{id}` | JWT | Sửa Device; thiết kế/chưa sẵn sàng |
| Device | DELETE | `/api/device/{id}` | JWT | Xóa Device; có xử lý |
| Device | POST | `/api/device/resolve` | JWT | Ánh xạ tag thành Device; chủ động trả **501** |
| Catalog | GET | `/api/device/catalog` | JWT | Snapshot Device cho NLP; có xử lý trực tiếp EF |
| Device tags | GET | `/api/device/{deviceId}/tags` | JWT | Nhãn hiện tại; thiết kế/chưa sẵn sàng |
| Device tags | PUT | `/api/device/{deviceId}/tags` | JWT | Thay toàn bộ nhãn; thiết kế/chưa sẵn sàng |
| TagGroup | GET | `/api/taggroup` | JWT | Nhóm tag của User; thiết kế/chưa sẵn sàng |
| Schedule | GET | `/api/device/{deviceId}/schedule` | JWT | Lấy lịch; thiết kế/chưa sẵn sàng |
| Schedule | PUT | `/api/device/{deviceId}/schedule` | JWT | Tạo/cập nhật lịch; thiết kế/chưa sẵn sàng |
| Schedule | DELETE | `/api/device/{deviceId}/schedule` | JWT | Hủy lịch; thiết kế/chưa sẵn sàng |
| Internal | PATCH | `/api/internal/devices/{deviceId}/binding` | KEY | Chốt MCU/GPIO sau xử lý vật lý; có xử lý EF |
| Internal | PUT | `/api/internal/devices/{deviceId}/status` | KEY | Báo trạng thái Device từ ESP32; có xử lý EF |
| Internal | POST | `/api/internal/microcontrollers/{mcuId}/refresh` | KEY | Đối soát snapshot từ MCU; có xử lý EF |
| Internal | POST | `/api/internal/schedules/{deviceId}/command` | KEY | Ghi commandId lịch trước MQTT; thiết kế/chưa sẵn sàng |
| Internal | POST | `/api/internal/schedules/{deviceId}/ack` | KEY | Áp kết quả ACK của ESP32; thiết kế/chưa sẵn sàng |

**Không có** action trong `TagController.cs` (chỉ là một dòng comment). **Không có** endpoint REST công khai để thêm alias đồng nghĩa trong các Controller được gửi.

---

## 4. Auth API

### 4.1. POST `/api/auth/register`

Đăng ký tài khoản và **trả JWT ngay**. Không cần Bearer token.

**Body — `CreateUserRequestDto`:**

```json
{
  "username": "quan",
  "password": "ExamplePass123",
  "phone": "0912345678"
}
```

- `username`: `string`, bắt buộc về nghiệp vụ (Service từ chối rỗng/trắng); DTO chưa gắn `[Required]`.
- `password`: `string`, bắt buộc, dài **ít nhất 8 ký tự**.
- `phone`: `string|null`, tùy chọn, nếu có phải **đúng 10 chữ số**.

**200 OK — `AuthResponseDto`:**

```json
{
  "accessToken": "<jwt>",
  "expiresAt": "2026-10-24T16:00:00Z",
  "userId": 1,
  "username": "quan"
}
```

**Lỗi:** `400` nếu thông tin không hợp lệ, Username trùng hoặc số điện thoại trùng. Không có `201` ở Controller này.

### 4.2. POST `/api/auth/login`

**Body — `LoginDto`:**

```json
{ "username": "quan", "password": "ExamplePass123" }
```

Cả hai trường `[Required]`.

**200 OK:** cùng cấu trúc `AuthResponseDto` của đăng ký.  
**401:** `{ "message": "Username hoặc password không chính xác." }` nếu tài khoản/mật khẩu sai.  
**400:** request thiếu hoặc sai định dạng theo validation.

---

## 5. User API

**Xác thực:** JWT cho tất cả endpoint. `UserResponseDto`:

```json
{
  "id": 1,
  "username": "quan",
  "phone": "0912345678",
  "createdAt": "2026-10-24T12:00:00Z"
}
```

Mật khẩu không được trả trong `UserResponseDto`.

### 5.1. POST `/api/user`

- Body: `CreateUserRequestDto` như API register.
- **201 Created:** `UserResponseDto`, có header `Location` hướng tới `/api/user/{id}`.
- **400:** Username trùng; lỗi validation.
- **Lưu ý:** tạo User ở route này **không** phát JWT; route vẫn yêu cầu JWT hiện có.

### 5.2. GET `/api/user`

- **200:** mảng `UserResponseDto[]` (có thể rỗng).

### 5.3. GET `/api/user/{id}`

- **200:** một `UserResponseDto`.
- **404:** `{ "message": "Không tìm thấy User." }`.

### 5.4. GET `/api/user/username/{username}`

- **200:** một `UserResponseDto`.
- **404:** không tìm thấy User.

### 5.5. PUT `/api/user/{id}`

Chỉ hỗ trợ cập nhật trường có giá trị được gửi.

```json
{ "username": "quan_new", "phone": "0987654321" }
```

- `username`: nullable; nếu có không được trống, không được trùng.
- `phone`: nullable; nếu có đúng 10 chữ số, không được trùng.
- `null` nghĩa là giữ nguyên trường; source chưa có thao tác đặt `phone` về null.
- **200:** `UserResponseDto`; **400:** dữ liệu không hợp lệ / trùng; **404:** không tìm thấy.

### 5.6. PUT `/api/user/{id}/password`

```json
{
  "oldPassword": "ExamplePass123",
  "newPassword": "NewExamplePass123"
}
```

- Hai trường bắt buộc; `newPassword` ít nhất 8 ký tự.
- **204:** đổi thành công, body rỗng.
- **401:** mật khẩu cũ sai; **400:** dữ liệu không hợp lệ; **404:** User không tồn tại.

### 5.7. DELETE `/api/user/{id}`

- **204:** đã xóa; **404:** không tìm thấy.

**Cảnh báo bảo mật:** `UserController` yêu cầu JWT nhưng **không đối chiếu `{id}` với User ID đang đăng nhập**, cũng không khai báo role quản trị. Theo source, bất kỳ tài khoản đã xác thực có thể gọi các route xem/sửa/xóa User khác nếu biết ID. Cần sửa authorization trước khi đưa vào môi trường có dữ liệu thực.

---

## 6. DeviceType API

**Xác thực:** JWT. Các loại thiết bị là dữ liệu dùng chung trong database hiện tại, không gắn `UserId`.

**DTO được thiết kế để trả — `DeviceTypeResponseDto`:**

```json
{
  "id": 1,
  "typeName": "light",
  "allowedStatuses": ["ON", "OFF"],
  "deviceCount": 3
}
```

> **Chênh lệch thực tế:** `DeviceTypeService` của ZIP trả **entity `DeviceType`**, trong đó `allowedStatuses` là **chuỗi JSON**, và **không có** thuộc tính `deviceCount`; không có mapper sang `DeviceTypeResponseDto`. Ví dụ trên chỉ là **hợp đồng DTO dự kiến**, không phải response được đảm bảo.

### 6.1. GET `/api/devicetype`

- **200:** theo Service hiện tại là danh sách `DeviceType` entities (không phải `DeviceTypeResponseDto[]`).

### 6.2. GET `/api/devicetype/{id}`

- **200:** entity `DeviceType` theo Service; **404:** không tìm thấy.

### 6.3. POST `/api/devicetype`

**Body DTO theo Controller:**

```json
{ "typeName": "light", "allowedStatuses": ["ON", "OFF"] }
```

- `typeName`: bắt buộc, tối đa 50 ký tự.
- `allowedStatuses`: mảng string bắt buộc, tối thiểu 1 phần tử theo DTO; không được chứa phần tử rỗng/trùng theo logic kiểm tra dự kiến của Service.
- **201:** tài nguyên mới; **400:** sai dữ liệu; **409:** xung đột (theo Controller).
- **[Chưa sẵn sàng]** Service nhận `DeviceType` entity, không nhận `CreateDeviceTypeRequestDto`; `AllowedStatuses` entity là string, khác `List<string>` DTO.

### 6.4. PATCH `/api/devicetype/{id}`

```json
{ "typeName": "ceiling_light", "allowedStatuses": ["ON", "OFF"] }
```

- Cho phép cập nhật một hoặc hai trường theo DTO (`null` nghĩa không cập nhật).
- **200:** tài nguyên đã cập nhật; **400**, **404**, **409** theo Controller.
- **[Chưa sẵn sàng]** Service hiện nhận entity, không phải `UpdateDeviceTypeRequestDto`.

### 6.5. DELETE `/api/devicetype/{id}`

- **204:** xóa thành công.
- **404:** không tìm thấy.
- **409:** không thể xóa loại đang được Device sử dụng.

**Cảnh báo phân quyền:** Bất kỳ JWT hợp lệ nào cũng có thể gọi CRUD `DeviceType`; source chưa giới hạn quyền quản trị.

---

## 7. Microcontroller API

**Xác thực:** JWT, User ID lấy từ JWT; tất cả endpoint phụ thuộc `MicrocontrollerService` **rỗng trong ZIP**.

**`MicrocontrollerResponseDto` dự kiến:**

```json
{
  "id": 1,
  "type": "esp32",
  "macAddress": "D8BFC0800FA0",
  "connectionStatus": "unknown",
  "lastSeenAt": null,
  "createdAt": "2026-10-24T12:00:00Z",
  "deviceCount": 0
}
```

### 7.1. POST `/api/microcontroller`

```json
{ "type": "esp32", "macAddress": "D8BFC0800FA0" }
```

- `type`, `macAddress`: `string`, bắt buộc.
- **201:** `MicrocontrollerResponseDto`; **400:** dữ liệu không hợp lệ; **409:** xung đột.
- Service thực hiện chuẩn hóa và kiểm tra trùng Type/MAC **chưa có trong ZIP**, không thể xác minh logic cuối cùng.

### 7.2. GET `/api/microcontroller`

- **200:** danh sách `MicrocontrollerResponseDto[]` của User hiện tại (dự kiến).

### 7.3. GET `/api/microcontroller/{id}`

- **200:** một `MicrocontrollerResponseDto`; **404:** không tìm thấy hoặc không thuộc User.

### 7.4. PATCH `/api/microcontroller/{id}`

```json
{ "type": "esp32", "macAddress": "D8BFC0800FA1" }
```

- Hai trường nullable; trường không gửi giữ nguyên.
- **200:** DTO mới; **400:** sai dữ liệu; **404:** không tồn tại; **409:** xung đột.
- Controller không chứa quy tắc chặn đổi loại/MAC khi đã có Device; cần xem Service triển khai mới xác định được.

### 7.5. DELETE `/api/microcontroller/{id}`

- **204:** xóa thành công; **404:** không tìm thấy.
- `AppDbContext` thiết lập `DeleteBehavior.SetNull` cho FK `Device.MicrocontrollerId`; không thể xác minh Service có cập nhật `SyncStatus` và `Gpio` thế nào vì file Service rỗng.

### 7.6. GET `/api/microcontroller/{id}/devices`

- **200:** dự kiến danh sách `MicrocontrollerDeviceDto[]`; **404:** MCU không tồn tại/không thuộc User.

```json
[
  {
    "id": 7,
    "deviceName": "Đèn bàn",
    "gpio": 25,
    "deviceTypeId": 1,
    "currentStatus": "UNKNOWN",
    "syncStatus": "pending"
  }
]
```

---

## 8. Device API

**Xác thực:** JWT; thiết bị lọc theo User ID lấy từ JWT ở Service có xử lý đọc/xóa.

**`DeviceResponseDto` dự kiến:**

```json
{
  "id": 7,
  "deviceName": "Đèn bàn",
  "description": "Đèn học ở phòng con gái tầng 2",
  "deviceTypeId": 1,
  "deviceTypeName": "light",
  "microcontrollerId": 1,
  "microcontrollerType": "esp32",
  "macAddress": "D8BFC0800FA0",
  "gpio": 25,
  "currentStatus": "UNKNOWN",
  "statusUpdatedAt": null,
  "syncStatus": "pending",
  "createdAt": "2026-10-24T12:00:00Z"
}
```

> **Chênh lệch Service:** `DeviceService.GetAllByUserIdAsync` và `GetByIdAsync` trả **entity `Device`** kèm navigation properties, không map sang `DeviceResponseDto`. Trả entity có quan hệ hai chiều có thể phát sinh lỗi serialize vòng tham chiếu vì `Program.cs` không thấy cấu hình `ReferenceHandler`/ignore cycles. Do đó **response thực tế chưa được xác minh**. Các endpoint create/update còn bất tương thích chữ ký Service.

### 8.1. POST `/api/device`

**Body — `CreateDeviceRequestDto`:**

```json
{
  "deviceTypeId": 1,
  "microcontrollerId": null,
  "gpio": null,
  "deviceName": "Đèn bàn",
  "description": "Đèn học trên bàn ở phòng con gái tầng 2"
}
```

- `deviceTypeId`: `int >= 1`, bắt buộc về mặt giá trị.
- `microcontrollerId`: `int|null`, tùy chọn.
- `gpio`: `int|null`, nếu có `>= 0`.
- `deviceName`: `string|null`, tối đa 150 ký tự.
- `description`: `string|null`, tối đa 2000 ký tự.
- Không gửi `userId`, `currentStatus`, `syncStatus`.
- **201:** tài nguyên mới + `Location`; **400:** dữ liệu không hợp lệ; **409:** xung đột nghiệp vụ.
- **[Chưa sẵn sàng]** Controller gọi `CreateAsync(userId, request)`, Service ZIP chỉ có `CreateAsync(Device device, int userId)`.
- **Không đồng nghĩa** ESP32 đã tạo thiết bị vật lý.

### 8.2. GET `/api/device`

- **200:** danh sách Device của User. Service hiện trả entity `Device[]`, không đảm bảo `DeviceResponseDto[]`.

### 8.3. GET `/api/device/unassigned`

- **200:** thiết kế lấy danh sách Device chưa được gắn MCU.
- **[Chưa sẵn sàng]** Service ZIP thiếu `GetUnassignedAsync`.

### 8.4. GET `/api/device/{id}`

- **200:** Device thuộc User; hiện trả entity.
- **404:** `{ "message": "Không tìm thấy Device." }`.

### 8.5. PATCH `/api/device/{id}`

**Body — `UpdateDeviceRequestDto`:**

```json
{
  "deviceName": "Đèn học",
  "description": "Đèn học ở tầng 2",
  "deviceTypeId": 1
}
```

- `deviceName`: nullable; giới hạn 150; `""` được DTO chú thích dùng để xóa tên.
- `description`: nullable; giới hạn 2000; `""` được DTO chú thích dùng để xóa mô tả.
- `deviceTypeId`: `int|null`, nếu có `>= 1`.
- **Không cho thay đổi** `microcontrollerId` hoặc `gpio` tại API này theo hợp đồng DTO; dùng API Internal binding sau khi NLP xử lý phần cứng.
- **200:** tài nguyên đã sửa; **400:** sai dữ liệu; **404:** không thấy; **409:** xung đột.
- **[Chưa sẵn sàng]** Service ZIP thiếu `UpdateAsync(int, int, UpdateDeviceRequestDto)`; chỉ có bản nhận entity `Device`.

### 8.6. DELETE `/api/device/{id}`

- **204:** xóa thành công trong database; **404:** không tìm thấy; **409:** xung đột theo Controller.
- Service hiện tại thực hiện xóa bản ghi trong EF trực tiếp; không có MQTT trong API này.
- Quan hệ Schedule–Device có cascade delete trong `AppDbContext`.

### 8.7. POST `/api/device/resolve`

**Body — `DeviceResolutionRequestDto`:**

```json
{ "userId": 1, "tags": ["đèn", "phòng khách"] }
```

**501 Not Implemented:**

```json
{ "message": "Device Resolution chưa được triển khai." }
```

Controller **không tra Device**, không đối chiếu `userId` body. Comment trong source yêu cầu không tin `request.UserId` và gợi ý có thể triển khai phân giải Device trên NLP Server. **Không được gọi endpoint này như API hoạt động.**

---

## 9. Device Catalog API

### GET `/api/device/catalog`

**Xác thực:** JWT. Endpoint này dùng trực tiếp `AppDbContext` và là **đầu vào phù hợp nhất cho NLP Server cần có catalog của người dùng** (cần một cơ chế ủy quyền hợp lệ; Internal API key **không** tự cho quyền gọi catalog).

- Chỉ trả Device thuộc User trong JWT.
- Mỗi Device có định tuyến MCU/MAC/GPIO, trạng thái và các nhóm tag đồng nghĩa.
- Mỗi phần tử trong `tagGroups` là **một nhóm từ đồng nghĩa riêng**, không được làm phẳng nếu cần phân giải ngữ nghĩa chính xác.
- `tagGroups` chỉ chứa TagGroup của chính User hiện tại.

**200 OK:**

```json
{
  "deviceCount": 1,
  "devices": [
    {
      "deviceId": 7,
      "deviceName": "Đèn bàn",
      "deviceType": "light",
      "microcontrollerId": 1,
      "microcontrollerType": "esp32",
      "macAddress": "D8BFC0800FA0",
      "gpio": 25,
      "currentStatus": "ON",
      "syncStatus": "synced",
      "tagGroups": [
        ["đèn học", "đèn bàn"],
        ["phòng con gái", "phòng của con gái"],
        ["tầng 2"]
      ]
    }
  ]
}
```

- **401:** JWT không có User ID hợp lệ hoặc không xác thực.
- Các thiết bị chưa gắn phần cứng có thể có `microcontrollerId`, `microcontrollerType`, `macAddress`, `gpio` = `null`.

---

## 10. Tag / TagGroup API

**Xác thực:** JWT. Các action có trong Controller nhưng `ManageTagsService` ZIP chưa triển khai các phương thức tương ứng.

### 10.1. GET `/api/device/{deviceId}/tags`

- **200:** dự kiến lấy các tag/nhóm tag gắn với Device.
- **404:** không tìm thấy Device.
- **[Chưa sẵn sàng]** Service thiếu `GetDeviceTagsAsync`; cấu trúc response cuối cùng chưa xác định đầy đủ. DTO có `TagGroupResponseDto` với `{ "tagGroupId": 10, "tags": ["đèn bàn", "đèn học"] }`.

### 10.2. PUT `/api/device/{deviceId}/tags`

**Body — `CreateTagRequestDto`:**

```json
{ "tags": ["đèn học", "phòng con gái", "tầng 2"] }
```

- `tags`: bắt buộc, list `string`, tối đa **20 phần tử** (`[MaxLength(20)]` trên list).
- `tags: []` theo comment DTO nghĩa là bỏ liên kết TagGroup hiện tại của Device, **không xóa TagGroup trong DB**.
- `deviceId` lấy từ route, User ID lấy từ JWT.
- **200:** kết quả thay thế (chưa rõ schema chính xác); **400**, **404**, **409** theo Controller.
- **[Chưa sẵn sàng]** Service thiếu `ReplaceDeviceTagsAsync`.
- Endpoint này **không gửi MQTT**; TagGroup phục vụ NLP/Device Resolution.

### 10.3. GET `/api/taggroup`

- **200:** dự kiến danh sách TagGroup thuộc User.
- **[Chưa sẵn sàng]** Service thiếu `GetAllGroupsAsync`.
- Không có endpoint POST/PATCH/DELETE TagGroup trong Controller được gửi.

**Quy tắc database đáng chú ý:** Tag không được trùng `Value` trong cùng `TagGroup`; liên kết `(DeviceId, TagGroupId)` là duy nhất; giới hạn `Tag.Value` 150 ký tự.

---

## 11. Schedule API

**Route gốc:** `/api/device/{deviceId}/schedule`  
**Xác thực:** JWT  
**Quan hệ:** tối đa một Schedule cho một Device (`1–0..1`).  
**Trạng thái:** Controller và DTO đã có, `ScheduleServices.cs` **rỗng trong ZIP**.

### 11.1. GET `/api/device/{deviceId}/schedule`

**200 — `ScheduleResponseDto` dự kiến:**

```json
{
  "id": 12,
  "deviceId": 7,
  "action": "off",
  "scheduledDelay": 300,
  "duration": null,
  "scheduledStartAt": null,
  "scheduledEndAt": null,
  "syncStatus": "pending",
  "commandId": null,
  "createdAt": "2026-10-24T12:00:00Z",
  "updatedAt": "2026-10-24T12:00:00Z",
  "acknowledgedAt": null
}
```

- **404:** `{ "message": "Không tìm thấy Schedule." }`.
- **Lưu ý tên trường:** DTO gọi `scheduledDelay`, trong Model `Schedule` cột tương ứng là `Delay`; cần mapper trong Service, hiện chưa có.

### 11.2. PUT `/api/device/{deviceId}/schedule`

Tạo mới hoặc cập nhật lịch của Device (upsert).

**Body — `UpsertScheduleRequestDto`:**

```json
{
  "action": "off",
  "scheduledDelay": 300,
  "duration": null,
  "scheduledStartAt": null,
  "scheduledEndAt": null
}
```

- `action`: string, bắt buộc; Model mô tả `on` hoặc `off` (logic Service xác minh cụ thể chưa có).
- `scheduledDelay`: `int|null`, **giây**, nếu có `>= 0`.
- `duration`: `int|null`, **giây**, nếu có `>= 1`.
- `scheduledStartAt`: `long|null`, **Unix timestamp giây**, nếu có `>= 1`.
- `scheduledEndAt`: `long|null`, **Unix timestamp giây**, nếu có `>= 1`.
- Không gửi `userId`, `deviceId` trong body; không gửi `commandId`/`syncStatus`.
- **200:** `ScheduleResponseDto` (dự kiến), mới lưu cấu hình vào DB.
- **400:** sai dữ liệu; **404:** không tìm thấy Device; **409:** xung đột.
- Không có đủ code Service để xác định **những tổ hợp thời gian nào được chấp nhận** hoặc xử lý xung đột cụ thể.

### 11.3. DELETE `/api/device/{deviceId}/schedule`

Đề nghị hủy lịch.

- **204 No Content:** theo comment Controller, với lịch `pending` chưa được gửi MQTT, lịch được xóa khỏi DB.
- **200 OK:** với lịch đã gửi, trả Schedule dự kiến có `syncStatus: "cancel_pending"`, chưa xóa ngay.
- **404:** không tìm thấy; **409:** xung đột.
- Chi tiết điều kiện chuyển trạng thái phụ thuộc Service chưa được cung cấp.

**Các trạng thái Schedule ghi trong Model:**

- `pending`: đã lưu/chờ đồng bộ.
- `acknowledged`: ESP đã xác nhận tiếp nhận lịch (không có nghĩa lịch đã chạy xong).
- `cancel_pending`: đã đề nghị hủy, đang chờ xác nhận.
- `unknown`: không xác định trạng thái thực tế.
- `failed`: kết quả thao tác thất bại.

---

## 12. Internal Sync API (dành cho NLP Server)

**Xác thực duy nhất trong Controller:** header `X-Internal-Key`. Không gọi trực tiếp từ trình duyệt.

### 12.1. PATCH `/api/internal/devices/{deviceId}/binding`

**Ý nghĩa:** Chốt liên kết MCU/GPIO mới trong DB **sau khi** NLP Server hoàn tất các lệnh vật lý cần thiết (nếu có). Registry không gửi MQTT tại đây.

**Body — `UpdateDeviceBindingRequestDto`:**

```json
{
  "userId": 1,
  "microcontrollerId": 2,
  "gpio": 26
}
```

Để bỏ gắn MCU:

```json
{
  "userId": 1,
  "microcontrollerId": null,
  "gpio": null
}
```

**Ràng buộc:**

- `userId >= 1`.
- `microcontrollerId` và `gpio` phải **cùng null hoặc cùng khác null**.
- `gpio >= 0` nếu được chỉ định.
- Device và MCU đích đều phải thuộc `userId`.
- Không cho hai Device khác nhau dùng cùng `(microcontrollerId, gpio)`.
- MCU loại `esp32` không được có quá **6 Device** sau thao tác gắn.

**200 OK:**

```json
{
  "deviceId": 7,
  "oldMicrocontrollerId": 1,
  "oldGpio": 25,
  "microcontrollerId": 2,
  "gpio": 26,
  "syncStatus": "synced"
}
```

Sau thành công, `Device.SyncStatus` là `synced` nếu đã gắn, `unassigned` nếu tháo; `CurrentStatus` được đặt `UNKNOWN` và `StatusUpdatedAt` đặt null. Nếu đổi MCU hoặc GPIO và đang có Schedule, `Schedule.SyncStatus` chuyển `unknown`.

**Lỗi:** `401` key sai/thiếu; `400` cặp MCU/GPIO sai, GPIO âm hoặc MCU đích không hợp lệ; `404` Device không tồn tại/không thuộc User; `409` GPIO trùng, ESP32 đã đủ 6 Device hoặc unique DB violation.

### 12.2. PUT `/api/internal/devices/{deviceId}/status`

**Ý nghĩa:** NLP báo trạng thái đồng bộ/trạng thái vật lý thực tế sau khi xác minh kết quả từ firmware.

**Body — `ReportDeviceStatusRequestDto`:**

```json
{
  "userId": 1,
  "microcontrollerId": 2,
  "gpio": 26,
  "syncStatus": "synced",
  "currentStatus": "ON"
}
```

- `syncStatus` bắt buộc, chỉ `synced`, `out_of_sync` hoặc `error` (Controller chuẩn hóa chữ thường).
- `currentStatus`: null hoặc một trong `ON`, `OFF`, `UNKNOWN` (chuẩn hóa chữ hoa).
- `userId`, `microcontrollerId >= 1`; `gpio >= 0`.
- Bắt buộc MCU/GPIO request **khớp chính xác** với Device hiện tại nhằm tránh ACK cũ cập nhật nhầm thiết bị.
- Nếu `currentStatus` là null, **không đổi** `CurrentStatus` hay thời điểm cập nhật.

**200 OK:**

```json
{
  "deviceId": 7,
  "syncStatus": "synced",
  "currentStatus": "ON",
  "statusUpdatedAt": "2026-10-24T12:05:00Z"
}
```

**Lỗi:** `401` sai key; `400` trạng thái sai; `404` không tìm thấy Device; `409` MCU/GPIO không khớp.

### 12.3. POST `/api/internal/microcontrollers/{mcuId}/refresh`

**Ý nghĩa:** Đối chiếu snapshot `REFRESH_DEVICE_RESPONSE` từ firmware với những Device đã đăng ký trong Registry. API này không tạo Device tự động.

**Body — `RefreshDevicesRequestDto`:**

```json
{
  "userId": 1,
  "hardwareId": "D8BFC0800FA0",
  "deviceCount": 2,
  "gpios": [25, 26],
  "deviceTypes": ["light", "fan"],
  "deviceNames": ["Đèn bàn", "Quạt trần"],
  "deviceStatus": ["ON", "OFF"]
}
```

- `hardwareId`: MAC/định danh so khớp với MCU sau khi bỏ `:` và `-`, so sánh không phân biệt hoa-thường.
- `deviceCount >= 0`; **cả bốn mảng** `gpios`, `deviceTypes`, `deviceNames`, `deviceStatus` phải có cùng số phần tử `deviceCount`.
- GPIO không trùng nhau, không âm.
- `deviceTypes` không có phần tử rỗng/trắng; `deviceStatus` chỉ chấp nhận `ON`/`OFF` (không chấp nhận `UNKNOWN` ở refresh).
- Với MCU `esp32`, `deviceCount <= 6`.
- Mỗi phần tử cùng index mô tả một thiết bị trên MCU.
- Device của Registry có GPIO khớp, loại và tên khớp (so sánh không phân biệt hoa-thường, bỏ khoảng trắng ngoài) được gắn `synced` và cập nhật trạng thái thực tế.
- Device có GPIO thiếu/sai metadata được đưa vào `mismatchedDeviceIds`; **nếu thiếu GPIO mà đang `pending` thì giữ nguyên `pending`**; nếu type/name sai thì đặt `out_of_sync`.
- GPIO xuất hiện trong firmware nhưng chưa được Registry đăng ký được trả ở `unknownGpios`, **không** tạo Device mới.
- MCU được cập nhật `connectionStatus = "online"`, `lastSeenAt = now`.
- **Không xác nhận Schedule** bằng snapshot này; firmware chưa cung cấp trạng thái Schedule trong response tương ứng.

**200 OK:**

```json
{
  "microcontrollerId": 1,
  "matchedDeviceIds": [7, 8],
  "mismatchedDeviceIds": [],
  "unknownGpios": [27],
  "refreshedAt": "2026-10-24T12:10:00Z"
}
```

**Lỗi:** `401` sai key; `400` mảng/giá trị sai hoặc >6 Device trên ESP32; `404` MCU không thuộc User; `409` `hardwareId` không khớp.

### 12.4. POST `/api/internal/schedules/{deviceId}/command`

**Ý nghĩa:** Đăng ký `commandId` trong Registry **trước khi NLP Server publish MQTT**, để đối chiếu ACK.

```json
{ "userId": 1, "commandId": "schedule-command-001" }
```

- `userId >= 1`.
- `commandId`: bắt buộc, không được trống theo validation mặc định (logic bổ sung chưa có).
- Kiểm tra Device thuộc User, sau đó gọi `ScheduleServices.RegisterCommandAsync`.
- **204:** ghi nhận thành công; **400:** dữ liệu sai; **401:** key sai; **404:** Device/Schedule không tồn tại; **409:** xung đột.
- **[Chưa sẵn sàng]** Service xử lý chưa có trong ZIP.

### 12.5. POST `/api/internal/schedules/{deviceId}/ack`

**Ý nghĩa:** Áp dụng kết quả xác nhận MQTT thực tế sau khi NLP xác thực response từ firmware.

```json
{
  "userId": 1,
  "commandId": "schedule-command-001",
  "accepted": true
}
```

- `userId >= 1`, `commandId` bắt buộc.
- `accepted` **phải có giá trị Boolean** (`true` hoặc `false`), không được null/missing.
- Controller kiểm tra Device thuộc User; comment yêu cầu `commandId` khớp lệnh đang chờ.
- **204:** xử lý ACK thành công; **400:** thiếu `accepted`; **401:** key sai; **404:** Device/Schedule không thấy; **409:** trạng thái/commandId xung đột.
- **[Chưa sẵn sàng]** Service xử lý ACK chưa có trong ZIP. Chưa thể khẳng định chính xác thao tác ACK sẽ xóa hay giữ Schedule ở từng nhánh.

---

## 13. Ví dụ tích hợp Frontend và NLP Server

### 13.1. Login và lấy JWT

```bash
curl -X POST "https://<YOUR-HOST>/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"quan","password":"ExamplePass123"}'
```

Lấy `accessToken` từ response, dùng cho các API Web bên dưới.

### 13.2. Frontend tải catalog thiết bị

```bash
curl "https://<YOUR-HOST>/api/device/catalog" \
  -H "Authorization: Bearer <accessToken>"
```

### 13.3. NLP Server báo trạng thái thực tế

```bash
curl -X PUT "https://<YOUR-HOST>/api/internal/devices/7/status" \
  -H "X-Internal-Key: <InternalApiKey>" \
  -H "Content-Type: application/json" \
  -d '{"userId":1,"microcontrollerId":2,"gpio":26,"syncStatus":"synced","currentStatus":"ON"}'
```

### 13.4. Quy trình tạo/gắn Device (trạng thái thiết kế)

1. FE đăng nhập, nhận JWT.
2. FE `POST /api/device` để tạo Device logic; Registry lưu DB.
3. Khi cần gắn MCU/GPIO, NLP Server dùng thông tin Registry và gửi lệnh MQTT CREATE tới MCU thích hợp.
4. Chỉ sau khi xác minh thao tác vật lý thành công, NLP Server `PATCH /api/internal/devices/{deviceId}/binding`.
5. Khi có báo cáo trạng thái vật lý, NLP Server `PUT /api/internal/devices/{deviceId}/status`.
6. FE `GET /api/device/catalog` (hoặc API chi tiết sau khi hoàn thiện Service) để đọc dữ liệu mới.

**Quan trọng:** quy trình trên là sự phối hợp nhiều component; Registry **không thực hiện trực tiếp bước MQTT**.

### 13.5. Quy trình tạo và thực thi lịch (trạng thái thiết kế)

1. FE `PUT /api/device/{deviceId}/schedule` để lưu lịch, `syncStatus` dự kiến `pending`.
2. NLP Server xác định MCU/GPIO đích, chuẩn bị `commandId` duy nhất.
3. NLP Server `POST /api/internal/schedules/{deviceId}/command` để ghi `commandId` trước MQTT.
4. NLP Server publish MQTT chứa lệnh/lịch tới ESP32.
5. NLP Server xác thực phản hồi đúng `commandId` và báo `POST /api/internal/schedules/{deviceId}/ack` với `accepted: true/false`.
6. FE đọc `GET /api/device/{deviceId}/schedule` để xem trạng thái mới.

Luồng ACK trong đoạn trên **chưa chạy được với phần Service trống của ZIP**. `acknowledged` chỉ xác nhận ESP tiếp nhận lịch, không có nghĩa lịch đã kích hoạt hoặc hoàn tất.

---

## 14. Các quy tắc dữ liệu và trạng thái đáng nhớ

### 14.1. Device

- `currentStatus`: `ON`, `OFF`, `UNKNOWN` là các giá trị được kiểm tra tại Internal report; mặc định Model là `UNKNOWN`.
- `syncStatus`: Model mô tả `unassigned`, `pending`, `synced`, `out_of_sync`, `error`.
- `currentStatus` và `syncStatus` có **ý nghĩa khác nhau**: trạng thái ON/OFF vật lý và trạng thái đồng bộ cấu hình.
- `microcontrollerId` và `gpio` có thể null khi chưa liên kết.
- Chỉ một Device trên mỗi cặp `(MicrocontrollerId, Gpio)` (unique index).

### 14.2. Microcontroller

- `connectionStatus`: `unknown`, `online`, `offline` theo Model; Internal refresh đặt `online`.
- `lastSeenAt`: thời điểm thấy MCU lần cuối.
- DB unique index hiện tại là **`(Type, MacAddress)`**, không phải `MacAddress` toàn hệ thống.

### 14.3. Schedule

- Thời gian trì hoãn/duy trì là **giây**; `scheduledStartAt`/`scheduledEndAt` là Unix UTC **giây**.
- `acknowledgedAt`: thời điểm nhận ACK, không phải thời điểm lịch chạy.
- Khi đổi binding phần cứng, Schedule cũ được đặt `unknown`, **không được tự chuyển logic thực thi lịch sang MCU mới**.

### 14.4. Tags

- `TagGroup` thuộc User; `Tag` thuộc TagGroup; một Device có thể liên kết nhiều TagGroup.
- Các phần tử trong cùng TagGroup có ý nghĩa đồng nghĩa; giữ nguyên nhóm khi cung cấp cho NLP.

---

## 15. Chênh lệch và việc cần hoàn thiện trước khi tích hợp

### 15.1. Lỗi không khớp code/khả năng build

1. **`MicrocontrollerService.cs` rỗng**, trong khi `Program.cs` đăng ký DI và Controller gọi 6 phương thức CRUD/lookup của class này.
2. **`ScheduleServices.cs` rỗng**, trong khi `Program.cs`, `ScheduleController` và `InternalSyncController` dùng nhiều method của class.
3. **`ManageTagsService` chỉ có các stub `CreateTag`, `UpdateAlias` trả `null`**; Controller đang gọi `GetAllGroupsAsync`, `GetDeviceTagsAsync`, `ReplaceDeviceTagsAsync` — không thấy trong Service.
4. **`DeviceController.Create` gọi `CreateAsync(userId, request)`**, nhưng Service chỉ có `CreateAsync(Device, userId)`; **`Update` gọi DTO**, Service chỉ có overload nhận entity; `GetUnassignedAsync` thiếu.
5. **`DeviceTypeController.Create/Update` gọi Service bằng DTO**, nhưng Service nhận entity `DeviceType` có `AllowedStatuses` kiểu `string`; DTO gửi `List<string>`.
6. `DeviceResponseDto` và `DeviceTypeResponseDto` có thiết kế response cụ thể nhưng phần Service hiện được gửi **chưa sử dụng mapper DTO**; `DeviceService` trả Entity liên kết hai chiều.
7. `Migrations_6(3).zip` **không có file migration**; chưa thể xác nhận schema đã được apply thực tế.

> **Hệ quả:** không nên import tài liệu này vào Postman rồi giả định tất cả 39 endpoint chạy được ngay. Cần chỉnh code cho nhất quán, build, chạy migrations, test từng route và cập nhật tài liệu theo kết quả.

### 15.2. Bảo mật và ranh giới quyền truy cập

1. User API thiếu ownership/role kiểm tra theo `{id}` — đã đăng nhập có thể thao tác trên User khác.
2. DeviceType CRUD áp dụng cho mọi JWT, không có role admin.
3. Internal API key là secret cho trusted backend, không được lộ cho FE/mobile/browser.
4. Internal API nhận `userId` từ body (tin cậy vì đã qua internal key) nhưng phải bảo vệ nghiêm ngặt key và đường mạng; cân nhắc thêm audit/rotation/key-per-service khi triển khai thật.
5. `GET /api/device/catalog` **chỉ chấp nhận JWT**, không nhận riêng `X-Internal-Key`. Nếu NLP Server cần catalog, phải thiết kế cơ chế gọi JWT theo User hoặc endpoint service-to-service có ủy quyền phù hợp.
6. `POST /api/device/resolve` đang trả `501`, không được dùng User ID do client tự cung cấp để phân giải thiết bị trước khi thêm kiểm tra quyền.

### 15.3. Các điểm cần chuẩn hóa hợp đồng API

1. Xác định response DTO cho `GET /api/device`, `/api/device/{id}`, các API DeviceType thay vì trả entity.
2. Thêm tài liệu OpenAPI/Swagger annotation và `Bearer`/Internal header security definitions nếu muốn test thuận tiện bằng Swagger UI.
3. Chốt quy tắc validate `action`, các tổ hợp trường thời gian Schedule và ngữ nghĩa Cancel/ACK trong `ScheduleServices`.
4. Chốt chính sách xóa MCU/Device về MQTT, GPIO, lịch và trạng thái sync để không làm Registry lệch firmware.
5. Kiểm thử đồng thời hai request gắn vào cùng GPIO, xử lý conflict DB và ACK đến trễ.
6. Không trả thông tin nhạy cảm trong response Entity; xử lý vòng tham chiếu JSON đúng cách.

---

## 16. Nguồn mã đã đối chiếu

Tài liệu này được biên soạn từ toàn bộ các tệp người dùng đính kèm:

- `Program(1).cs`: DI, EF Core, JWT, Internal key, Swagger, middleware.
- `Controllers_1(3).zip`: định nghĩa route, HTTP method, kết quả trả và kiểm tra lỗi.
- `DTOs_2(3).zip`: hợp đồng dữ liệu, validation và response DTO dự kiến.
- `Services_3(3).zip`: logic thực tế sẵn có và các stub/Service trống.
- `Models_5(3).zip`, `Data_4(3).zip`: Entity, quan hệ, trạng thái và ràng buộc dữ liệu.
- `Migrations_6(3).zip`: không chứa file migration.

**Phạm vi xác minh:** kiểm tra mã nguồn tĩnh, chưa chạy `dotnet build`, chưa kết nối database, chưa chạy request thực tế. Các JSON có giá trị mẫu là **ví dụ mô phỏng** nhằm giải thích hợp đồng API.
