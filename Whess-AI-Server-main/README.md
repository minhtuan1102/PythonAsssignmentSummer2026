# Whess AI Server (Multi-Agent Chess Engine)

Đây là Backend Server cung cấp trí tuệ nhân tạo cho dự án **Whess**. Hệ thống được xây dựng trên kiến trúc Đa tác tử (Multi-Agent) để mô phỏng một ban huấn luyện cờ vua thực thụ, kết hợp giữa sức mạnh tính toán của **Stockfish 16.1** và khả năng ngôn ngữ của **LLM (Gemini/ChatGPT)**.

---

## 🏛️ Cấu trúc Codebase (Theo chuẩn Separation of Concerns)

```text
Whess-AI-Server/
├── src/ai_engine/
│   ├── api/
│   │   └── routers.py          # (Lớp Giao tiếp) Định nghĩa API Endpoint (VD: /api/predict-elo) để Web Server gọi.
│   ├── core/
│   │   ├── config.py           # Quản lý cấu hình, đọc biến môi trường từ file .env.
│   │   └── full_pipeline.py    # Nhạc trưởng điều phối luồng 3 bước: Stockfish -> Predict ELO -> LLM Agents.
│   ├── ai_agents/
│   │   ├── data_miner.py       # (Agent 1 - Máy Xúc): Chạy Stockfish, tính toán CPL, bắt lỗi Blunder thô.
│   │   ├── tactician.py        # (Agent 2 - Chuyên Gia): Đọc FEN, giải thích chi tiết các lỗi mất quân, chĩa đôi...
│   │   ├── head_coach.py       # (Agent 3 - HLV Trưởng): Tổng hợp toàn bộ dữ liệu, viết báo cáo đánh giá cực gắt.
│   │   ├── orchestrator.py     # Quản lý vòng đời và thứ tự chạy của các Agents.
│   │   └── prompts/            # Thư mục chứa kịch bản (Prompt) chuyên biệt để ép LLM đóng vai chuyên gia.
│   ├── services/
│   │   ├── eco_data/           # Chứa file eco.json (Bách khoa toàn thư Khai cuộc với >3000 thế cờ).
│   │   └── opening_book.py     # Module tự động nhận diện tên Khai cuộc từ chuỗi PGN.
│   ├── models/
│   │   ├── predictor.py        # Nạp model Deep Learning (PyTorch) dự đoán ELO (Hikaru_V1).
│   │   └── stockfish_analyzer.py # Giao tiếp với file chạy C++ của Stockfish thông qua chuẩn UCI.
│   └── main.py                 # Điểm khởi chạy của FastAPI.
├── .env.example                # File mẫu chứa các biến môi trường cần thiết.
└── requirements.txt            # Danh sách thư viện Python.
```

---

## 🚀 Hướng dẫn Setup & Chạy Local (Cho Team Dev)

Để chạy được Server AI này dưới máy cá nhân, bạn làm tuần tự theo các bước sau:

### Bước 1: Cài đặt Môi trường Python
Chúng tôi khuyến nghị sử dụng `conda` để tránh xung đột thư viện.
```bash
conda create -n MMDS python=3.11
conda activate MMDS
pip install -r requirements.txt
```

### Bước 2: Tải Engine Stockfish 16.1
Hệ thống bắt buộc phải có Stockfish để tính toán CPL.
1. Truy cập: [Stockfish Download](https://stockfishchess.org/download/)
2. Tải bản Windows (`.exe`) hoặc Mac/Linux tương ứng.
3. Giải nén và lưu file `stockfish.exe` vào máy (Ví dụ: `C:/stockfish/stockfish-windows-x86-64.exe`).

### Bước 3: Cấu hình File `.env`
1. Tại thư mục gốc `Whess-AI-Server`, copy file `.env.example` và đổi tên thành `.env` (chú ý có dấu chấm ở đầu).
2. Mở file `.env` và điền 2 thông tin sống còn:
```env
# Trỏ đường dẫn tuyệt đối vào cái file .exe vừa tải ở Bước 2
STOCKFISH_PATH=C:/stockfish/stockfish-windows-x86-64.exe

# URL và API Key của LLM (Bắt buộc phải có để Agent chạy)
LLM_AGENT_API_URL=https://api.openai.com/v1/chat/completions
LLM_AGENT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
*(Lưu ý: File `.env` đã được liệt kê vào `.gitignore` để tránh lộ Key lên Github).*

### Bước 4: Tải Data Khai cuộc (Tùy chọn nếu chưa có)
Chạy script dưới đây để tự động kéo >3000 biến thể khai cuộc từ Lichess:
```bash
python download_eco.py
```

### Bước 5: Khởi động Server
Chạy lệnh sau tại thư mục gốc:
```bash
python -m uvicorn src.ai_engine.main:app --host 0.0.0.0 --port 8000
```
Server sẽ chạy ở địa chỉ: `http://localhost:8000`

---

## 🧪 Test API (Swagger UI)
Sau khi Server báo chạy thành công, hãy mở trình duyệt và truy cập:
👉 **http://localhost:8000/docs**

Tại đây, bạn tìm Endpoint `POST /api/predict-elo`, bấm **Try it out**, ném chuỗi PGN của một ván cờ vào mục `pgn` và bấm **Execute** để chiêm ngưỡng sức mạnh của dàn HLV AI!
