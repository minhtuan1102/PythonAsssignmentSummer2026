# AI Engine Implementation Report

Ngày lập report: 2026-06-14

## 1. Mục Tiêu

Mục tiêu của phần triển khai này là dựng `AI Engine Server` cho hệ thống phân tích ván cờ, nối đủ 3 bước trong plan:

1. **Step 1 - Stockfish Analysis**
   - Nhận PGN.
   - Replay từng nước bằng `python-chess`.
   - Gọi Stockfish trước và sau mỗi nước.
   - Sinh `cpl_sequence`, `blunder_flags`, và dữ liệu phụ trợ cho agent.

2. **Step 2 - ELO Prediction**
   - Rút logic từ `app_demo.py`.
   - Load model `models/Hikaru_Nakamura_V1`.
   - Chuẩn hóa board states, clock times, CPL, blunder flags.
   - Chạy `RatingNet` để dự đoán `white_elo`, `black_elo`.

3. **Step 3 - Multi-Agent Explanation**
   - Data Miner: tổng hợp dữ liệu, ECO, stats, critical moves.
   - Tactician: phân tích lỗi chiến thuật bằng LLM.
   - Head Coach: viết nhận xét tiếng Việt cuối cùng.

Server cần cung cấp endpoint chính:

```text
POST /api/predict-elo
```

và trả response theo dạng:

```json
{
  "success": true,
  "data": {
    "white_elo": 1606,
    "black_elo": 1607,
    "eco": {},
    "stats": {},
    "explanation": "..."
  },
  "error": null
}
```

## 2. Cấu Trúc Code Đã Tạo

Package mới nằm tại:

```text
src/ai_engine/
```

Các file chính:

```text
src/ai_engine/
├── api_models.py
├── config.py
├── errors.py
├── full_pipeline.py
├── main.py
├── pipeline.py
├── predictor.py
├── server.py
├── stockfish_analyzer.py
├── schemas.py
│
├── agents/
│   ├── data_miner.py
│   ├── tactician.py
│   └── head_coach.py
│
├── llm/
│   ├── client.py
│   └── json_utils.py
│
├── services/
│   └── opening_book.py
│
└── eco_data/
    └── eco.json
```

## 3. Luồng Hoạt Động Tổng Thể

Luồng chính nằm trong `PredictEloPipeline` tại `full_pipeline.py`.

```text
Request từ Web
    |
    v
POST /api/predict-elo
    |
    v
StockfishAnalyzer.analyze(pgn)
    |
    |-- cpl_sequence
    |-- blunder_flags
    |-- stockfish_records
    v
EloPredictor.predict(...)
    |
    |-- white_elo
    |-- black_elo
    v
MultiAgentAnalyst.run(AnalysisContext)
    |
    |-- DataMinerAgent
    |-- TacticianAgent
    |-- HeadCoachAgent
    v
JSON response
```

Code nối Step 2 sang Step 3:

```python
report = self.analyst.run(
    AnalysisContext(
        pgn=pgn,
        cpl_sequence=stockfish_result.cpl_sequence,
        blunder_flags=stockfish_result.blunder_flags,
        clock_times=clock_times,
        result=result,
        time_control=time_control,
        white_elo=prediction.white_elo,
        black_elo=prediction.black_elo,
        stockfish_records=stockfish_result.stockfish_records,
    )
)
```

Như vậy Step 3 nhận đủ dữ liệu từ Step 1 và Step 2.

## 4. Step 1 - Stockfish Analysis

File:

```text
src/ai_engine/stockfish_analyzer.py
```

Các thành phần chính:

- `_score_to_cp(score, turn)`
- `analyze_game_cpl_sequence(moves_san, engine, depth)`
- `StockfishAnalyzer`
- `StockfishAnalysisResult`

Output của Step 1:

```python
StockfishAnalysisResult(
    cpl_sequence=(...),
    blunder_flags=(...),
    stockfish_records=(...)
)
```

