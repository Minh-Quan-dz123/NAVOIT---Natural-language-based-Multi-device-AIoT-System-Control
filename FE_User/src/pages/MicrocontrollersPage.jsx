
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

import {
    refreshAllDeviceStatuses,
    formatRefreshResult,
} from "../api/deviceRefreshApi";

import {
    reconcileAllDevices,
    formatReconcileResult,
} from "../api/deviceReconcileApi";


import ManualDeviceControls from "../components/ManualDeviceControls";
import NaturalCommandControls from "../components/NaturalCommandControls";
import ManualScheduleControls from "../components/ManualScheduleControls";

import { syncSchedules } from "../api/scheduleSyncApi";

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

    const [refreshing, setRefreshing] = useState(false);
    const [refreshMessage, setRefreshMessage] = useState("");
    const [refreshError, setRefreshError] = useState("");

    // Trạng thái đồng bộ cấu hình Device/GPIO
    const [reconciling, setReconciling] = useState(false);
    const [reconcileResult, setReconcileResult] = useState(null);
    const [reconcileError, setReconcileError] = useState("");

    const [scheduleSyncBusy, setScheduleSyncBusy] = useState(false);
    const [scheduleSyncResult, setScheduleSyncResult] = useState(null);
    const [scheduleSyncError, setScheduleSyncError] = useState("");

    // 4. TẢI DANH SÁCH MCU CỦA USER
    useEffect(() => {
        let cancelled = false;

        async function loadMicrocontrollers()
         {
            // 1. Đọc danh sách MCU hiện có.
            try {
                const data = await getMyMicrocontrollers();

                if (!cancelled) {setMicrocontrollers(data);}
            }
            catch (err) 
            {
                if (!cancelled) setError(err.message);
            }
            finally 
            {
                if (!cancelled) setLoading(false);
            }

            if (cancelled) return;

            // 2. Tự động đồng bộ trạng thái khi vào trang.
            setRefreshing(true);

            try 
            {
                const result = await refreshAllDeviceStatuses();
                if (cancelled) return;

                const message = formatRefreshResult(result);
                if (result.state === "success" || result.state === "empty") {
                    setRefreshMessage(message);
                }
                else 
                {
                    setRefreshError(message);
                }

                // 3. Đọc lại thông tin sau đồng bộ.
                const updated = await getMyMicrocontrollers();

                if (!cancelled)setMicrocontrollers(updated);
            }
            catch (err) 
            {
                if (!cancelled) setRefreshError(err.message);
            }
            finally 
            {
                if (!cancelled) setRefreshing(false);
            }
        }

        loadMicrocontrollers();

        return () => {cancelled = true;};
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


    // 6.5. hàm refresh thủ công
    async function handleRefreshStatuses() 
    {
        if (refreshing || bindingBusy || reconciling || scheduleSyncBusy || loading) return;

        setRefreshing(true);
        setRefreshMessage("");
        setRefreshError("");

        try {
            // 1. Yêu cầu NLP đồng bộ tất cả MCU.
            const result = await refreshAllDeviceStatuses();

            const message = formatRefreshResult(result);

            if (result.state === "success" || result.state === "empty") {
                setRefreshMessage(message);
            }
            else {
                setRefreshError(message);
            }

            // 2. Đọc lại danh sách MCU từ Registry.
            const mcus = await getMyMicrocontrollers();
            setMicrocontrollers(mcus);

            // 3. Nếu đang xem một MCU, đọc lại Device của nó.
            if (selectedId !== null) {
                const updatedDevices =await getMyMicrocontrollerDevices(selectedId);

                setDevices(updatedDevices);
            }

            // 4. Nếu đã đối soát được MCU từng có kết quả
            // không xác định thì bỏ trạng thái chặn thao tác.
            if (unknownMcuId !== null) {
                const checked = result.results.find(
                    (item) => item.mcuId === unknownMcuId
                );

                if (
                    checked?.state === "success" &&
                    checked.mismatchedDeviceIds.length === 0 &&
                    checked.unknownGpios.length === 0
                ) {
                    setUnknownMcuId(null);
                }
            }
        }
        catch (err) {
            setRefreshError(err.message);
        }
        finally {
            setRefreshing(false);
        }
    }


    // 6.6.
    async function handleReconcileDevices() 
    {
        if (reconciling || refreshing || bindingBusy || scheduleSyncBusy || loading) {return;}

        const confirmed = window.confirm(
            "Đồng bộ cấu hình sẽ lấy Registry làm dữ liệu chuẩn.\n\n" +
            "Hệ thống có thể xóa DeviceTask thừa, sửa DeviceTask sai " +
            "và tạo lại những DeviceTask bị thiếu trên MCU.\n\n" +
            "Thiết bị được tạo lại sẽ khởi đầu ở trạng thái OFF. " +
            "Device có Schedule chưa hết hạn sẽ được bỏ qua.\n\n" +
            "Bạn có muốn tiếp tục không?"
        );

        if (!confirmed) return;

        setReconciling(true);
        setReconcileResult(null);
        setReconcileError("");
        setRefreshMessage("");
        setRefreshError("");

        try {
            // 1. Yêu cầu NLP đối soát và sửa cấu hình.
            const result = await reconcileAllDevices();

            setReconcileResult(result);

            // 2. Đọc lại danh sách MCU từ Registry.
            const mcus = await getMyMicrocontrollers();
            setMicrocontrollers(mcus);

            // 3. Nếu đang xem một MCU, đọc lại toàn bộ Device.
            if (selectedId !== null) 
            {
                const [updatedDevices, updatedFreeDevices] =
                    await Promise.all([
                        getMyMicrocontrollerDevices(selectedId),
                        getUnassignedDevices(),
                    ]);

                setDevices(updatedDevices);
                setUnassignedDevices(updatedFreeDevices);
            }
        }
        catch (err) 
        {
            setReconcileError(err.message);
        }
        finally 
        {
            setReconciling(false);
        }
    }

    // 6.7. hàm refresh trạng thái gpio và lịch
    async function handleScheduleSync(apply) 
    {
        if (scheduleSyncBusy || reconciling || refreshing || bindingBusy || loading) {return;}

        if (apply) 
        {
            const confirmed = window.confirm(
                "Hệ thống sẽ khôi phục những Schedule bị thiếu " +
                "trên MCU nếu có đủ thông tin và thời gian còn hợp lệ.\n\n" +
                "Schedule đang tồn tại nhưng không khớp sẽ không " +
                "bị ghi đè. Lịch hết hạn cũng không bị tự động xóa.\n\n" +
                "Bạn muốn tiếp tục?"
            );

            if (!confirmed) return;
        }

        setScheduleSyncBusy(true);
        setScheduleSyncError("");
        setScheduleSyncResult(null);

        try {
            const result = await syncSchedules(apply);

            setScheduleSyncResult(result);

            // Đọc lại Device để component Schedule
            // bên dưới tải lại dữ liệu mới nhất.
            if (selectedId !== null) {
                const updatedDevices = await getMyMicrocontrollerDevices(selectedId);

                setDevices(updatedDevices);
            }
        }
        catch (err) {
            setScheduleSyncError(err.message);
        }
        finally {
            setScheduleSyncBusy(false);
        }
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
                    "MCU đã xác nhận và Registry đã lưu, " +
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
    // MCU đang được người dùng chọn
    const selectedMcu = microcontrollers.find((mcu) => mcu.id === selectedId);

    // Loại MCU lấy từ Registry
    const mcuType = String(selectedMcu?.type || "")
        .trim()
        .toLowerCase();

    const isEsp32 = mcuType === "esp32";

    // Danh sách GPIO riêng cho ESP32
    const availableGpios = OUTPUT_GPIOS.filter((pin) => !devices.some((device) => device.gpio === pin));

    // Giá trị GPIO nhập/chọn
    const gpioNumber = Number(gpio);

    const selectedGpio = isEsp32
        ? (
            availableGpios.includes(gpioNumber)
                ? gpioNumber
                : (availableGpios[0] ?? null)
        )
        : (
            gpio.trim() !== "" &&
            Number.isSafeInteger(gpioNumber) &&
            gpioNumber >= 0 &&
            !devices.some((device) => device.gpio === gpioNumber)
                ? gpioNumber
                : null
        );

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
        refreshing ||
        reconciling ||
        scheduleSyncBusy ||
        unknownMcuId === selectedId;

    const canBind =
        !bindingBlocked &&
        selectedId !== null &&
        selectedMcu !== undefined &&
        deviceId !== "" &&
        selectedGpio !== null &&
        (!isEsp32 || devices.length < 6);

    const syncBusy =
        refreshing ||
        reconciling ||
        scheduleSyncBusy ||
        bindingBusy ||
        loading;


    // 10. GIAO DIỆN
    return (
        <div className="min-h-screen bg-gray-100 px-4 py-8">
            <div className="mx-auto max-w-5xl space-y-6">


                {/* HEADER */}
                <div className="flex flex-wrap items-center justify-between gap-5 rounded-xl border border-[#e1e9e3] bg-white p-6 shadow-sm">

                    <div>
                        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-emerald-600">
                            DEVICE MANAGEMENT
                        </p>

                        <h1 className="text-2xl font-semibold text-[#1d3527]">
                            Vi điều khiển của tôi
                        </h1>

                        <p className="mt-2 text-sm text-gray-500">
                            Quản lý MCU, cấu hình GPIO và Schedule
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">

                        {/* 1. LÀM MỚI TRẠNG THÁI */}
                        <button
                            type="button"
                            onClick={handleRefreshStatuses}
                            disabled={syncBusy}
                            className="inline-flex items-center gap-2 rounded-lg border border-[#dce5de] bg-white px-4 py-2.5 text-sm font-medium text-[#344c3d] shadow-sm transition hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            <span className="text-lg leading-none">↻</span>

                            {refreshing
                                ? "Đang làm mới..."
                                : "Làm mới trạng thái"}
                        </button>

                        {/* 2. ĐỒNG BỘ CẤU HÌNH */}
                        <button
                            type="button"
                            onClick={handleReconcileDevices}
                            disabled={syncBusy}
                            className="inline-flex items-center gap-2 rounded-lg border border-[#dce5de] bg-white px-4 py-2.5 text-sm font-medium text-[#344c3d] shadow-sm transition hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            <span className="text-base">⚙</span>

                            {reconciling
                                ? "Đang đồng bộ..."
                                : "Đồng bộ cấu hình"}
                        </button>

                        {/* 3. MENU SCHEDULE */}
                        <details
                            className={`relative ${
                                syncBusy ? "pointer-events-none opacity-50" : ""
                            }`}
                        >
                            <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-700 shadow-sm transition hover:bg-emerald-100 [&::-webkit-details-marker]:hidden">
                                <span>▦</span>

                                <span>
                                    {scheduleSyncBusy
                                        ? "Đang xử lý..."
                                        : "Schedule"}
                                </span>

                                <span className="ml-1 text-xs">▾</span>
                            </summary>

                            <div className="absolute right-0 z-30 mt-2 w-64 rounded-xl border border-[#e0e8e1] bg-white p-2 shadow-xl">

                                <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                                    Quản lý Schedule
                                </p>

                                {/* KIỂM TRA SCHEDULE */}
                                <button
                                    type="button"
                                    disabled={syncBusy}
                                    onClick={(event) => {
                                        event.currentTarget.closest("details").open = false;
                                        handleScheduleSync(false);
                                    }}
                                    className="w-full rounded-lg px-3 py-3 text-left transition hover:bg-[#f1f8f3] disabled:opacity-50"
                                >
                                    <p className="text-sm font-semibold text-[#294332]">
                                        Kiểm tra Schedule
                                    </p>

                                    <p className="mt-1 text-xs text-gray-500">
                                        Đối chiếu Schedule giữa Registry và MCU
                                    </p>
                                </button>

                                <div className="my-1 border-t border-gray-100" />

                                {/* KHÔI PHỤC SCHEDULE */}
                                <button
                                    type="button"
                                    disabled={syncBusy}
                                    onClick={(event) => {
                                        event.currentTarget.closest("details").open = false;
                                        handleScheduleSync(true);
                                    }}
                                    className="w-full rounded-lg px-3 py-3 text-left transition hover:bg-[#f1f8f3] disabled:opacity-50"
                                >
                                    <p className="text-sm font-semibold text-[#294332]">
                                        Khôi phục Schedule
                                    </p>

                                    <p className="mt-1 text-xs text-gray-500">
                                        Khôi phục lịch hợp lệ còn thiếu trên MCU
                                    </p>
                                </button>

                            </div>
                        </details>

                    </div>
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


                {refreshing && (
                    <p
                        role="status"
                        className="rounded-lg bg-blue-50 p-4 text-sm text-blue-700"
                    >
                        Đang lấy trạng thái thiết bị từ các MCU...
                    </p>
                )}

                {refreshMessage && !refreshing && (
                    <p
                        role="status"
                        className="rounded-lg bg-green-50 p-4 text-sm text-green-700"
                    >
                        {refreshMessage}
                    </p>
                )}

                {refreshError && !refreshing && (
                    <p
                        role="alert"
                        className="rounded-lg bg-amber-50 p-4 text-sm text-amber-800"
                    >
                        {refreshError}
                    </p>
                )}


                {reconciling && (
                    <p
                        role="status"
                        className="rounded-lg bg-blue-50 p-4 text-sm text-blue-700"
                    >
                        Đang đối chiếu và sửa cấu hình Device/GPIO trên MCU...
                    </p>
                )}


                {scheduleSyncBusy && (
                    <p
                        role="status"
                        className="rounded-lg bg-blue-50 p-4 text-sm text-blue-700"
                    >
                        Đang kiểm tra Schedule trên các MCU...
                    </p>
                )}

                {scheduleSyncError && (
                    <p
                        role="alert"
                        className="rounded-lg bg-red-50 p-4 text-sm text-red-700"
                    >
                        {scheduleSyncError}
                    </p>
                )}

                {scheduleSyncResult && !scheduleSyncBusy && (
                    <div className="rounded-xl border bg-white p-4 text-sm">
                        <h3 className="mb-3 font-semibold">
                            Kết quả đồng bộ Schedule
                        </h3>

                        <p className="mb-3 text-gray-600">
                            Đã đối chiếu {scheduleSyncResult.totalMcus} MCU.
                        </p>

                        <div className="space-y-4">
                            {scheduleSyncResult.results.map((mcu) => (
                                <div
                                    key={mcu.mcuId}
                                    className="rounded-lg bg-gray-50 p-3"
                                >
                                    <p className="font-medium">
                                        MCU #{mcu.mcuId} — {mcu.state}
                                    </p>

                                    <p className="mt-1 text-gray-600">
                                        {mcu.message}
                                    </p>

                                    {mcu.items.map((item, index) => (
                                        <div
                                            key={`${item.gpio}-${index}`}
                                            className="mt-2 rounded border bg-white p-2"
                                        >
                                            <p className="font-medium">
                                                {item.deviceId !== null
                                                    ? `Device #${item.deviceId}`
                                                    : "Device không xác định"}
                                                {" — "}
                                                GPIO {item.gpio}
                                            </p>

                                            <p className="text-gray-500">
                                                Trạng thái: {item.state}
                                            </p>

                                            <p className="mt-1">
                                                {item.message}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            ))}
                        </div>
                    </div>
                )}


                {reconcileError && (
                    <p
                        role="alert"
                        className="rounded-lg bg-red-50 p-4 text-sm text-red-700"
                    >
                        {reconcileError}
                    </p>
                )}

                {reconcileResult && !reconciling && (
                    <div
                        role="status"
                        className="rounded-lg border border-gray-200 bg-white p-4 text-sm"
                    >
                        <p className="font-semibold">
                            {formatReconcileResult(reconcileResult)}
                        </p>

                        <div className="mt-3 space-y-3">
                            {reconcileResult.results.map((item) => (
                                <div
                                    key={item.mcuId}
                                    className="rounded-lg bg-gray-50 p-3"
                                >
                                    <p className="font-medium">
                                        MCU #{item.mcuId} — {item.state}
                                    </p>

                                    <p className="mt-1 text-gray-600">
                                        {item.message}
                                    </p>

                                    {item.actions.length > 0 && (
                                        <p className="mt-1 text-gray-600">
                                            Đã xác minh:{" "}
                                            {item.actions.map(
                                                (action) =>
                                                    `${action.command} GPIO ${action.gpio}`
                                            ).join(", ")}
                                        </p>
                                    )}

                                    {item.skipped.map((skipped) => (
                                        <p
                                            key={skipped.gpio}
                                            className="mt-1 text-amber-700"
                                        >
                                            Bỏ qua GPIO {skipped.gpio}:{" "}
                                            {skipped.reason}
                                        </p>
                                    ))}

                                    {item.refresh?.state === "success" && (
                                        <p className="mt-1 text-gray-600">
                                            Device còn không khớp:{" "}
                                            {item.refresh.mismatchedDeviceIds.length}.
                                            {" "}GPIO thừa:{" "}
                                            {item.refresh.unknownGpios.length}.
                                        </p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}



                {/* ĐIỀU KHIỂN BẰNG NGÔN NGỮ TỰ NHIÊN */}
                <fieldset
                    disabled={refreshing || reconciling || scheduleSyncBusy || bindingBusy}
                    className="min-w-0 border-0 p-0"
                >
                    <NaturalCommandControls
                        onChanged={async () => {
                            const mcus = await getMyMicrocontrollers();
                            setMicrocontrollers(mcus);

                            if (selectedId !== null) 
                            {
                                const data = await getMyMicrocontrollerDevices(selectedId);
                                setDevices(data);
                            }
                        }}
                    />
                </fieldset>

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
                                        disabled={bindingBusy || refreshing || reconciling || scheduleSyncBusy ||loading}
                                        onClick={() => {
                                            setSelectedId(item.id);
                                            setGpio(
                                                String(item.type || "").trim().toLowerCase() === "esp32"
                                                    ? "25"
                                                    : ""
                                            );
                                        }}
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
                                disabled={bindingBusy || refreshing || reconciling || scheduleSyncBusy}
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
                                Cần đối soát MCU với Registry trước khi gửi
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
                                    {isEsp32 ? (
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
                                    ) : (
                                        <input
                                            type="number"
                                            min="0"
                                            step="1"
                                            value={gpio}
                                            onChange={(e) => setGpio(e.target.value)}
                                            disabled={bindingBlocked}
                                            className="w-full rounded-lg border p-2"
                                            placeholder="Nhập số GPIO của MCU"
                                        />
                                    )}

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

                            {isEsp32 && devices.length >= 6 && (
                                <p className="mt-3 text-sm text-red-600">
                                    ESP32 đã đạt giới hạn 6 Device.
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

                        <fieldset
                            disabled={refreshing || reconciling || scheduleSyncBusy || bindingBusy}
                            className="min-w-0 border-0 p-0"
                        >
                            <ManualDeviceControls
                                devices={devices}
                                onChanged={async () => {
                                    const data = await getMyMicrocontrollerDevices(selectedId);
                                    setDevices(data);
                                }}
                            />

                            <ManualScheduleControls devices={devices} />
                        </fieldset>

                    </section>
                )}
            </div>
        </div>
    );
}
