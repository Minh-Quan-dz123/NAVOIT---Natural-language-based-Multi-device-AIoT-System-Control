import { useState } from "react";
import { Link, useNavigate } from "react-router";


import { registerUser } from "../api/authApi";
import { useAuth } from "../contexts/AuthContext";


export default function RegisterPage() 
{
    const navigate = useNavigate();
    const { login } = useAuth();    

    // 1. đăng ký thì có username, phone, password
    const [username, setUsername] = useState("");
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    // 2. vẫn có error và loading
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    // 1. hàm gửi đăng ký
    async function handleSubmit(event) 
    {
        event.preventDefault();
        setError("");

        // 1.1. kiểm tra username, phone, password
        if (password.length < 8) 
        {
            setError("Mật khẩu phải có ít nhất 8 ký tự.");
            return;
        }

        if (password !== confirmPassword) 
        {
            setError("Mật khẩu xác nhận không khớp.");
            return;
        }

        if (phone.trim() && !/^[0-9]{10}$/.test(phone.trim())) 
        {
            setError("Số điện thoại phải có đúng 10 chữ số.");
            return;
        }

        setLoading(true);

        try {
            // Backend sẽ tự gán Role = "User"
            const result = await registerUser({
                username: username.trim(),
                password: password,
                phone: phone.trim() || null
            });

            // Cập nhật phiên đăng nhập
            login(result);

            navigate("/", { replace: true });
        } 
            
        catch (err) {
            setError(err.message);
        } 
        finally {
            setLoading(false);
        }
    }

    const inputClass ="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-blue-500";

    return (
        <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4 py-8">
            <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">

                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-bold text-blue-700">
                        Tạo tài khoản
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Đăng ký sử dụng AIoT Smart Home
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">

                    <div>
                        <label className="mb-2 block text-sm font-medium">
                            Tên đăng nhập
                        </label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className={inputClass}
                            required
                            disabled={loading}
                            autoComplete="username"
                            placeholder="Nhập tên đăng nhập"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium">
                            Số điện thoại (không bắt buộc)
                        </label>
                        <input
                            type="tel"
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            className={inputClass}
                            maxLength={10}
                            disabled={loading}
                            autoComplete="tel"
                            placeholder="Ví dụ: 0912345678"
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="register-password"
                            className="mb-2 block text-sm font-medium"
                        >
                            Mật khẩu
                        </label>
                        <input
                            id="register-password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className={inputClass}
                            required
                            disabled={loading}
                            minLength={8}
                            autoComplete="new-password"
                            placeholder="Ít nhất 8 ký tự"
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="register-confirm-password"
                            className="mb-2 block text-sm font-medium"
                        >
                            Xác nhận mật khẩu
                        </label>

                        <input
                            id="register-confirm-password"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className={inputClass}
                            required
                            disabled={loading}
                            minLength={8}
                            autoComplete="new-password"
                            placeholder="Nhập lại mật khẩu"
                        />
                    </div>

                    {error && (
                        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                            {error}
                        </p>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                    >
                        {loading ? "Đang đăng ký..." : "Đăng ký"}
                    </button>
                </form>

                <p className="mt-6 text-center text-sm text-slate-600">
                    Đã có tài khoản?{" "}
                    <Link
                        to="/login"
                        className="font-semibold text-blue-600 hover:underline"
                    >
                        Đăng nhập
                    </Link>
                </p>
            </div>
        </div>
    );
}
