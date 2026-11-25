import { useEffect, useRef, useState } from "react";
import { executeNaturalCommand } from "../api/naturalCommandApi";

function operationLabel(operation) 
{
    if (operation === "device_controlled") return "Điều khiển ON/OFF";
    if (operation === "schedule_created") return "Tạo Schedule";
    if (operation === "schedule_cancelled") return "Hủy Schedule";

    return operation || "Thực hiện lệnh";
}

// component nhận 1 hàm callback khi có sự thay đổi
export default function NaturalCommandControls({ onChanged }) 
{
    // 1. nội dung câu lệnh
    const [text, setText] = useState("");

    // 2. đang xử lý lệnh hay ko
    const [busy, setBusy] = useState(false);

    // 3. Đang nhận giọng nói hay không.
    const [listening, setListening] = useState(false);

    // 4. Kết quả từ Backend.
    const [result, setResult] = useState(null);

    // 5. Danh sách thiết bị gợi ý.
    const [candidates, setCandidates] = useState([]);

    const [error, setError] = useState("");

    const [unknownResult, setUnknownResult] = useState(false);

    // đối tượng nhận giọng nói
    const recognitionRef = useRef(null);

    // recognitionRef.current: Đối tượng nhận dạng giọng nói
    // stop(): Dừng nghe và cố gắng trả về kết quả đã thu được.
    // abort(): Hủy nhận dạng mà không trả kết quả.
    useEffect(() => {
        return () => recognitionRef.current?.abort();
    }, []);

    // 1. CHUYỂN GIỌNG NÓI THÀNH VĂN BẢN
    function handleVoice() 
    {
        if (busy || unknownResult) return;

        if (listening) 
        {
            recognitionRef.current?.stop();
            return;
        }

        // Speech-to-text chạy trên trình duyệt.
        // NLP Server vẫn chỉ nhận văn bản.
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) 
        {
            setError(
                "Trình duyệt chưa hỗ trợ nhận dạng giọng nói. " +
                "Hãy nhập văn bản."
            );
            return;
        }

        setError("");

        // SpeechRecognition là API của trình duyệt
        // tạo 1 đối tượng để thu thập giọng nói và chuyển thành văn bản
        const recognition = new SpeechRecognition();

        recognition.lang = "vi-VN";
        recognition.interimResults = false; // Chỉ trả về kết quả cuối cùng, không trả kết quả tạm thời trong lúc nói.
        recognition.maxAlternatives = 1;    // Chỉ trả về 1 phương án nhận dạng giọng nói tốt nhất.

        // khi nhận dạng thành công, onresult chạy khi có kết quả
        recognition.onresult = event => {
            // lấy văn bản được nhận dạng
            const transcript = event.results[0][0].transcript;

            // Chỉ lấy tối đa 500 ký tự.
            setText(transcript.slice(0, 500));
        };

        recognition.onerror = event => {
            setError(`Không nhận được giọng nói: ${event.error}`);
        };

        // khi kết thúc nhận dạng, set listening = false
        recognition.onend = () => {
            setListening(false);
        };

        // Lưu đối tượng để có thể gọi stop() hoặc abort() sau này.
        recognitionRef.current = recognition;
        setListening(true);

        try 
        {
            recognition.start();
        } 
        catch (err) 
        {
            setListening(false);
            setError(err.message);
        }
    }

    // 2. GỬI LỆNH ĐẾN NLP
    async function handleSubmit(event) 
    {
        event.preventDefault();
        const command = text.trim();

        if (!command || busy || unknownResult) return;

        setBusy(true);
        setError("");
        setResult(null);
        setCandidates([]);

        try {
            const data = await executeNaturalCommand(command);
            setResult(data);

            if (onChanged && data.state !== "failed") 
            {
                try 
                {   // chạy hàm mà cha truyền vào khi thành công
                    await onChanged();
                } 
                catch 
                {
                    setError(
                        "Lệnh đã được xử lý nhưng chưa cập nhật " +
                        "được dữ liệu hiển thị."
                    );
                }
            }
        } 
        catch (err) 
        {
            setError(err.message);
            setCandidates(err.candidates || []);

            if (err.state === "unknown") setUnknownResult(true);
        } 
        finally {
            setBusy(false);
        }
    }

    // 3. CHUẨN HÓA KẾT QUẢ ĐỂ HIỂN THỊ
    
    // Backend 
    // {
    //     state: "success",
    //     results: [
    //         {state: "success", device: {...}, operation: "...", result: {...}},
    //         {state: "success", device: {...}, operation: "...", result: {...}}
    //     ]
    // }

    const items = result
        ? Array.isArray(result.results)
            ? result.results
            : [result]
        : [];

    return (
        <section className="ui-card overflow-hidden">
            {/* vùng 1. vùng trên cùng hiển thị title */}
            <div className="ui-section-header">
                <div>
                    <p className="ui-eyebrow">
                        NATURAL LANGUAGE
                    </p>

                    <h2 className="ui-section-title mt-1">
                        Điều khiển bằng ngôn ngữ tự nhiên
                    </h2>

                    <p className="ui-section-description">
                        Nhập câu lệnh hoặc chuyển giọng nói thành văn bản trước khi gửi.
                    </p>
                </div>

                <span className="ui-badge ui-badge-green">
                    NLP
                </span>
            </div>

            {/* 2. vùng lớn - vùng nhập giọng nói */}
            <div className="p-5 sm:p-6">

                {/* 2.1. khu vực dành cho input */}
                <form
                    onSubmit={handleSubmit}
                    className="flex flex-col gap-3 lg:flex-row"
                >
                    <input
                        className="ui-input min-w-0 flex-1"
                        type="text"
                        maxLength={500}
                        value={text}
                        onChange={e => setText(e.target.value)}
                        disabled={busy || unknownResult}
                        placeholder="Ví dụ: Bật các đèn sau 10 phút"
                        aria-label="Câu lệnh điều khiển"
                    />

                    <button
                        type="button"
                        className="ui-btn ui-btn-outline"
                        onClick={handleVoice}
                        disabled={busy || unknownResult}
                    >
                        {listening ? "■ Dừng ghi âm" : "◉ Nhập bằng giọng nói"}
                    </button>

                    <button
                        type="submit"
                        className="ui-btn ui-btn-primary"
                        disabled={!text.trim() || busy || unknownResult}
                    >
                        {busy ? "Đang xử lý..." : "Gửi lệnh →"}   
                    </button>
                </form>

                <p className="mt-3 text-xs text-[#819489]">
                    Có thể ra lệnh cho nhiều Device.
                    Nhận dạng giọng nói phụ thuộc trình duyệt và quyền microphone.
                </p>

                {/* 3. KẾT QUẢ CHƯA XÁC ĐỊNH */}
                {unknownResult && (
                    <div className="ui-alert-warning mt-4">
                        Kết quả chưa xác định do mất kết nối.
                        Hãy đối soát MCU với Registry trước khi gửi lại lệnh.
                    </div>
                )}

                {/* LỖI */}
                {error && (
                    <p role="alert" className="ui-alert-error mt-4">
                        {error}
                    </p>
                )}

                {/* HỖ TRỢ RESPONSE CŨ CỦA NLP */}
                {candidates.length > 0 && (
                    <div className="ui-alert-warning mt-4">
                        Device gợi ý:{" "}
                        {candidates
                            .map(item =>
                                item.deviceName ||
                                `#${item.deviceId}`
                            )
                            .join(", ")}
                    </div>
                )}

                {/* 4. KẾT QUẢ LỆNH */}
                {result && (
                    <div className="mt-5 rounded-xl border border-[#e1eae2] bg-[#fbfdfb] p-4 sm:p-5">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <p className="text-xs text-[#7b9182]">
                                    Câu lệnh
                                </p>

                                <p className="mt-1 font-semibold text-[#213c2b]">
                                    {result.text || text}
                                </p>

                                <p className="mt-1 text-xs text-[#7b9182]">
                                    {result.intent} · {result.predictor}
                                    {" · "}
                                    {result.deviceTags?.join(", ")}
                                </p>
                            </div>

                            <span
                                className={
                                    "ui-badge " +
                                    (result.state === "failed"
                                        ? "ui-badge-red"
                                        : result.state === "partial"
                                            ? "ui-badge-neutral"
                                            : "ui-badge-green")
                                }
                            >
                                {result.state || "success"}
                            </span>
                        </div>

                        {/* 5. TỔNG HỢP NHIỀU DEVICE */}
                        {Array.isArray(result.results) && (
                            <p className="mt-4 text-sm text-[#5c7565]">
                                Thành công: {result.successCount ?? 0}
                                {" / "}
                                {result.totalDevices ?? items.length}
                                {" · "}
                                Thất bại: {result.failedCount ?? 0}
                            </p>
                        )}

                        <div className="mt-4 space-y-3">
                            {items.map((item, index) => {
                                const device = item.device || result.device || {};
                                const payload =item.result || item;
                                const failed = item.state === "failed";

                                return (
                                    <div
                                        key={`${device.deviceId ?? index}-${index}`}
                                        className="rounded-lg border border-[#e1eae2] bg-white p-4"
                                    >
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <div>
                                                <p className="font-semibold text-[#24412f]">
                                                    {device.deviceName ||
                                                        `Device #${device.deviceId ?? "?"}`}
                                                </p>

                                                <p className="mt-1 text-xs text-[#83958a]">
                                                    ID #{device.deviceId ?? "—"}
                                                    {" · "}
                                                    MCU #{device.microcontrollerId ?? "—"}
                                                    {" · "}
                                                    GPIO {device.gpio ?? "—"}
                                                </p>
                                            </div>

                                            <span
                                                className={
                                                    "ui-badge " +
                                                    (failed
                                                        ? "ui-badge-red"
                                                        : "ui-badge-green")
                                                }
                                            >
                                                {failed
                                                    ? "Thất bại"
                                                    : "Thành công"}
                                            </span>
                                        </div>

                                        <p className="mt-3 text-sm">
                                            {operationLabel(
                                                item.operation ||
                                                result.operation
                                            )}
                                        </p>

                                        {failed ? (
                                            <p className="mt-1 text-sm text-red-700">
                                                {typeof item.message === "string"
                                                    ? item.message
                                                    : JSON.stringify(
                                                        item.message ||
                                                        "Không thực hiện được"
                                                    )}
                                            </p>
                                        ) : (
                                            <div className="mt-1 space-y-1 text-sm text-[#607668]">
                                                {payload.commandId && (
                                                    <p>
                                                        Command ID: {payload.commandId}
                                                    </p>
                                                )}

                                                {payload.currentStatus && (
                                                    <p>
                                                        Trạng thái: {payload.currentStatus}
                                                    </p>
                                                )}

                                                {payload.schedule && (
                                                    <p>
                                                        Schedule ID: #
                                                        {payload.schedule.id ?? "—"}
                                                        {" · "}
                                                        Action:{" "}
                                                        {payload.schedule.action ?? "—"}
                                                    </p>
                                                )}

                                                {payload.scheduleId != null && (
                                                    <p>
                                                        Schedule đã hủy: #
                                                        {payload.scheduleId}
                                                    </p>
                                                )}

                                                {payload.message && (
                                                    <p>{payload.message}</p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </section>
    );
}