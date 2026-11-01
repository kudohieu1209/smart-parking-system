# THIẾT KẾ CƠ SỞ DỮ LIỆU — DATABASE DESIGN

## 1. Mô hình quan hệ thực thể (ERD)

Hệ thống sử dụng SQLite (giai đoạn Lab/Phát triển) kết hợp SQLAlchemy ORM. Thiết kế tương thích hoàn toàn để chuyển đổi sang PostgreSQL hoặc MySQL khi lên production.

```mermaid
erDiagram
    RFID_CARD ||--o{ PARKING_SESSION : "authorizes"
    PARKING_SLOT ||--o{ PARKING_SESSION : "assigned_to"
    PARKING_SLOT ||--o{ SYSTEM_ALERT : "triggers"

    RFID_CARD {
        string card_uid PK "Mã định danh thẻ (UID)"
        string owner_name "Tên chủ thẻ"
        string vehicle_plate "Biển số xe đăng ký"
        string card_type "STANDARD, VIP, MONTHLY"
        boolean is_active "Trạng thái kích hoạt"
        datetime created_at "Thời gian tạo"
    }

    PARKING_SLOT {
        string slot_id PK "P01, P02, P03, P04"
        string status "EMPTY, OCCUPIED, MISMATCH, DISABLED"
        float sensor_distance_cm "Khoảng cách đo được gần nhất"
        boolean sensor_occupied "Trạng thái từ cảm biến"
        boolean camera_occupied "Trạng thái từ camera AI"
        float camera_confidence "Độ tin cậy nhận diện"
        boolean has_mismatch "Cờ phát hiện không khớp"
        datetime updated_at "Lần cập nhật cuối"
    }

    PARKING_SESSION {
        int id PK "Khóa chính tự tăng"
        string card_uid FK "Tham chiếu thẻ RFID"
        string vehicle_plate "Biển số xe tại thời điểm gửi"
        string slot_id FK "Vị trí đỗ (nếu xác định)"
        datetime entry_time "Thời điểm vào bãi"
        datetime exit_time "Thời điểm ra bãi"
        int duration_minutes "Thời gian gửi (phút)"
        int fee_amount "Phí gửi xe (VNĐ)"
        string status "ACTIVE, COMPLETED, CANCELLED"
        string notes "Ghi chú phiên"
    }

    SYSTEM_ALERT {
        int id PK "Khóa chính"
        string alert_type "MISMATCH, SENSOR_FAULT, GATE_OBSTRUCTION, UNAUTHORIZED"
        string slot_id "Vị trí liên quan (P01..P04 hoặc GATE)"
        string severity "INFO, WARNING, CRITICAL"
        string message "Nội dung cảnh báo chi tiết"
        boolean is_resolved "Đã xử lý hay chưa"
        datetime created_at "Thời điểm phát sinh"
    }
```

---

## 2. Chi tiết các bảng (Table Schema)

### 2.1. Bảng `rfid_cards`
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `card_uid` | VARCHAR(32) | PRIMARY KEY | Mã UID của thẻ RFID (VD: `TAG-8F2B10`) |
| `owner_name` | VARCHAR(100) | NOT NULL | Tên chủ phương tiện |
| `vehicle_plate` | VARCHAR(20) | NOT NULL, INDEX | Biển kiểm soát xe |
| `card_type` | VARCHAR(20) | DEFAULT 'STANDARD' | Loại thẻ: `STANDARD`, `VIP`, `STAFF` |
| `is_active` | BOOLEAN | DEFAULT 1 | 1: Đang hoạt động, 0: Đã khoá |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời điểm cấp thẻ |

### 2.2. Bảng `parking_slots`
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `slot_id` | VARCHAR(10) | PRIMARY KEY | Định danh vị trí (`P01`, `P02`, `P03`, `P04`) |
| `status` | VARCHAR(20) | DEFAULT 'EMPTY' | `EMPTY`, `OCCUPIED`, `MISMATCH`, `DISABLED` |
| `sensor_distance_cm` | FLOAT | DEFAULT 100.0 | Khoảng cách đo được từ cảm biến siêu âm |
| `sensor_occupied` | BOOLEAN | DEFAULT 0 | 1: Có xe theo cảm biến |
| `camera_occupied` | BOOLEAN | DEFAULT 0 | 1: Có xe theo camera AI |
| `camera_confidence` | FLOAT | DEFAULT 1.0 | Độ tin cậy nhận diện (0.0 - 1.0) |
| `has_mismatch` | BOOLEAN | DEFAULT 0 | Cờ báo không khớp giữa cảm biến và camera |
| `updated_at` | DATETIME | ON UPDATE CURRENT_TIMESTAMP | Thời điểm đồng bộ cuối cùng |

### 2.3. Bảng `parking_sessions`
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Mã định danh phiên gửi xe |
| `card_uid` | VARCHAR(32) | FOREIGN KEY -> `rfid_cards.card_uid` | Mã thẻ gửi xe |
| `vehicle_plate` | VARCHAR(20) | NULLABLE | Biển số xe ghi nhận |
| `slot_id` | VARCHAR(10) | NULLABLE, FK -> `parking_slots.slot_id` | Ô đỗ xe |
| `entry_time` | DATETIME | NOT NULL | Giờ xe vào bãi |
| `exit_time` | DATETIME | NULLABLE | Giờ xe ra bãi (NULL nếu đang gửi) |
| `duration_minutes` | INTEGER | DEFAULT 0 | Tổng thời gian đỗ tính theo phút |
| `fee_amount` | INTEGER | DEFAULT 0 | Số tiền thanh toán (VNĐ) |
| `status` | VARCHAR(20) | DEFAULT 'ACTIVE', INDEX | `ACTIVE`, `COMPLETED`, `CANCELLED` |
| `notes` | TEXT | NULLABLE | Ghi chú bất thường nếu có |

### 2.4. Bảng `system_alerts`
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Mã cảnh báo |
| `alert_type` | VARCHAR(30) | NOT NULL | Phân loại cảnh báo |
| `slot_id` | VARCHAR(10) | NULLABLE | Vị trí ô đỗ phát sinh |
| `severity` | VARCHAR(20) | DEFAULT 'WARNING' | `INFO`, `WARNING`, `CRITICAL` |
| `message` | TEXT | NOT NULL | Chi tiết sự kiện |
| `is_resolved` | BOOLEAN | DEFAULT 0 | Trạng thái đã xử lý |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời điểm ghi nhận |
