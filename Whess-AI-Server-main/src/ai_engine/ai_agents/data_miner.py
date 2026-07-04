from __future__ import annotations

import io
from typing import Any, Mapping

import chess
import chess.pgn

from src.ai_engine.core.errors import AgentInputError
from src.ai_engine.domain.schemas import (
    AnalysisContext,
    DataMinerResult,
    EcoInfo,
    GameStats,
    MoveMetric,
)
from src.ai_engine.services.opening_book import OpeningBook


class DataMinerAgent:
    """Pure-Python agent that prepares facts for the LLM agents."""

    def __init__(
        self,
        opening_book: OpeningBook | None = None,
        blunder_threshold: float = 200.0,
        critical_threshold: float = 50.0,
        critical_count: int = 3,
    ):
        self.opening_book = opening_book or OpeningBook.default()
        self.blunder_threshold = blunder_threshold
        self.critical_threshold = critical_threshold
        self.critical_count = critical_count

    def run(self, context: AnalysisContext) -> DataMinerResult:
        move_rows = self._moves_from_pgn(context.pgn)
        if not move_rows:
            raise AgentInputError("PGN does not contain any moves.")

        cpl_values = tuple(float(value) for value in context.cpl_sequence)
        if len(cpl_values) != len(move_rows):
            raise AgentInputError(
                "cpl_sequence length must match the number of PGN half-moves."
            )

        metrics = tuple(
            self._build_metric(
                row=row,
                index=index,
                context=context,
                cpl=cpl_values[index],
            )
            for index, row in enumerate(move_rows)
        )
        stats = self._build_stats(metrics)
        critical_blunders = self._top_critical_moves(metrics)
        eco = context.eco or self.opening_book.match(row["move"] for row in move_rows)

        return DataMinerResult(
            eco=eco if eco else EcoInfo.unknown(),
            stats=stats,
            critical_blunders=critical_blunders,
            move_metrics=metrics,
            result=context.result,
            time_control=context.time_control,
            white_elo=context.white_elo,
            black_elo=context.black_elo,
        )

    def _moves_from_pgn(self, pgn: str) -> tuple[dict[str, Any], ...]:
        if not pgn.strip():
            raise AgentInputError("PGN is empty.")

        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            raise AgentInputError("Cannot parse PGN.")

        board = game.board()
        rows: list[dict[str, Any]] = []
        for move in game.mainline_moves():
            fen_before = board.fen()
            rows.append(
                {
                    "ply": len(rows) + 1,
                    "move_number": board.fullmove_number,
                    "side": "white" if board.turn == chess.WHITE else "black",
                    "move": board.san(move),
                    "fen_before": fen_before,
                }
            )
            board.push(move)
            rows[-1]["fen_after"] = board.fen()
        return tuple(rows)

    def _build_metric(
        self,
        row: Mapping[str, Any],
        index: int,
        context: AnalysisContext,
        cpl: float,
    ) -> MoveMetric:
        record = (
            context.stockfish_records[index]
            if index < len(context.stockfish_records)
            else {}
        )
        flag = (
            bool(context.blunder_flags[index])
            if index < len(context.blunder_flags)
            else cpl > self.blunder_threshold
        )
        time_spent = (
            float(context.clock_times[index])
            if index < len(context.clock_times)
            else None
        )

        return MoveMetric(
            ply=int(row["ply"]),
            move_number=int(row["move_number"]),
            side=str(row["side"]),
            move=str(record.get("move") or record.get("san") or row["move"]),
            cpl=max(0.0, cpl),
            is_blunder=flag,
            time_spent=time_spent,
            fen_before=str(record.get("fen_before") or row.get("fen_before") or ""),
            fen_after=str(record.get("fen_after") or row.get("fen_after") or ""),
            best_move=record.get("best_move") or record.get("best_move_uci"),
            eval_before_cp=self._optional_float(record.get("eval_before_cp")),
            eval_after_cp=self._optional_float(record.get("eval_after_cp")),
        )

    def _build_stats(self, metrics: tuple[MoveMetric, ...]) -> GameStats:
        white = [move for move in metrics if move.side == "white"]
        black = [move for move in metrics if move.side == "black"]
        return GameStats(
            white_avg_cpl=self._avg_cpl(white),
            black_avg_cpl=self._avg_cpl(black),
            white_blunders=sum(1 for move in white if move.is_blunder),
            black_blunders=sum(1 for move in black if move.is_blunder),
            total_moves=len(metrics),
        )

    def _top_critical_moves(
        self, metrics: tuple[MoveMetric, ...]
    ) -> tuple[MoveMetric, ...]:
        candidates = [
            move
            for move in metrics
            if move.is_blunder or move.cpl >= self.critical_threshold
        ]
        ranked = sorted(candidates, key=lambda move: move.cpl, reverse=True)
        return tuple(ranked[: self.critical_count])

    @staticmethod
    def _avg_cpl(moves: list[MoveMetric]) -> float:
        if not moves:
            return 0.0
        return round(sum(move.cpl for move in moves) / len(moves), 1)

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
