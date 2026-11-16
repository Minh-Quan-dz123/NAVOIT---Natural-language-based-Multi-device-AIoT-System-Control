
import { apiRequest } from "./apiClient";
import { getAccessToken } from "./userApi";

export const OUTPUT_GPIOS = [
    13, 14, 16, 17, 18, 19, 21,
    22, 23, 25, 26, 27, 32, 33
];

// 1. Lấy Device chưa gắn MCU từ Registry
export async function getUnassignedDevices() {
    return await apiRequest("/api/device/unassigned");
}

// 2. Gửi yêu cầu liên kết/tháo tới NLP Server
async function sendBindingRequest(deviceId, method, body = null) {
    const baseUrl = import.meta.env.VITE_NLP_API_URL;

    if (!baseUrl) { throw new Error("Thiếu VITE_NLP_API_URL trong .env.");}

    const token = getAccessToken();

    if (!token) throw new Error("Bạn chưa đăng nhập.");

    const url =`${baseUrl.replace(/\/$/, "")}/api/devices/${deviceId}/binding`;

    const options = {
        method,
        headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
        },
    };

    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    let response;

    try 
    {
        response = await fetch(url, options);
    } 
    catch 
    {
        const error = new Error(
            "Mất kết nối NLP Server. Chưa rõ yêu cầu đã được " +
            "ESP32 thực hiện hay chưa. Cần kiểm tra trước khi thử lại."
        );

        error.state = "unknown";
        throw error;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const detail = data?.detail;

        const message =
            detail?.message ||
            (typeof detail === "string" ? detail : null) ||
            data?.message ||
            `Yêu cầu thất bại. HTTP ${response.status}`;

        const error = new Error(message);

        error.status = response.status;
        error.state = detail?.state || "failed";

        throw error;
    }

    return data;
}

// 3. Liên kết Device vào MCU/GPIO
export async function bindDevice(deviceId, mcuId, gpio) {
    return await sendBindingRequest(
        deviceId,
        "POST",
        {
            microcontrollerId: mcuId,
            gpio: gpio,
        }
    );
}

// 4. Tháo liên kết, không xóa Device logic
export async function unbindDevice(deviceId) {
    return await sendBindingRequest(deviceId, "DELETE");
}
