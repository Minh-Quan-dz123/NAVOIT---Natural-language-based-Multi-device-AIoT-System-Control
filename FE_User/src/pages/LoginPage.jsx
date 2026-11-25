
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { loginUser} from "../api/authApi";
import { useAuth } from "../contexts/AuthContext";


export default function LoginPage() 
{
    // 0. dùng navigate trong thư viện
    const navigate = useNavigate();

    // 1. username, password
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const { login } = useAuth();

    // 2. state phụ: lỗi và load
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    // 1. hàm gửi : event là đối tượng sự kiện (Event Object) 
    // được React tự động truyền vào hàm handleSubmit khi người dùng gửi form đăng nhập.
    async function handleSubmit(event) 
    {
        // 1.1. chặn hành vi mặc định của trình duyệt khi một sự kiện xảy ra.
        event.preventDefault();

        // 1.2. khởi tạo error chưa có và đang load (true)
        setError("");
        setLoading(true);

        try {
            // 1.3 Gọi API đăng nhập
            const result = await loginUser({
                username: username.trim(),
                password: password.trim()
            });

            login(result);

            // 1.5. Chuyển đến trang tài khoản
            navigate("/", { replace: true }); 
        } 
        catch (err) 
        {
            setError(err.message);
        } 
        finally 
        {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
            <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">

                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-blue-700">
                        AIoT Smart Home - Minh Quân - 20225386
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Đăng nhập để quản lý hệ thống
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">

                    <div>
                        <label
                            htmlFor="username"
                            className="block text-sm font-medium mb-2"
                        >
                            Tên đăng nhập
                        </label>

                        <input
                            id="username"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            autoComplete="username"
                            required
                            className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-blue-500"
                            placeholder="Nhập tên đăng nhập"
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="password"
                            className="block text-sm font-medium mb-2"
                        >
                            Mật khẩu
                        </label>

                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoComplete="current-password"
                            required
                            disabled={loading}
                            className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-blue-500"
                            placeholder="Nhập mật khẩu"
                        />
                    </div>

                    {error && (<p className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</p>)}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                    >
                        {loading ? "Đang đăng nhập..." : "Đăng nhập"}
                    </button>
                </form>

                <p className="mt-6 text-center text-sm text-slate-600">
                    Chưa có tài khoản?{" "}
                    <Link
                        to="/register"
                        className="font-semibold text-blue-600 hover:underline"
                    >
                        Đăng ký
                    </Link>
                </p>
            </div>
        </div>
    );
}
