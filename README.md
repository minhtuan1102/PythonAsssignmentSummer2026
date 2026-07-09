# PythonAsssignmentSummer2026

Whess là ứng dụng web chơi cờ vua realtime cho 2 người trên cùng một máy, kèm phân tích AI sau ván đấu. Người chơi tạo phòng, người thứ hai vào bằng mã phòng, hai tab trình duyệt đồng bộ qua Socket.IO, backend kiểm tra luật cờ và đồng hồ, sau đó gửi ván đấu sang AI service để dự đoán ELO và sinh nhận xét tiếng Việt.

## Tính năng chính

- Tạo phòng và vào phòng bằng mã.
- Chơi cờ realtime giữa 2 tab trình duyệt.
- Backend validate nước đi bằng `python-chess`.
- Đồng hồ server-authoritative với các mốc 3, 5, 10, 15 phút.
- Kết thúc ván do chiếu bí, hết giờ, xin thua, hòa hoặc rời phòng.
- Gọi AI service sau trận để phân tích PGN, ECO, CPL, blunder và ELO dự đoán.
- Frontend hiển thị bàn cờ, lịch sử nước đi, đồng hồ, kết quả và báo cáo AI.

## Kiến trúc

```text
PythonAsssignmentSummer2026/
├── Backend/                    # Web Game Server: FastAPI + Socket.IO
├── Frontend/chessFE/           # React + Vite frontend
├── Whess-AI-Server-main/       # AI service phân tích ván cờ
├── whess-technical-specification.md
└── README.md
```

Luồng chính:

1. Frontend kết nối Web Game Server bằng Socket.IO.
2. Backend quản lý phòng, luật cờ, đồng hồ và kết quả.
3. Khi ván kết thúc, backend gọi AI service qua endpoint `/api/predict-elo`.
4. Frontend nhận `analysis_result` và hiển thị báo cáo.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|:--|:--|
| Frontend | React, Vite, TypeScript, Tailwind CSS, Socket.IO Client |
| Backend | Python 3.11+, FastAPI, Uvicorn, python-socketio, python-chess |
| AI Service | Python 3.11+, FastAPI, Stockfish, LLM API |

## Yêu cầu môi trường

- Python 3.11 trở lên.
- Node.js và npm.
- Stockfish 16.1 hoặc bản tương thích.
- API key LLM nếu muốn chạy đầy đủ phần nhận xét AI.

## Cài đặt và chạy

Nên mở 3 terminal riêng: AI service, backend và frontend.

### 1. Chạy AI Service

```powershell
cd D:\PythonAsssignmentSummer2026\Whess-AI-Server-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo file `.env` từ `.env.example`, sau đó cấu hình tối thiểu:

```env
STOCKFISH_PATH=C:/stockfish/stockfish-windows-x86-64.exe
LLM_AGENT_API_URL=https://api.openai.com/v1/chat/completions
LLM_AGENT_API_KEY=your_api_key_here
```

Khởi động service:

```powershell
python -m uvicorn src.ai_engine.main:app --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### 2. Chạy Backend

```powershell
cd D:\PythonAsssignmentSummer2026\Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m whess_backend
```

Backend mặc định chạy ở `http://localhost:3000`.

Các biến môi trường backend có thể cấu hình trong `.env`:

```env
PORT=3000
AI_ENGINE_URL=http://localhost:8000/api/predict-elo
AI_ENGINE_TIMEOUT_MS=60000
AI_ENGINE_INCLUDE_DEBUG=true
ROOM_CODE_LENGTH=6
ROOM_INACTIVE_CLEANUP_MS=1800000
CLOCK_UPDATE_INTERVAL_MS=1000
```

### 3. Chạy Frontend

```powershell
cd D:\PythonAsssignmentSummer2026\Frontend\chessFE
npm install
npm run dev
```

Mở URL mà Vite hiển thị, thường là `http://localhost:5173`.

## Cách demo

1. Chạy đủ 3 service: AI service port `8000`, backend port `3000`, frontend port `5173`.
2. Mở frontend ở tab trình duyệt thứ nhất.
3. Chọn thời lượng và tạo phòng.
4. Copy mã phòng.
5. Mở frontend ở tab thứ hai và nhập mã phòng để tham gia.
6. Hai tab lần lượt đi cờ.
7. Khi ván kết thúc, frontend hiển thị kết quả cơ bản trước, sau đó cập nhật phân tích AI nếu service phản hồi thành công.

## Script hữu ích

Frontend:

```powershell
npm run dev
npm run build
npm run lint
npm run preview
```

Backend:

```powershell
python -m whess_backend
```

AI Service:

```powershell
python -m uvicorn src.ai_engine.main:app --host 0.0.0.0 --port 8000
python download_eco.py
```

## Tài liệu liên quan

- `whess-technical-specification.md`: tài liệu phân tích và thiết kế tổng thể.
- `Backend/IMPLEMENTATION_GUIDE.md`: contract và hướng dẫn triển khai backend.
- `Frontend/IMPLEMENTATION_GUIDE.md`: contract và hướng dẫn triển khai frontend.
- `Whess-AI-Server-main/README.md`: hướng dẫn chi tiết cho AI service.

## Ghi chú phạm vi

- Dự án demo không có đăng nhập, database, matchmaking công khai hoặc spectator.
- Trạng thái phòng lưu RAM-only.
- Refresh tab sẽ mất phiên và quay về lobby.
- Một room chỉ chơi một ván; muốn chơi lại thì tạo room mới.
- Nếu AI service lỗi, ván đấu vẫn kết thúc bình thường và frontend hiển thị lỗi phân tích.
