import { useState } from "react";

import { executeNaturalCommand } from "../api/naturalCommandApi";


export default function NaturalCommandControls({ onChanged }) 
{
    const [text, setText] = useState("");
    const [busy, setBusy] = useState(false);

    const [result, setResult] = useState(null);
    const [error, setError] = useState("");
    const [candidates, setCandidates] = useState([]);
    const [unknownResult, setUnknownResult] = useState(false);


    // 1. GỬI CÂU LỆNH
    async function handleSubmit(event) 
    {
        event.preventDefault();

        const command = text.trim();

        if (!command || busy || unknownResult) return;

        setBusy(true);
        setResult(null);
        setError("");
        setCandidates([]);

        try 
        {
            const data = await executeNaturalCommand(command);

            setResult(data);

            // Làm mới Device và Schedule đang hiển thị.
            if (onChanged) 
            {
                try 
                {
                    await onChanged();
                } 
                catch 
                {
                    setError(
                        "Lệnh đã thực hiện thành công nhưng " +
                        "chưa làm mới được dữ liệu giao diện."
                    );
                }
            }

        } 
        catch (err) 
        {
            setError(err.message);
            setCandidates(err.candidates || []);

            if (err.state === "unknown") setUnknownResult(true);

        } 
        finally 
        {
            setBusy(false);
        }
    }


    // 2. HIỂN THỊ KẾT QUẢ THEO CHỨC NĂNG
    function renderOperationResult() 
    {
        if (!result) return null;

        if (result.operation === "schedule_created") 
        {
            return (
                <div className="space-y-2">
                    <p className="font-semibold text-green-700">
                        ESP32 đã tiếp nhận lịch điều khiển
                    </p>

                    <p>
                        <strong>Schedule ID:</strong>{" "}
                        {result.schedule?.id}
                    </p>

                    <p>
                        <strong>Hành động:</strong>{" "}
                        {result.schedule?.action}
                    </p>

                    <p>
                        <strong>Delay:</strong>{" "}
                        {result.schedule?.scheduledDelay ?? "—"} giây
                    </p>

                    <p>
                        <strong>Duration:</strong>{" "}
                        {result.schedule?.duration ?? "—"} giây
                    </p>

                    <p>
                        <strong>Trạng thái đồng bộ:</strong>{" "}
                        {result.schedule?.syncStatus}
                    </p>
                </div>
            );
        }

        if (result.operation === "schedule_cancelled") 
        {
            return (
                <div className="space-y-2">
                    <p className="font-semibold text-green-700">
                        Đã xác nhận hủy Schedule
                    </p>

                    <p>
                        <strong>Schedule ID:</strong>{" "}
                        {result.scheduleId}
                    </p>

                    <p>{result.message}</p>
                </div>
            );
        }

        return (
            <div>
                <p className="font-semibold text-green-700">
                    Điều khiển ON/OFF thành công
                </p>

                <p className="mt-2">
                    <strong>Trạng thái:</strong>{" "}
                    {result.currentStatus}
                </p>
            </div>
        );
    }


    return (
        <section className="rounded-xl bg-white p-6 shadow-sm">

            <h2 className="mb-2 text-lg font-semibold">
                Điều khiển bằng ngôn ngữ tự nhiên
            </h2>

            <p className="mb-4 text-sm text-gray-500">
                MockPredictor — ON/OFF, tạo và hủy lịch.
                Ví dụ: bật đèn học sau 10 phút,
                hủy lịch đèn học.
            </p>

            {/* FORM NHẬP CÂU LỆNH */}
            <form
                onSubmit={handleSubmit}
                className="flex flex-col gap-3 sm:flex-row"
            >
                <input
                    type="text"
                    value={text}
                    maxLength={500}
                    onChange={e => setText(e.target.value)}
                    disabled={busy || unknownResult}
                    placeholder="Nhập câu lệnh tiếng Việt..."
                    className="min-w-0 flex-1 rounded-lg border px-4 py-3"
                />

                <button
                    type="submit"
                    disabled={!text.trim() || busy || unknownResult}
                    className="rounded-lg bg-blue-600 px-6 py-3 text-white disabled:opacity-50"
                >
                    {busy ? "Đang xử lý..." : "Gửi lệnh"}
                </button>
            </form>

            {/* KẾT QUẢ CHƯA XÁC ĐỊNH */}
            {unknownResult && (
                <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                    Kết quả chưa xác định. Cần đối soát
                    ESP32 với Registry trước khi gửi lệnh mới.
                </p>
            )}

            {/* THÔNG BÁO LỖI */}
            {error && (
                <p
                    role="alert"
                    className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700"
                >
                    {error}
                </p>
            )}

            {/* NHIỀU DEVICE TRÙNG TAG */}
            {candidates.length > 0 && (
                <div className="mt-4 rounded-lg border p-4">
                    <p className="mb-2 font-medium">
                        Có nhiều Device phù hợp:
                    </p>

                    <ul className="list-inside list-disc text-sm">
                        {candidates.map(device => (
                            <li key={device.deviceId}>
                                {device.deviceName ||
                                    `Device #${device.deviceId}`}
                                {" — "}
                                {device.deviceType}
                            </li>
                        ))}
                    </ul>

                    <p className="mt-2 text-sm text-gray-500">
                        Hãy bổ sung Tag vị trí hoặc tên Device.
                    </p>
                </div>
            )}

            {/* KẾT QUẢ THÀNH CÔNG */}
            {result && (
                <div className="mt-5 rounded-lg border p-4 text-sm">

                    <div className="mb-4 space-y-2">
                        <p>
                            <strong>Câu lệnh:</strong>{" "}
                            {result.text}
                        </p>

                        <p>
                            <strong>Predictor:</strong>{" "}
                            {result.predictor}
                        </p>

                        <p>
                            <strong>Intent:</strong>{" "}
                            {result.intent}
                        </p>

                        <p>
                            <strong>Device Tags:</strong>{" "}
                            {result.deviceTags?.join(", ")}
                        </p>

                        <p>
                            <strong>Device:</strong>{" "}
                            {result.device?.deviceName ||
                                `Device #${result.device?.deviceId}`}
                        </p>

                        <p>
                            <strong>MCU:</strong>{" "}
                            #{result.device?.microcontrollerId}
                        </p>

                        <p>
                            <strong>GPIO:</strong>{" "}
                            {result.device?.gpio}
                        </p>
                    </div>

                    <div className="border-t pt-4">
                        {renderOperationResult()}
                    </div>
                </div>
            )}
        </section>
    );
}
