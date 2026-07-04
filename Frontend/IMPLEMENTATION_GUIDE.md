# Whess Frontend Implementation Guide

Mục tiêu: xây dựng frontend greenfield cho Whess, kết nối với Web Game Server qua Socket.IO, cho phép 2 tab chơi cờ realtime và hiển thị phân tích AI sau trận đấu.

Tài liệu này dành cho AI coding agent hoặc developer implement frontend độc lập, nhưng phải tương thích chính xác với backend contract.

---

## 1. Phạm Vi Frontend

Frontend cần làm:

| Hạng mục | Yêu cầu |
|:--|:--|
| Lobby | Tạo phòng, chọn time control, nhập mã phòng. |
| Room | Bàn cờ, đồng hồ, move history, trạng thái lượt, resign, leave. |
| Result Overlay | Kết quả ván, AI loading, ELO, ECO, stats, CPL chart, blunder list, explanation. |
| Socket.IO | Gửi/nhận event đúng contract. |
| Session per tab | Không lưu phiên; refresh tab là mất ván và quay về Lobby. |
| One-shot game | Một room chỉ chơi một ván; muốn chơi tiếp thì tạo room mới. |
| Graceful AI fallback | AI lỗi/thiếu debug không crash UI. |

Frontend không được làm:

| Không làm | Lý do |
|:--|:--|
| Tự quyết định kết quả ván | Backend là nguồn sự thật. |
| Tự tính timeout cuối cùng | Backend quyết định timeout. |
| Gửi SAN làm move source | Backend tự sinh SAN. |
| Lưu session bằng `localStorage` hoặc `sessionStorage` | Demo không phục hồi phiên sau refresh. |
| Gọi AI service trực tiếp | Browser chỉ nói chuyện với Web Game Server. |

---

## 2. Tech Stack

| Thành phần | Công nghệ |
|:--|:--|
| Runtime | React 18 |
| Build | Vite |
| Realtime | socket.io-client |
| Chess board | react-chessboard |
| Client preview | chess.js |
| Chart | Recharts |
| Markdown | react-markdown |
| Icons | lucide-react |
| Styling | Tailwind CSS hoặc CSS modules bám token |

Không tạo landing page. Màn đầu tiên là lobby có thể thao tác ngay.

---

## 3. UI Architecture

Component/screen trách nhiệm:

| Screen/Component | Trách nhiệm |
|:--|:--|
| App | Khởi tạo routing/state root. |
| SocketProvider | Tạo socket singleton, quản lý connect/disconnect. |
| LobbyScreen | Create room, join room, time control. |
| RoomScreen | Layout chính khi chơi. |
| ChessBoardPanel | Render board, drag/drop, click move, orientation. |
| ClockPanel | Hiển thị clocks theo phe. |
| MoveHistoryPanel | SAN history dạng cặp nước. |
| ActionBar | Resign, leave, copy room link/code. |
| ResultOverlay | Hiển thị result và AI analysis. |
| CplChart | Render `cpl_sequence` + `blunder_flags`. |
| BlunderAccordion | Render `critical_blunders` + reason từ `tactical_report`. |
| ExplanationMarkdown | Render markdown explanation. |

State chính nên nằm ở Room/App level, các component con nhận props.

---

## 4. Session Và Refresh

Không persist state ván đấu vào `localStorage`, `sessionStorage`, IndexedDB hoặc database client-side.

Quy tắc:

| Tình huống | Hành vi |
|:--|:--|
| `room_created` | Giữ `roomId`, `color` trong React state memory và chuyển sang Room. |
| `room_joined` | Giữ `roomId`, `color`, hydrate `state` nếu backend gửi. |
| Browser refresh | App khởi động lại ở Lobby, không gửi event phục hồi. |
| Socket disconnect do refresh khi đang chơi | Backend kết thúc ván bằng `abandon`; tab mới không biết room cũ. |
| User bấm leave | Emit `leave_room`, clear React state, quay về Lobby. |
| `room_error` | Hiển thị lỗi và giữ/đưa user về Lobby tùy trạng thái. |

---

## 5. Socket.IO Contract FE Phải Dùng

### 5.1. FE Gửi BE

| Event | Payload | Khi nào |
|:--|:--|:--|
| `create_room` | `{ timeControlMinutes }` | User bấm tạo phòng. |
| `join_room` | `{ roomId }` | User nhập mã phòng và bấm vào. |
| `make_move` | `{ roomId, from, to, promotion? }` | User kéo/thả hoặc click move. |
| `resign` | `{ roomId }` | User xác nhận xin thua. |
| `leave_room` | `{ roomId }` | User thoát phòng. |

### 5.2. FE Nhận Từ BE

