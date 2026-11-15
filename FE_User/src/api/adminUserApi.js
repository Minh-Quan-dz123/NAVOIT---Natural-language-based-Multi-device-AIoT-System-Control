
import { apiRequest } from "./apiClient";

// Chỉ Admin được gọi API này.
// Kết quả: [{ id, username }, ...]
export async function getUsersForAssignment() {
    return await apiRequest("/api/admin/users/options");
}