`stockfish_records` gồm thông tin bổ sung cho LLM:

- `ply`
- `move_number`
- `side`
- `move`
- `fen_before`
- `fen_after`
- `best_move_uci`
- `eval_before_cp`
- `eval_after_cp`
- `cpl`

Logic blunder:

```python
blunder = cpl > 200
```

Lưu ý đã sửa:

- Parser PGN đã chuyển sang `chess.pgn.read_game`, thay vì split string thủ công.
- Nhờ đó chịu được PGN có header tốt hơn.

## 5. Step 2 - ELO Prediction

File:

```text
src/ai_engine/predictor.py
```

Đã rút từ `app_demo.py`:

- `CONFIG`
- `RatingNet`
- `encode_board(board)`
- `replay_game(moves_san)`
- `prepare_game(row, config)`

Thêm wrapper runtime:

- `prepare_game_from_sequences(...)`
- `EloPredictor`
- `EloPrediction`

Model mặc định:

```text
models/Hikaru_Nakamura_V1
```

Các input đưa vào model:

- Board states: `[1, T, 12, 8, 8]`
- Clock times normalized
- CPL sequence normalized
- Blunder flags
- Sequence length

Denormalize ELO:

```python
elo = pred * CONFIG["ratings_std"] + CONFIG["ratings_mean"]
```

## 6. Step 3 - Multi-Agent Analyst

Orchestrator:

```text
src/ai_engine/pipeline.py
```

Agents:

```text
src/ai_engine/agents/data_miner.py
src/ai_engine/agents/tactician.py
src/ai_engine/agents/head_coach.py
```

### 6.1 Data Miner Agent

Nhiệm vụ:

- Parse PGN.
- Match ECO.
- Tính stats:
  - `white_avg_cpl`
  - `black_avg_cpl`
  - `white_blunders`
  - `black_blunders`
  - `total_moves`
- Lọc các nước đáng phân tích.

Sửa quan trọng đã thực hiện:

Ban đầu Data Miner lấy top 3 CPL dù CPL rất nhỏ, ví dụ 5, 6, 11. Điều này khiến LLM phóng đại thành "sai lầm chiến thuật nghiêm trọng".

Đã sửa logic:

```python
critical move = is_blunder or cpl >= 50
```

Với ván có CPL thấp, `critical_blunders` sẽ rỗng.

### 6.2 Tactician Agent

Nhiệm vụ:

- Nhận `critical_blunders`.
- Gọi LLM để phân tích chiến thuật.
- Ép output JSON:

```json
{
  "analysis": [
    {
      "move_number": 18,
      "side": "black",
      "move": "Qd5",
      "reason": "...",
      "category": "fork|pin|hanging_piece|king_safety|opening|endgame|other",
      "severity": "blunder|mistake|inaccuracy"
    }
  ]
}
```

Prompt đã được siết:

- Chỉ phân tích các nước có trong `critical_blunders`.
- Không gọi minor CPL là blunder/mistake.
- Không chê các nước khai cuộc lý thuyết như `e5`, `Nc6`, `a6` chỉ vì best move khác ở depth thấp.

### 6.3 Head Coach Agent

Nhiệm vụ:

- Nhận stats, tactical report, ELO dự đoán.
- Viết `explanation` tiếng Việt.

Prompt đã được siết:

- Nếu không có critical blunder, phải nói rõ ván không có lỗi chiến thuật lớn.
- Không tự bịa lỗi khai cuộc.
- Nếu CPL thấp, nhận xét theo hướng hai bên chơi ổn định.

## 7. LLM Client

File:

```text
src/ai_engine/llm/client.py
```

Client dùng OpenAI-compatible API:

```text
POST {LLM_AGENT_BASE_URL}/chat/completions
```

Các biến env:

