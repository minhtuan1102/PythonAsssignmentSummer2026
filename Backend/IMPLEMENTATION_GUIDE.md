# Whess Backend Implementation Guide

Mục tiêu: xây dựng Web Game Server greenfield cho Whess. Backend là nguồn sự thật cho phòng chơi, luật cờ, đồng hồ, kết quả ván và tích hợp AI service sau trận đấu.

Tài liệu này dành cho AI coding agent hoặc developer implement backend độc lập, nhưng phải tương thích chính xác với frontend và AI service.

---

## 1. Phạm Vi Backend

Backend cần làm:

| Hạng mục | Yêu cầu |
|:--|:--|
| Realtime server | Socket.IO server cho 2 tab chơi cờ. |
| Room system | Tạo phòng, join phòng, giới hạn 2 người. |
| Session | Không có session bền vững; refresh tab là mất phiên và quay về Lobby. |
| Chess rules | Validate bằng `python-chess`, không tin client. |
| Clock | Server-authoritative, đơn vị emit là millisecond. |
| Move history | Lưu SAN theo thứ tự nửa nước. |
| AI payload | Dựng PGN/movetext, `clock_times`, `result`, `time_control`, `include_debug`. |
| AI result | Emit `analysis_result` cho cả hai client. |
| Fallback | AI lỗi không làm crash game/result. |
| Static serving | Có thể phục vụ frontend build ở chế độ demo một cổng. |

Backend không cần làm:

| Không làm | Lý do |
|:--|:--|
| Database | Demo RAM-only. |
| Login/register | Không có user thật. |
| Matchmaking | Chỉ join bằng room code. |
| Rating persistence | AI dự đoán ELO ván đấu, không lưu hồ sơ. |
| Chat/spectator | Ngoài scope. |

---

## 2. Tech Stack Bắt Buộc

| Thành phần | Công nghệ |
|:--|:--|
| Runtime | Python 3.11+ |
| HTTP app | FastAPI |
| Server | Uvicorn |
| Realtime | python-socketio ASGI |
| Chess rules | `python-chess` package import là `chess` |
| HTTP client | `httpx` |
| Config | `.env` qua `python-dotenv` hoặc Pydantic settings |

Không thay backend sang Node/Express. Không thêm database.

---

## 3. Cấu Hình Môi Trường

| Biến | Mặc định | Ghi chú |
|:--|:--|:--|
| `PORT` | `3000` | Port Web Game Server. |
| `AI_ENGINE_URL` | `http://localhost:8000/api/predict-elo` | AI service có sẵn. |
| `AI_ENGINE_TIMEOUT_MS` | `60000` | Timeout gọi AI. |
| `AI_ENGINE_INCLUDE_DEBUG` | `true` | Luôn bật để FE có chart/blunder. |
| `ROOM_CODE_LENGTH` | `6` | Mã phòng. |
| `ROOM_INACTIVE_CLEANUP_MS` | `1800000` | Cleanup phòng inactive. |
| `CLOCK_UPDATE_INTERVAL_MS` | `1000` | Emit clock định kỳ. |

AI service chạy riêng ở `Whess-AI-Server-main` port `8000`. Backend chỉ gọi endpoint, không sửa AI service.

---

## 4. Kiến Trúc Module

Implement theo module trách nhiệm, tên file tùy codebase nhưng không trộn logic.

| Module | Trách nhiệm |
|:--|:--|
| Config | Đọc env, constants, default values. |
| Socket Gateway | Định nghĩa Socket.IO event handlers. |
| Room Manager | Tạo/join/leave/cleanup room RAM. |
| Game Engine | Bọc `python-chess`, validate move, sinh SAN, FEN, detect game over. |
| Clock Manager | Start/switch/stop clock, timeout task, ghi time spent. |
| AI Client | Dựng payload, gọi AI, normalize lỗi. |
| Static Server | Serve frontend build nếu có. |

Thứ tự implement khuyến nghị:

1. Config và data model.
2. Game Engine thuần, test bằng unit nhỏ.
3. Room Manager.
4. Clock Manager.
5. Socket events cơ bản create/join/move.
6. Game over.
7. AI Client.
8. Disconnect/cleanup và AI fallback.
9. Static serving và E2E manual.

---

## 5. Data Model Bắt Buộc

### 5.1. Room State

