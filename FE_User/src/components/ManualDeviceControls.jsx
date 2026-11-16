import { useState } from "react";
import { controlDevice } from "../api/deviceControlApi";

export default function ManualDeviceControls({devices,onChanged,}) 
{
    const [busyId, setBusyId] = useState(null);
    const [unknownIds, setUnknownIds] = useState([]);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    async function handleControl(device, action) 
    {
        setBusyId(device.id);
        setMessage("");
        setError("");

        let succeeded = false;

        try {
            // 1. Gửi lệnh tới NLP Server
            await controlDevice(device.id, action);
            succeeded = true;

            // 2. Tải trạng thái mới từ Registry
            await onChanged();

            setMessage(
                `Đã ${action === "ON" ? "bật" : "tắt"} ` +
                `${device.deviceName || `Device #${device.id}`}.`
            );

        } 
        catch (err) 
        {
            if (err.state === "unknown") 
            {
                setUnknownIds(old =>[...new Set([...old, device.id])]);  
            }

            setError(
                succeeded
                    ? "Đã điều khiển thành công, nhưng chưa tải lại " +
                      "được trạng thái từ Registry."
                    : err.message
            );
        } finally {
            setBusyId(null);
        }
    }

    if (!devices || devices.length === 0) {
        return null;
    }

    return (
        <div className="mt-6 rounded-lg border border-gray-200 p-4">
            <h3 className="mb-4 font-semibold">
                Điều khiển Device thủ công
            </h3>

            {error && (
                <p role="alert" className="mb-3 text-sm text-red-600">
                    {error}
                </p>
            )}

            {message && (
                <p role="status" className="mb-3 text-sm text-green-700">
                    {message}
                </p>
            )}

            <div className="space-y-3">
                {devices.map((device) => {
                    const blocked =
                        busyId !== null ||
                        device.syncStatus !== "synced" ||
                        unknownIds.includes(device.id);

                    return (
                        <div
                            key={device.id}
                            className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-gray-50 p-3"
                        >
                            <div>
                                <p className="font-medium">
                                    {device.deviceName ||`Device #${device.id}`}
                                        
                                </p>

                                <p className="text-sm text-gray-500">
                                    GPIO {device.gpio ?? "—"} ·
                                    Trạng thái: {device.currentStatus}
                                </p>

                                {unknownIds.includes(device.id) && (
                                    <p className="text-xs text-amber-700">
                                        Kết quả chưa xác định.
                                        Cần đối soát trước khi gửi lệnh mới.
                                    </p>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    disabled={blocked}
                                    onClick={() =>handleControl(device, "ON")}  
                                    className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white disabled:opacity-40"
                                >
                                    Bật
                                </button>

                                <button
                                    type="button"
                                    disabled={blocked}
                                    onClick={() =>handleControl(device, "OFF")}
                                    className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white disabled:opacity-40"
                                >
                                    Tắt
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
