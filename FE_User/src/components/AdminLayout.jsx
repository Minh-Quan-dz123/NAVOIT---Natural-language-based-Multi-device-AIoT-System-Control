// khung giao diện dùng chung cho các trang Admin
import { Link, NavLink, Outlet } from "react-router";

const menuItems = [
    {
        label: "Quản lý loại MCU",
        path: "/admin/microcontroller-types",
    },
    {
        label: "Quản lý MCU",
        path: "/admin/microcontrollers",
    },
    {
        label: "Quản lý loại thiết bị",
        path: "/admin/device-types",
    },
];

export default function AdminLayout() 
{
    function menuClass({ isActive }) 
    {
        return (
            "block rounded-lg px-4 py-3 text-sm font-medium " +
            (isActive
                ? "bg-blue-600 text-white"
                : "text-gray-700 hover:bg-gray-100")
        );
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Thanh điều hướng chung */}
            <header className="border-b bg-white">
                <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
                    <h1 className="text-xl font-bold text-blue-700">
                        AIoT Admin
                    </h1>

                    <Link
                        to="/account"
                        className="text-sm font-medium text-gray-600 hover:text-blue-600"
                    >
                        Về tài khoản
                    </Link>
                </div>
            </header>

            <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 md:grid-cols-[220px_1fr]">
                {/* Menu Admin */}
                <nav className="h-fit rounded-xl bg-white p-3 shadow-sm">
                    <p className="mb-3 px-4 text-xs font-semibold uppercase text-gray-400">
                        Quản trị hệ thống
                    </p>

                    <div className="space-y-1">
                        {menuItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={menuClass}
                            >
                                {item.label}
                            </NavLink>
                        ))}
                    </div>
                </nav>

                {/* Trang Admin đang được chọn */}
                <main className="min-w-0">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