| Field | Type logic | Bắt buộc | Ghi chú |
|:--|:--|:--|:--|
| `roomId` | string | Có | Uppercase, tránh ký tự dễ nhầm. |
| `status` | enum | Có | `waiting`, `playing`, `finished`. |
| `timeControl` | string | Có | Ví dụ `5+0`. |
| `timeControlMs` | int | Có | Ví dụ `300000`. |
| `players.white` | Player/null | Có | Creator luôn white. |
| `players.black` | Player/null | Có | Joiner luôn black. |
| `board` | chess.Board | Có | Server-authoritative. |
| `movesSan` | list[str] | Có | Dùng dựng PGN. |
| `clockTimes` | list[float] | Có | Giây suy nghĩ từng nửa nước. |
| `clocks.white` | int | Có | Millisecond còn lại. |
| `clocks.black` | int | Có | Millisecond còn lại. |
| `turn` | `white`/`black` | Có | Bên đang đi. |
| `turnStartedAt` | timestamp/null | Có | Epoch ms. |
| `result` | string/null | Có | `"1-0"`, `"0-1"`, `"1/2-1/2"`. |
| `reason` | string/null | Có | Lý do game over. |
| `createdAt` | timestamp | Có | Epoch ms. |
| `lastActivityAt` | timestamp | Có | Dùng cleanup. |

### 5.2. Player State

| Field | Type | Ghi chú |
|:--|:--|:--|
| `socketId` | string | Socket hiện tại của player slot. |
| `color` | `white`/`black` | Phe được gán cố định trong một room. |
| `connected` | boolean | True khi socket active; disconnect trong ván đang chơi kết thúc ván. |

---

## 6. Socket.IO Contract

Backend phải implement chính xác các event dưới đây.

### 6.1. Client -> Server

| Event | Payload | Hành vi |
|:--|:--|:--|
| `create_room` | `{ timeControlMinutes }` | Tạo room, gán socket là white. |
| `join_room` | `{ roomId }` | Join room, gán socket là black. |
| `make_move` | `{ roomId, from, to, promotion? }` | Validate và broadcast move. |
| `resign` | `{ roomId }` | Người gửi thua. |
| `leave_room` | `{ roomId }` | Rời phòng chủ động. |

### 6.2. Server -> Client

| Event | Payload | Khi nào emit |
|:--|:--|:--|
| `room_created` | `{ roomId, color }` | Sau `create_room` thành công. |
| `room_joined` | `{ roomId, color, state }` | Sau `join_room` thành công. |
| `room_error` | `{ code, message }` | Lỗi create/join/move/leave. |
| `opponent_joined` | `{}` | Gửi cho white khi black join. |
| `game_started` | `{ fen, turn, clocks, moves }` | Khi đủ hai người. |
| `move_made` | `{ san, from, to, promotion?, fen, turn, clocks, moveNumber }` | Sau move hợp lệ. |
| `move_rejected` | `{ reason }` | Chỉ gửi cho socket gửi move lỗi. |
| `clock_update` | `{ clocks, turn, serverTime }` | Emit định kỳ khi playing. |
| `game_over` | `{ result, reason }` | Ngay khi ván kết thúc. |
| `analysis_result` | `{ success, data?, basicResult, error? }` | Sau AI success/failure. |

### 6.3. Error Codes

| Code | Message gợi ý |
|:--|:--|
| `ROOM_NOT_FOUND` | `Phòng không tồn tại`. |
| `ROOM_FULL` | `Phòng đã đầy`. |
| `ROOM_FINISHED` | `Ván đấu đã kết thúc`. |
| `INVALID_PAYLOAD` | `Dữ liệu gửi lên không hợp lệ`. |
| `NOT_YOUR_TURN` | `Chưa đến lượt bạn`. |
| `ILLEGAL_MOVE` | `Nước đi không hợp lệ`. |
| `GAME_NOT_ACTIVE` | `Ván đấu chưa sẵn sàng hoặc đã kết thúc`. |

---

## 7. Luật Cờ Và Move Handling

Backend là nguồn sự thật.

Quy trình `make_move`:

