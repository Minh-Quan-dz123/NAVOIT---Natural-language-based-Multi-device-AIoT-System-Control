import { Routes, Route, Navigate } from "react-router";
import ProtectedRoute from "./components/ProtectedRoute";
import WorkspaceLayout from "./components/WorkspaceLayout";
import AdminLayout from "./components/AdminLayout";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import DeviceDetailPage from "./pages/DeviceDetailPage";
import McuExplorerPage from "./pages/McuExplorerPage";
import ProfilePage from "./pages/ProfilePage";
import DevicesPage from "./pages/DevicesPage";
import MicrocontrollersPage from "./pages/MicrocontrollersPage";
import AdminMicrocontrollersPage from "./pages/AdminMicrocontrollersPage";
import AdminMicrocontrollerTypesPage from "./pages/AdminMicrocontrollerTypesPage";
import AdminDeviceTypesPage from "./pages/AdminDeviceTypesPage";

export default function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route element={<ProtectedRoute />}>
                <Route element={<WorkspaceLayout />}>
    
                    <Route index element={<HomePage />} /> 
                    <Route path="device/:deviceId" element={<DeviceDetailPage />} />
                    <Route path="mcu" element={<McuExplorerPage />} />
                    <Route path="account" element={<ProfilePage />} />
                    <Route path="devices" element={<DevicesPage />} />
                    <Route path="microcontrollers" element={<MicrocontrollersPage />} />

                    <Route element={<ProtectedRoute requiredRole="Admin" />}>
                        <Route path="admin" element={<AdminLayout />}>
                            <Route index element={<Navigate to="microcontrollers" replace />} />
                            <Route path="microcontrollers" element={<AdminMicrocontrollersPage />} />
                            <Route path="microcontroller-types" element={<AdminMicrocontrollerTypesPage />} />
                            <Route path="device-types" element={<AdminDeviceTypesPage />} />
                        </Route>
                    </Route>
                </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}