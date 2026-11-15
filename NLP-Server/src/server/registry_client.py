import httpx

class RegistryClient:

    def __init__(self, base_url: str, timeout_seconds: float = 5.0):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    async def get_device_catalog(self, token: str) -> dict:

        # 1. Tạo HTTP Client
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            follow_redirects=False,
        ) as client:

            # 2. call api tới Device Registry
            response = await client.get("/api/device/catalog",
                headers={"Authorization": f"Bearer {token}"},
            )

        # 3. Kiểm tra HTTP status
        response.raise_for_status()

        # 4. Đọc kết quả JSON
        data = response.json()

        # 5. Kiểm tra định dạng cơ bản
        if not isinstance(data, dict) or not isinstance(data.get("devices"), list):
            raise ValueError("Device Catalog không đúng định dạng.")

        return data
