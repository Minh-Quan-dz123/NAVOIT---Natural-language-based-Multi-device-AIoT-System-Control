// xử lý ba chức năng xem thông tin, cập nhật tài khoản và đổi mật khẩu.

const BASE_URL = "/api/user/me";
const TOKEN_KEY = "accessToken";

// Quản lý JWT trong sessionStorage
export function getAccessToken() {return sessionStorage.getItem(TOKEN_KEY);}

export function saveAccessToken(token) {sessionStorage.setItem(TOKEN_KEY, token);}

export function removeAccessToken() {sessionStorage.removeItem(TOKEN_KEY);}

// Hàm gửi request dùng chung cho user
async function request(url, method = "GET", body = null) 
{
    // lấy token ra để sử dụng
    const token = getAccessToken();

    if (!token) 
    {
        const error = new Error("Bạn chưa đăng nhập.");
        error.status = 401;
        throw error;
    }

    const options = {
        method,
        headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
        },
    };

    if (body !== null) 
    {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    // Hỗ trợ cả JSON và response rỗng (204).
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
        data?.detail ||
        data?.title ||
        `Yêu cầu thất bại. HTTP ${response.status}`;

        // Xử lý lỗi validation của ASP.NET Core.
        if (data?.errors) 
        {
            const validationErrors = Object.values(data.errors).flat();

            if (validationErrors.length > 0) message = validationErrors.join(" ");
        }

        const error = new Error(message);
        error.status = response.status;
        throw error;
    }

    return data;
}

// 1. GET /api/user/me
export async function getMyProfile() 
{
    return await request(BASE_URL);
}

// 2. PUT /api/user/me
export async function updateMyProfile(username, phone) 
{
    return await request(BASE_URL, "PUT", {username,phone,});
}


// 3. PUT /api/user/me/password
export async function changeMyPassword(oldPassword, newPassword) {
    return await request(`${BASE_URL}/password`, "PUT", {oldPassword, newPassword,});
}
