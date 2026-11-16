import { apiRequest } from "./apiClient";
import { getAccessToken } from "./userApi";

export async function createDeviceSchedule(deviceId, schedule) {
    const baseUrl = import.meta.env.VITE_NLP_API_URL;
    if (!baseUrl) throw new Error("Thiếu VITE_NLP_API_URL.");

    const token = getAccessToken();
    if (!token) throw new Error("Bạn chưa đăng nhập.");

    let response;

    try 
    {
        response = await fetch(
            `${baseUrl.replace(/\/$/, "")}/api/devices/${deviceId}/schedule`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(schedule),
            }
        );
    } 
    catch 
    {
        const error = new Error("Mất kết nối NLP Server. Kết quả tạo lịch chưa xác định." );
        error.state = "unknown";
        throw error;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) 
    {
        const detail = data?.detail;

        const message =
            detail?.message ||
            (typeof detail === "string" ? detail : null) ||
            (Array.isArray(detail)
                ? detail.map(item => item.msg).join("; ")
                : null) ||
            `Tạo lịch thất bại. HTTP ${response.status}`;

        const error = new Error(message);
        error.state = detail?.state || "failed";
        throw error;
    }

    if (data?.state !== "success") 
    {
        const error = new Error("Chưa xác nhận lưu Schedule.");
        error.state = "unknown";
        throw error;
    }

    return data;
}


// 1. Xem Schedule qua Registry
export async function getDeviceSchedule(deviceId) 
{
    try 
    {
        return await apiRequest(`/api/device/${deviceId}/schedule`);
    } 
    catch (err) 
    {
        // 404: Device chưa có Schedule.
        if (err.status === 404) return null;
        throw err;
    }
}


// 2. Hủy Schedule qua NLP Server
export async function cancelDeviceSchedule(deviceId) 
{
    const baseUrl = import.meta.env.VITE_NLP_API_URL;
    if (!baseUrl) throw new Error("Thiếu VITE_NLP_API_URL.");

    const token = getAccessToken();
    if (!token) throw new Error("Bạn chưa đăng nhập.");

    let response;

    try 
    {
        response = await fetch(
            `${baseUrl.replace(/\/$/, "")}/api/devices/${deviceId}/schedule`,
            {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: "application/json",
                },
            }
        );
    } 
    catch 
    {
        const error = new Error(
            "Mất kết nối NLP Server. " +
            "Chưa rõ ESP32 đã tiếp nhận lệnh hủy hay chưa."
        );
        error.state = "unknown";
        throw error;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) 
    {
        const detail = data?.detail;

        const error = new Error(
            detail?.message ||
            (typeof detail === "string" ? detail : null) ||
            `Hủy lịch thất bại. HTTP ${response.status}`
        );

        error.state = detail?.state || "failed";
        throw error;
    }

    if (data?.state !== "success") 
    {
        const error = new Error("Chưa xác nhận được kết quả hủy lịch.");
        error.state = "unknown";
        throw error;
    }

    return data;
}
