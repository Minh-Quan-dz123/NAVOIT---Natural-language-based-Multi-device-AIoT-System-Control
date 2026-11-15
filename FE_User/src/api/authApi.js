
const API_URL = "/api/auth";

//1. Hàm gửi dữ liệu JSON lên Backend
async function postJson(url, data) 
{
    const response = await fetch(url, 
    {
        method: "POST",
        headers: 
        {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await response.json().catch(() => null);

    if (!response.ok) 
    {
        // ASP.NET Core có thể trả lỗi validation
        // trong object "errors".
        let message = result?.message;

        if (!message && result?.errors) 
        {
            const errorLists = Object.values(result.errors);
            message = errorLists.flat()[0];
        }

        throw new Error(message || `Lỗi HTTP ${response.status}`);
    }

    return result;
}

// 2. POST /api/auth/register
export async function registerUser(data) 
{
    return await postJson(`${API_URL}/register`, data);
}

// 3. POST /api/auth/login
export async function loginUser(data) 
{
    return await postJson(`${API_URL}/login`, data);
}


