import { apiRequest } from "./apiClient";

const BASE_URL = "/api/microcontrollertype";

// 1. Lấy danh sách loại vi điều khiển
export async function getMicrocontrollerTypes() {
    return await apiRequest(BASE_URL);
}

// 2. Lấy một loại theo ID
export async function getMicrocontrollerTypeById(id) {
    return await apiRequest(`${BASE_URL}/${id}`);
}

// 3. Thêm loại vi điều khiển (Admin)
export async function createMicrocontrollerType(typeName) {
    return await apiRequest(BASE_URL, "POST", { typeName,});
}

// 4. Cập nhật loại vi điều khiển (Admin)
export async function updateMicrocontrollerType(id, typeName) {
    return await apiRequest(`${BASE_URL}/${id}`, "PATCH", {typeName,});
}

// 5. Xóa loại vi điều khiển (Admin)
export async function deleteMicrocontrollerType(id) {
    return await apiRequest(`${BASE_URL}/${id}`, "DELETE");
}
