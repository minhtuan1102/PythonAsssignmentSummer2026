from __future__ import annotations

from dataclasses import dataclass

import chess

from whess_backend.errors import BackendError, invalid_payload
from whess_backend.models import Color, GameOver, chess_turn_to_color

PROMOTION_PIECES = {"q", "r", "b", "n"}


@dataclass(frozen=True)
class ValidatedMove:
    move: chess.Move
    san: str
    from_square: str
    to_square: str
    promotion: str | None = None


class GameEngine:
    def validate_move(
        self,
        board: chess.Board,
        from_square: str,
        to_square: str,
        promotion: str | None = None,
    ) -> ValidatedMove:
        if not from_square or not to_square:
            raise invalid_payload()

        from_square = str(from_square).lower().strip()
        to_square = str(to_square).lower().strip()
        promotion = str(promotion).lower().strip() if promotion else None

        try:
            from_index = chess.parse_square(from_square)
            to_index = chess.parse_square(to_square)
        except ValueError as exc:
            raise invalid_payload() from exc

        if promotion is not None and promotion not in PROMOTION_PIECES:
            raise invalid_payload("Invalid promotion piece")

        piece = board.piece_at(from_index)
        if (
            piece is not None
            and piece.piece_type == chess.PAWN
            and chess.square_rank(to_index) in {0, 7}
            and promotion is None
        ):
            raise invalid_payload("Promotion piece is required")

        try:
            move = chess.Move.from_uci(f"{from_square}{to_square}{promotion or ''}")
        except ValueError as exc:
            raise invalid_payload() from exc

        if move not in board.legal_moves:
            raise BackendError("ILLEGAL_MOVE")

        return ValidatedMove(
            move=move,
            san=board.san(move),
            from_square=from_square,
            to_square=to_square,
            promotion=promotion,
        )

    def detect_game_over(self, room_id: str, board: chess.Board, mover: Color) -> GameOver | None:
        if board.is_checkmate():
            return GameOver(
                room_id=room_id,
                result="1-0" if mover == "white" else "0-1",
                reason="checkmate",
            )
        if board.is_stalemate():
            return GameOver(room_id=room_id, result="1/2-1/2", reason="stalemate")
        if board.is_insufficient_material():
            return GameOver(
                room_id=room_id,
                result="1/2-1/2",
                reason="insufficient_material",
            )
        can_claim_threefold = getattr(
            board,
            "can_claim_threefold",
            board.can_claim_threefold_repetition,
        )
        if can_claim_threefold() or board.is_repetition(3):
            return GameOver(room_id=room_id, result="1/2-1/2", reason="threefold")
        return None

    @staticmethod
    def current_turn(board: chess.Board) -> Color:
        return chess_turn_to_color(board.turn)


def moves_to_movetext(moves_san: tuple[str, ...] | list[str]) -> str:
    tokens: list[str] = []
    for index, san in enumerate(moves_san):
        if index % 2 == 0:
            tokens.append(f"{index // 2 + 1}. {san}")
        else:
            tokens.append(san)
    return " ".join(tokens)
