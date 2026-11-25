import { NavLink, Outlet } from "react-router";

const items = [
    {
        to: "/admin/microcontrollers",
        label: "Quản lý MCU & User",
    },
    {
        to: "/admin/microcontroller-types",
        label: "Loại vi điều khiển",
    },
    {
        to: "/admin/device-types",
        label: "Loại thiết bị",
    },
];

export default function AdminLayout() {
    return (
        <div className="space-y-6">
            <div>
                <p className="ui-eyebrow">ADMINISTRATION</p>

                <h1 className="ui-title">
                    Quản trị hệ thống
                </h1>

                <p className="ui-subtitle">
                    Các chức năng quản trị hiện tại được giữ nguyên.
                </p>
            </div>

            <nav className="ui-card flex flex-wrap gap-2 p-3">
                {items.map(item => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        className={({ isActive }) =>
                            `ui-btn ${
                                isActive
                                    ? "ui-btn-primary"
                                    : "ui-btn-outline"
                            }`
                        }
                    >
                        {item.label}
                    </NavLink>
                ))}
            </nav>

            <Outlet />
        </div>
    );
}