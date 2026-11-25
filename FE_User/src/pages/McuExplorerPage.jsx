import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
    getMyMicrocontrollers,
    getMyMicrocontrollerById,
    getMyMicrocontrollerDevices,
} from "../api/microcontrollerApi";

const fieldLabels = {
    id: "MCU ID",
    type: "Loại MCU",
    macAddress: "MAC Address",
    connectionStatus: "Trạng thái kết nối",
    deviceCount: "Số thiết bị",
    lastSeenAt: "Kết nối gần nhất",
    userId: "User ID",
};

function displayValue(value) 
{
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    if (typeof value === "object") {
        return JSON.stringify(value);
    }

    return String(value);
}

export default function McuExplorerPage() 
{
    const [searchParams, setSearchParams] = useSearchParams();
    const selectedId = searchParams.get("selected");

    const [mcus, setMcus] = useState([]);
    const [mcu, setMcu] = useState(null);
    const [devices, setDevices] = useState([]);
    const [search, setSearch] = useState("");

    const [loading, setLoading] = useState(true);
    const [detailLoading, setDetailLoading] = useState(false);

    const [error, setError] = useState("");
    const [detailError, setDetailError] = useState("");

    // 1. Lấy danh sách MCU
    useEffect(() => {
        let active = true;

        async function loadList() 
        {
            try 
            {
                const list = await getMyMicrocontrollers();
                if (active) setMcus(list);
            } 
            catch (err) 
            {
                if (active) setError(err.message);
            } 
            finally 
            {
                if (active) setLoading(false);
            }
        }

        loadList();

        return () => {active = false;};
    }, []);

    // 2. Lấy thông tin MCU đang chọn
    useEffect(() => {
        if (!selectedId) 
        {
            setMcu(null);
            setDevices([]);
            setDetailError("");
            return;
        }

        let active = true;

        async function loadDetail() 
        {
            setDetailLoading(true);
            setMcu(null);
            setDevices([]);
            setDetailError("");

            try 
            {
                const [detail, deviceList] = await Promise.all([
                    getMyMicrocontrollerById(selectedId),
                    getMyMicrocontrollerDevices(selectedId),
                ]);

                if (!active) return;

                setMcu(detail);
                setDevices(deviceList);
            } 
            catch (err) 
            {
                if (active) 
                {
                    setDetailError(err.message);
                }
            } 
            finally 
            {
                if (active) 
                {
                    setDetailLoading(false);
                }
            }
        }

        loadDetail();

        return () => {active = false;};
    }, [selectedId]);


    const filtered = mcus.filter(item => {
        const keyword = search.trim().toLowerCase();

        return [item.id, item.type, item.macAddress].some(value =>
            String(value ?? "").toLowerCase().includes(keyword)
        );
    });

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <p className="ui-eyebrow">MICROCONTROLLERS</p>
                    <h1 className="ui-title">
                        Danh sách vi điều khiển
                    </h1>
                    <p className="ui-subtitle">
                        Chọn MCU bên trái để xem chi tiết và các Device bên phải.
                    </p>
                </div>

                <div className="flex gap-2">
                    <Link to="/" className="ui-btn ui-btn-outline">
                        ⌂ Về Home
                    </Link>

                    <Link
                        to="/microcontrollers"
                        className="ui-btn ui-btn-primary"
                    >
                        Quản lý liên kết
                    </Link>
                </div>
            </div>

            {error && (
                <p role="alert" className="ui-alert-error">
                    {error}
                </p>
            )}

            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,1fr)]">
                {/* BẢNG MCU BÊN TRÁI */}
                <section className="ui-card overflow-hidden">
                    <div className="ui-section-header">
                        <div>
                            <h2 className="ui-section-title">
                                Vi điều khiển của tôi
                            </h2>

                            <p className="ui-section-description">
                                {mcus.length} vi điều khiển trong Registry
                            </p>
                        </div>
                    </div>

                    <div className="p-5">
                        <input
                            className="ui-input"
                            type="search"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Tìm theo MCU ID, loại hoặc MAC..."
                        />
                    </div>

                    <div className="overflow-x-auto">
                        <table className="ui-table min-w-[480px]">
                            <thead>
                                <tr>
                                    <th>Loại / ID</th>
                                    <th>MAC Address</th>
                                    <th>Thiết bị</th>
                                    <th></th>
                                </tr>
                            </thead>

                            <tbody>
                                {filtered.map(item => (
                                    <tr
                                        key={item.id}
                                        className={ String(selectedId) === String(item.id) ? "ui-table-selected" : "" }  
                                    >
                                        <td>
                                            <button
                                                type="button"
                                                className="ui-table-link text-left"
                                                onClick={() => setSearchParams({selected: String(item.id),})} 
                                            >
                                                {item.type || "MCU"}

                                                <small className="mt-1 block text-[#87978c]">
                                                    ID #{item.id}
                                                </small>
                                            </button>
                                        </td>

                                        <td className="font-mono text-xs">
                                            {item.macAddress}
                                        </td>

                                        <td>
                                            {item.deviceCount ?? "—"}
                                        </td>

                                        <td>
                                            <button
                                                type="button"
                                                className="ui-btn ui-btn-quiet"
                                                onClick={() =>setSearchParams({selected: String(item.id),}) }
                                            >
                                                Xem →
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        {loading && (
                            <p className="p-6 text-sm text-[#7d9083]">
                                Đang tải MCU...
                            </p>
                        )}

                        {!loading && filtered.length === 0 && (
                            <p className="p-6 text-sm text-[#7d9083]">
                                Không tìm thấy MCU.
                            </p>
                        )}
                    </div>
                </section>

                {/* CHI TIẾT MCU BÊN PHẢI */}
                <aside className="ui-card p-6">
                    {!selectedId && (
                        <div className="py-16 text-center">
                            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-[#e9f8ef] text-2xl text-[#278954]">
                                ▤
                            </div>

                            <h2 className="ui-section-title">
                                Chọn một vi điều khiển
                            </h2>

                            <p className="ui-section-description mt-2">
                                Chi tiết MCU và danh sách thiết bị sẽ xuất hiện tại đây.
                            </p>
                        </div>
                    )}

                    {detailLoading && (
                        <p className="text-sm text-[#7c8d83]">
                            Đang tải thông tin MCU...
                        </p>
                    )}

                    {detailError && (
                        <p role="alert" className="ui-alert-error">
                            {detailError}
                        </p>
                    )}

                    {mcu && !detailLoading && (
                        <>
                            <p className="ui-eyebrow">
                                MCU DETAIL · #{mcu.id}
                            </p>

                            <h2 className="mt-2 text-xl font-semibold text-[#1f3a2b]">
                                {mcu.type || "Vi điều khiển"}
                            </h2>

                            <dl className="mt-5 grid gap-2 sm:grid-cols-2">
                                {Object.entries(mcu).map(([key, value]) => (
                                    <div
                                        key={key}
                                        className="border-b border-[#edf1ee] py-2"
                                    >
                                        <dt className="text-xs text-[#7d9083]">
                                            {fieldLabels[key] || key}
                                        </dt>

                                        <dd className="mt-1 break-words text-sm font-medium">
                                            {displayValue(value)}
                                        </dd>
                                    </div>
                                ))}
                            </dl>

                            <div className="mt-6 border-t border-[#e4ece5] pt-5">
                                <div className="flex items-center justify-between gap-2">
                                    <h3 className="ui-section-title">
                                        Thiết bị đang liên kết
                                    </h3>

                                    <span className="ui-badge ui-badge-green">
                                        {devices.length}
                                    </span>
                                </div>

                                <div className="mt-4 space-y-2">
                                    {devices.map(device => (
                                        <Link
                                            key={device.id}
                                            to={`/device/${device.id}`}
                                            className="ui-device-link"
                                        >
                                            <span>
                                                <strong className="block text-sm">
                                                    {device.deviceName ||  `Device #${device.id}`}
                                                </strong>

                                                <small className="mt-1 block text-[#84968a]">
                                                    ID #{device.id} · GPIO{" "}
                                                    {device.gpio ?? "—"}
                                                </small>
                                            </span>

                                            <span className="text-[#2a9960]">
                                                →
                                            </span>
                                        </Link>
                                    ))}

                                    {devices.length === 0 && (
                                        <p className="text-sm text-[#829487]">
                                            MCU chưa liên kết thiết bị.
                                        </p>
                                    )}
                                </div>
                            </div>

                            <Link
                                to="/microcontrollers"
                                className="ui-btn ui-btn-primary mt-6"
                            >
                                Liên kết / Đồng bộ MCU
                            </Link>
                        </>
                    )}
                </aside>
            </div>
        </div>
    );
}