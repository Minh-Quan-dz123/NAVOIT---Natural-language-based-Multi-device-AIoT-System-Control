
import { useEffect, useState } from "react";
import { Link } from "react-router";

import {
    getMyMicrocontrollers,
    getMyMicrocontrollerDevices,
} from "../api/microcontrollerApi";

export default function MicrocontrollersPage() 
{
    const [microcontrollers, setMicrocontrollers] = useState([]);
    const [selectedId, setSelectedId] = useState(null);

    const [devices, setDevices] = useState([]);

    const [loading, setLoading] = useState(true);
    const [devicesLoading, setDevicesLoading] = useState(false);
    const [error, setError] = useState("");

    // 1. LẤY DANH SÁCH MCU CỦA USER
    useEffect(() => {
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
        return () => {cancelled = true; };
    }, []);

    // 2. LẤY DEVICE KHI CHỌN MCU
    useEffect(() => {
        if (selectedId === null) return;

        let cancelled = false;

        async function loadDevices() 
        {
            setDevices([]);
            setDevicesLoading(true);
            setError("");

            try 
            {
                const data = await getMyMicrocontrollerDevices(selectedId);
                if (!cancelled) setDevices(data);
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
        return () => { cancelled = true;};
    }, [selectedId]);

    // 3. GIAO DIỆN
    return (
        <div className="min-h-screen bg-gray-100 px-4 py-8">
            <div className="mx-auto max-w-5xl space-y-6">

                {/* Header */}
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            Vi điều khiển của tôi
                        </h1>

                        <p className="mt-1 text-sm text-gray-500">
                            Các MCU đã được hệ thống cấp cho tài khoản
                        </p>
                    </div>

                    <Link
                        to="/account"
                        className="rounded-lg bg-white px-4 py-2 text-sm shadow-sm hover:bg-gray-50"
                    >
                        Về tài khoản
                    </Link>
                </div>

                {/* Thông báo lỗi */}
                {error && (
                    <p
                        role="alert"
                        className="rounded-lg bg-red-50 p-4 text-sm text-red-700"
                    >
                        {error}
                    </p>
                )}

                {/* Danh sách MCU */}
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
                        <div className="py-8 text-center">
                            <p className="text-gray-600">
                                Bạn chưa được cấp vi điều khiển nào.
                            </p>

                            <p className="mt-2 text-sm text-gray-400">
                                Vui lòng liên hệ quản trị viên để được cấp MCU.
                            </p>
                        </div>
                    ) : (
                        <div className="grid gap-4 sm:grid-cols-2">
                            {microcontrollers.map((item) => (
                                <div
                                    key={item.id}
                                    className="rounded-xl border border-gray-200 p-4"
                                >
                                    <div className="mb-4 flex items-start justify-between gap-3">
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
                                                ? new Date(
                                                    item.lastSeenAt
                                                ).toLocaleString("vi-VN")
                                                : "Chưa có dữ liệu"}
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={() => {setSelectedId(item.id);}}
                                        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
                                    >
                                        Xem Device
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </section>

                {/* Device thuộc MCU được chọn */}
                {selectedId !== null && (
                    <section className="rounded-xl bg-white p-6 shadow-sm">
                        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold">
                                Device thuộc MCU #{selectedId}
                            </h2>

                            <button
                                type="button"
                                onClick={() => {
                                    setSelectedId(null);
                                    setDevices([]);
                                }}
                                className="text-sm text-gray-500 hover:text-gray-800"
                            >
                                Đóng
                            </button>
                        </div>

                        {devicesLoading ? (
                            <p className="text-gray-500">
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
                                            <th className="px-3 py-3">
                                                Device
                                            </th>
                                            <th className="px-3 py-3">
                                                GPIO
                                            </th>
                                            <th className="px-3 py-3">
                                                Trạng thái
                                            </th>
                                            <th className="px-3 py-3">
                                                Đồng bộ
                                            </th>
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
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>
                )}

            </div>
        </div>
    );
}
