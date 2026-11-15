// Giao diện để thêm/sửa danh sách DeviceType. 
// phần AllowedStatuses nhập bằng dấu phẩy:
// - ON, OFF → ["ON", "OFF"]
// - OPEN, CLOSED → ["OPEN", "CLOSED"]
import { useEffect, useState } from "react";

import {
    getDeviceTypes,
    createDeviceType,
    updateDeviceType,
    deleteDeviceType,
} from "../api/deviceTypeApi";

export default function AdminDeviceTypesPage() 
{
    // 1. STATE
    const [types, setTypes] = useState([]);

    const [typeName, setTypeName] = useState("");
    const [statusesText, setStatusesText] = useState("");
    const [editingId, setEditingId] = useState(null);

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // 2. LẤY DANH SÁCH TỪ BACKEND
    async function reloadTypes()
    {
        const data = await getDeviceTypes();
        setTypes(data);
    }

    useEffect(() => {
        let cancelled = false;

        async function loadInitialData() 
        {
            try {
                const data = await getDeviceTypes();
                if (!cancelled) setTypes(data);
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

        loadInitialData();
        return () => {cancelled = true;};
    }, []);

    // 3. FORM THÊM / SỬA
    function resetForm() 
    {
        setEditingId(null);
        setTypeName("");
        setStatusesText("");
    }

    function handleEdit(item) 
    {
        // Backend không cho sửa loại đang được Device dùng.
        if (item.deviceCount > 0) 
        {
            setError("Loại này đang được Device sử dụng.");
            return;
        }

        setEditingId(item.id);
        setTypeName(item.typeName);
        setStatusesText(item.allowedStatuses.join(", "));

        setError("");
        setSuccess("");
    }

    // 4. KIỂM TRA DỮ LIỆU FORM
    function validateForm() 
    {
        const name = typeName.trim().toLowerCase();

        if (!/^[a-z][a-z0-9_]{0,49}$/.test(name)) 
        {
            throw new Error(
                "Tên loại phải bắt đầu bằng chữ cái, " +
                "chỉ chứa chữ thường, số, _ và tối đa 50 ký tự."
            );
        }

        const statuses = statusesText
            .split(",")
            .map((value) => value.trim().toUpperCase());

        if (statuses.length === 0 || statuses.some((s) => !s)) 
        {
            throw new Error("Nhập ít nhất một trạng thái, ngăn cách bằng dấu phẩy.");
        }

        for (const status of statuses) 
        {
            if (status.length > 32 || !/^[A-Z][A-Z0-9_]*$/.test(status)) 
            {
                throw new Error(`Trạng thái "${status}" không hợp lệ.`);
            }
        }

        if (new Set(statuses).size !== statuses.length) 
        {
            throw new Error("Danh sách trạng thái không được trùng nhau.");
        }

        return { name, statuses };
    }

    // 5. THÊM / CẬP NHẬT
    async function handleSubmit(event) 
    {
        event.preventDefault();

        setError("");
        setSuccess("");

        let values;

        try 
        {
            values = validateForm();
        } 
        catch (err) 
        {
            setError(err.message);
            return;
        }

        const isEditing = editingId !== null;
        setSaving(true);

        try 
        {
            if (isEditing) 
            {
                await updateDeviceType(editingId, values.name, values.statuses);     
            } 
            else 
            {
                await createDeviceType( values.name, values.statuses);  
            }

            resetForm();
            setSuccess(isEditing ? "Cập nhật loại thiết bị thành công." : "Thêm loại thiết bị thành công.");

            try 
            {
                await reloadTypes();
            } 
            catch 
            {
                setError("Đã lưu thành công nhưng không tải lại được danh sách.");
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

    // 6. XÓA LOẠI THIẾT BỊ
    async function handleDelete(item) 
    {
        if (item.deviceCount > 0) 
        {
            setError( "Không thể xóa loại đang được Device sử dụng." );
            return;
        }

        const confirmed = window.confirm(`Bạn có chắc muốn xóa loại "${item.typeName}" không?`);

        if (!confirmed) return;

        setError("");
        setSuccess("");
        setDeletingId(item.id);

        try 
        {
            await deleteDeviceType(item.id);
            if (editingId === item.id) {resetForm();}
            setSuccess("Xóa loại thiết bị thành công.");

            try 
            {
                await reloadTypes();
            } 
            catch 
            {
                setError("Đã xóa thành công nhưng không tải lại được danh sách.");
            }
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setDeletingId(null);
        }
    }

    // 7. GIAO DIỆN
    const busy = saving || deletingId !== null;

    const inputClass =
        "w-full rounded-lg border border-gray-300 px-3 py-2.5 " +
        "outline-none focus:border-blue-500 disabled:bg-gray-100";

    return (
        <div className="space-y-6">
            {/* Tiêu đề */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900">
                    Quản lý loại thiết bị
                </h1>

                <p className="mt-1 text-sm text-gray-500">
                    Khai báo loại Device và các trạng thái cho phép
                </p>
            </div>

            {/* Thông báo */}
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

            {/* Form thêm / sửa */}
            <section className="rounded-xl bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-lg font-semibold">
                    {editingId === null ? "Thêm loại thiết bị": `Chỉnh sửa loại thiết bị #${editingId}`}
                </h2>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label
                            htmlFor="device-type-name"
                            className="mb-2 block text-sm font-medium"
                        >
                            Tên loại thiết bị
                        </label>

                        <input
                            id="device-type-name"
                            type="text"
                            value={typeName}
                            onChange={(e) => setTypeName(e.target.value)}
                            placeholder="Ví dụ: light, fan, door"
                            maxLength={50}
                            disabled={busy}
                            required
                            className={inputClass}
                        />

                        <p className="mt-1 text-xs text-gray-500">
                            Dùng mã không dấu, ví dụ ceiling_fan.
                        </p>
                    </div>

                    <div>
                        <label
                            htmlFor="device-type-statuses"
                            className="mb-2 block text-sm font-medium"
                        >
                            Các trạng thái cho phép
                        </label>

                        <input
                            id="device-type-statuses"
                            type="text"
                            value={statusesText}
                            onChange={(e) =>setStatusesText(e.target.value)}
                            placeholder="Ví dụ: ON, OFF"
                            disabled={busy}
                            required
                            className={inputClass}
                        />

                        <p className="mt-1 text-xs text-gray-500">
                            Các trạng thái cách nhau bằng dấu phẩy.
                            Hệ thống tự chuyển thành chữ hoa.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-3">
                        <button
                            type="submit"
                            disabled={busy}
                            className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            {saving
                                ? "Đang lưu..."
                                : editingId === null
                                    ? "Thêm loại"
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
                </form>
            </section>

            {/* Danh sách */}
            <section className="rounded-xl bg-white p-5 shadow-sm">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold">
                        Danh sách loại thiết bị
                    </h2>

                    <span className="text-sm text-gray-500">
                        Tổng số: {types.length}
                    </span>
                </div>

                {loading ? (
                    <p className="py-6 text-gray-500">
                        Đang tải dữ liệu...
                    </p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-gray-50 text-gray-600">
                                <tr>
                                    <th className="px-3 py-3">ID</th>
                                    <th className="px-3 py-3">Tên loại</th>
                                    <th className="px-3 py-3">
                                        Trạng thái cho phép
                                    </th>
                                    <th className="px-3 py-3">Số Device</th>
                                    <th className="px-3 py-3 text-right">
                                        Thao tác
                                    </th>
                                </tr>
                            </thead>

                            <tbody>
                                {types.map((item) => (
                                    <tr
                                        key={item.id}
                                        className="border-b border-gray-100 align-top"
                                    >
                                        <td className="px-3 py-4">
                                            {item.id}
                                        </td>

                                        <td className="px-3 py-4 font-medium">
                                            {item.typeName}
                                        </td>

                                        <td className="px-3 py-4">
                                            <div className="flex flex-wrap gap-1">
                                                {item.allowedStatuses.map(
                                                    (status) => (
                                                        <span
                                                            key={status}
                                                            className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700"
                                                        >
                                                            {status}
                                                        </span>
                                                    )
                                                )}
                                            </div>
                                        </td>

                                        <td className="px-3 py-4">
                                            {item.deviceCount}
                                        </td>

                                        <td className="px-3 py-4">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => handleEdit(item)}
                                                    disabled={busy ||item.deviceCount > 0}
                                                    className="rounded-lg bg-amber-100 px-3 py-2 text-amber-800 hover:bg-amber-200 disabled:opacity-40"
                                                >
                                                    Sửa
                                                </button>

                                                <button
                                                    type="button"
                                                    onClick={() =>handleDelete(item)}
                                                    disabled={ busy || item.deviceCount > 0}
                                                    className="rounded-lg bg-red-100 px-3 py-2 text-red-700 hover:bg-red-200 disabled:opacity-40"
                                                >
                                                    {deletingId === item.id ? "Đang xóa..." : "Xóa"}
                                                       
                                                        
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        {types.length === 0 && (
                            <p className="py-8 text-center text-gray-500">
                                Chưa có loại thiết bị nào.
                            </p>
                        )}
                    </div>
                )}

                <p className="mt-4 text-xs text-gray-500">
                    Không thể sửa hoặc xóa loại thiết bị đang
                    được Device sử dụng.
                </p>
            </section>
        </div>
    );
}
