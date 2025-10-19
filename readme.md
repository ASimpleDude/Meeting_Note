## Cài đặt

### 1. Xóa môi trường ảo cũ (nếu có)
Remove-Item -Recurse -Force .venv


### 2. Tạo môi trường ảo mới
python -m venv .venv


### 3. Kích hoạt môi trường ảo
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1


> **Lưu ý:** Lệnh trên chỉ áp dụng cho Terminal trong VS CODE.

### 4. Cài đặt các package cần thiết
pip install -r requirements.txt


## Chạy ứng dụng
uvicorn api.main:app --reload --port 8000