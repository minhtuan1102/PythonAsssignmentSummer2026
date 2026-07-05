from __future__ import annotations


ERROR_MESSAGES: dict[str, str] = {
    "ROOM_NOT_FOUND": "Phong khong ton tai",
    "ROOM_FULL": "Phong da day",
    "ROOM_FINISHED": "Van dau da ket thuc",
    "INVALID_PAYLOAD": "Du lieu gui len khong hop le",
    "NOT_YOUR_TURN": "Chua den luot ban",
    "ILLEGAL_MOVE": "Nuoc di khong hop le",
    "GAME_NOT_ACTIVE": "Van dau chua san sang hoac da ket thuc",
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
