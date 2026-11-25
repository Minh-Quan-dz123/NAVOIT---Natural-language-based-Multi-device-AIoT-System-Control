
import { getAccessToken } from "./userApi";

let pendingRefresh = null;
let pendingToken = null;

// 1. GỌI NLP SERVER
async function sendRefreshRequest() 
{
    const baseUrl = import.meta.env.VITE_NLP_API_URL;
    if (!baseUrl) throw new Error("Chưa cấu hình VITE_NLP_API_URL.");

    const token = getAccessToken();
    if (!token) throw new Error("Bạn chưa đăng nhập.");

    let response;

    try 
    {
        response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/microcontrollers/refresh`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: "application/json",
                },
            }
        );
    }
    catch 
    {
        throw new Error("Không kết nối được NLP Server.");
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) 
    {
        const detail = data?.detail;

        throw new Error(
            detail?.message ||
            (typeof detail === "string" ? detail : null) ||
            `Đồng bộ thất bại. HTTP ${response.status}`
        );
    }

    return data;
}


// 2. ĐỒNG BỘ TRẠNG THÁI
export function refreshAllDeviceStatuses() 
{
    const token = getAccessToken();

    if (pendingRefresh !== null && pendingToken === token) {return pendingRefresh;}

    pendingToken = token;

    const request = sendRefreshRequest().finally(() => {
        if (pendingRefresh === request) 
        {
            pendingRefresh = null;
            pendingToken = null;
        }
    });

    pendingRefresh = request;
    return request;
}


// 3. TẠO THÔNG BÁO KẾT QUẢ
export function formatRefreshResult(result) 
{
    if (result.state === "empty") return "Bạn chưa có MCU để đồng bộ.";

    let prefix;

    if (result.state === "success") prefix = "Đã đồng bộ";
    else if (result.state === "failed") prefix = "Đồng bộ thất bại";
    else prefix = "Đồng bộ chưa hoàn tất";

    let message =`${prefix}: ${result.successCount}/${result.totalMcus} MCU thành công.`;

    const mismatched = result.results.filter((item) =>
            item.mismatchedDeviceIds.length > 0 ||
            item.unknownGpios.length > 0
    );

    if (mismatched.length > 0) 
    {
        message += ` Có ${mismatched.length} MCU có dữ liệu không khớp Registry.`;
    }

    const failed = result.results.filter((item) => item.state !== "success" );

    if (failed.length > 0) 
    {
        const errors = failed.map((item) => `MCU #${item.mcuId}: ${item.message}`);
        message += " " + errors.join(" | ");
    }

    return message;
}
