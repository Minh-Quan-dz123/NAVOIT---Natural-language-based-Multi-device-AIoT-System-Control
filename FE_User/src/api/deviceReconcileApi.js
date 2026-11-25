import { getAccessToken } from "./userApi";


// 1. GỬI YÊU CẦU ĐỒNG BỘ CẤU HÌNH
export async function reconcileAllDevices() 
{
    const baseUrl = import.meta.env.VITE_NLP_API_URL;
    if (!baseUrl) throw new Error("Chưa cấu hình VITE_NLP_API_URL.");

    const token = getAccessToken();
    if (!token) throw new Error("Bạn chưa đăng nhập.");

    let response;

    try {
        response = await fetch(
            `${baseUrl.replace(/\/$/, "")}/api/microcontrollers/reconcile`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: "application/json",
                },
            }
        );
    }
    catch {
        throw new Error("Không kết nối được NLP Server.");
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) 
    {
        const detail = data?.detail;

        throw new Error(
            detail?.message ||
            (typeof detail === "string" ? detail : null) ||
            `Đồng bộ cấu hình thất bại. HTTP ${response.status}`
        );
    }

    return data;
}


// 2. TẠO THÔNG BÁO KẾT QUẢ
export function formatReconcileResult(result)
{
    if (result.state === "empty") {return "Bạn chưa có MCU cần đồng bộ.";}

    const total = result.totalMcus;
    const success = result.successCount;
    const partial = result.partialCount;
    const failed = result.failedCount;

    let message = `Đồng bộ hoàn tất: ${success}/${total} MCU thành công.`;

    if (partial > 0) {
        message += ` ${partial} MCU còn sai lệch.`;
    }

    if (failed > 0) {
        message += ` ${failed} MCU thất bại hoặc chưa rõ kết quả.`;
    }

    return message;
}
