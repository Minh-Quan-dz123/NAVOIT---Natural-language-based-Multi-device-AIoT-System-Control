import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { useAuth } from "../contexts/AuthContext";

const navigation = [
    { to: "/", label: "Tổng quan", icon: "◫", end: true },
    { to: "/mcu", label: "Vi điều khiển", icon: "▤" },
    { to: "/devices", label: "Quản lý thiết bị", icon: "◇" },
    { to: "/microcontrollers", label: "Liên kết & điều khiển", icon: "⌘" },
];


// tạo bố cục giao diện chung cho các trang sau khi người dùng đăng nhập.
// Sidebar: Hiển thị menu điều hướng như Home, Devices, MCU.
// Header: Hiển thị thanh tiêu đề, thông tin tài khoản và avatar.
// Bố cục: Sắp xếp Sidebar, Header và vùng nội dung chính.
// <Outlet />: Xác định vị trí hiển thị các trang con như HomePage, DevicesPage, McuExplorerPage
export default function WorkspaceLayout() 
{
    const {user} = useAuth();
    const location = useLocation();
    const [menuOpen, setMenuOpen] = useState(false);

    // mỗi làn pathnam hay search hay đổi, set = MenuOpen  = false
    useEffect(() => {
        setMenuOpen(false);
    }, [location.pathname, location.search]);

    const avatar = (user?.username || "U").slice(0, 2).toUpperCase();

    return (
        <div className="workspace">
            {menuOpen && (
                <button
                    type="button"
                    className="workspace-overlay"
                    aria-label="Đóng menu"
                    onClick={() => setMenuOpen(false)}
                />
            )}

            {/* 1. vùng bên trái khi mở menu */}
            <aside className={`workspace-sidebar ${menuOpen ? "is-open" : ""}`}>
                <Link to="/" className="brand">
                    <span className="brand-icon">S</span>
                    <span>
                        <strong>SmartHome</strong>
                        <small>AIoT Workspace</small>
                    </span>
                </Link>

                <div className="workspace-nav">
                    <p className="workspace-nav-label">KHÔNG GIAN LÀM VIỆC</p>

                    {navigation.map(item => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.end}
                            className={({ isActive }) =>`workspace-nav-link ${isActive ? "active" : ""}`}
                        >
                            <span className="workspace-nav-icon">{item.icon}</span>
                            {item.label}
                        </NavLink>
                    ))}

                    {user?.role === "Admin" && (
                        <>
                            <p className="workspace-nav-label mt-6">QUẢN TRỊ</p>
                            <NavLink
                                to="/admin/microcontrollers"
                                className={({ isActive }) =>
                                    `workspace-nav-link ${isActive ? "active" : ""}`
                                }
                            >
                                <span className="workspace-nav-icon">⚙</span>
                                Quản trị hệ thống
                            </NavLink>
                        </>
                    )}
                </div>

                <Link to="/account" className="workspace-account">
                    <span className="avatar">{avatar}</span>
                    <span className="min-w-0">
                        <strong className="block truncate text-sm">
                            {user?.username || "Tài khoản"}
                        </strong>
                        <small className="text-[#8daca0]">
                            {user?.role || "User"}
                        </small>
                    </span>
                </Link>
            </aside>

            {/* 2. Vùng phía trên có các nút mở ra vùng 1, hiển thị thêm tên của mục hiện tại mà user đang mở*/}
            <div className="workspace-main">
                <header className="workspace-topbar">
                    {/* gap-3 tạo khoảng cách 12px giữa các phần tử con */}
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            className="ui-btn ui-btn-outline workspace-menu-button"
                            onClick={() => setMenuOpen(true)}
                            aria-label="Mở menu"
                        >
                            ☰
                        </button>

                        <span className="text-sm font-medium text-[#64796f]">
                            Workspace
                        </span>

                        <span className="text-[#b6c5bd]">/</span>

                        <span className="text-sm font-semibold text-[#203b2d]">
                            {location.pathname === "/"
                                ? "Tổng quan"
                                : "Quản lý hệ thống"}
                        </span>
                    </div>
                    
                    {/* 3. Hiển thị chữ Home và 2 chữ đầu của tên tài khoản */}
                    <div className="flex items-center gap-3">
                        <Link
                            to="/"
                            className="ui-btn ui-btn-outline hidden sm:inline-flex"
                        >
                            ⌂ Home
                        </Link>

                        <Link
                            to="/account"
                            className="avatar avatar-light"
                            title="Thông tin tài khoản"
                            aria-label="Thông tin tài khoản"
                        >
                            {avatar}
                        </Link>
                    </div>
                </header>

                {/* 4. khu vực rộng lớn cho các page con, dùng main vì ý nghĩa sematic */}
                <main className="workspace-content">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}