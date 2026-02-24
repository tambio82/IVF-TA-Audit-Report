# 🏥 IVF Tâm Anh HN – Quality Audit System

Hệ thống Quản lý Quality Audit xây dựng bằng **Streamlit** và **Supabase**.

---

## 📦 Cấu trúc dự án

```
ivf_audit/
├── app.py                      # Entry point chính
├── requirements.txt            # Python dependencies
├── supabase_schema.sql         # Database schema (chạy trên Supabase)
├── .env.example                # Mẫu cấu hình môi trường
├── .streamlit/
│   └── secrets.toml            # Secrets cho Streamlit Cloud
├── modules/
│   ├── module1_planning.py     # Module 1: Kế hoạch Audit
│   ├── module2_reporting.py    # Module 2: Ghi nhận Kết quả
│   ├── module3_dashboard.py    # Module 3: Dashboard Analytics
│   ├── module4_export.py       # Module 4: Xuất Báo cáo
│   ├── module5_users.py        # Module 5: Quản lý Users
│   └── module6_options.py      # Module 6: Cấu hình
└── utils/
    ├── db.py                   # Kết nối Supabase & helper functions
    └── auth.py                 # Authentication & session management
```

---

## 🚀 Hướng dẫn Cài đặt

### Bước 1: Tạo dự án Supabase

1. Vào [supabase.com](https://supabase.com) → Tạo project mới
2. Vào **SQL Editor** → Paste toàn bộ nội dung file `supabase_schema.sql` → Chạy
3. Sao chép **Project URL** và **anon public key** từ Settings → API

### Bước 2: Cài đặt môi trường local

```bash
# Clone/tải source code
cd ivf_audit

# Tạo virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# hoặc: venv\Scripts\activate   # Windows

# Cài dependencies
pip install -r requirements.txt

# Cấu hình credentials
cp .env.example .env
# Mở .env và điền SUPABASE_URL và SUPABASE_KEY

# Chạy ứng dụng
streamlit run app.py
```

### Bước 3: Đăng nhập lần đầu

- Tài khoản mặc định: **admin / Admin@123**
- ⚠️ **Đổi mật khẩu ngay** sau lần đăng nhập đầu tiên!

---

## ☁️ Deploy lên Streamlit Cloud

1. Push code lên GitHub (bỏ file `.env`, giữ `.env.example`)
2. Vào [share.streamlit.io](https://share.streamlit.io) → New app
3. Điền repo, branch, file: `app.py`
4. Vào **Advanced settings → Secrets** → Paste:
   ```toml
   SUPABASE_URL = "https://xxx.supabase.co"
   SUPABASE_KEY = "your-key"
   ```
5. Deploy!

---

## 📋 Tính năng các Module

### Module 1: Kế hoạch Audit
- Tạo và quản lý đợt audit theo năm (2025-2029), theo thứ tự đợt (1-12)
- Phân loại: Cấp độ (Urgent/Moderate/Intensive/RTAC), Tính chất (Bổ sung/Định kỳ/Theo yêu cầu)
- Thêm mục tiêu động với bộ phận liên quan, KPIs và Outcomes

### Module 2: Ghi nhận Kết quả
- Tra cứu tự động từ Module 1 (năm, đợt → mục tiêu, KPIs)
- Ghi nhận từng vấn đề phát hiện với:
  - Đánh giá định tính và định lượng (0-5, mỗi mức 0.5)
  - FMEA: S/O/D (1-10), tính RPN tự động
  - So sánh RPN với đợt trước
  - Process Indicator, giải pháp khắc phục
  - 3 tùy chọn gợi ý thêm

### Module 3: Dashboard
- Biểu đồ time series điểm KPI theo đợt/quý/6 tháng/năm
- Phân loại kết quả (Dưới kỳ vọng / Tạm chấp nhận / Kết quả ổn)
- So sánh RPN cũ vs mới
- Thống kê tỷ lệ % gợi ý thêm
- Phân tích theo bộ phận

### Module 4: Xuất Báo cáo
- Xuất kế hoạch (HTML + Excel) để trình lãnh đạo
- Xuất kết quả audit (HTML + Excel)
- Xuất toàn bộ dữ liệu Excel (3 sheets: Kế hoạch, Mục tiêu-KPI, Kết quả)

### Module 5: Quản lý Users
- Tạo/sửa/xóa tài khoản
- 3 vai trò: Admin / Auditor / Viewer
- Đổi mật khẩu

### Module 6: Cấu hình
- Quản lý danh sách bộ phận (thêm/sửa/xóa)
- Cấu hình năm audit
- Tài liệu hướng dẫn thang điểm FMEA

---

## 🔒 Bảo mật

- Mật khẩu được hash bằng **bcrypt**
- Phân quyền theo vai trò (admin/auditor/viewer)
- Có thể bật Row Level Security (RLS) trên Supabase nếu cần

---

## 📞 Hỗ trợ

Liên hệ team IT IVF Tâm Anh HN để được hỗ trợ cài đặt và vận hành.
