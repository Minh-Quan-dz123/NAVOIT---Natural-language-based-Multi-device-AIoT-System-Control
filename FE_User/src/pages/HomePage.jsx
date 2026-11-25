import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getMyDevices } from "../api/deviceApi";
import { getMyMicrocontrollers } from "../api/microcontrollerApi";
import {
    refreshAllDeviceStatuses,
    formatRefreshResult,
} from "../api/deviceRefreshApi";
import NaturalCommandControls from "../components/NaturalCommandControls";

// component con, có nhiệm vụ hiển thị màu + giá trị trạng thái cho đẹp
// trả về 1 thẻ span hiển thị trạng thái với màu sắc tương ứng.
function Badge({ value }) 
{
    // 1. chuẩn hóa giá trị value về String và viết thường
    const key = String(value || "unknown").toLowerCase();

    // màu nền xanh rất nhạt + màu chữ xám xanh đậm hơn
    let type = "ui-badge-neutral"; // tên class CSS trong index.css/ app.css

    // nếu value chứa các từ là kiểu ý nghĩa <=> đã kết nối
    if (["on", "online", "connected", "synced"].includes(key)) 
    {
        type = "ui-badge-green"; 
    }

    // nếu value chứa các từ là kiểu ý nghĩa <=> chưa kết nối
    if (["off", "offline", "disconnected", "out_of_sync", "failed"].includes(key)) 
    {
        type = "ui-badge-red";
    }

    return (
        <span className={`ui-badge ${type}`}>
            {value || "Không rõ"}
        </span>
    );
}

