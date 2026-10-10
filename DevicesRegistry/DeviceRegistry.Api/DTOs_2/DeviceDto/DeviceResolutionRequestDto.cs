namespace DeviceRegistry.Api.DTOs;
// cho request ánh xạ tới request để lấy ra Device cần

public class DeviceResolutionRequestDto // Ánh xạ
{
    // ID của user cần tìm thiết bị
    public int UserId { get; set; }

    // Danh sách tag từ câu lệnh người dùng sau khi NLP xử lý
    // Ví dụ: ["bật", "đèn", "phòng khách"]
    public List<string> Tags { get; set; } = new();

}