import { getAccessToken } from "./userApi";

export async function controlDevice(deviceId, action) {
    const baseUrl = import.meta.env.VITE_NLP_API_URL;

    if (!baseUrl) throw new Error("Chưa cấu hình VITE_NLP_API_URL.");

    const token = getAccessToken();

    if (!token)  throw new Error("Bạn chưa đăng nhập.");

    let response;

    try {
        response = await fetch(
            `${baseUrl.replace(/\/$/, "")}/api/devices/${deviceId}/control`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ action }),
            }
        );
    } 
    catch 
    {
        const error = new Error(
            "Mất kết nối NLP Server. " +
            "Chưa rõ MCU đã thực hiện lệnh hay chưa."
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
            `Điều khiển thất bại. HTTP ${response.status}`
        );

        error.state = detail?.state || "failed";
        throw error;
    }

    if (data?.state !== "success") {
        const error = new Error("NLP Server chưa xác nhận kết quả điều khiển.");

        error.state = "unknown";
        throw error;
    }

    return data;
}
