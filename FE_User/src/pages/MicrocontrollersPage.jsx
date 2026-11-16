
import { useEffect, useState } from "react";
import { Link } from "react-router";

import {
    getMyMicrocontrollers,
    getMyMicrocontrollerDevices,
} from "../api/microcontrollerApi";

import {
    getUnassignedDevices,
    bindDevice,
    unbindDevice,
    OUTPUT_GPIOS,
} from "../api/deviceBindingApi";

import ManualDeviceControls from "../components/ManualDeviceControls";
import NaturalCommandControls from "../components/NaturalCommandControls";
import ManualScheduleControls from "../components/ManualScheduleControls";

export default function MicrocontrollersPage()
{
    // 1. DỮ LIỆU
    const [microcontrollers, setMicrocontrollers] = useState([]);
    const [selectedId, setSelectedId] = useState(null);

    const [devices, setDevices] = useState([]);
    const [unassignedDevices, setUnassignedDevices] = useState([]);

    // 2. DỮ LIỆU FORM
    const [deviceId, setDeviceId] = useState("");
    const [gpio, setGpio] = useState("25");

    // 3. TRẠNG THÁI
    const [loading, setLoading] = useState(true);
    const [devicesLoading, setDevicesLoading] = useState(false);
    const [bindingBusy, setBindingBusy] = useState(false);

    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    // Nếu timeout hoặc chưa xác định kết quả, không tự retry.
    const [unknownMcuId, setUnknownMcuId] = useState(null);


    // 4. TẢI DANH SÁCH MCU CỦA USER
    useEffect(() => 
    {
        let cancelled = false;

        async function loadMicrocontrollers() 
        {
            try 
            {
                const data = await getMyMicrocontrollers();
                if (!cancelled) setMicrocontrollers(data);
            } 
            catch (err) 
            {
                if (!cancelled) setError(err.message);
            } 
            finally 
            {
                if (!cancelled) setLoading(false);
            }
        }

        loadMicrocontrollers();
        return () => { cancelled = true;};
    }, []);


    // 5. TẢI DEVICE KHI CHỌN MCU
    useEffect(() => {
        if (selectedId === null) 
        {
            setDevices([]);
            return;
        }

        let cancelled = false;

        async function loadDevices() 
        {
            setDevicesLoading(true);
            setError("");
            setMessage("");

            try {
                const [mcuDevices, freeDevices] = await Promise.all([
                    getMyMicrocontrollerDevices(selectedId),
                    getUnassignedDevices(),
                ]);

                if (!cancelled) 
                {
                    setDevices(mcuDevices);
                    setUnassignedDevices(freeDevices);
                    setDeviceId("");
                }
            } 
            catch (err) 
            {
                if (!cancelled) setError(err.message);
            } 
            finally 
            {
                if (!cancelled) setDevicesLoading(false);
            }
        }

        loadDevices();

        return () => {cancelled = true; };
    }, [selectedId]);


    // 6. LÀM MỚI DỮ LIỆU SAU KHI THAO TÁC
    async function reloadData() 
    {
        const [mcus, mcuDevices, freeDevices] = await Promise.all([
            getMyMicrocontrollers(),
            getMyMicrocontrollerDevices(selectedId),
            getUnassignedDevices(),
        ]);

        setMicrocontrollers(mcus);
        setDevices(mcuDevices);
        setUnassignedDevices(freeDevices);
        setDeviceId("");
    }


    // 7. LIÊN KẾT DEVICE VỚI GPIO
    async function handleBind() 
    {
        if (!deviceId || selectedId === null) return;

        if (selectedGpio === null) return;

        setBindingBusy(true);
        setError("");
        setMessage("");

        let commandSucceeded = false;

        try {
            await bindDevice(Number(deviceId), selectedId, selectedGpio);
            commandSucceeded = true;
            await reloadData();

            setMessage("Liên kết Device với GPIO thành công.");
        } 
        catch (err) 
        {
            if (err.state === "unknown") setUnknownMcuId(selectedId);

            if (commandSucceeded) 
            {
                setError(
                    "ESP32 đã xác nhận và Registry đã lưu, " +
                    "nhưng không tải lại được dữ liệu: " + err.message
                );
            } 
            else 
            {
                setError(err.message);
            }
        } 
        finally 
        {
            setBindingBusy(false);
        }
    }


    // 8. THÁO LIÊN KẾT DEVICE
    async function handleUnbind(device) 
    {
        const confirmed = window.confirm(
            `Tháo "${device.deviceName || `Device #${device.id}`}" ` +
            `khỏi MCU #${selectedId}, GPIO ${device.gpio}?`
        );

        if (!confirmed) return;

        setBindingBusy(true);
        setError("");
        setMessage("");

        let commandSucceeded = false;

        try {
            await unbindDevice(device.id);

            commandSucceeded = true;

            await reloadData();

            setMessage(
                "Đã tháo liên kết thành công. " +
                "Device logic vẫn được giữ trong Registry."
            );
        } 
        catch (err) 
        {
            if (err.state === "unknown") setUnknownMcuId(selectedId);

            if (commandSucceeded) 
            {
                setError(
                    "Tháo liên kết thành công nhưng không tải lại được " +
                    "dữ liệu: " + err.message
                );
            } 
            else 
            {
                setError(err.message);
            }
        } 
        finally 
        {
            setBindingBusy(false);
        }
    }


    // 9. DỮ LIỆU CHO FORM
    const availableGpios = OUTPUT_GPIOS.filter((pin) => !devices.some((device) => device.gpio === pin));

    const selectedGpio = availableGpios.includes(Number(gpio))
        ? Number(gpio)
        : (availableGpios[0] ?? null);

    // Chỉ hiển thị các Device thực sự chưa liên kết.
    const freeDevices = unassignedDevices.filter(
        (device) =>
            device.microcontrollerId === null &&
            device.gpio === null &&
            device.syncStatus === "unassigned"
    );

    const bindingBlocked =
        bindingBusy ||
        devicesLoading ||
        unknownMcuId === selectedId;

    const canBind =
        !bindingBlocked &&
        selectedId !== null &&
        deviceId !== "" &&
        selectedGpio !== null &&
        devices.length < 6;


    // 10. GIAO DIỆN
    return (
        <div className="min-h-screen bg-gray-100 px-4 py-8">
            <div className="mx-auto max-w-5xl space-y-6">

                {/* HEADER */}
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            Vi điều khiển của tôi
                        </h1>

                        <p className="mt-1 text-sm text-gray-500">
                            Quản lý MCU và các Device liên kết GPIO
                        </p>
                    </div>

                    <Link
                        to="/account"
                        className="rounded-lg bg-white px-4 py-2 text-sm shadow-sm hover:bg-gray-50"
                    >
                        Về tài khoản
                    </Link>
                </div>

                {/* THÔNG BÁO */}
                {error && (
                    <p
                        role="alert"
                        className="rounded-lg bg-red-50 p-4 text-sm text-red-700"
                    >
                        {error}
                    </p>
                )}

                {message && (
                    <p
                        role="status"
                        className="rounded-lg bg-green-50 p-4 text-sm text-green-700"
                    >
                        {message}
                    </p>
                )}


                {/* ĐIỀU KHIỂN BẰNG NGÔN NGỮ TỰ NHIÊN */}
                <NaturalCommandControls
                    onChanged={async () => {
                        const mcus = await getMyMicrocontrollers();
                        setMicrocontrollers(mcus);

                        if (selectedId !== null) {
                            const data = await getMyMicrocontrollerDevices(selectedId);
                            setDevices(data);
                        }
                    }}
                />


                {/* DANH SÁCH MCU */}
                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <div className="mb-5 flex items-center justify-between">
                        <h2 className="text-lg font-semibold">
                            Danh sách MCU
                        </h2>

                        <span className="text-sm text-gray-500">
                            Tổng số: {microcontrollers.length}
                        </span>
                    </div>

                    {loading ? (
                        <p className="py-6 text-gray-500">
                            Đang tải dữ liệu...
                        </p>
                    ) : microcontrollers.length === 0 ? (
                        <p className="py-6 text-gray-500">
                            Bạn chưa được cấp vi điều khiển nào.
                        </p>
                    ) : (
                        <div className="grid gap-4 sm:grid-cols-2">
                            {microcontrollers.map((item) => (
                                <div
                                    key={item.id}
                                    className={`rounded-xl border p-4 ${
                                        selectedId === item.id
                                            ? "border-blue-500"
                                            : "border-gray-200"
                                    }`}
                                >
                                    <div className="mb-4 flex items-start justify-between">
                                        <div>
                                            <h3 className="text-lg font-semibold">
                                                {item.type}
                                            </h3>

                                            <p className="text-xs text-gray-400">
                                                MCU ID: {item.id}
                                            </p>
                                        </div>

                                        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs">
                                            {item.connectionStatus}
                                        </span>
                                    </div>

                                    <div className="space-y-2 text-sm">
                                        <p>
                                            <span className="text-gray-500">
                                                MAC:
                                            </span>{" "}
                                            <span className="font-mono">
                                                {item.macAddress}
                                            </span>
                                        </p>

                                        <p>
                                            <span className="text-gray-500">
                                                Device liên kết:
                                            </span>{" "}
                                            {item.deviceCount}
                                        </p>

                                        <p>
                                            <span className="text-gray-500">
                                                Kết nối gần nhất:
                                            </span>{" "}
                                            {item.lastSeenAt
                                                ? new Date(item.lastSeenAt)
                                                    .toLocaleString("vi-VN")
                                                : "Chưa có dữ liệu"}
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        disabled={bindingBusy}
                                        onClick={() => setSelectedId(item.id)}
                                        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
                                    >
                                        Quản lý Device
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
                


                {/* CHI TIẾT MCU */}
                {selectedId !== null && (
                    <section className="rounded-xl bg-white p-6 shadow-sm">

                        <div className="mb-5 flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold">
                                Device thuộc MCU #{selectedId}
                            </h2>

                            <button
                                type="button"
                                disabled={bindingBusy}
                                onClick={() => setSelectedId(null)}
                                className="text-sm text-gray-500 hover:text-gray-800 disabled:opacity-50"
                            >
                                Đóng
                            </button>
                        </div>

                        {/* KHÔNG TỰ THỬ LẠI KHI KẾT QUẢ CHƯA RÕ */}
                        {unknownMcuId === selectedId && (
                            <p
                                role="alert"
                                className="mb-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-800"
                            >
                                Một thao tác trên MCU này có kết quả chưa xác định.
                                Cần đối soát ESP32 với Registry trước khi gửi
                                lệnh liên kết hoặc tháo tiếp.
                            </p>
                        )}

                        {/* FORM LIÊN KẾT */}
                        <div className="mb-6 rounded-lg border border-gray-200 p-4">
                            <h3 className="mb-4 font-semibold">
                                Liên kết Device với GPIO
                            </h3>

                            <div className="grid gap-4 sm:grid-cols-3">

                                <div>
                                    <label className="mb-1 block text-sm">
                                        Device chưa liên kết
                                    </label>

                                    <select
                                        value={deviceId}
                                        disabled={bindingBlocked}
                                        onChange={(e) => setDeviceId(e.target.value)}
                                        className="w-full rounded-lg border p-2"
                                    >
                                        <option value="">
                                            Chọn Device
                                        </option>

                                        {freeDevices.map((device) => (
                                            <option
                                                key={device.id}
                                                value={device.id}
                                            >
                                                {device.deviceName ||
                                                    `Device #${device.id}`}
                                                {" — "}
                                                {device.deviceTypeName}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="mb-1 block text-sm">
                                        GPIO
                                    </label>

                                    <select
                                        value={selectedGpio ?? ""}
                                        disabled={bindingBlocked || selectedGpio === null}
                                        onChange={(e) => setGpio(e.target.value)}
                                        className="w-full rounded-lg border p-2"
                                    >
                                        {availableGpios.length === 0 && (
                                            <option value="">
                                                Không còn GPIO khả dụng
                                            </option>
                                        )}

                                        {availableGpios.map((pin) => (
                                            <option key={pin} value={pin}>
                                                GPIO {pin}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="flex items-end">
                                    <button
                                        type="button"
                                        disabled={!canBind}
                                        onClick={handleBind}
                                        className="w-full rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
                                    >
                                        {bindingBusy
                                            ? "Đang xử lý..."
                                            : "Liên kết"}
                                    </button>
                                </div>
                            </div>

                            {freeDevices.length === 0 && !devicesLoading && (
                                <p className="mt-3 text-sm text-gray-500">
                                    Không có Device chưa liên kết.
                                    Hãy tạo Device logic trước.
                                </p>
                            )}

                            {devices.length >= 6 && (
                                <p className="mt-3 text-sm text-red-600">
                                    MCU đã đạt giới hạn 6 Device.
                                </p>
                            )}
                        </div>

                        {/* DANH SÁCH DEVICE ĐÃ LIÊN KẾT */}
                        <h3 className="mb-3 font-semibold">
                            Device đang liên kết
                        </h3>

                        {devicesLoading ? (
                            <p className="py-4 text-gray-500">
                                Đang tải Device...
                            </p>
                        ) : devices.length === 0 ? (
                            <p className="py-4 text-gray-500">
                                MCU này chưa có Device liên kết.
                            </p>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-3 py-3">Device</th>
                                            <th className="px-3 py-3">GPIO</th>
                                            <th className="px-3 py-3">Trạng thái</th>
                                            <th className="px-3 py-3">Đồng bộ</th>
                                            <th className="px-3 py-3">Thao tác</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {devices.map((device) => (
                                            <tr
                                                key={device.id}
                                                className="border-b border-gray-100"
                                            >
                                                <td className="px-3 py-3">
                                                    {device.deviceName ||
                                                        `Device #${device.id}`}
                                                </td>

                                                <td className="px-3 py-3">
                                                    {device.gpio ?? "—"}
                                                </td>

                                                <td className="px-3 py-3">
                                                    {device.currentStatus}
                                                </td>

                                                <td className="px-3 py-3">
                                                    {device.syncStatus}
                                                </td>

                                                <td className="px-3 py-3">
                                                    <button
                                                        type="button"
                                                        disabled={
                                                            bindingBlocked ||
                                                            device.syncStatus !== "synced"
                                                        }
                                                        onClick={() => handleUnbind(device)}
                                                        className="rounded-lg bg-red-600 px-3 py-2 text-white disabled:opacity-50"
                                                    >
                                                        Tháo liên kết
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        <ManualDeviceControls
                            devices={devices}
                            onChanged={async () => {
                                const data = await getMyMicrocontrollerDevices(selectedId);
                                setDevices(data);
                            }}
                        />

                        <ManualScheduleControls devices={devices} />
                    </section>
                )}
            </div>
        </div>
    );
}
