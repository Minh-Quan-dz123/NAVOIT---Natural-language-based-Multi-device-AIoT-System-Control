import { getAccessToken } from "./userApi";


export async function executeNaturalCommand(text) {
    const baseUrl = import.meta.env.VITE_NLP_API_URL;

    if (!baseUrl) throw new Error("Chưa cấu hình VITE_NLP_API_URL.");

    const token = getAccessToken();

    if (!token) throw new Error("Bạn chưa đăng nhập.");

    let response;

    try 
    {
        response = await fetch(
            `${baseUrl.replace(/\/$/, "")}/api/commands/natural/execute`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ text }),
            }
        );
    } 
    catch 
    {
        const error = new Error("Mất kết nối NLP Server. Kết quả điều khiển chưa xác định.");
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
            `Yêu cầu thất bại. HTTP ${response.status}`
        );

        error.state = detail?.state || "failed";
        error.candidates = detail?.candidates || [];

        throw error;
    }

    return data;
}
