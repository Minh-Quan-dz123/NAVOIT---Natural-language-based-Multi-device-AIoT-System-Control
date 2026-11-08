
from pathlib import Path
from urllib.request import urlretrieve
import zipfile

# Thư mục lưu mô hình trên ổ D
# Tránh đường dẫn chứa dấu cách và ký tự tiếng Việt
BASE_DIR = Path("D:/vncorenlp")

# URL GitHub
BASE_URL = "https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master"

# Danh sách file cần tải
FILES = [
    "VnCoreNLP-1.2.jar",
    "models/wordsegmenter/vi-vocab",
    "models/wordsegmenter/wordsegmenter.rdr",
]


def download_vncorenlp():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    for file in FILES:
        destination = BASE_DIR / file

        # Tạo thư mục nếu chưa tồn tại
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Bỏ qua nếu file đã tồn tại và không rỗng
        if destination.is_file() and destination.stat().st_size > 0:
            print(f"Already exists: {destination}")
            continue

        url = f"{BASE_URL}/{file}"

        try:
            print(f"Downloading: {file}")

            urlretrieve(url, destination)

            # Kiểm tra file JAR hợp lệ
            if file.endswith(".jar"):
                if not zipfile.is_zipfile(destination):
                    raise ValueError("Invalid JAR file")

            print(f"Downloaded: {destination}")

        except Exception as e:
            destination.unlink(missing_ok=True)
            print(f"Error downloading {file}: {e}")
            raise

    print("\nVnCoreNLP is ready!")
    print(f"Model directory: {BASE_DIR.resolve()}")


if __name__ == "__main__":
    download_vncorenlp()
