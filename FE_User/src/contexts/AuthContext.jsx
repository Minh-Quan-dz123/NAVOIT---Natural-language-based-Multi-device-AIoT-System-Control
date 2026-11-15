// quản lý phiên đăng nhập tập trung. 
// Khi load lại trang, 
// Context sử dụng JWT đang lưu để call luôn cho Backend để lấy thông tin tài khoản.


import { createContext, useContext, useEffect, useState,} from "react";

// tận dụng các hàm đã code trước đó
import {
  getAccessToken,
  saveAccessToken,
  removeAccessToken,
  getMyProfile,
} from "../api/userApi";

const AuthContext = createContext(null);

// 1. Quản lý và chia sẻ trạng thái đăng nhập cho toàn bộ ứng dụng.
export function AuthProvider({ children }) 
{
    // 1.1. cầm token và thông tin user
    const [token, setToken] = useState(getAccessToken);
    const [user, setUser] = useState(null);

    // 1.2. state load và lỗi
    const [isLoading, setIsLoading] = useState(() => Boolean(getAccessToken()));
    const [sessionError, setSessionError] = useState("");

    // 1.3. Kiểm tra JWT khi tải trang hoặc khi đăng nhập.
    useEffect(() => {
        if (!token) return;

        // nếu có thì check thông tin hiện tại
        let cancelled = false;

        async function checkSession() 
        {
            try 
            {
                // call api lấy thông tin cá nhân
                const profile = await getMyProfile();

                // nếu đã bấm hủy thì return luôn, nếu chưa thì tiếp tục
                if (cancelled) return;

                setUser(profile);
                setSessionError("");
            } 
            catch (error) 
            {
                if (cancelled) return;
                setUser(null);

                if (error.status === 401) 
                {
                    // JWT không còn được Backend chấp nhận.
                    removeAccessToken();
                    setToken(null);
                } 
                else 
                {
                    // Lỗi mạng hoặc lỗi khác
                    setSessionError(error.message || "Không thể kiểm tra phiên đăng nhập.");
                }
            } 
            finally 
            {
                if (!cancelled) {setIsLoading(false);}
            }
        }

        checkSession();

        return () => {cancelled = true;};
    }, [token]);

    // 1.4. Được gọi sau khi authApi đăng nhập/đăng ký thành công.
    function login(authResponse) 
    {
        const accessToken = typeof authResponse === "string"? authResponse: authResponse?.accessToken;

        if (!accessToken) { throw new Error("Backend không trả về accessToken.");}

        saveAccessToken(accessToken);

        setUser(null);
        setSessionError("");
        setIsLoading(true);
        setToken(accessToken);
    }

    function logout() 
    {
        removeAccessToken();

        setToken(null);
        setUser(null);
        setSessionError("");
        setIsLoading(false);
    }

    // 1.5. Lấy lại thông tin User từ Backend.
    async function refreshUser() 
    {
        setIsLoading(true);
        setSessionError("");

        try 
        {
            const profile = await getMyProfile();

            setUser(profile);
            return profile;
        } 
        catch (error) 
        {
            if (error.status === 401) logout();
            else 
            {
                setSessionError(error.message || "Không thể tải thông tin tài khoản.");
            }

        throw error;
        } 
        finally {
            setIsLoading(false);
        }
    }

    // 1.6. Đồng bộ User trong Context sau khi cập nhật tài khoản.
    function updateUser(updatedUser) 
    {
        setUser(updatedUser);
    }

    const value = {
        token,
        user,
        isLoading,
        sessionError,
        isAuthenticated: Boolean(token && user),
        login,
        logout,
        refreshUser,
        updateUser,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// lấy dữ liệu từ authContext
export function useAuth() 
{
    const context = useContext(AuthContext);
    if (!context) {throw new Error("useAuth phải được sử dụng trong AuthProvider.");}

    return context;
}
