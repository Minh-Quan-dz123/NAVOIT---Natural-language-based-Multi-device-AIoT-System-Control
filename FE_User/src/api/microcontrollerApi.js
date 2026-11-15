
import { apiRequest } from "./apiClient";

const BASE_URL = "/api/microcontroller";

// 1. USER XEM MCU CỦA MÌNH

// GET /api/microcontroller
export async function getMyMicrocontrollers() {
    return await apiRequest(BASE_URL);
}

// GET /api/microcontroller/{id}
export async function getMyMicrocontrollerById(id) {
    return await apiRequest(`${BASE_URL}/${id}`);
}

// GET /api/microcontroller/{id}/devices
export async function getMyMicrocontrollerDevices(id) {
    return await apiRequest(`${BASE_URL}/${id}/devices`);
}


// 2. ADMIN QUẢN LÝ TOÀN BỘ MCU
// GET /api/microcontroller/admin
export async function getAdminMicrocontrollers() {
    return await apiRequest(`${BASE_URL}/admin`);
}

// POST /api/microcontroller
// userId có thể null khi MCU chưa có chủ sở hữu.
export async function createMicrocontroller(type, macAddress, userId = null) 
{
    const body = {type, macAddress};
    if (userId !== null) body.userId = userId;
    return await apiRequest(BASE_URL, "POST", body);
}

// PATCH /api/microcontroller/{id}
export async function updateMicrocontroller(id, type, macAddress) {
    return await apiRequest(`${BASE_URL}/${id}`, "PATCH", {
        type,
        macAddress,
    });
}

// PATCH /api/microcontroller/{id}/owner
export async function transferMicrocontroller(id, userId) {
    return await apiRequest(
        `${BASE_URL}/${id}/owner`,
        "PATCH",
        { userId }
    );
}

// DELETE /api/microcontroller/{id}
export async function deleteMicrocontroller(id) {
    return await apiRequest(`${BASE_URL}/${id}`, "DELETE");
}
