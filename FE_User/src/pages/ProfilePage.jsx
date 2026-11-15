
import { useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";

import { getMyProfile, updateMyProfile, changeMyPassword,} from "../api/userApi";


export default function ProfilePage() 
{
    const navigate = useNavigate();

    // 1. chứa thông tin user, thông tin chỉnh sửa và boolean logout ko dùng để reander
    const { user, updateUser, logout } = useAuth();

    // 2. Thông tin tài khoản
    const [username, setUsername] = useState(user.username || "");
    const [phone, setPhone] = useState(user.phone || "");

    // 3. boolean 
    const [savingProfile, setSavingProfile] = useState(false);

    // 4. profile
    const [profileMessage, setProfileMessage] = useState({
        type: "",
        text: "",
    });

    // 5. Đổi mật khẩu
    const [oldPassword, setOldPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    // 6. boolean
    const [savingPassword, setSavingPassword] = useState(false);

    const [passwordMessage, setPasswordMessage] = useState({
        type: "",
        text: "",
    });


    // 1. Hàm cập nhật tài khoản
    async function handleUpdateProfile(event) 
    {
        event.preventDefault();

        setProfileMessage({ type: "", text: "" });

        const usernameValue = username.trim();
        const phoneValue = phone.trim();

        if (!usernameValue) 
        {
            setProfileMessage({
                type: "error",
                text: "Username không được để trống.",
            });
            return;
        }

        if (phoneValue && !/^[0-9]{10}$/.test(phoneValue)) 
        {
            setProfileMessage({
                type: "error",
                text: "Số điện thoại phải gồm đúng 10 chữ số.",
            });
            return;
        }

        // ko cho xóa số điện thoại
        if (!phoneValue && user.phone) 
        {
            setProfileMessage({
                type: "error",
                text: "Hiện chưa hỗ trợ xóa số điện thoại đã đăng ký.",
            });
            return;
        }

        setSavingProfile(true);

        try 
        {   
            // call api
            await updateMyProfile(
                usernameValue,
                phoneValue || null
            );

            // Đọc lại dữ liệu thực tế đã lưu trong Backend.
            const updatedProfile = await getMyProfile();

            // Đồng bộ thông tin trên toàn ứng dụng.
            updateUser(updatedProfile);

            // hiển thị bọn này về thông tin mới
            setUsername(updatedProfile.username || "");
            setPhone(updatedProfile.phone || "");

            setProfileMessage({
                type: "success",
                text: "Cập nhật tài khoản thành công.",
            });
        } 
        catch (error) {
            setProfileMessage({
                type: "error",
                text: error.message || "Không thể cập nhật tài khoản.",
            });
        } 
        finally {
            // cập nhật state là đã lưu xong rồi
            setSavingProfile(false);
        }
    }

    // 2. Hàm đổi mật khẩu
    async function handleChangePassword(event) 
    {
        event.preventDefault();

        setPasswordMessage({ type: "", text: "" });

        if (!oldPassword || !newPassword || !confirmPassword)
        {
            setPasswordMessage({
                type: "error",
                text: "Vui lòng nhập đầy đủ thông tin mật khẩu.",
            });
            return;
        }

        if (newPassword.length < 8) 
        {
            setPasswordMessage({
                type: "error",
                text: "Mật khẩu mới phải có ít nhất 8 ký tự.",
            });
            return;
        }

        if (newPassword !== confirmPassword) 
        {
            setPasswordMessage({
                type: "error",
                text: "Xác nhận mật khẩu mới không khớp.",
            });
            return;
        }

        if (newPassword === oldPassword) 
        {
            setPasswordMessage({
                type: "error",
                text: "Mật khẩu mới phải khác mật khẩu cũ.",
            });
            return;
        }

        setSavingPassword(true);

        try {
            await changeMyPassword(oldPassword, newPassword);

            setOldPassword("");
            setNewPassword("");
            setConfirmPassword("");

            setPasswordMessage({
                type: "success",
                text: "Đổi mật khẩu thành công.",
            });
        } 
        catch (error) {
            setPasswordMessage({
                type: "error",
                text: error.message || "Không thể đổi mật khẩu.",
            });
        } 
        finally {
            setSavingPassword(false);
        }
    }


    // 3. hàm chuyển hướng về login khi bấm nút Đăng xuất
    function handleLogout() 
    {
        logout();
        navigate("/login", { replace: true });
    }

    const inputClass = "w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

    const labelClass = "mb-2 block text-sm font-medium text-gray-700";

    return (
        <div className="min-h-screen bg-gray-100 px-4 py-10">
            <div className="mx-auto max-w-2xl space-y-6">

                {/* 1. Tiêu đề */}
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                        Quản lý tài khoản
                        </h1>

                        <p className="mt-1 text-sm text-gray-500">
                        Xem và cập nhật thông tin cá nhân
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={handleLogout}
                        className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
                    >
                        Đăng xuất
                    </button>
                </div>

                {/* 2. Thông tin tài khoản*/}
                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <h2 className="mb-5 text-xl font-semibold">
                        Thông tin cá nhân
                    </h2>

                    <form
                        onSubmit={handleUpdateProfile}
                        className="space-y-5"
                    >
                        {/* 2.1. ID */}
                        <div>
                            <label className={labelClass}>
                                User ID
                            </label>

                            <input
                                type="text"
                                value={user.id ?? ""}
                                disabled
                                className={`${inputClass} bg-gray-100 text-gray-500`}
                            />
                        </div>

                        {/* 2.2. Username */}
                        <div>
                            <label
                                htmlFor="profile-username"
                                className={labelClass}
                            >
                                Username
                            </label>

                            <input
                                id="profile-username"
                                type="text"
                                autoComplete="username"
                                value={username}
                                onChange={(event) => {setUsername(event.target.value);}}
                                disabled={savingProfile}
                                required
                                className={inputClass}
                            />
                        </div>

                        {/* 2.3. Phone */}
                        <div>
                            <label
                                htmlFor="profile-phone"
                                className={labelClass}
                            >
                                Số điện thoại
                            </label>

                            <input
                                id="profile-phone"
                                type="tel"
                                autoComplete="tel"
                                inputMode="numeric"
                                value={phone}
                                onChange={(event) => {setPhone(event.target.value);}}
                                disabled={savingProfile}
                                placeholder="Nhập số điện thoại"
                                maxLength={10}
                                className={inputClass}
                            />
                        </div>

                        {/* 2.4. Role */}
                        <div>
                            <label className={labelClass}>
                                Vai trò
                            </label>

                            <input
                                type="text"
                                value={user.role ?? ""}
                                disabled
                                className={`${inputClass} bg-gray-100 text-gray-500`}
                            />
                        </div>

                        {/* 3 Thông báo */}
                        {profileMessage.text && (
                            <p
                                role="status"
                                className={
                                    profileMessage.type === "success"
                                        ? "text-sm text-green-600"
                                        : "text-sm text-red-600"
                                }
                            >
                                {profileMessage.text}
                            </p>
                        )}

                        <button
                            type="submit"
                            disabled={savingProfile}
                            className="w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {savingProfile ? "Đang cập nhật..." : "Lưu thay đổi"}
                        </button>
                    </form>
                </section>

                {/* 3. Đổi mật khẩu */}

                <section className="rounded-xl bg-white p-6 shadow-sm">
                    <h2 className="mb-5 text-xl font-semibold">
                        Đổi mật khẩu
                    </h2>

                    <form
                        onSubmit={handleChangePassword}
                        className="space-y-5"
                    >
                        {/* Nhập mật khẩu cũ */}
                        <div>
                        <label
                            htmlFor="old-password"
                            className={labelClass}
                        >
                            Mật khẩu cũ
                        </label>

                        <input
                            id="old-password"
                            type="password"
                            autoComplete="current-password"
                            value={oldPassword}
                            onChange={(event)=>{setOldPassword(event.target.value);}}
                            disabled={savingPassword}
                            required
                            className={inputClass}
                        />
                        </div>

                        {/* Nhập mật khẩu mới */}
                        <div>
                            <label
                                htmlFor="new-password"
                                className={labelClass}
                            >
                                Mật khẩu mới
                            </label>

                            <input
                                id="new-password"
                                type="password"
                                autoComplete="new-password"
                                value={newPassword}
                                onChange={(event) => {
                                setNewPassword(event.target.value);
                                }}
                                disabled={savingPassword}
                                minLength={8}
                                required
                                className={inputClass}
                            />
                        </div>

                        {/* Xác nhận mật khẩu */}
                        <div>
                            <label
                                htmlFor="confirm-password"
                                className={labelClass}
                            >
                                Xác nhận mật khẩu mới
                            </label>

                            <input
                                id="confirm-password"
                                type="password"
                                autoComplete="new-password"
                                value={confirmPassword}
                                onChange={(event) => {
                                setConfirmPassword(event.target.value);
                                }}
                                disabled={savingPassword}
                                minLength={8}
                                required
                                className={inputClass}
                            />
                        </div>

                        {/* Thông báo */}
                        {passwordMessage.text && (
                        <p
                            role="status"
                            className={
                            passwordMessage.type === "success"
                                ? "text-sm text-green-600"
                                : "text-sm text-red-600"
                            }
                        >
                            {passwordMessage.text}
                        </p>
                        )}

                        <button
                            type="submit"
                            disabled={savingPassword}
                            className="w-full rounded-lg bg-gray-800 px-4 py-2 font-medium text-white hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                            {savingPassword
                                ? "Đang đổi mật khẩu..."
                                : "Đổi mật khẩu"}
                        </button>
                    </form>
                </section>

            </div>
        </div>
    );
}