export default function HomePage() 
{
    // 1. quản lý hiển thị các thông tin devices và MCU
    const [devices, setDevices] = useState([]);
    const [mcus, setMcus] = useState([]);

    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    // 1. hàm call api để lấy devices và MCU
    async function reload() 
    {
        // call api
        const [deviceList, mcuList] = await Promise.all([
            getMyDevices(),
            getMyMicrocontrollers(),
        ]);

        setDevices(deviceList);
        setMcus(mcuList);
    }

    // 2. khi vào pages này cái thì call api để lấy thông tin luôn
    useEffect(() => {
        let active = true;

        async function load() 
        {
            // call api lấy thông tin
            try 
            {
                const [deviceList, mcuList] = await Promise.all([
                    getMyDevices(),
                    getMyMicrocontrollers(),
                ]);

                if (!active) return;

                setDevices(deviceList);
                setMcus(mcuList);
            } 
            catch (err) 
            {
                if (active) setError(err.message);
            } 
            finally 
            {
                if (active) setLoading(false);
            }

            // Giữ cơ chế tự làm mới trạng thái khi vào trang chính.
            try 
            {   // call api gọi hàm đồng độ trạng thái, trả về thông tin từng mcu cùng danh sách id của device khớp và 
                // mismatchedDeviceIds: danh sách id của device có trên server nhưng esp ko có hoặc sai id
                // unknownGpios: danh sách id của device ko có trên server mà mcu lại có
                const result = await refreshAllDeviceStatuses();
                const deviceList = await getMyDevices(); // lấy devices lại từ đầu

                if (!active) return;

                setDevices(deviceList);

                const refreshText = formatRefreshResult(result);

                if (result.state === "success" || result.state === "empty") {
                    setMessage(refreshText);
                } else {
                    setError(refreshText);
                }
            } 
            catch (err) 
            {
                if (active) 
                {
                    setError(`Chưa làm mới được trạng thái: ${err.message}`);
                }
            }
        }

        load();

        return () => {active = false;};
    }, []);

    // 3. định nghĩa hàm refresh để bấm nút
    async function handleRefresh() 
    {
        if (refreshing) return;

        setRefreshing(true);
        setError("");
        setMessage("");

        try {
            const result = await refreshAllDeviceStatuses();
            await reload();
            const refreshText = formatRefreshResult(result);

            if (result.state === "success" || result.state === "empty") {
                setMessage(refreshText);
            } 
            else {
                setError(refreshText);
            }
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setRefreshing(false);
        }
    }

    // mỗi lần render, tạo 1 biến filtered là danh sách device sau khi search
    const filtered = devices.filter(device => {
        const keyword = search.toLowerCase().trim();

        return [
            device.deviceName,
            device.id,
            device.deviceTypeName,
            device.microcontrollerType,
        ].some(value =>String(value ?? "").toLowerCase().includes(keyword));
    });

    // trả về số lượng devices đã đc liên kết
    const linked = devices.filter(device => device.microcontrollerId != null).length;

    return (
        <div className="space-y-6">
            
            {/* 1. vùng trên cùng hiển thị các title */}
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <p className="ui-eyebrow">OVERVIEW</p>
                    <h1 className="ui-title">Thiết bị của tôi</h1>
                    <p className="ui-subtitle">
                        Theo dõi thiết bị, MCU và gửi lệnh bằng ngôn ngữ tự nhiên.
                    </p>
                </div>

                <div className="flex flex-wrap gap-2">
                    <Link to="/mcu" className="ui-btn ui-btn-outline">
                        Danh sách MCU
                    </Link>

                    <button
                        type="button"
                        onClick={handleRefresh}
                        disabled={refreshing}
                        className="ui-btn ui-btn-primary"
                    >
                        {refreshing
                            ? "Đang đồng bộ..."
                            : "↻ Làm mới trạng thái"}
                    </button>
                </div>
            </div>

            {error && (
                <p role="alert" className="ui-alert-error">
                    {error}
                </p>
            )}

            {message && (
                <p role="status" className="ui-alert-info">
                    {message}
                </p>
            )}

            {/* vùng 2. hiển thị tổng thiết bị, thiết bị đã liên kết vs vi điều khiển và số lượng vi điều khiển */}
            <div className="grid gap-4 sm:grid-cols-3">
                <div className="ui-card ui-stat">
                    <span>Tổng thiết bị</span>
                    <strong>{devices.length}</strong>
                    <small>Device trong Registry</small>
                </div>

                <div className="ui-card ui-stat">
                    <span>Đã liên kết</span>
                    <strong>{linked}</strong>
                    <small>Đang gắn với MCU</small>
                </div>

                <div className="ui-card ui-stat">
                    <span>Vi điều khiển</span>
                    <strong>{mcus.length}</strong>
                    <small>MCU thuộc tài khoản</small>
                </div>
            </div>

            {/* vùng 3. hiển thị danh sách thiết bị dưới dạng bảng, tên, id, loại mcu, gpio, trạng thái, đồng bộ */}
            <section className="ui-card overflow-hidden">
                <div className="ui-section-header">
                    <div>
                        <h2 className="ui-section-title">
                            Danh sách thiết bị
                        </h2>
                        <p className="ui-section-description">
                            Bấm vào thiết bị để xem thông tin chi tiết.
                        </p>
                    </div>

                    <Link to="/devices" className="ui-btn ui-btn-outline">
                        Quản lý Device
                    </Link>
                </div>

                <div className="p-5">
                    <input
                        className="ui-input max-w-md"
                        type="search"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Tìm tên, ID, loại thiết bị hoặc MCU..."
                    />
                </div>

                <div className="overflow-x-auto">
                    <table className="ui-table min-w-[720px]">
                        <thead>
                            <tr>
                                <th>Thiết bị</th>
                                <th>ID</th>
                                <th>Loại MCU</th>
                                <th>GPIO</th>
                                <th>Trạng thái</th>
                                <th>Đồng bộ</th>
                                <th></th>
                            </tr>
                        </thead>

                        <tbody>
                            {filtered.map(device => (
                                <tr key={device.id}>
                                    <td>
                                        <Link
                                            className="ui-table-link"
                                            to={`/device/${device.id}`}
                                        >
                                            {device.deviceName ||
                                                `Device #${device.id}`}
                                        </Link>

                                        <small className="mt-1 block text-[#83968a]">
                                            {device.deviceTypeName || "—"}
                                        </small>
                                    </td>

                                    <td className="font-mono text-xs">
                                        #{device.id}
                                    </td>

                                    <td>
                                        {device.microcontrollerType ||
                                            "Chưa liên kết"}
                                    </td>

                                    <td className="font-mono">
                                        {device.gpio ?? "—"}
                                    </td>

                                    <td>
                                        <Badge value={device.currentStatus} />
                                    </td>

                                    <td>
                                        <Badge value={device.syncStatus} />
                                    </td>

                                    <td>
                                        <Link
                                            to={`/device/${device.id}`}
                                            className="ui-btn ui-btn-quiet"
                                        >
                                            Chi tiết →
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {!loading && filtered.length === 0 && (
                        <p className="p-8 text-center text-sm text-[#74877b]">
                            Không tìm thấy thiết bị.
                        </p>
                    )}

                    {loading && (
                        <p className="p-8 text-center text-sm text-[#74877b]">
                            Đang tải thiết bị...
                        </p>
                    )}
                </div>
            </section>

            {/* vùng 4. lấy từ component khác */}
            <NaturalCommandControls onChanged={reload} />
        </div>
    );
}