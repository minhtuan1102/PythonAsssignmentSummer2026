from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.ai_engine.schemas import EcoInfo


@dataclass(frozen=True)
class OpeningLine:
    eco: EcoInfo
    moves: tuple[str, ...]


class OpeningBook:
    def __init__(self, lines: Iterable[OpeningLine]):
        self.lines = tuple(lines)

    @classmethod
    def default(cls) -> "OpeningBook":
        path = Path(__file__).resolve().parents[1] / "eco_data" / "eco.json"
        return cls.from_json(path)

    @classmethod
    def from_json(cls, path: Path) -> "OpeningBook":
        if not path.exists():
            return cls(())
        raw_entries = json.loads(path.read_text(encoding="utf-8"))
        lines = []
        for entry in raw_entries:
            lines.append(
                OpeningLine(
                    eco=EcoInfo.from_mapping(entry),
                    moves=tuple(str(move) for move in entry.get("moves", ())),
                )
            )
        return cls(lines)

    def match(self, san_moves: Iterable[str]) -> EcoInfo:
        moves = tuple(san_moves)
        best: OpeningLine | None = None
        for line in self.lines:
            if len(line.moves) > len(moves):
                continue
            if moves[: len(line.moves)] == line.moves:
                if best is None or len(line.moves) > len(best.moves):
                    best = line
        return best.eco if best else EcoInfo.unknown()
