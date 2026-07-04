from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chess
import chess.engine
import chess.pgn

from src.ai_engine.core.errors import StockfishAnalysisError


@dataclass(frozen=True)
class StockfishAnalysisResult:
    cpl_sequence: tuple[float, ...]
    blunder_flags: tuple[int, ...]
    stockfish_records: tuple[dict[str, Any], ...]


def _score_to_cp(score: chess.engine.PovScore, turn: chess.Color) -> float | None:
    """Convert a Stockfish score to centipawns from the mover's perspective."""
    cp = score.pov(turn).score()
    return float(cp) if cp is not None else None


def _moves_from_pgn(pgn: str) -> tuple[chess.Move, ...]:
    game = chess.pgn.read_game(io.StringIO(pgn or ""))
    if game is None:
        raise StockfishAnalysisError("Cannot parse PGN.")
    moves = tuple(game.mainline_moves())
    if not moves:
        raise StockfishAnalysisError("PGN does not contain any valid moves.")
    return moves


def analyze_game_cpl_sequence(
    moves_san: str,
    engine: chess.engine.SimpleEngine,
    depth: int = 12,
) -> list[float]:
    """Analyze a SAN move string and return one CPL value per half-move."""
    board = chess.Board()
    cpl_seq: list[float] = []
    limit = chess.engine.Limit(depth=depth)

    for move in _moves_from_pgn(moves_san):
        turn = board.turn
        try:
            info_before = engine.analyse(board, limit, info=chess.engine.INFO_SCORE)
            cp_before = _score_to_cp(info_before["score"], turn)
        except Exception:
            cp_before = None

        board.push(move)

        try:
            info_after = engine.analyse(board, limit, info=chess.engine.INFO_SCORE)
            cp_after = _score_to_cp(info_after["score"], turn)
        except Exception:
            cp_after = None

        if cp_before is None or cp_after is None:
            cpl_seq.append(float("nan"))
        else:
            cpl_seq.append(max(0.0, float(cp_before) - float(cp_after)))

    return cpl_seq


class StockfishAnalyzer:
    def __init__(
        self,
        engine_path: str | Path,
        depth: int = 12,
        blunder_threshold: float = 200.0,
    ):
        self.engine_path = str(engine_path)
        self.depth = depth
        self.blunder_threshold = blunder_threshold

    def analyze(self, pgn: str) -> StockfishAnalysisResult:
        if not pgn.strip():
            raise StockfishAnalysisError("PGN is empty.")
        if not Path(self.engine_path).exists() and self.engine_path.lower() != "stockfish":
            raise StockfishAnalysisError(f"Stockfish binary not found: {self.engine_path}")

        engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        try:
            return self._analyze_with_engine(pgn, engine)
        finally:
            engine.quit()

    def _analyze_with_engine(
        self,
        pgn: str,
        engine: chess.engine.SimpleEngine,
    ) -> StockfishAnalysisResult:
        board = chess.Board()
        limit = chess.engine.Limit(depth=self.depth)
        cpl_sequence: list[float] = []
        records: list[dict[str, Any]] = []

        for ply, move in enumerate(_moves_from_pgn(pgn), start=1):
            turn = board.turn
            side = "white" if turn == chess.WHITE else "black"
            move_number = board.fullmove_number
            san = board.san(move)
            fen_before = board.fen()

            info_before = engine.analyse(board, limit)
            score_before = info_before.get("score")
            cp_before = _score_to_cp(score_before, turn) if score_before else None
            best_move_uci = None
            if info_before.get("pv"):
                best_move_uci = info_before["pv"][0].uci()

            board.push(move)
            fen_after = board.fen()

            info_after = engine.analyse(board, limit, info=chess.engine.INFO_SCORE)
            score_after = info_after.get("score")
            cp_after = _score_to_cp(score_after, turn) if score_after else None

            if cp_before is None or cp_after is None:
                raw_cpl = float("nan")
                model_cpl = 0.0
            else:
                raw_cpl = max(0.0, float(cp_before) - float(cp_after))
                model_cpl = raw_cpl

            cpl_sequence.append(model_cpl)
            records.append(
                {
                    "ply": ply,
                    "move_number": move_number,
                    "side": side,
                    "move": san,
                    "san": san,
                    "fen_before": fen_before,
                    "fen_after": fen_after,
                    "best_move_uci": best_move_uci,
                    "eval_before_cp": cp_before,
                    "eval_after_cp": cp_after,
                    "cpl": None if math.isnan(raw_cpl) else raw_cpl,
                }
            )

        if not cpl_sequence:
            raise StockfishAnalysisError("PGN does not contain any valid moves.")

        blunder_flags = tuple(
            1 if cpl > self.blunder_threshold else 0 for cpl in cpl_sequence
        )
        return StockfishAnalysisResult(
            cpl_sequence=tuple(cpl_sequence),
            blunder_flags=blunder_flags,
            stockfish_records=tuple(records),
        )
