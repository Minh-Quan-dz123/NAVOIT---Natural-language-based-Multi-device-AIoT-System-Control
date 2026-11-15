
import { Routes, Route, Navigate, Link } from "react-router";
import { useAuth } from "./contexts/AuthContext";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ProfilePage from "./pages/ProfilePage";

import MicrocontrollersPage from "./pages/MicrocontrollersPage";
import DevicesPage from "./pages/DevicesPage";

import AdminMicrocontrollersPage from "./pages/AdminMicrocontrollersPage";
import AdminMicrocontrollerTypesPage from "./pages/AdminMicrocontrollerTypesPage";
import AdminDeviceTypesPage from "./pages/AdminDeviceTypesPage";

import AdminLayout from "./components/AdminLayout";
import ProtectedRoute from "./components/ProtectedRoute";

import "./App.css";

// TRANG TÀI KHOẢN
function AccountPage() 
{
    const { user } = useAuth();

    return (
        <>
            <div className="flex flex-wrap justify-center gap-3 bg-gray-100 px-4 pt-4">

                {/* User và Admin quản lý Device của mình */}
                <Link
                    to="/devices"
                    className="rounded-lg bg-green-700 px-4 py-2 text-white hover:bg-green-800"
                >
                    Thiết bị của tôi
                </Link>

                {/* User và Admin xem MCU của mình */}
                <Link
                    to="/microcontrollers"
                    className="rounded-lg bg-gray-800 px-4 py-2 text-white hover:bg-gray-900"
                >
                    Vi điều khiển của tôi
                </Link>

                {/* Chỉ Admin thấy nút quản trị */}
                {user?.role === "Admin" && (
                    <Link
                        to="/admin/microcontrollers"
                        className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                    >
                        Quản trị hệ thống
                    </Link>
                )}
            </div>

            <ProfilePage />
        </>
    );
}

// ROUTES
export default function App() {
    return (
        <Routes>
            {/* Trang mặc định */}
            <Route
                path="/"
                element={<Navigate to="/account" replace />}
            />

            {/* Đăng nhập */}
            <Route
                path="/login"
                element={<LoginPage />}
            />

            {/* Đăng ký */}
            <Route
                path="/register"
                element={<RegisterPage />}
            />

            {/* Thông tin tài khoản */}
            <Route
                path="/account"
                element={
                    <ProtectedRoute>
                        <AccountPage />
                    </ProtectedRoute>
                }
            />

            {/* USER Quản lý Device của mình */}
            <Route
                path="/devices"
                element={
                    <ProtectedRoute>
                        <DevicesPage />
                    </ProtectedRoute>
                }
            />

            {/* USER Xem MCU của mình */}
            <Route
                path="/microcontrollers"
                element={
                    <ProtectedRoute>
                        <MicrocontrollersPage />
                    </ProtectedRoute>
                }
            />

            {/* ADMIN Các trang quản trị */}
            <Route
                path="/admin"
                element={
                    <ProtectedRoute requiredRole="Admin">
                        <AdminLayout />
                    </ProtectedRoute>
                }
            >
                {/* Trang quản trị mặc định */}
                <Route
                    index
                    element={
                        <Navigate
                            to="/admin/microcontrollers"
                            replace
                        />
                    }
                />

                {/* Quản lý loại MCU */}
                <Route
                    path="microcontroller-types"
                    element={ <AdminMicrocontrollerTypesPage />}  
                />

                {/* Quản lý MCU */}
                <Route
                    path="microcontrollers"
                    element={<AdminMicrocontrollersPage />}  
                />

                {/* Quản lý loại Device */}
                <Route
                    path="device-types"
                    element={ <AdminDeviceTypesPage />}
                />
            </Route>

            {/* Đường dẫn không tồn tại */}
            <Route
                path="*"
                element={<Navigate to="/account" replace />}
            />
        </Routes>
    );
}