| Event | FE phải làm |
|:--|:--|
| `room_created` | Lưu state memory, chuyển sang Room, chờ đối thủ. |
| `room_joined` | Lưu state memory, hydrate state từ `state` nếu có. |
| `room_error` | Hiển thị lỗi rõ, không crash. |
| `opponent_joined` | Bỏ trạng thái waiting nếu đang host. |
| `game_started` | Set board, clocks, turn, status `playing`. |
| `move_made` | Update FEN, move history, clocks, turn. |
| `move_rejected` | Revert local preview nếu có, hiển thị lỗi. |
| `clock_update` | Sync clocks và turn. |
| `game_over` | Mở ResultOverlay với basic result và AI loading. |
| `analysis_result` | Dừng loading, render AI data hoặc error. |

---

## 6. Frontend State Model

State tối thiểu:

| State | Type logic | Ghi chú |
|:--|:--|:--|
| `screen` | `lobby`, `room` | Overlay result không nhất thiết là route riêng. |
| `roomId` | string/null | Mã phòng hiện tại. |
| `color` | `white`/`black`/null | Phe của tab. |
| `status` | `waiting`, `playing`, `finished` | Từ backend. |
| `fen` | string | Render board. |
| `turn` | `white`/`black` | Bên tới lượt. |
| `clocks` | `{ white, black }` | Millisecond. |
| `moves` | string[] | SAN history. |
| `gameOver` | `{ result, reason }`/null | Basic result. |
| `aiLoading` | boolean | True sau `game_over` đến `analysis_result`. |
| `analysis` | object/null | AI data. |
| `analysisError` | string/null | AI failure. |
| `moveError` | string/null | Reject feedback. |

Derived state:

| Derived | Công thức |
|:--|:--|
| `isMyTurn` | `status === playing && color === turn`. |
| `orientation` | `black` nếu color black, ngược lại white. |
| `myClock` | `clocks[color]`. |
| `opponentClock` | clock còn lại. |

---

## 7. Chess Move UI

Frontend được phép dùng `chess.js` để preview legal moves, nhưng không được tin kết quả client.

Move flow:

1. User drag/drop hoặc click source/target.
2. FE kiểm tra cơ bản:
   - Đang `playing`.
   - Đúng lượt.
   - Chọn quân của mình.
3. Nếu move là promotion, FE hiển thị chọn `q`, `r`, `b`, `n`.
4. FE gửi `make_move` với `from`, `to`, `promotion`.
5. FE không tự append move vào history vĩnh viễn.
6. FE chỉ commit state khi nhận `move_made`.
7. Nếu nhận `move_rejected`, hiển thị lỗi và giữ state từ server.

Không gửi `san` lên backend.

---

## 8. Clock UI

Backend emit `clocks` bằng millisecond.

Frontend hiển thị:

| Trạng thái | UI |
|:--|:--|
| Bên đang đi | Clock màu accent, có trạng thái active. |
| Không tới lượt | Clock màu muted/normal. |
| Dưới 30s | Màu warning/danger theo design. |
| Opponent disconnect | Không cần banner reconnect; backend sẽ gửi `game_over` với `reason=abandon`. |

Để UI mượt, FE có thể countdown local giữa các `clock_update`, nhưng phải resync mỗi khi nhận event backend.

Không tự emit timeout.

---

## 9. Result Overlay

Overlay mở ngay khi nhận `game_over`.

### 9.1. Basic Result

Mapping hiển thị:

| `result` | Với White tab | Với Black tab |
|:--|:--|:--|
| `1-0` | Bạn thắng | Bạn thua |
| `0-1` | Bạn thua | Bạn thắng |
| `1/2-1/2` | Hòa | Hòa |

Reason label:

| reason | Label |
|:--|:--|
| `checkmate` | Chiếu bí |
| `timeout` | Hết giờ |
| `resign` | Xin thua |
| `abandon` | Rời ván hoặc mất kết nối |
| `stalemate` | Hòa pat |
| `threefold` | Hòa lặp thế |
| `insufficient_material` | Hòa thiếu quân chiếu bí |

### 9.2. AI Loading

Sau `game_over`, set:

| State | Value |
|:--|:--|
| `aiLoading` | true |
| `analysis` | null |
| `analysisError` | null |

Hiển thị loading "Đang phân tích ván đấu..." nhưng vẫn cho thấy kết quả cơ bản.

### 9.3. AI Success

Khi nhận `analysis_result.success=true`:

| Data | UI |
|:--|:--|
| `white_elo`, `black_elo` | ELO cards. |
| `eco.code`, `eco.name` | Opening badge/name. |
| `stats` | CPL avg, blunders, total moves. |
| `explanation` | Markdown. |
| `cpl_sequence` + `blunder_flags` | CPL chart nếu có. |
| `critical_blunders` | Accordion nếu có. |
| `tactical_report.analysis` | Reason gắn với blunder nếu match được. |

Nếu thiếu debug fields, ẩn chart/blunder accordion và không hiện lỗi.

### 9.4. AI Failure

Khi `analysis_result.success=false`:

| UI | Quy tắc |
|:--|:--|
| Warning | "Không thể phân tích bằng AI lúc này." |
| Basic result | Vẫn hiển thị. |
| Buttons | Về Lobby/tạo phòng mới vẫn hoạt động. |
| Crash | Không được xảy ra. |