```env
LLM_AGENT_API_KEY=
LLM_AGENT_BASE_URL=
LLM_AGENT_MODEL=
LLM_AGENT_TIMEOUT_SECONDS=30
LLM_AGENT_MAX_RETRIES=2
LLM_AGENT_TEMPERATURE=0.2
LLM_AGENT_JSON_MODE=false
```

Trong quá trình test, endpoint `/models` trả về:

```text
qwen2.5:7b
```

Vì server LLM local bị timeout khi dùng `response_format={"type": "json_object"}`, đã chuyển:

```env
LLM_AGENT_JSON_MODE=false
```

LLM vẫn bị ép JSON bằng prompt và parser `extract_json_object`.

## 8. API Server

File:

```text
src/ai_engine/server.py
```

Endpoint:

```text
GET /health
POST /api/predict-elo
POST /api/multi-agent-analysis
```

### 8.1 `/health`

Kiểm tra server sống:

```json
{
  "status": "ok"
}
```

### 8.2 `/api/predict-elo`

Endpoint chính cho web game server.

Request:

```json
{
  "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6",
  "clock_times": [5.2, 3.1, 12.0, 8.5, 2.1, 45.3, 3.0, 7.2],
  "result": "1-0",
  "time_control": "5+0"
}
```

Debug request:

```json
{
  "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6",
  "clock_times": [5.2, 3.1, 12.0, 8.5, 2.1, 45.3, 3.0, 7.2],
  "result": "1-0",
  "time_control": "5+0",
  "include_debug": true
}
```

Debug response có thêm:

- `critical_blunders`
- `tactical_report`
- `cpl_sequence`
- `blunder_flags`

## 9. Environment

File `.env` cần có:

```env
STOCKFISH_PATH=stockfish/stockfish-windows-x86-64-avx2.exe
STOCKFISH_DEPTH=12
ELO_MODEL_PATH=models/Hikaru_Nakamura_V1

LLM_AGENT_API_KEY=
LLM_AGENT_BASE_URL=http://localhost:11434/v1
LLM_AGENT_MODEL=qwen2.5:7b
LLM_AGENT_TIMEOUT_SECONDS=30
LLM_AGENT_MAX_RETRIES=2
LLM_AGENT_TEMPERATURE=0.2
LLM_AGENT_JSON_MODE=false
```

Ghi chú:

- Nếu LLM local không yêu cầu key, `LLM_AGENT_API_KEY` có thể để rỗng.
- Nếu dùng remote API cần key, điền value vào `LLM_AGENT_API_KEY`.

## 10. Cách Chạy Server

Khuyến nghị:

```powershell
conda run --no-capture-output -n chess python -m uvicorn src.ai_engine.main:app --host 0.0.0.0 --port 8000
```

Hoặc:

```powershell
conda activate chess
python -m uvicorn src.ai_engine.main:app --host 0.0.0.0 --port 8000
```

Lưu ý:

- Dùng `--no-capture-output` để Uvicorn log hiện live trên Windows.
- Server chạy foreground, không trả prompt lại cho tới khi bấm `Ctrl+C`.

## 11. Cách Test

### 11.1 Test health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected:

```json
{
  "status": "ok"
}
```

### 11.2 Test endpoint chính