1. Kiểm tra payload có `roomId`, `from`, `to`.
2. Tìm room, kiểm tra `status == playing`.
3. Xác định màu của socket trong room.
4. Kiểm tra đúng lượt.
5. Tạo move UCI từ `from`, `to`, `promotion`.
6. Validate move trong `board.legal_moves`.
7. Trước khi push, lấy SAN bằng `board.san(move)`.
8. Cập nhật đồng hồ và push `timeSpentSeconds` vào `clockTimes`.
9. Push move vào board.
10. Push SAN vào `movesSan`.
11. Cập nhật `turn`, `fen`, `clocks`.
12. Broadcast `move_made`.
13. Kiểm tra game over.

Promotion:

| Tình huống | Quy tắc |
|:--|:--|
| Pawn tới hàng cuối và FE gửi promotion | Dùng promotion FE gửi. |
| Pawn tới hàng cuối nhưng thiếu promotion | Reject với `INVALID_PAYLOAD`, không tự đoán. |
| Promotion value không thuộc `q`, `r`, `b`, `n` | Reject với `INVALID_PAYLOAD`. |

Game over mapping:

| Điều kiện | `result` | `reason` |
|:--|:--|:--|
| White checkmates black | `"1-0"` | `checkmate` |
| Black checkmates white | `"0-1"` | `checkmate` |
| White timeout | `"0-1"` | `timeout` |
| Black timeout | `"1-0"` | `timeout` |
| White resign | `"0-1"` | `resign` |
| Black resign | `"1-0"` | `resign` |
| White disconnect/leave khi đang chơi | `"0-1"` | `abandon` |
| Black disconnect/leave khi đang chơi | `"1-0"` | `abandon` |
| Stalemate | `"1/2-1/2"` | `stalemate` |
| Threefold | `"1/2-1/2"` | `threefold` |
| Insufficient material | `"1/2-1/2"` | `insufficient_material` |

---

## 8. Clock Manager

Clock là server-authoritative.

Yêu cầu:

| Hạng mục | Quy tắc |
|:--|:--|
| Đơn vị emit | Millisecond trong `clocks`. |
| Đơn vị gửi AI | Second trong `clockTimes`. |
| Start | Khi đủ hai người, Trắng chạy trước. |
| Switch | Chỉ switch sau move hợp lệ. |
| Timeout | Do server task/timer quyết định. |
| Clock update | Có thể emit mỗi 1 giây. |
| Disconnect | Nếu đang chơi thì kết thúc ngay bằng `abandon`; không có grace/rejoin. |
| Game over | Dừng mọi timer/update. |

Tính `timeSpent`:

| Bước | Mô tả |
|:--|:--|
| 1 | `elapsedMs = now - turnStartedAt`. |
| 2 | Trừ `elapsedMs` khỏi đồng hồ bên vừa đi. |
| 3 | Push `round(elapsedMs / 1000, 2)` vào `clockTimes`. |
| 4 | Set `turnStartedAt = now` cho bên tiếp theo. |

Không push `clockTimes` cho resign/timeout không gắn với một move.

---

## 9. AI Integration

AI endpoint có sẵn:

| Field | Giá trị |
|:--|:--|
| Method | `POST` |
| URL default | `http://localhost:8000/api/predict-elo` |
| Health | `http://localhost:8000/health` |
| Request | `PredictEloRequest` |
| Response | `PredictEloResponse` |

Request backend gửi:

```json
{
  "pgn": "1. e4 e5 2. Nf3 Nc6",
  "clock_times": [5.2, 3.1, 12.0, 8.5],
  "result": "1-0",
  "time_control": "5+0",
  "include_debug": true
}
```

Payload rules:

| Field | Backend phải đảm bảo |
|:--|:--|
| `pgn` | Movetext từ `movesSan`, không header. |
| `clock_times` | Cùng length với `movesSan`, đơn vị giây. |
| `result` | Đúng result đã emit trong `game_over`. |
| `time_control` | Dạng phút+increment, ví dụ `5+0`. |
| `include_debug` | Luôn `true`. |

Response success core:

| Field | Forward cho FE |
|:--|:--|
| `white_elo` | Có |
| `black_elo` | Có |
| `eco` | Có |
| `stats` | Có |
| `explanation` | Có |
| `critical_blunders` | Có nếu debug |
| `tactical_report` | Có nếu debug |
| `cpl_sequence` | Có nếu debug |
| `blunder_flags` | Có nếu debug |

AI failure behavior:

