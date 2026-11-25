import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { getMyDeviceById } from "../api/deviceApi";
import { getDeviceSchedule } from "../api/deviceScheduleApi";

const labels = {
    id: "Device ID",
    deviceName: "Tên thiết bị",
    description: "Mô tả",
    deviceTypeId: "Device Type ID",
    deviceTypeName: "Loại thiết bị",
    microcontrollerId: "MCU ID",
    microcontrollerType: "Loại MCU",
    gpio: "GPIO",
    currentStatus: "Trạng thái hiện tại",
    syncStatus: "Trạng thái đồng bộ",
    tagGroups: "Tag / Alias",
    action: "Hành động",
    scheduledDelay: "Delay (giây)",
    duration: "Duration (giây)",
    scheduledStartAt: "Bắt đầu lúc",
    scheduledEndAt: "Kết thúc lúc",
    expiresAt: "Hết hạn lúc",
    isExpired: "Đã hết hạn",
};

function showValue(key, value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    if (typeof value === "boolean") {
        return value ? "Có" : "Không";
    }

    if (["scheduledStartAt", "scheduledEndAt", "expiresAt"].includes(key)) {
        const date = new Date(Number(value) * 1000);

        return Number.isNaN(date.getTime())
            ? "—"
            : date.toLocaleString("vi-VN");
    }

    if (typeof value === "object") {
        return JSON.stringify(value, null, 2);
    }

    return String(value);
}

function InformationGrid({ data }) {
    return (
        <dl className="grid gap-x-8 sm:grid-cols-2">
            {Object.entries(data).map(([key, value]) => (
                <div
                    key={key}
                    className="border-b border-[#edf1ee] py-4"
                >
                    <dt className="text-xs font-medium text-[#819489]">
                        {labels[key] || key}
                    </dt>

                    <dd className="mt-1 whitespace-pre-wrap break-words text-sm font-medium text-[#243d30]">
                        {showValue(key, value)}
                    </dd>
                </div>
            ))}
        </dl>
    );
}

export default function DeviceDetailPage() {
    const { deviceId } = useParams();

    const [device, setDevice] = useState(null);
    const [schedule, setSchedule] = useState(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [scheduleError, setScheduleError] = useState("");

    useEffect(() => {
        let active = true;

        async function load() {
            setLoading(true);
            setError("");
            setScheduleError("");
            setSchedule(null);

            try {
                const detail = await getMyDeviceById(deviceId);

                if (!active) return;

                setDevice(detail);

                try {
                    const currentSchedule = await getDeviceSchedule(deviceId);

                    if (active) {
                        setSchedule(currentSchedule);
                    }
                } catch (err) {
                    if (active) {
                        setScheduleError(err.message);
                    }
                }
            } catch (err) {
                if (active) {
                    setError(err.message);
                }
            } finally {
                if (active) {
                    setLoading(false);
                }
            }
        }

        load();

        return () => {
            active = false;
        };
    }, [deviceId]);

    return (
        <div className="space-y-6">
            <Link className="ui-back" to="/">
                ← Về Home / Danh sách thiết bị
            </Link>

            {loading && (
                <p className="ui-card p-6">
                    Đang tải thông tin thiết bị...
                </p>
            )}

            {error && (
                <p role="alert" className="ui-alert-error">
                    {error}
                </p>
            )}

            {device && !loading && (
                <>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p className="ui-eyebrow">
                                DEVICE DETAIL · #{device.id}
                            </p>

                            <h1 className="ui-title">
                                {device.deviceName || `Device #${device.id}`}
                            </h1>

                            <p className="ui-subtitle">
                                Thông tin chi tiết lấy trực tiếp từ Device Registry.
                            </p>
                        </div>

                        <div className="flex flex-wrap gap-2">
                            {device.microcontrollerId != null && (
                                <Link
                                    to={`/mcu?selected=${device.microcontrollerId}`}
                                    className="ui-btn ui-btn-primary"
                                >
                                    Xem MCU liên kết →
                                </Link>
                            )}

                            <Link
                                to="/devices"
                                className="ui-btn ui-btn-outline"
                            >
                                Quản lý thiết bị
                            </Link>
                        </div>
                    </div>

                    <div className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
                        <section className="ui-card p-6">
                            <h2 className="ui-section-title">
                                Thông tin thiết bị
                            </h2>

                            <InformationGrid data={device} />
                        </section>

                        <section className="ui-card h-fit p-6">
                            <h2 className="ui-section-title">
                                Schedule trong Registry
                            </h2>

                            {scheduleError && (
                                <p
                                    role="alert"
                                    className="ui-alert-error mt-4"
                                >
                                    {scheduleError}
                                </p>
                            )}

                            {!schedule && !scheduleError && (
                                <p className="mt-5 text-sm text-[#7b8d82]">
                                    Thiết bị chưa có Schedule.
                                </p>
                            )}

                            {schedule && (
                                <InformationGrid data={schedule} />
                            )}

                            <Link
                                to="/microcontrollers"
                                className="ui-btn ui-btn-outline mt-6"
                            >
                                Điều khiển / Quản lý lịch
                            </Link>
                        </section>
                    </div>
                </>
            )}
        </div>
    );
}