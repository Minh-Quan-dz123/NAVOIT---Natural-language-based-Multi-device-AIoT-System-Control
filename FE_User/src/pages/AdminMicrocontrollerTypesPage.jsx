
import { useEffect, useState } from "react";
import { Link } from "react-router";

import {
    getMicrocontrollerTypes,
    createMicrocontrollerType,
    updateMicrocontrollerType,
    deleteMicrocontrollerType,
} from "../api/microcontrollerTypeApi";

export default function AdminMicrocontrollerTypesPage() 
{
    // 1. Danh sách loại MCU
    const [types, setTypes] = useState([]);

    // 2. Form thêm/sửa
    const [typeName, setTypeName] = useState("");
    const [editingId, setEditingId] = useState(null);

    // 3. Phụ - Trạng thái
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState(null);

    // 4. Thông báo
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // 1. LẤY DANH SÁCH
    async function loadTypes() 
    {
        const result = await getMicrocontrollerTypes();
        setTypes(result);
    }

    // 2. Chạy khi trang được mở thì lấy danh sách
    useEffect(() => {
        let cancelled = false;

        async function loadInitialData() 
        {
            try {
                const result = await getMicrocontrollerTypes();
                if (!cancelled) {setTypes(result);}
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

        return () => { cancelled = true;};
    }, []);


    // 3. CHỌN SỬA
    function handleEdit(item) 
    {
        setEditingId(item.id);
        setTypeName(item.typeName);

        setError("");
        setSuccess("");
    }


    // 4. HỦY CHỈNH SỬA
    function handleCancelEdit() 
    {
        setEditingId(null);
        setTypeName("");

        setError("");
        setSuccess("");
    }


    // 5. THÊM HOẶC CẬP NHẬT
    async function handleSubmit(event) 
    {
        event.preventDefault();

        setError("");
        setSuccess("");

        const normalizedName = typeName.trim().toLowerCase();

        if (!normalizedName) 
        {
            setError("Tên loại vi điều khiển không được để trống.");
            return;
        }

        if (!/^[a-z0-9][a-z0-9_-]*$/.test(normalizedName)) 
        {
            setError("Tên loại chỉ được chứa chữ thường, số, _ hoặc -.");
            return;
        }

        if (normalizedName.length > 50) 
        {
            setError("Tên loại không được vượt quá 50 ký tự.");
            return;
        }

        setSaving(true);

        try 
        {
            if (editingId === null) await createMicrocontrollerType(normalizedName);
            else 
            {
                // Chế độ chỉnh sửa
                await updateMicrocontrollerType(editingId, normalizedName);
            }

            // Lấy lại danh sách từ database.
            await loadTypes();

            setSuccess(
                editingId === null
                    ? "Thêm loại vi điều khiển thành công."
                    : "Cập nhật loại vi điều khiển thành công."
            );

            setTypeName("");
            setEditingId(null);

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

    // 6. XÓA LOẠI vi điều khiểu
    async function handleDelete(item) 
    {
        const confirmed = window.confirm(`Bạn có chắc muốn xóa loại "${item.typeName}" không?`);

        if (!confirmed) return;

        setError("");
        setSuccess("");
        setDeletingId(item.id);

        try 
        {
            await deleteMicrocontrollerType(item.id);
            await loadTypes();

            // Nếu đang sửa loại vừa xóa thì hủy form.
            if (editingId === item.id) 
            {
                setEditingId(null);
                setTypeName("");
            }

            setSuccess("Xóa loại vi điều khiển thành công.");

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


    // 6. GIAO DIỆN
    return (
        <div className="min-h-screen bg-gray-100 px-4 py-8">
            <div className="mx-auto max-w-4xl space-y-6">

                {/* 1. Header */}
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            Quản lý loại vi điều khiển
                        </h1>

                        <p className="mt-1 text-sm text-gray-500">
                            Quản trị danh mục các loại MCU được hỗ trợ
                        </p>
                    </div>

                    <Link
                        to="/account"
                        className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm hover:bg-gray-50"
                    >
                        Quay về tài khoản
                    </Link>
                </div>

                {/* 2. Thông báo */}
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

                {/* 3. Form thêm/sửa */}
                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <h2 className="mb-4 text-lg font-semibold">
                        {editingId === null ? "Thêm loại vi điều khiển" : "Chỉnh sửa loại vi điều khiển"}
                    </h2>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label
                                htmlFor="microcontroller-type-name"
                                className="mb-2 block text-sm font-medium"
                            >
                                Tên loại
                            </label>

                            <input
                                id="microcontroller-type-name"
                                type="text"
                                value={typeName}
                                onChange={(e) => { setTypeName(e.target.value); }}
                                maxLength={50}
                                placeholder="Ví dụ: esp32, esp8266, stm32"
                                disabled={saving}
                                required
                                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                            />

                            <p className="mt-2 text-xs text-gray-500">
                                Tên sẽ được chuyển về chữ thường trước khi lưu.
                            </p>
                        </div>

                        <div className="flex flex-wrap gap-3">
                            <button
                                type="submit"
                                disabled={saving || deletingId !== null}
                                className="rounded-lg bg-blue-600 px-5 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
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
                                    onClick={handleCancelEdit}
                                    disabled={saving}
                                    className="rounded-lg bg-gray-200 px-5 py-2 text-gray-800 hover:bg-gray-300"
                                >
                                    Hủy chỉnh sửa
                                </button>
                            )}
                        </div>
                    </form>
                </section>

                {/* Danh sách loại MCU */}
                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                        <h2 className="text-lg font-semibold">
                            Danh sách loại vi điều khiển
                        </h2>

                        <span className="text-sm text-gray-500">
                            Tổng số: {types.length}
                        </span>
                    </div>

                    {loading ? (
                        <p className="text-gray-500">
                            Đang tải dữ liệu...
                        </p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full border-collapse text-left text-sm">
                                <thead>
                                    <tr className="border-b bg-gray-50">
                                        <th className="px-4 py-3">ID</th>
                                        <th className="px-4 py-3">Tên loại</th>
                                        <th className="px-4 py-3 text-right">
                                            Thao tác
                                        </th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {types.map((item) => (
                                        <tr
                                            key={item.id}
                                            className="border-b last:border-b-0"
                                        >
                                            <td className="px-4 py-3">
                                                {item.id}
                                            </td>

                                            <td className="px-4 py-3 font-medium">
                                                {item.typeName}
                                            </td>

                                            <td className="px-4 py-3">
                                                <div className="flex justify-end gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleEdit(item)}
                                                        disabled={saving || deletingId !== null}
                                                        className="rounded-lg bg-amber-100 px-3 py-2 text-amber-800 hover:bg-amber-200 disabled:opacity-50"
                                                    >
                                                        Sửa
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() => handleDelete(item)}
                                                        disabled={saving || deletingId !== null}
                                                        className="rounded-lg bg-red-100 px-3 py-2 text-red-700 hover:bg-red-200 disabled:opacity-50"
                                                    >
                                                        {deletingId === item.id
                                                            ? "Đang xóa..."
                                                            : "Xóa"}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            {types.length === 0 && (
                                <p className="py-8 text-center text-gray-500">
                                    Chưa có loại vi điều khiển nào.
                                </p>
                            )}
                        </div>
                    )}
                </section>

            </div>
        </div>
    );
}
