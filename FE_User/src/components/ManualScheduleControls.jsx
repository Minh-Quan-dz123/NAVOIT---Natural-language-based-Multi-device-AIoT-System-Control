
import { useEffect, useState } from "react";

import {
    createDeviceSchedule,
    getDeviceSchedule,
    cancelDeviceSchedule,
} from "../api/deviceScheduleApi";


export default function ManualScheduleControls({ devices }) {
    // 1. FORM TẠO SCHEDULE
    const [deviceId, setDeviceId] = useState("");
    const [action, setAction] = useState("on");

    const [startMode, setStartMode] = useState("delay");
    const [delaySeconds, setDelaySeconds] = useState("600");
    const [startDate, setStartDate] = useState("");

    const [endMode, setEndMode] = useState("none");
    const [durationSeconds, setDurationSeconds] = useState("1800");
    const [endDate, setEndDate] = useState("");

    const [busy, setBusy] = useState(false);
    const [unknown, setUnknown] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    // 2. DANH SÁCH SCHEDULE
    const [scheduleRows, setScheduleRows] = useState([]);
    const [loadingSchedules, setLoadingSchedules] = useState(false);
    const [scheduleVersion, setScheduleVersion] = useState(0);
    const [cancelBusyId, setCancelBusyId] = useState(null);
    const [unknownCancelIds, setUnknownCancelIds] = useState([]);


    // 3. CHUYỂN DATETIME-LOCAL SANG UNIX SECONDS
    function toUnixSeconds(value) {
        const timestamp = new Date(value).getTime();

        if (!value || !Number.isFinite(timestamp)) {
            throw new Error("Ngày giờ không hợp lệ.");
        }

        return Math.floor(timestamp / 1000);
    }


    // 4. KIỂM TRA GIÁ TRỊ GIÂY
    function positiveSeconds(value, label) {
        const number = Number(value);

        if (!Number.isSafeInteger(number) || number <= 0) {
            throw new Error(
                `${label} phải là số giây nguyên dương.`
            );
        }

        return number;
    }


    // 5. XÂY DỰNG REQUEST TẠO SCHEDULE
    function buildSchedule() {
        const body = {
            action,
            scheduledDelay: null,
            duration: null,
            scheduledStartAt: null,
            scheduledEndAt: null,
        };

        // Thời điểm bắt đầu
        if (startMode === "delay") {
            body.scheduledDelay = positiveSeconds(
                delaySeconds,
                "Thời gian trì hoãn"
            );
        }

        if (startMode === "at") {
            body.scheduledStartAt = toUnixSeconds(startDate);
        }

        // Thời điểm kết thúc
        if (endMode === "duration") {
            body.duration = positiveSeconds(
                durationSeconds,
                "Thời lượng"
            );
        }

        if (endMode === "at") {
            if (startMode === "now") {
                throw new Error(
                    "Khi dùng thời điểm kết thúc, " +
                    "hãy chọn thời điểm bắt đầu cụ thể."
                );
            }

            body.scheduledEndAt = toUnixSeconds(endDate);
        }

        // Không tạo Schedule cho ON/OFF tức thời.
        if (startMode === "now" && endMode === "none") {
            throw new Error(
                "Lệnh tức thời không có thời lượng. " +
                "Hãy dùng chức năng Bật/Tắt thủ công."
            );
        }

        return body;
    }


    // 6. GỬI YÊU CẦU TẠO SCHEDULE
    async function handleSubmit(event) {
        event.preventDefault();

        if (!deviceId || busy || unknown) return;

        setBusy(true);
        setError("");
        setMessage("");

        try {
            const body = buildSchedule();

            // Frontend gửi qua NLP Server.
            // NLP gửi MQTT, nhận ACK rồi xác nhận Registry.
            const result = await createDeviceSchedule(
                Number(deviceId),
                body
            );

            setMessage(
                `MCU đã tiếp nhận lịch. ` +
                `Registry lưu Schedule #${result.schedule.id}.`
            );

            refreshSchedules();
        }
        catch (err) {
            setError(err.message);

            if (err.state === "unknown") {
                setUnknown(true);
            }
        }
        finally {
            setBusy(false);
        }
    }


    // 7. CHỈ CHỌN DEVICE ĐÃ LIÊN KẾT
    // Đây là SyncStatus của Device, không phải Schedule.
    const readyDevices = (devices || []).filter(
        device =>
            device.gpio !== null &&
            device.syncStatus === "synced"
    );


    // 8. TẢI SCHEDULE CỦA CÁC DEVICE
    useEffect(() => {
        let cancelled = false;

        async function loadSchedules() {
            if (!devices || devices.length === 0) {
                setScheduleRows([]);
                return;
            }

            setLoadingSchedules(true);
            setScheduleRows([]);

            try {
                const rows = await Promise.all(
                    devices.map(async (device) => ({
                        device,
                        schedule: await getDeviceSchedule(device.id),
                    }))
                );

                if (!cancelled) {
                    setScheduleRows(
                        rows.filter(row => row.schedule !== null)
                    );
                }
            }
            catch (err) {
                if (!cancelled) {
                    setError(err.message);
                }
            }
            finally {
                if (!cancelled) {
                    setLoadingSchedules(false);
                }
            }
        }

        loadSchedules();

        return () => {
            cancelled = true;
        };
    }, [devices, scheduleVersion]);


    // 9. LÀM MỚI DANH SÁCH SCHEDULE
    function refreshSchedules() {
        setScheduleVersion(value => value + 1);
    }


    // 10. HỦY SCHEDULE
    async function handleCancelSchedule(row) {
        const device = row.device;

        const confirmed = window.confirm(
            `Hủy Schedule #${row.schedule.id} của ` +
            `"${device.deviceName || `Device #${device.id}`}"?`
        );

        if (!confirmed) return;

        setCancelBusyId(device.id);
        setError("");
        setMessage("");

        try {
            // Hủy qua NLP Server, không xóa DB trực tiếp.
            const result = await cancelDeviceSchedule(device.id);

            setMessage(result.message);
            refreshSchedules();
        }
        catch (err) {
            if (err.state === "unknown") {
                setUnknownCancelIds(old => [
                    ...new Set([...old, device.id])
                ]);
            }

            setError(err.message);
        }
        finally {
            setCancelBusyId(null);
        }
    }


    // 11. HIỂN THỊ UNIX TIMESTAMP
    function formatScheduleTime(seconds) {
        if (seconds == null) return "—";

        return new Date(seconds * 1000)
            .toLocaleString("vi-VN");
    }


    // 12. GIAO DIỆN
    return (
        <div className="mt-6 rounded-lg border border-gray-200 p-4">

            <h3 className="mb-4 text-lg font-semibold">
                Tạo lịch điều khiển thủ công
            </h3>

            {/* THÔNG BÁO LỖI */}
            {error && (
                <p role="alert" className="mb-3 text-sm text-red-600">
                    {error}
                </p>
            )}

            {/* THÔNG BÁO THÀNH CÔNG */}
            {message && (
                <p role="status" className="mb-3 text-sm text-green-700">
                    {message}
                </p>
            )}

            {/* KẾT QUẢ TẠO LỊCH CHƯA XÁC ĐỊNH */}
            {unknown && (
                <p className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                    Kết quả tạo lịch chưa xác định.
                    Cần đối soát Registry và MCU trước khi thử lại.
                </p>
            )}

            {/* FORM TẠO SCHEDULE */}
            {readyDevices.length === 0 ? (
                <p className="text-sm text-gray-500">
                    Chưa có Device đã liên kết và đồng bộ để tạo lịch.
                </p>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-4">

                    {/* DEVICE VÀ ACTION */}
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label className="block text-sm">
                            Device

                            <select
                                value={deviceId}
                                onChange={e => setDeviceId(e.target.value)}
                                disabled={busy || unknown}
                                className="mt-1 w-full rounded-lg border p-2"
                            >
                                <option value="">
                                    Chọn Device
                                </option>

                                {readyDevices.map(device => (
                                    <option
                                        key={device.id}
                                        value={device.id}
                                    >
                                        {device.deviceName ||
                                            `Device #${device.id}`}
                                        {" — GPIO "}
                                        {device.gpio}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label className="block text-sm">
                            Hành động

                            <select
                                value={action}
                                onChange={e => setAction(e.target.value)}
                                disabled={busy || unknown}
                                className="mt-1 w-full rounded-lg border p-2"
                            >
                                <option value="on">Bật (ON)</option>
                                <option value="off">Tắt (OFF)</option>
                            </select>
                        </label>
                    </div>

                    {/* THỜI ĐIỂM BẮT ĐẦU */}
                    <div className="rounded-lg border p-3">
                        <h4 className="mb-3 font-medium">
                            Thời điểm bắt đầu
                        </h4>

                        <select
                            value={startMode}
                            onChange={e => setStartMode(e.target.value)}
                            disabled={busy || unknown}
                            className="w-full rounded-lg border p-2"
                        >
                            <option value="now">
                                Ngay bây giờ
                            </option>

                            <option value="delay">
                                Sau một khoảng thời gian
                            </option>

                            <option value="at">
                                Vào ngày giờ cụ thể
                            </option>
                        </select>

                        {startMode === "delay" && (
                            <label className="mt-3 block text-sm">
                                Trì hoãn (giây)

                                <input
                                    type="number"
                                    min="1"
                                    step="1"
                                    value={delaySeconds}
                                    onChange={e =>
                                        setDelaySeconds(e.target.value)
                                    }
                                    disabled={busy || unknown}
                                    className="mt-1 w-full rounded-lg border p-2"
                                />
                            </label>
                        )}

                        {startMode === "at" && (
                            <label className="mt-3 block text-sm">
                                Ngày giờ bắt đầu

                                <input
                                    type="datetime-local"
                                    value={startDate}
                                    onChange={e =>
                                        setStartDate(e.target.value)
                                    }
                                    disabled={busy || unknown}
                                    className="mt-1 w-full rounded-lg border p-2"
                                />
                            </label>
                        )}
                    </div>

                    {/* THỜI ĐIỂM KẾT THÚC */}
                    <div className="rounded-lg border p-3">
                        <h4 className="mb-3 font-medium">
                            Thời điểm kết thúc
                        </h4>

                        <select
                            value={endMode}
                            onChange={e => setEndMode(e.target.value)}
                            disabled={busy || unknown}
                            className="w-full rounded-lg border p-2"
                        >
                            <option value="none">
                                Không đặt thời điểm kết thúc
                            </option>

                            <option value="duration">
                                Duy trì trong một khoảng thời gian
                            </option>

                            <option value="at">
                                Kết thúc vào ngày giờ cụ thể
                            </option>
                        </select>

                        {endMode === "duration" && (
                            <label className="mt-3 block text-sm">
                                Thời lượng (giây)

                                <input
                                    type="number"
                                    min="1"
                                    step="1"
                                    value={durationSeconds}
                                    onChange={e =>
                                        setDurationSeconds(e.target.value)
                                    }
                                    disabled={busy || unknown}
                                    className="mt-1 w-full rounded-lg border p-2"
                                />
                            </label>
                        )}

                        {endMode === "at" && (
                            <label className="mt-3 block text-sm">
                                Ngày giờ kết thúc

                                <input
                                    type="datetime-local"
                                    value={endDate}
                                    onChange={e =>
                                        setEndDate(e.target.value)
                                    }
                                    disabled={busy || unknown}
                                    className="mt-1 w-full rounded-lg border p-2"
                                />
                            </label>
                        )}
                    </div>

                    {/* NÚT TẠO SCHEDULE */}
                    <button
                        type="submit"
                        disabled={!deviceId || busy || unknown}
                        className="rounded-lg bg-blue-600 px-5 py-2 text-white disabled:opacity-50"
                    >
                        {busy ? "Đang tạo lịch..." : "Tạo lịch"}
                    </button>
                </form>
            )}


            {/* DANH SÁCH SCHEDULE */}
            <div className="mt-8 border-t border-gray-200 pt-5">

                <div className="mb-4 flex items-center justify-between gap-3">
                    <h3 className="font-semibold">
                        Schedule hiện tại
                    </h3>

                    <button
                        type="button"
                        disabled={
                            loadingSchedules ||
                            cancelBusyId !== null
                        }
                        onClick={refreshSchedules}
                        className="rounded-lg border px-3 py-2 text-sm disabled:opacity-50"
                    >
                        Làm mới
                    </button>
                </div>

                {loadingSchedules ? (
                    <p className="text-sm text-gray-500">
                        Đang tải Schedule...
                    </p>
                ) : scheduleRows.length === 0 ? (
                    <p className="text-sm text-gray-500">
                        Các Device của MCU này chưa có Schedule.
                    </p>
                ) : (
                    <div className="space-y-3">
                        {scheduleRows.map(({ device, schedule }) => (
                            <div
                                key={schedule.id}
                                className="rounded-lg border border-gray-200 p-4"
                            >
                                {/* TÊN DEVICE VÀ THỜI HẠN */}
                                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                        <p className="font-semibold">
                                            {device.deviceName ||
                                                `Device #${device.id}`}
                                        </p>

                                        <p className="text-xs text-gray-500">
                                            Schedule #{schedule.id}
                                            {" · GPIO "}
                                            {device.gpio}
                                        </p>
                                    </div>

                                    <span className="rounded-lg bg-gray-100 px-3 py-1 text-xs">
                                        {schedule.isExpired
                                            ? "Đã tới thời hạn cấu hình"
                                            : "Chưa hết hạn"}
                                    </span>
                                </div>

                                {/* THÔNG TIN SCHEDULE */}
                                <div className="grid gap-2 text-sm sm:grid-cols-2">
                                    <p>
                                        <strong>Hành động:</strong>{" "}
                                        {schedule.action === "on"
                                            ? "Bật"
                                            : "Tắt"}
                                    </p>

                                    <p>
                                        <strong>Trì hoãn:</strong>{" "}
                                        {schedule.scheduledDelay == null
                                            ? "—"
                                            : `${schedule.scheduledDelay} giây`}
                                    </p>

                                    <p>
                                        <strong>Thời lượng:</strong>{" "}
                                        {schedule.duration == null
                                            ? "—"
                                            : `${schedule.duration} giây`}
                                    </p>

                                    <p>
                                        <strong>Bắt đầu lúc:</strong>{" "}
                                        {formatScheduleTime(
                                            schedule.scheduledStartAt
                                        )}
                                    </p>

                                    <p>
                                        <strong>Kết thúc lúc:</strong>{" "}
                                        {formatScheduleTime(
                                            schedule.scheduledEndAt
                                        )}
                                    </p>

                                    <p>
                                        <strong>Thời điểm hết hạn:</strong>{" "}
                                        {formatScheduleTime(
                                            schedule.expiresAt
                                        )}
                                    </p>
                                </div>

                                <p className="mt-3 text-xs text-gray-500">
                                    Thời hạn chỉ được tính theo cấu hình.
                                    Không xác nhận MCU đã thực thi lịch.
                                </p>

                                {/* KẾT QUẢ HỦY CHƯA XÁC ĐỊNH */}
                                {unknownCancelIds.includes(device.id) && (
                                    <p className="mt-3 text-sm text-amber-700">
                                        Kết quả hủy chưa xác định.
                                        Cần đối soát trước khi thử lại.
                                    </p>
                                )}

                                {/* HỦY SCHEDULE QUA NLP SERVER */}
                                <button
                                    type="button"
                                    disabled={
                                        busy ||
                                        unknown ||
                                        cancelBusyId !== null ||
                                        unknownCancelIds.includes(device.id)
                                    }
                                    onClick={() =>
                                        handleCancelSchedule({
                                            device,
                                            schedule,
                                        })
                                    }
                                    className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm text-white disabled:opacity-50"
                                >
                                    {cancelBusyId === device.id
                                        ? "Đang hủy..."
                                        : "Hủy Schedule"}
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