```powershell
$body = @{
  pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6"
  clock_times = @(5.2, 3.1, 12.0, 8.5, 2.1, 45.3, 3.0, 7.2)
  result = "1-0"
  time_control = "5+0"
  include_debug = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/predict-elo" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### 11.3 Test Swagger UI

Mở:

```text
http://127.0.0.1:8000/docs
```

Chọn:

```text
POST /api/predict-elo
```

Sau đó bấm `Try it out`.

## 12. Kết Quả Test Đã Chạy

### 12.1 Compile

Command:

```powershell
conda run -n chess python -m compileall -f src\ai_engine
```

Kết quả:

```text
Pass
```

### 12.2 Step 1 - Stockfish

Test với PGN:

```text
1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6
```

Kết quả:

```text
cpl_sequence length: 8
blunder_flags length: 8
stockfish_records length: 8
```

### 12.3 Step 2 - ELO Model

Model:

```text
models/Hikaru_Nakamura_V1
```

Kết quả smoke test:

```text
white_elo ~= 1108-1606
black_elo ~= 1109-1607
```

Giá trị thay đổi theo `STOCKFISH_DEPTH` và CPL sequence thực tế.

### 12.4 Full Pipeline

Test qua:

```text
POST /api/predict-elo
```

Kết quả:

```json
{
  "success": true,
  "data": {
    "eco": {
      "code": "C70",
      "name": "Ruy Lopez: Morphy Defense"
    },
    "stats": {
      "white_avg_cpl": 2.8,
      "black_avg_cpl": 7.0,
      "white_blunders": 0,
      "black_blunders": 0,
      "total_moves": 8
    },
    "white_elo": 1606,
    "black_elo": 1607,
    "critical_blunders": [],
    "tactical_report": {
      "analysis": []
    },
    "cpl_sequence": [5, 6, 2, 11, 2, 11, 2, 0],
    "blunder_flags": [0, 0, 0, 0, 0, 0, 0, 0]
  },
  "error": null
}
```

## 13. Vấn Đề Đã Gặp Và Cách Xử Lý

### 13.1 Uvicorn không hiện log khi chạy bằng `conda run`

Triệu chứng:

```text
conda run -n chess uvicorn ...
```

Terminal không in gì, tưởng server đứng.

Nguyên nhân:

- `conda run` trên Windows capture output.

Cách xử lý:

```powershell
conda run --no-capture-output -n chess python -m uvicorn src.ai_engine.main:app --host 0.0.0.0 --port 8000
```

### 13.2 Server đang chạy nhưng terminal không trả prompt

Đây là hành vi bình thường của Uvicorn. Server chạy foreground và chỉ dừng khi bấm:

```text
Ctrl+C
```

### 13.3 LLM JSON mode timeout

Triệu chứng:

- `/models` OK.
- `/chat/completions` timeout khi bật `response_format`.

Cách xử lý:

```env
LLM_AGENT_JSON_MODE=false
```

Vẫn ép JSON bằng prompt và parser.

### 13.4 LLM over-analysis minor CPL

Triệu chứng:

- CPL chỉ 5-11.
- Không có blunder.
- LLM vẫn nói "sai lầm chiến thuật nghiêm trọng".

Nguyên nhân:

- Data Miner gửi top 3 CPL dù CPL rất nhỏ.

Cách xử lý:

```python
critical move = is_blunder or cpl >= 50
```

Kết quả sau sửa:

```json
"critical_blunders": [],
"tactical_report": { "analysis": [] }
```

## 14. Trạng Thái Hiện Tại

Đã hoàn thành:

- FastAPI server.
- Endpoint `/api/predict-elo`.
- Step 1 Stockfish.
- Step 2 ELO model.
- Step 3 multi-agent.
- Env config.
- Swagger UI.
- Debug response.
- Test end-to-end.

Đã xác nhận:

- Server chạy ở port `8000`.
- `/health` OK.
- `/api/predict-elo` OK.
- Response đúng contract.
- Web có thể gọi endpoint này trực tiếp.

## 15. Việc Cần Làm Tiếp Theo

1. Nối Web Game Server sang:

```text
http://<AI_ENGINE_HOST>:8000/api/predict-elo
```

2. Nếu web chạy cùng máy:

```text
http://127.0.0.1:8000/api/predict-elo
```

3. Nếu web chạy máy khác trong LAN/VPN:

```text
http://<IP_MAY_HOST>:8000/api/predict-elo
```

4. Mở firewall port `8000` nếu máy khác không gọi được.

5. Test với PGN dài hơn để đánh giá:

- Response time.
- Chất lượng ELO.
- Chất lượng explanation.
- Độ ổn định Stockfish.

