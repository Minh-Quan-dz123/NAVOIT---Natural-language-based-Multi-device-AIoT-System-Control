
import { apiRequest } from "./apiClient";

const BASE_URL = "/api/devicetype";

// User và Admin: xem danh mục.
export async function getDeviceTypes() {
    return await apiRequest(BASE_URL);
}

export async function getDeviceTypeById(id) {
    return await apiRequest(`${BASE_URL}/${id}`);
}

// Admin: thêm loại thiết bị.
export async function createDeviceType(typeName, allowedStatuses) {
    return await apiRequest(BASE_URL, "POST", {
        typeName,
        allowedStatuses,
    });
}

// Admin: cập nhật loại thiết bị.
export async function updateDeviceType(id, typeName, allowedStatuses) 
{
    return await apiRequest(`${BASE_URL}/${id}`, "PATCH", {
        typeName,
        allowedStatuses,
    });
}

// Admin: xóa loại thiết bị.
export async function deleteDeviceType(id) {
    return await apiRequest(`${BASE_URL}/${id}`, "DELETE");
}
