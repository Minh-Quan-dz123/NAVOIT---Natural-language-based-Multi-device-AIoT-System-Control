
"use client";

import { useEffect, useRef, useState } from "react";

// Khai báo kiểu dữ liệu cho Web Speech API
interface SpeechResult {
  isFinal: boolean;
  [index: number]: { transcript: string };
}

interface SpeechResultEvent {
  results: ArrayLike<SpeechResult>;
}

interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;

  onstart: (() => void) | null;
  onend: (() => void) | null;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;

  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor =
  new () => SpeechRecognitionInstance;

type SpeechWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

export default function Home() {
  const [transcript, setTranscript] = useState("");
  const [interimText, setInterimText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  // Kiểm tra trình duyệt có hỗ trợ SpeechRecognition hay không
  useEffect(() => {
    const browser = window as SpeechWindow;

    setIsSupported(
      Boolean(
        browser.SpeechRecognition ||
        browser.webkitSpeechRecognition
      )
    );

    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  // Bắt đầu Speech-to-Text
  const startListening = () => {
    const browser = window as SpeechWindow;

    const SpeechRecognition =
      browser.SpeechRecognition ||
      browser.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError("Trình duyệt không hỗ trợ Speech-to-Text.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    // Cấu hình Speech-to-Text
    recognition.lang = "vi-VN";
    recognition.continuous = true;
    recognition.interimResults = true;

    // Giữ lại văn bản từ những lần ghi âm trước
    const previousText = transcript.trim();

    recognition.onstart = () => {
      setIsListening(true);
      setError("");
    };

    recognition.onresult = (event) => {
      const finalParts: string[] = [];
      const interimParts: string[] = [];

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0]?.transcript.trim();

        if (!text) continue;

        if (result.isFinal) {
          finalParts.push(text);
        } else {
          interimParts.push(text);
        }
      }

      const finalText = finalParts.join(" ");

      setTranscript(
        [previousText, finalText].filter(Boolean).join(" ")
      );

      setInterimText(interimParts.join(" "));
    };

    recognition.onerror = (event) => {
      const messages: Record<string, string> = {
        "not-allowed": "Bạn chưa cấp quyền sử dụng microphone.",
        "audio-capture": "Không tìm thấy microphone.",
        "no-speech": "Không phát hiện giọng nói.",
        "network": "Lỗi kết nối dịch vụ nhận dạng giọng nói.",
      };

      setError(
        messages[event.error] ||
        `Lỗi nhận dạng: ${event.error}`
      );
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimText("");
    };

    try {
      setCopied(false);
      setIsListening(true);
      recognition.start();
    } catch {
      setIsListening(false);
      setError("Không thể bắt đầu nhận dạng giọng nói.");
    }
  };

  // Dừng Speech-to-Text
  const stopListening = () => {
    recognitionRef.current?.stop();
  };

  // Xóa kết quả
  const clearTranscript = () => {
    setTranscript("");
    setInterimText("");
    setCopied(false);
    setError("");
  };

  // Sao chép văn bản
  const copyTranscript = async () => {
    try {
      await navigator.clipboard.writeText(transcript);
      setCopied(true);
    } catch {
      setError("Không thể sao chép văn bản.");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-12 text-white">
      <div className="mx-auto max-w-3xl">

        {/* HEADER */}
        <header className="mb-8 text-center">
          <div className="mb-4 text-5xl">🎙️</div>

          <h1 className="text-3xl font-bold tracking-tight">
            Speech to Text
          </h1>

          <p className="mt-3 text-slate-400">
            Chuyển giọng nói tiếng Việt thành văn bản
          </p>
        </header>

        {/* MAIN CARD */}
        <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-xl sm:p-8">

          {/* TRẠNG THÁI */}
          <div className="mb-8 flex items-center justify-center gap-3">
            <span
              className={`h-3 w-3 rounded-full ${
                isListening
                  ? "animate-pulse bg-red-500"
                  : "bg-emerald-500"
              }`}
            />

            <span className="text-sm text-slate-300">
              {isListening
                ? "Đang nhận dạng giọng nói..."
                : "Sẵn sàng ghi âm"}
            </span>
          </div>

          {/* MICROPHONE */}
          <div className="mb-8 flex justify-center">
            <button
              onClick={
                isListening ? stopListening : startListening
              }
              disabled={isSupported !== true}
              className={`flex h-28 w-28 items-center justify-center rounded-full text-5xl shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40 ${
                isListening
                  ? "bg-red-600 shadow-red-600/20"
                  : "bg-blue-600 shadow-blue-600/20 hover:bg-blue-500"
              }`}
            >
              {isListening ? "⏹️" : "🎤"}
            </button>
          </div>

          <p className="mb-8 text-center text-sm text-slate-400">
            {isListening
              ? "Nhấn để dừng ghi âm"
              : "Nhấn microphone để bắt đầu nói"}
          </p>

          {/* THÔNG BÁO LỖI */}
          {isSupported === false && (
            <p className="mb-5 rounded-xl bg-amber-950 p-3 text-sm text-amber-300">
              Trình duyệt này không hỗ trợ SpeechRecognition.
            </p>
          )}

          {error && (
            <p className="mb-5 rounded-xl bg-red-950 p-3 text-sm text-red-300">
              {error}
            </p>
          )}

          {/* VĂN BẢN */}
          <div>
            <label
              htmlFor="transcript"
              className="mb-3 block text-sm font-semibold text-slate-300"
            >
              Văn bản nhận dạng
            </label>

            <textarea
              id="transcript"
              value={transcript}
              onChange={(e) => {
                setTranscript(e.target.value);
                setCopied(false);
              }}
              disabled={isListening}
              placeholder="Văn bản sẽ xuất hiện ở đây..."
              className="h-52 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 p-4 text-base text-white outline-none transition-colors placeholder:text-slate-600 focus:border-blue-500 disabled:opacity-80"
            />

            {interimText && (
              <p className="mt-3 text-sm italic text-blue-300">
                Đang nghe: {interimText}
              </p>
            )}
          </div>

          {/* BUTTONS */}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={copyTranscript}
              disabled={!transcript.trim()}
              className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-medium transition-colors hover:bg-blue-500 disabled:opacity-40"
            >
              {copied ? "✓ Đã sao chép" : "Sao chép"}
            </button>

            <button
              onClick={clearTranscript}
              disabled={isListening}
              className="rounded-lg border border-slate-700 px-5 py-3 text-sm font-medium transition-colors hover:bg-slate-800 disabled:opacity-40"
            >
              Xóa văn bản
            </button>
          </div>

        </section>

        <p className="mt-6 text-center text-xs text-slate-500">
          Ngôn ngữ nhận dạng: Tiếng Việt (vi-VN)
        </p>
      </div>
    </main>
  );
}
