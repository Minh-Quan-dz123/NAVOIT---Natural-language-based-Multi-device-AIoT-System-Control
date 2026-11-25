
import { apiRequest } from "./apiClient";

const BASE_URL = "/api/device";

// Lấy tất cả Device thuộc tài khoản đang đăng nhập.
// GET /api/device
export async function getMyDevices() {
    return await apiRequest(BASE_URL);
}

// Lấy chi tiết một Device.
// GET /api/device/{id}
export async function getMyDeviceById(id) {
    return await apiRequest(`${BASE_URL}/${id}`);
}

// Lấy các Device chưa gắn MCU.
// GET /api/device/unassigned
export async function getUnassignedDevices() {
    return await apiRequest(`${BASE_URL}/unassigned`);
}

// Tạo Device logic, chưa liên kết phần cứng.
// UserId được Backend lấy từ JWT.
// POST /api/device/
export async function createDevice(deviceTypeId, deviceName, description) {
    return await apiRequest(BASE_URL, "POST", {
        deviceTypeId,
        deviceName,
        description,
        microcontrollerId: null,
        gpio: null,
    });
}

// Sửa thông tin Device.
// data là object gồm các trường cần cập nhật.
// PATCH /api/device/{id}
export async function updateDevice(id, data) {
    return await apiRequest(`${BASE_URL}/${id}`, "PATCH", data);
}

// Xóa Device.
// Backend sẽ từ chối nếu còn liên kết MCU hoặc Schedule.
// DELETE /api/device/{id}
export async function deleteDevice(id) {
    return await apiRequest(`${BASE_URL}/${id}`, "DELETE");
}
