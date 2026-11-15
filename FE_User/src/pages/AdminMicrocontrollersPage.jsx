
import { useEffect, useState } from "react";

import {
    getAdminMicrocontrollers,
    createMicrocontroller,
    updateMicrocontroller,
    transferMicrocontroller,
    deleteMicrocontroller,
} from "../api/microcontrollerApi";

import { getMicrocontrollerTypes } from "../api/microcontrollerTypeApi";
import { getUsersForAssignment } from "../api/adminUserApi";

export default function AdminMicrocontrollersPage() 
{
    // 1. STATE DỮ LIỆU
    const [microcontrollers, setMicrocontrollers] = useState([]);
    const [types, setTypes] = useState([]);
    const [users, setUsers] = useState([]);

    // Form tạo / sửa MCU
    const [type, setType] = useState("");
    const [macAddress, setMacAddress] = useState("");
    const [ownerId, setOwnerId] = useState("");
    const [editingId, setEditingId] = useState(null);

    // Form cấp / chuyển quyền
    const [assigningId, setAssigningId] = useState(null);
    const [assignUserId, setAssignUserId] = useState("");

    // Trạng thái giao diện
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // 2. LẤY DỮ LIỆU
    async function reloadMicrocontrollers() 
    {
        const data = await getAdminMicrocontrollers();
        setMicrocontrollers(data);
    }

    useEffect(() => {
        let cancelled = false;

        async function loadInitialData() 
        {
            try {
                const [mcuData, typeData, userData] =
                    await Promise.all([
                        getAdminMicrocontrollers(),
                        getMicrocontrollerTypes(),
                        getUsersForAssignment(),
                    ]);

                if (cancelled) return;

                setMicrocontrollers(mcuData);
                setTypes(typeData);
                setUsers(userData);
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

    // 3. RESET FORM
    function resetForm() 
    {
        setEditingId(null);
        setType("");
        setMacAddress("");
        setOwnerId("");
    }

    function clearMessages() 
    {
        setError("");
        setSuccess("");
    }

    // 4. CHỌN MCU ĐỂ SỬA
    function handleEdit(item) 
    {
        clearMessages();

        setAssigningId(null);
        setEditingId(item.id);

        setType(item.type);
        setMacAddress(item.macAddress);
    }

    // 5. TẠO / SỬA MCU
    async function handleSubmit(event) 
    {
        event.preventDefault();
        clearMessages();

        if (!type) 
        {
            setError("Vui lòng chọn loại vi điều khiển.");
            return;
        }

        if (!macAddress.trim()) 
        {
            setError("Vui lòng nhập địa chỉ MAC.");
            return;
        }

        const isEditing = editingId !== null;

        setBusy(true);

        try 
        {
            if (isEditing) 
            {
                await updateMicrocontroller(editingId, type, macAddress.trim());     
            } 
            else 
            {
                // Không chọn User => truyền null.
                const userId = ownerId === "" ? null : Number(ownerId);

                await createMicrocontroller(type, macAddress.trim(), userId);
            }

            resetForm();

            setSuccess(isEditing? "Cập nhật MCU thành công.": "Tạo MCU thành công.");

            try 
            {
                await reloadMicrocontrollers();
            } 
            catch 
            {
                setError("Đã lưu thành công nhưng không tải lại được danh sách." );
            }
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setBusy(false);
        }
    }

    // 6. CHỌN CẤP / CHUYỂN QUYỀN
    function handleChooseOwner(item) 
    {
        clearMessages();
        resetForm();

        setAssigningId(item.id);

        // Nếu đã có chủ sở hữu, chọn sẵn User hiện tại.
        setAssignUserId(item.userId == null ? "" : String(item.userId));
    }

    function cancelAssign() 
    {
        setAssigningId(null);
        setAssignUserId("");
    }

    // 7. LƯU CHỦ SỞ HỮU MỚI
    async function handleAssign(event) 
    {
        event.preventDefault();
        clearMessages();

        if (assigningId === null || !assignUserId) {
            setError("Vui lòng chọn User nhận MCU.");
            return;
        }

        setBusy(true);
        try {
            await transferMicrocontroller(
                assigningId,
                Number(assignUserId)
            );

            cancelAssign();
            setSuccess("Cấp / chuyển quyền MCU thành công.");
            try 
            {
                await reloadMicrocontrollers();
            } 
            catch 
            {
                setError("Đã cập nhật chủ sở hữu nhưng không tải lại được danh sách.");
            }
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setBusy(false);
        }
    }

    // 8. XÓA MCU
    async function handleDelete(item) 
    {
        if (item.deviceCount > 0) 
        {
            setError("MCU đang có Device liên kết, không thể xóa.");
            return;
        }

        const confirmed = window.confirm(`Bạn có chắc muốn xóa MCU ${item.type} (${item.macAddress}) không?`);

        if (!confirmed) return;

        clearMessages();
        setBusy(true);

        try 
        {
            await deleteMicrocontroller(item.id);

            if (editingId === item.id) {resetForm();}
            if (assigningId === item.id)  cancelAssign();
            setSuccess("Xóa MCU thành công.");

            try 
            {
                await reloadMicrocontrollers();
            } 
            catch 
            {
                setError( "Đã xóa thành công nhưng không tải lại được danh sách.");
            }
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setBusy(false);
        }
    }

    // 9. THỐNG KÊ
    const total = microcontrollers.length;
    const assigned = microcontrollers.filter((item) => item.userId != null).length;
    const unassigned = total - assigned;
    const inputClass =
        "w-full rounded-lg border border-gray-300 px-3 py-2.5 " +
        "outline-none focus:border-blue-500 disabled:bg-gray-100";

    // 10. GIAO DIỆN
    return (
        <div className="space-y-6">
            {/* 1. Tiêu đề */}
            <div>
                <h2 className="text-2xl font-bold text-gray-900">
                    Quản lý Microcontroller
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                    Tạo MCU, quản lý định danh và quyền sở hữu
                </p>
            </div>

            {/* 2. Thống kê */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-xl bg-white p-5 shadow-sm">
                    <p className="text-sm text-gray-500">Tổng MCU</p>
                    <p className="mt-2 text-3xl font-bold">{total}</p>
                </div>

                <div className="rounded-xl bg-white p-5 shadow-sm">
                    <p className="text-sm text-gray-500">Đã cấp</p>
                    <p className="mt-2 text-3xl font-bold text-green-700">
                        {assigned}
                    </p>
                </div>

                <div className="rounded-xl bg-white p-5 shadow-sm">
                    <p className="text-sm text-gray-500">Chưa cấp</p>
                    <p className="mt-2 text-3xl font-bold text-orange-600">
                        {unassigned}
                    </p>
                </div>
            </div>

            {/* 3. Thông báo */}
            {error && (
                <p
                    role="alert"
                    className="rounded-lg bg-red-50 p-4 text-sm text-red-700"
                >
                    {error}
                </p>
            )}

            {success && (
                <p
                    role="status"
                    className="rounded-lg bg-green-50 p-4 text-sm text-green-700"
                >
                    {success}
                </p>
            )}

            {/* 4. FORM TẠO/SỬA MCU */}
            <section className="rounded-xl bg-white p-5 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold">
                    {editingId === null? "Tạo Microcontroller": `Chỉnh sửa MCU #${editingId}`}
                </h3>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                        {/* Loại MCU */}
                        <div>
                            <label
                                htmlFor="mcu-type"
                                className="mb-2 block text-sm font-medium"
                            >
                                Loại vi điều khiển
                            </label>

                            <select
                                id="mcu-type"
                                value={type}
                                onChange={(e) => setType(e.target.value)}
                                disabled={busy || loading}
                                required
                                className={inputClass}
                            >
                                <option value="">-- Chọn loại MCU --</option>

                                {types.map((item) => (
                                    <option
                                        key={item.id}
                                        value={item.typeName}
                                    >
                                        {item.typeName}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* MAC */}
                        <div>
                            <label
                                htmlFor="mcu-mac"
                                className="mb-2 block text-sm font-medium"
                            >
                                MAC Address
                            </label>

                            <input
                                id="mcu-mac"
                                value={macAddress}
                                onChange={(e) =>setMacAddress(e.target.value)}
                                placeholder="AA:BB:CC:DD:EE:FF"
                                maxLength={17}
                                disabled={busy || loading}
                                required
                                className={inputClass}
                            />
                        </div>
                    </div>

                    {/* Chủ sở hữu chỉ xuất hiện khi tạo MCU */}
                    {editingId === null && (
                        <div>
                            <label
                                htmlFor="mcu-owner"
                                className="mb-2 block text-sm font-medium"
                            >
                                Chủ sở hữu (không bắt buộc)
                            </label>

                            <select
                                id="mcu-owner"
                                value={ownerId}
                                onChange={(e) =>setOwnerId(e.target.value)}
                                disabled={busy || loading}
                                className={inputClass}
                            >
                                <option value="">
                                    -- Chưa cấp cho User nào --
                                </option>

                                {users.map((user) => (
                                    <option
                                        key={user.id}
                                        value={user.id}
                                    >
                                        {user.username} (ID: {user.id})
                                    </option>
                                ))}
                            </select>

                            <p className="mt-2 text-xs text-gray-500">
                                Có thể để trống và cấp quyền sau.
                            </p>
                        </div>
                    )}

                    <div className="flex flex-wrap gap-3">
                        <button
                            type="submit"
                            disabled={busy || loading || types.length === 0}
                            className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            {busy
                                ? "Đang xử lý..."
                                : editingId === null
                                    ? "Tạo MCU"
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

            {/* 5. FORM CẤP / CHUYỂN QUYỀN */}
            {assigningId !== null && (
                <section className="rounded-xl border border-blue-200 bg-white p-5 shadow-sm">
                    <h3 className="mb-4 text-lg font-semibold">
                        Cấp / chuyển quyền MCU #{assigningId}
                    </h3>

                    <form onSubmit={handleAssign} className="space-y-4">
                        <div>
                            <label
                                htmlFor="assign-user"
                                className="mb-2 block text-sm font-medium"
                            >
                                Chọn User nhận MCU
                            </label>

                            <select
                                id="assign-user"
                                value={assignUserId}
                                onChange={(e) =>setAssignUserId(e.target.value)}
                                disabled={busy}
                                required
                                className={inputClass}
                            >
                                <option value="">
                                    -- Chọn tài khoản --
                                </option>

                                {users.map((user) => (
                                    <option
                                        key={user.id}
                                        value={user.id}
                                    >
                                        {user.username} (ID: {user.id})
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="flex flex-wrap gap-3">
                            <button
                                type="submit"
                                disabled={busy}
                                className="rounded-lg bg-blue-600 px-5 py-2.5 text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                                Xác nhận cấp quyền
                            </button>

                            <button
                                type="button"
                                onClick={cancelAssign}
                                disabled={busy}
                                className="rounded-lg bg-gray-200 px-5 py-2.5 hover:bg-gray-300"
                            >
                                Hủy
                            </button>
                        </div>

                        <p className="text-xs text-gray-500">
                            MCU đang liên kết Device chưa được phép
                            chuyển nhượng trong Backend hiện tại.
                        </p>
                    </form>
                </section>
            )}

            {/* 6. DANH SÁCH MCU */}
            <section className="rounded-xl bg-white p-5 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold">
                    Danh sách MCU
                </h3>

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
                                    <th className="px-3 py-3">Loại</th>
                                    <th className="px-3 py-3">MAC</th>
                                    <th className="px-3 py-3">Chủ sở hữu</th>
                                    <th className="px-3 py-3">Device</th>
                                    <th className="px-3 py-3">Kết nối</th>
                                    <th className="px-3 py-3 text-right">
                                        Thao tác
                                    </th>
                                </tr>
                            </thead>

                            <tbody>
                                {microcontrollers.map((item) => (
                                    <tr
                                        key={item.id}
                                        className="border-b border-gray-100 align-top"
                                    >
                                        <td className="px-3 py-4">
                                            {item.id}
                                        </td>

                                        <td className="px-3 py-4 font-medium">
                                            {item.type}
                                        </td>

                                        <td className="px-3 py-4 font-mono text-xs">
                                            {item.macAddress}
                                        </td>

                                        <td className="px-3 py-4">
                                            {item.userId == null ? (
                                                <span className="rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-700">
                                                    Chưa cấp
                                                </span>
                                            ) : (
                                                <div>
                                                    <p className="font-medium">
                                                        {item.ownerUsername}
                                                    </p>

                                                    <p className="text-xs text-gray-400">
                                                        ID: {item.userId}
                                                    </p>
                                                </div>
                                            )}
                                        </td>

                                        <td className="px-3 py-4">
                                            {item.deviceCount}
                                        </td>

                                        <td className="px-3 py-4">
                                            {item.connectionStatus}
                                        </td>

                                        <td className="px-3 py-4">
                                            <div className="flex flex-wrap justify-end gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => handleEdit(item)}
                                                    disabled={busy ||item.deviceCount > 0 }
                                                    className="rounded-lg bg-gray-100 px-3 py-2 hover:bg-gray-200 disabled:opacity-40"
                                                >
                                                    Sửa
                                                </button>

                                                <button
                                                    type="button"
                                                    onClick={() =>handleChooseOwner(item)}
                                                    disabled={busy ||item.deviceCount > 0 }
                                                    className="rounded-lg bg-blue-100 px-3 py-2 text-blue-700 hover:bg-blue-200 disabled:opacity-40"
                                                >
                                                    {item.userId == null ? "Cấp quyền": "Chuyển quyền"}
                                                        
                                                        
                                                </button>

                                                <button
                                                    type="button"
                                                    onClick={() => handleDelete(item)}
                                                    disabled={busy ||item.deviceCount > 0 }
                                                    className="rounded-lg bg-red-100 px-3 py-2 text-red-700 hover:bg-red-200 disabled:opacity-40"
                                                >
                                                    Xóa
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        {microcontrollers.length === 0 && (
                            <p className="py-8 text-center text-gray-500">
                                Chưa có Microcontroller nào.
                            </p>
                        )}
                    </div>
                )}

                <p className="mt-4 text-xs text-gray-500">
                    Các thao tác sửa định danh, chuyển quyền và xóa
                    được khóa khi MCU đang có Device liên kết.
                </p>
            </section>
        </div>
    );
}