1. Catch HTTP error, timeout, `success=false`, JSON parse error.
2. Log lỗi.
3. Emit `analysis_result`:
   - `success: false`
   - `basicResult: { result, reason }`
   - `error: message thân thiện`
4. Không đổi `game_over`.
5. Không block UI quay về Lobby hoặc tạo phòng mới.

---

## 10. Disconnect, Refresh Và Cleanup

Không implement business reconnect. Không cấp `sessionToken`, không nhận `rejoin_room`, không lưu session vào database. Nếu browser refresh, Socket.IO cũ disconnect và tab mới bắt đầu lại từ Lobby.

State trả về trong `room_joined.state` chỉ dùng cho join lần đầu:

| Field | Mục đích |
|:--|:--|
| `status` | FE biết lobby/room/result. |
| `fen` | Render board. |
| `turn` | Xác định lượt. |
| `clocks` | Đồng hồ hiện tại. |
| `moves` | Move history SAN. |
| `result` | Nếu đã game over. |
| `reason` | Nếu đã game over. |
| `analysis` | Optional, nếu AI đã trả rất nhanh trước khi client hydrate. |

Lifecycle bắt buộc:

| Tình huống | Xử lý |
|:--|:--|
| Disconnect/leave khi `waiting` | Xóa room ngay hoặc đánh dấu inactive để cleanup. |
| Disconnect/leave khi `playing` | Dừng clock, set `status=finished`, đối thủ thắng, emit `game_over` với `reason=abandon`, rồi gọi AI nếu có ít nhất một nước đi. |
| Disconnect/leave khi `finished` | Không đổi kết quả; cleanup theo `ROOM_INACTIVE_CLEANUP_MS`. |
| Cả hai rời phòng | Cleanup khỏi RAM. |
| Server restart | Mất toàn bộ room, đúng thiết kế RAM-only. |

Room đã `finished` là terminal. Không có `play_again`, không emit `game_reset`. Muốn chơi ván mới thì frontend quay về Lobby và tạo room mới.

---

## 11. Logging

Log theo format dễ đọc:

`[ROOM <roomId>] <event>: <detail>`

Log bắt buộc:

| Event | Detail |
|:--|:--|
| room_created | socketId, timeControl |
| room_joined | socketId, color |
| move_made | color, san, timeSpent |
| move_rejected | reason |
| clock_timeout | side |
| game_over | result, reason, moveCount |
| ai_request | pgn length, clockTimes length |
| ai_response | success, durationMs |
| disconnect | color |
| cleanup | reason |

Không log API key hoặc stack trace dài ra client.

---

## 12. Backend Test Checklist

Unit-level:

| Test | Kỳ vọng |
|:--|:--|
| Generate room code | 6 ký tự uppercase, không trùng trong RAM. |
| Create room | White slot được fill. |
| Join room | Black slot được fill, status `playing`. |
| Join full room | `ROOM_FULL`. |
| Validate legal move | SAN/FEN đúng. |
| Reject illegal move | Board không đổi. |
| Clock switch | Push đúng `clockTimes`. |
| Build AI payload | PGN no header, `include_debug=true`. |

E2E manual:

| Flow | Kỳ vọng |
|:--|:--|
| 2 tab create/join | Ván bắt đầu. |
| Move realtime | Tab còn lại nhận move. |
| Wrong turn | Reject. |
| Resign | Game over đúng result. |
| AI unavailable | Result vẫn hiển thị fallback. |
| Refresh khi waiting | Tab mới quay về Lobby; room cũ không cần phục hồi. |
| Refresh/disconnect khi playing | Đối thủ nhận `game_over` reason `abandon`. |
| Room mới sau result | User tạo room mới từ Lobby, không reuse room cũ. |

---

## 13. Backend Definition Of Done

Backend hoàn thành khi:

1. Chạy được server trên port `3000`.
2. Socket.IO frontend connect được.
3. Create/join/leave hoạt động, không có database và không có session recovery.
4. Move hợp lệ realtime dưới 500ms local.
5. Sai lượt/sai luật bị reject.
6. Clock server-authoritative và timeout đúng.
7. Game over emit trước khi gọi AI.
8. AI request khớp contract và có `include_debug: true`.
9. AI lỗi không crash.
10. Refresh/disconnect đang chơi kết thúc bằng `abandon`; room terminal được cleanup.
