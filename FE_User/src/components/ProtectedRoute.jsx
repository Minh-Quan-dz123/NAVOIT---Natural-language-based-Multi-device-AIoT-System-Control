// Không có JWT: chuyển về /login.
// Có JWT: chờ Backend xác minh.
// Backend từ chối JWT: Context xóa phiên và chuyển về /login.
// Lỗi kết nối: cho phép thử lại thay vì tự động đăng xuất.

import { Navigate, Outlet, useLocation} from "react-router";

import { useAuth } from "../contexts/AuthContext";

export default function ProtectedRoute({ children, requiredRole = null}) 
{
    // 1. componetn có token, user, các giá trị phụ
    const {
        token,
        user,
        isLoading,
        sessionError,
        refreshUser,
    } = useAuth();

    const location = useLocation();

    if (isLoading) 
    {
        return (
        <div className="flex min-h-screen items-center justify-center">
            <p className="text-gray-600">
                Đang kiểm tra phiên đăng nhập...
            </p>
        </div>
        );
    }

    // nếu ko có token thì về login luôn
    if (!token) 
    {
        return (
            <Navigate
                to="/login"
                replace
                state={{ from: location }}
            />
        );
    }

    // có token nhưng ko lấy được user thì chứng tỏ có lỗi
    // trả về thông báo và nút bấm thử lại
    if (!user) 
    {
        return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="rounded-lg border border-gray-200 bg-white p-6 text-center shadow-sm">
                <p className="mb-4 text-red-600">
                    {sessionError || "Không thể tải thông tin tài khoản."}
                </p>

                <button
                    type="button"
                    onClick={() => {refreshUser().catch(() => {});}}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                >
                    Thử lại
                </button>
            </div>
        </div>
        );
    }

    // 4. Nếu route yêu cầu Role Cụ thể mà tài khoản ko có quyền => vào /account
    if (requiredRole && user.role !== requiredRole) {
        return <Navigate to="/account" replace />;
    }

    // 5. nếu có đủ điều kiện thì hiển thị component con
    return children || <Outlet />;
}
