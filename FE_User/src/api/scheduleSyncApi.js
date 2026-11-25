import { getAccessToken } from "./userApi";

export async function syncSchedules(apply = false) 
{
    const baseUrl = import.meta.env.VITE_NLP_API_URL;
    const token = getAccessToken();

    if (!baseUrl)  throw new Error("Chưa cấu hình VITE_NLP_API_URL.");
    if (!token) throw new Error("Bạn chưa đăng nhập.");

    let response;

    try 
    {
        response = await fetch(
            `${baseUrl.replace(/\/$/, "")}/api/devices/schedules/sync`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ apply }),
            }
        );
    }
    catch 
    {
        const error = new Error(
            apply
                ? "Mất kết nối NLP Server. Kết quả khôi phục " +
                  "Schedule chưa xác định. Không thử lại ngay."
                : "Không kết nối được NLP Server."
        );

        error.state = apply ? "unknown" : "failed";
        throw error;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) 
    {
        const detail = data?.detail;

        throw new Error(
            detail?.message ||
            (typeof detail === "string" ? detail : null) ||
            `Đồng bộ Schedule thất bại. HTTP ${response.status}`
        );
    }

    return data;
}