---

## 10. CPL Chart

Input:

| Field | Meaning |
|:--|:--|
| `cpl_sequence[i]` | CPL tại ply `i + 1`. |
| `blunder_flags[i]` | `1` nếu ply đó là blunder. |

Chart requirements:

| Yêu cầu | Ghi chú |
|:--|:--|
| X-axis | Ply hoặc move number. |
| Y-axis | CPL. |
| Blunder marker | Điểm màu danger khi `blunder_flags[i] === 1`. |
| Missing data | Không render chart nếu thiếu sequence. |
| Long game | Chart scroll/resize được, không làm tràn modal. |

---

## 11. Blunder Accordion

Nguồn dữ liệu:

| Data | Dùng cho |
|:--|:--|
| `critical_blunders` | Danh sách chính. |
| `tactical_report.analysis` | Reason/category/severity nếu có. |

Ghép reason theo key:

`move_number + side + move`

Fallback:

| Thiếu field | Hành vi |
|:--|:--|
| Không có `critical_blunders` | Ẩn accordion. |
| Có blunder nhưng không có reason | Hiển thị thông tin CPL/FEN/best move nếu có, reason ghi "Chưa có giải thích chi tiết". |
| Không có FEN/best move | Không render dòng đó. |

---

## 12. Lobby UX

Lobby phải thao tác được ngay.

| Element | Yêu cầu |
|:--|:--|
| Time control | Chọn 3, 5, 10, 15 phút. Default 5 hoặc 10 phút. |
| Create room | Emit `create_room`. Disable khi loading. |
| Join room | Input room code, normalize uppercase visually. |
| Error | Hiển thị lỗi từ `room_error.message`. |
| Share | Sau create, hiển thị room code rõ và nút copy. |

Không có login/register.

---

## 13. Room UX

| Element | Yêu cầu |
|:--|:--|
| Room code | Hiển thị rõ, có copy. |
| Player side | Hiển thị "Bạn cầm Trắng/Đen". |
| Turn status | "Lượt của bạn" hoặc "Lượt đối thủ". |
| Board | Center, responsive, orientation theo color. |
| Clocks | Một clock cho bạn, một clock cho đối thủ. |
| Move history | SAN theo cặp move number. |
| Resign | Có confirm trước khi emit. |
| Waiting | Nếu chỉ có một người, hiện trạng thái chờ đối thủ. |
| Disconnect | Nếu socket hiện tại mất kết nối, app khởi động lại ở Lobby; nếu đối thủ mất kết nối, chờ `game_over`. |

---

## 14. Design Tokens

| Token | Value |
|:--|:--|
| `bg` | `#0B0E14` |
| `surface` | `#141822` |
| `elevated` | `#1C212D` |
| `border` | `#262B38` |
| `text` | `#F4F6F8` |
| `muted` | `#9AA3B2` |
| `accent` | `#E8B959` |
| `success` | `#3FBE73` |
| `danger` | `#E5484D` |
| `warning` | `#F2B84B` |
| `boardLight` | `#E8E4DA` |
| `boardDark` | `#3B4252` |

UI should be compact, dark, board-focused. Do not create marketing hero/landing page.

---

## 15. Frontend Test Checklist

Manual/E2E:

| Test | Kỳ vọng |
|:--|:--|
| Open lobby | Có create/join/time control. |
| Create room | Nhận room code, lưu memory state, vào waiting/room. |
| Join room | Tab 2 vào được, màu black. |
| Game start | Cả hai tab thấy board/clocks. |
| Move legal | Cả hai tab update FEN/history. |
| Wrong turn | FE chặn hoặc backend reject, UI không đổi sai. |
| Promotion | FE gửi promotion. |
| Resign | Overlay hiện kết quả đúng. |
| AI loading | Sau game_over có loading. |
| AI success | Render ELO/ECO/stats/explanation. |
| AI debug | Render chart/blunder nếu data có. |
| AI error | Warning, không crash. |
| Refresh tab | App quay về Lobby, không gửi restore/rejoin. |
| Opponent refresh khi playing | Nhận `game_over` reason `abandon`. |
| New room after result | User về Lobby và tạo room mới. |
| Responsive | Không tràn text/modal ở width nhỏ. |

---

## 16. Frontend Definition Of Done

Frontend hoàn thành khi:

1. Connect được Socket.IO backend.
2. Create/join/leave flow hoạt động bằng React state memory, không persist session.
3. Board render đúng orientation theo color.
4. Move gửi đúng `{ roomId, from, to, promotion? }`.
5. State chỉ commit sau event backend.
6. Clock hiển thị đúng và resync từ backend.
7. Result overlay xử lý đủ loading/success/error.
8. CPL chart và blunder accordion render có điều kiện, không crash khi thiếu debug.
9. Refresh không phục hồi ván; app khởi động lại ở Lobby.
10. Hai tab local chơi được một ván end-to-end tới result overlay.
