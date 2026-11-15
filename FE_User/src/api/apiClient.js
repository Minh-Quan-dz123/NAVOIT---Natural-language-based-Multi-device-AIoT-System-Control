import { getAccessToken } from "./userApi";

// Hàm chung gửi request tới Backend.
// url: /api/...
// method: GET, POST, PATCH, PUT, DELETE
// body: dữ liệu JSON cần gửi (nếu có)

export async function apiRequest(url, method = "GET", body = null) 
{
    const token = getAccessToken();

    if (!token) 
    {
        const error = new Error("Bạn chưa đăng nhập.");
        error.status = 401;
        throw error;
    }

    const headers = {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
    };

    const options = {
        method,
        headers,
    };

    if (body !== null) 
    {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    let response;

    try {
        response = await fetch(url, options);
    } 
    catch {
        throw new Error("Không thể kết nối tới Backend.");
    }

    // Hỗ trợ JSON và response rỗng (204).
    const responseText = await response.text();

    let data = null;

    if (responseText) 
    {
        try 
        {
            data = JSON.parse(responseText);
        } 
        catch 
        {
            data = null;
        }
    }

    if (!response.ok) 
    {
        let message =
            data?.message ||
            data?.title ||
            `Yêu cầu thất bại. HTTP ${response.status}`;

        if (data?.errors) 
        {
            const errors = Object.values(data.errors).flat();

            if (errors.length > 0) {  message = errors.join(" "); }
        }

        const error = new Error(message);
        error.status = response.status;

        throw error;
    }

    return data;
}
