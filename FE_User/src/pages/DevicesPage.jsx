
import { useEffect, useState } from "react";
import { Link } from "react-router";

import {
    getMyDevices,
    createDevice,
    updateDevice,
    deleteDevice,
} from "../api/deviceApi";

import {
    refreshAllDeviceStatuses,
    formatRefreshResult,
} from "../api/deviceRefreshApi";

import { getDeviceTypes } from "../api/deviceTypeApi";

const emptyForm = {
    deviceName: "",
    deviceTypeId: "",
    description: "",
};

export default function DevicesPage() 
{
    // 1. DỮ LIỆU
    const [devices, setDevices] = useState([]);
    const [deviceTypes, setDeviceTypes] = useState([]);

    const [form, setForm] = useState(emptyForm);
    const [editingId, setEditingId] = useState(null);

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const [refreshing, setRefreshing] = useState(false);
    const [refreshMessage, setRefreshMessage] = useState("");
    const [refreshError, setRefreshError] = useState("");

    // Device đang được sửa, nếu có.
    const editingDevice = devices.find((item) => item.id === editingId);

    // Khi đã gắn MCU, Backend không cho đổi tên
    // hoặc loại Device nếu cần đồng bộ firmware.
    const isBound = editingDevice?.microcontrollerId != null;

    const busy = saving || deletingId !== null || refreshing;

    // 2. LẤY DỮ LIỆU BAN ĐẦU
    useEffect(() => {
        let cancelled = false;

        async function loadData() 
        {
            // 1. Tải dữ liệu có sẵn từ Registry.
            try {
                const [deviceData, typeData] = await Promise.all([
                    getMyDevices(),
                    getDeviceTypes(),
                ]);

                if (cancelled) return;

                setDevices(deviceData);
                setDeviceTypes(typeData);
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

            // 2. Tự động hỏi trạng thái MCU
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
            }
            catch (err) 
            {
                if (!cancelled) setRefreshError(err.message);
            }

            // 3. Đọc lại trạng thái từ Registry.
            try {
                const updatedDevices = await getMyDevices();
                if (!cancelled) setDevices(updatedDevices);
            }
            catch (err) {
                if (!cancelled) setRefreshError(err.message);
            }
            finally {
                if (!cancelled) setRefreshing(false);
            }
        }

        loadData();

        return () => {cancelled = true;};
    }, []);


    // Đọc lại danh sách sau khi thao tác.
    async function reloadDevices()
    {
        const data = await getMyDevices();
        setDevices(data);
    }

    // 2.5. refresh thủ công
    async function handleRefreshStatuses() 
    {
        if (refreshing || saving || deletingId !== null) return;

        setRefreshing(true);
        setRefreshMessage("");
        setRefreshError("");

        try {
            const result = await refreshAllDeviceStatuses();

            const message = formatRefreshResult(result);

            if (result.state === "success" || result.state === "empty") {
                setRefreshMessage(message);
            }
            else {
                setRefreshError(message);
            }

            // Lấy trạng thái mới từ PostgreSQL thông qua Registry.
            await reloadDevices();
        }
        catch (err) {
            setRefreshError(err.message);
        }
        finally {
            setRefreshing(false);
        }
    }


    // 3. HÀM HỖ TRỢ FORM
    function updateForm(field, value) 
    {
        setForm((previous) => ({
            ...previous,
            [field]: value,
        }));
    }

    function resetForm() 
    {
        setForm(emptyForm);
        setEditingId(null);
    }

    function clearMessages() 
    {
        setError("");
        setSuccess("");
    }

    // 4. CHỌN DEVICE ĐỂ SỬA
    function handleEdit(device) 
    {
        clearMessages();
        setEditingId(device.id);
        setForm({
            deviceName: device.deviceName || "",
            deviceTypeId: String(device.deviceTypeId),
            description: device.description || "",
        });

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    }

    // 5. THÊM / SỬA DEVICE

    async function handleSubmit(event) 
    {
        event.preventDefault();
        clearMessages();

        const name = form.deviceName.trim();
        const description = form.description.trim();
        const typeId = Number(form.deviceTypeId);

        const isEditing = editingId !== null;

        // Khi chưa gắn MCU, người dùng nhập đầy đủ
        // tên và loại thiết bị.
        if (!isBound && !name) 
        {
            setError("Vui lòng nhập tên thiết bị.");
            return;
        }

        if (!isBound && !typeId) 
        {
            setError("Vui lòng chọn loại thiết bị.");
            return;
        }

        if (name.length > 150) 
        {
            setError("Tên thiết bị không được quá 150 ký tự.");
            return;
        }

        if (description.length > 2000) 
        {
            setError("Mô tả không được quá 2000 ký tự.");
            return;
        }

        setSaving(true);

        try 
        {
            if (isEditing) 
            {
                // Mô tả có thể sửa ngay cả khi Device
                // đã gắn MCU vì nó chỉ lưu trên Registry.
                const changes = {description,};
                if (!isBound) 
                {
                    changes.deviceName = name;
                    changes.deviceTypeId = typeId;
                }

                await updateDevice(editingId, changes);
            } 
            else 
            {
                // Tạo Device chưa gắn MCU/GPIO.
                await createDevice(typeId, name, description);
            }

            resetForm();

            setSuccess(isEditing ? "Cập nhật thiết bị thành công.": "Tạo thiết bị thành công.");
            try 
            {
                await reloadDevices();
            } 
            catch 
            {
                setError(
                    "Đã lưu nhưng chưa tải lại được danh sách. " +
                    "Hãy tải lại trang."
                );
            }
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setSaving(false);
        }
    }

    // 6. XÓA DEVICE
    async function handleDelete(device) 
    {
        clearMessages();

        // Backend yêu cầu gỡ liên kết phần cứng
        // trước khi xóa Device.
        if (device.microcontrollerId != null) {
            setError(
                "Device đang gắn MCU. " +
                "Cần hủy liên kết trước khi xóa."
            );
            return;
        }

        const confirmed = window.confirm(
            `Bạn có chắc muốn xóa thiết bị "${device.deviceName || device.id}" không?`);
        

        if (!confirmed) return;
        setDeletingId(device.id);

        try 
        {
            await deleteDevice(device.id);
            if (editingId === device.id) resetForm();
            setSuccess("Xóa thiết bị thành công.");

            try 
            {
                await reloadDevices();
            } 
            catch 
            {
                setError( "Đã xóa nhưng chưa tải lại được danh sách." );  
            }
        } 
        catch (err) 
        {
            // Ví dụ: Device đang có Schedule.
            setError(err.message);
        } 
        finally 
        {
            setDeletingId(null);
        }
    }

    // 7. THỐNG KÊ
    const total = devices.length;
    const unassigned = devices.filter((item) => item.microcontrollerId == null).length;
    const assigned = total - unassigned;
    const inputClass =
        "w-full rounded-lg border border-gray-300 px-3 py-2.5 " +
        "outline-none focus:border-blue-500 disabled:bg-gray-100";

    // 8. GIAO DIỆN
    return (
        <div className="min-h-screen bg-gray-100 px-4 py-8">
            <div className="mx-auto max-w-6xl space-y-6">

                {/* Vùng 1. HEADER */}
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            Quản lý thiết bị
                        </h1>

                        <p className="mt-1 text-sm text-gray-500">
                            Thêm, xem và cập nhật các Device của bạn
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <Link
                            to="/microcontrollers"
                            className="rounded-lg bg-white px-4 py-2 text-sm shadow-sm hover:bg-gray-50"
                        >
                            Vi điều khiển của tôi
                        </Link>

                        <Link
                            to="/account"
                            className="rounded-lg bg-white px-4 py-2 text-sm shadow-sm hover:bg-gray-50"
                        >
                            Về tài khoản
                        </Link>
                    </div>
                </div>

                {/* Vùng 2. THỐNG KÊ */}
                <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-xl bg-white p-5 shadow-sm">
                        <p className="text-sm text-gray-500">
                            Tổng thiết bị
                        </p>
                        <p className="mt-2 text-3xl font-bold">
                            {total}
                        </p>
                    </div>

                    <div className="rounded-xl bg-white p-5 shadow-sm">
                        <p className="text-sm text-gray-500">
                            Chưa gắn MCU
                        </p>
                        <p className="mt-2 text-3xl font-bold text-orange-600">
                            {unassigned}
                        </p>
                    </div>

                    <div className="rounded-xl bg-white p-5 shadow-sm">
                        <p className="text-sm text-gray-500">
                            Đã khai báo MCU
                        </p>
                        <p className="mt-2 text-3xl font-bold text-blue-700">
                            {assigned}
                        </p>
                    </div>
                </div>

                {/* THÔNG BÁO */}
                {error && (
                    <div
                        role="alert"
                        className="rounded-lg bg-red-50 p-4 text-sm text-red-700"
                    >
                        {error}
                    </div>
                )}

                {success && (
                    <div
                        role="status"
                        className="rounded-lg bg-green-50 p-4 text-sm text-green-700"
                    >
                        {success}
                    </div>
                )}

                {/* Vùng 3. FORM THÊM / SỬA */}
                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <h2 className="mb-4 text-lg font-semibold">
                        {editingId === null ? "Thêm thiết bị mới" : `Chỉnh sửa thiết bị #${editingId}`}     
                    </h2>

                    <form
                        onSubmit={handleSubmit}
                        className="space-y-4"
                    >
                        <div className="grid gap-4 sm:grid-cols-2">
                            {/* TÊN THIẾT BỊ */}
                            <div>
                                <label
                                    htmlFor="device-name"
                                    className="mb-2 block text-sm font-medium"
                                >
                                    Tên thiết bị
                                </label>

                                <input
                                    id="device-name"
                                    type="text"
                                    value={form.deviceName}
                                    onChange={(e) => updateForm("deviceName",e.target.value)}
                                    placeholder="Ví dụ: Đèn học"
                                    maxLength={150}
                                    required={!isBound}
                                    disabled={busy || isBound}
                                    className={inputClass}
                                />
                            </div>

                            {/* LOẠI THIẾT BỊ */}
                            <div>
                                <label
                                    htmlFor="device-type"
                                    className="mb-2 block text-sm font-medium"
                                >
                                    Loại thiết bị
                                </label>

                                <select
                                    id="device-type"
                                    value={form.deviceTypeId}
                                    onChange={(e) =>updateForm("deviceTypeId",e.target.value)}
                                    required={!isBound}
                                    disabled={busy || isBound}
                                    className={inputClass}
                                >
                                    <option value="">
                                        -- Chọn loại thiết bị --
                                    </option>

                                    {deviceTypes.map((item) => (
                                        <option
                                            key={item.id}
                                            value={item.id}
                                        >
                                            {item.typeName}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* MÔ TẢ */}
                        <div>
                            <label
                                htmlFor="device-description"
                                className="mb-2 block text-sm font-medium"
                            >
                                Mô tả
                            </label>

                            <textarea
                                id="device-description"
                                rows={4}
                                value={form.description}
                                onChange={(e) => updateForm( "description", e.target.value)}
                                maxLength={2000}
                                placeholder="Ví dụ: Đèn học trên bàn ở phòng ngủ tầng 2"
                                disabled={busy}
                                className={inputClass}
                            />

                            <p className="mt-2 text-xs text-gray-500">
                                Mô tả được lưu để phục vụ chức năng
                                Tag và NLP ở giai đoạn tiếp theo.
                            </p>
                        </div>

                        {/* THÔNG TIN LIÊN KẾT */}
                        {editingId === null && (
                            <p className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
                                Thiết bị mới sẽ được tạo ở trạng thái
                                chưa gắn MCU. Bạn có thể cấu hình
                                MCU và GPIO sau.
                            </p>
                        )}

                        {isBound && (
                            <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                                Thiết bị đã khai báo liên kết MCU.
                                Hiện chỉ cho sửa mô tả; đổi tên hoặc
                                loại cần quy trình đồng bộ phần cứng.
                            </p>
                        )}

                        {/* NÚT LƯU */}
                        <div className="flex flex-wrap gap-3">
                            <button
                                type="submit"
                                disabled={
                                    busy ||
                                    loading ||
                                    (!isBound && deviceTypes.length === 0)
                                }
                                className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                                {saving
                                    ? "Đang lưu..."
                                    : editingId === null
                                        ? "Tạo thiết bị"
                                        : "Lưu thay đổi"}
                            </button>

                            {editingId !== null && (
                                <button
                                    type="button"
                                    onClick={resetForm}
                                    disabled={busy}
                                    className="rounded-lg bg-gray-200 px-5 py-2.5 hover:bg-gray-300"
                                >
                                    Hủy chỉnh sửa
                                </button>
                            )}
                        </div>

                        {!loading && deviceTypes.length === 0 && (
                            <p className="text-sm text-red-600">
                                Chưa có DeviceType nào.
                                Cần tạo loại thiết bị trước.
                            </p>
                        )}
                    </form>
                </section>
                

                {refreshing && (
                    <p
                        role="status"
                        className="rounded-lg bg-blue-50 p-4 text-sm text-blue-700"
                    >
                        Đang đồng bộ trạng thái với MCU...
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


                {/* Vùng 4. DANH SÁCH DEVICE */}
                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <h2 className="text-lg font-semibold">
                            Danh sách thiết bị
                        </h2>


                        <div className="flex flex-wrap items-center gap-3">
                            <span className="text-sm text-gray-500">
                                Tổng số: {total}
                            </span>

                            <button
                                type="button"
                                onClick={handleRefreshStatuses}
                                disabled={refreshing || loading}
                                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                                {refreshing
                                    ? "Đang đồng bộ..."
                                    : "Làm mới trạng thái"}
                            </button>
                        </div>

                    </div>

                    {loading ? (
                        <p className="py-6 text-gray-500">
                            Đang tải dữ liệu...
                        </p>
                    ) : devices.length === 0 ? (
                        <p className="py-8 text-center text-gray-500">
                            Bạn chưa tạo thiết bị nào.
                        </p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="bg-gray-50 text-gray-600">
                                    <tr>
                                        <th className="px-3 py-3">
                                            Thiết bị
                                        </th>

                                        <th className="px-3 py-3">
                                            Loại
                                        </th>

                                        <th className="px-3 py-3">
                                            MCU / GPIO
                                        </th>

                                        <th className="px-3 py-3">
                                            Trạng thái
                                        </th>

                                        <th className="px-3 py-3">
                                            Đồng bộ
                                        </th>

                                        <th className="px-3 py-3 text-right">
                                            Thao tác
                                        </th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {devices.map((device) => (
                                        <tr
                                            key={device.id}
                                            className="border-b border-gray-100 align-top"
                                        >
                                            <td className="px-3 py-4">
                                                <p className="font-medium text-gray-900">
                                                    {device.deviceName ||
                                                        `Device #${device.id}`}
                                                </p>

                                                <p className="mt-1 text-xs text-gray-500">
                                                    ID: {device.id}
                                                </p>

                                                {device.description && (
                                                    <p className="mt-2 max-w-xs whitespace-pre-wrap break-words text-xs text-gray-500">
                                                        {device.description}
                                                    </p>
                                                )}
                                            </td>

                                            <td className="px-3 py-4">
                                                {device.deviceTypeName}
                                            </td>

                                            <td className="px-3 py-4">
                                                {device.microcontrollerId == null ? (
                                                    <span className="text-orange-600">
                                                        Chưa gắn
                                                    </span>
                                                ) : (
                                                    <div>
                                                        <p>
                                                            {device.microcontrollerType}
                                                            {" "}
                                                            #{device.microcontrollerId}
                                                        </p>

                                                        <p className="mt-1 text-xs text-gray-500">
                                                            GPIO {device.gpio ?? "—"}
                                                        </p>
                                                    </div>
                                                )}
                                            </td>

                                            <td className="px-3 py-4">
                                                {device.currentStatus}
                                            </td>

                                            <td className="px-3 py-4">
                                                {device.syncStatus}
                                            </td>

                                            <td className="px-3 py-4">
                                                <div className="flex flex-wrap justify-end gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() =>handleEdit(device)}
                                                        disabled={busy}
                                                        className="rounded-lg bg-amber-100 px-3 py-2 text-amber-800 hover:bg-amber-200 disabled:opacity-50"
                                                    >
                                                        Sửa
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>  handleDelete(device)}
                                                        disabled={busy || device.microcontrollerId != null}
                                                        className="rounded-lg bg-red-100 px-3 py-2 text-red-700 hover:bg-red-200 disabled:opacity-40"
                                                        title={
                                                            device.microcontrollerId != null
                                                                ? "Phải hủy liên kết MCU trước"
                                                                : "Xóa thiết bị"
                                                        }
                                                    >
                                                        {deletingId === device.id ? "Đang xóa...": "Xóa"}   
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    <p className="mt-4 text-xs text-gray-500">
                        Device đã liên kết MCU hoặc còn Schedule
                        có thể không được phép xóa.
                        Backend sẽ kiểm tra trước khi thực hiện.
                    </p>
                </section>
            </div>
        </div>
    );
}
