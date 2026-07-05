from __future__ import annotations


ERROR_MESSAGES: dict[str, str] = {
    "ROOM_NOT_FOUND": "Phòng không tồn tại",
    "ROOM_FULL": "Phòng đã đầy",
    "ROOM_FINISHED": "Ván đấu đã kết thúc",
    "INVALID_PAYLOAD": "Dữ liệu gửi lên không hợp lệ",
    "NOT_YOUR_TURN": "Chưa đến lượt bạn",
    "ILLEGAL_MOVE": "Nước đi không hợp lệ",
    "GAME_NOT_ACTIVE": "Ván đấu chưa sẵn sàng hoặc đã kết thúc",
}


class BackendError(Exception):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, code)
        super().__init__(self.message)

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def invalid_payload(message: str | None = None) -> BackendError:
    return BackendError("INVALID_PAYLOAD", message)
