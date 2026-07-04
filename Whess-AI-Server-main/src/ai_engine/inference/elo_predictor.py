from __future__ import annotations

import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import chess
import chess.pgn

from src.ai_engine.core.errors import PredictionError

try:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    np = None
    torch = None
    nn = None
    F = None
    pack_padded_sequence = None
    pad_packed_sequence = None


CONFIG: dict[str, Any] = {
    "conv_filters": 32,
    "lstm_layers": 3,
    "lstm_hidden": 64,
    "fc1_hidden": 32,
    "dropout_rate": 0.5,
    "bidirectional": True,
    "use_cpl": True,
    "use_blunder": True,
    "max_moves": 150,
    "ratings_mean": 1514.0,
    "ratings_std": 366.0,
    "clocks_mean": 273.0,
    "clocks_std": 380.0,
    "cpl_mean": 50.0,
    "cpl_std": 100.0,
    "blunder_threshold": 200,
}

PIECE_TYPE_TO_PLANE = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
    chess.KING: 5,
}

_BaseRatingNet = nn.Module if nn is not None else object


class RatingNet(_BaseRatingNet):
    """CNN-BiLSTM architecture copied from app_demo.py for runtime inference."""

    def __init__(
        self,
        conv_filters: int = 32,
        lstm_layers: int = 3,
        lstm_hidden: int = 64,
        fc1_hidden: int = 32,
        dropout_rate: float = 0.5,
        bidirectional: bool = True,
        use_cpl: bool = True,
        use_blunder: bool = True,
    ):
        if nn is None:
            raise PredictionError("PyTorch is required for RatingNet inference.")
        super().__init__()
        self.use_cpl = use_cpl
        self.use_blunder = use_blunder
        self.conv1 = nn.Conv2d(12, conv_filters, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(conv_filters)
        self.conv2 = nn.Conv2d(conv_filters, conv_filters * 2, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(conv_filters * 2)
        self.conv3 = nn.Conv2d(conv_filters * 2, conv_filters * 4, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(conv_filters * 4)
        self.conv4 = nn.Conv2d(conv_filters * 4, conv_filters * 8, kernel_size=3, padding=1)
        self.bn4 = nn.BatchNorm2d(conv_filters * 8)
        self.pool = nn.AvgPool2d(2, 2)
        self.dropout = nn.Dropout(dropout_rate)
        extra = 1
        if use_cpl:
            extra += 1
        if use_blunder:
            extra += 1
        self.lstm = nn.LSTM(
            input_size=conv_filters * 8 + extra,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=bidirectional,
        )
        fc_in = lstm_hidden * 2 if bidirectional else lstm_hidden
        self.fc1 = nn.Linear(fc_in, fc1_hidden)
        self.fc2 = nn.Linear(fc1_hidden, 2)

    def forward(self, positions, clocks, lengths, cpls=None, blunders=None):
        batch_size, timesteps = positions.size(0), positions.size(1)
        x = positions.view(-1, 12, 8, 8)
        x = self.pool(F.leaky_relu(self.bn1(self.conv1(x))))
        x = self.pool(F.leaky_relu(self.bn2(self.conv2(x))))
        x = self.pool(F.leaky_relu(self.bn3(self.conv3(x))))
        x = self.dropout(F.leaky_relu(self.bn4(self.conv4(x))))
        x = x.view(batch_size, timesteps, -1)
        cats = [x, clocks.unsqueeze(2)]
        if self.use_cpl and cpls is not None:
            cats.append(cpls.unsqueeze(2))
        if self.use_blunder and blunders is not None:
            cats.append(blunders.unsqueeze(2))
        lstm_in = torch.cat(cats, dim=2)
        packed = pack_padded_sequence(
            lstm_in,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        packed_out, _ = self.lstm(packed)
        lstm_out, _ = pad_packed_sequence(packed_out, batch_first=True)
        y = self.dropout(F.leaky_relu(self.fc1(lstm_out)))
        all_out = self.fc2(y)
        idx = torch.arange(batch_size, device=positions.device)
        last_out = all_out[idx, lengths - 1, :]
        return all_out, last_out


@dataclass(frozen=True)
class EloPrediction:
    white_elo: int
    black_elo: int
    white_elo_raw: float
    black_elo_raw: float


def _require_dependencies() -> None:
    if np is None or torch is None or nn is None:
        raise PredictionError(
            "ELO inference requires numpy and torch. Install runtime dependencies first."
        )


def encode_board(board: chess.Board):
    _require_dependencies()
    planes = np.zeros((12, 8, 8), dtype=np.float32)
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        plane = PIECE_TYPE_TO_PLANE[piece.piece_type]
        if piece.color == chess.BLACK:
            plane += 6
        planes[plane, square // 8, square % 8] = 1.0
    return planes


def replay_game(moves_san: str, max_moves: int = 150):
    _require_dependencies()
    board = chess.Board()
    boards = []
    game = chess.pgn.read_game(io.StringIO(moves_san or ""))
    if game is None:
        return boards
    for move in tuple(game.mainline_moves())[:max_moves]:
        board.push(move)
        boards.append(encode_board(board))
    return boards


def _parse_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return json.loads(str(value).replace("NaN", "null").replace("Infinity", "null")) or []


def _clean_cpl(value: Any) -> float:
    try:
        cpl = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(cpl) or math.isinf(cpl):
        return 0.0
    return max(0.0, min(cpl, 2000.0))


def prepare_game(row: Mapping[str, Any], config: Mapping[str, Any]):
    """Prepare tensors for one game, adapted from app_demo.py."""
    _require_dependencies()
    boards = replay_game(str(row.get("Moves", "")), int(config["max_moves"]))
    if not boards:
        boards = [np.zeros((12, 8, 8), dtype=np.float32)]
    length = len(boards)
    positions = torch.tensor(np.stack(boards), dtype=torch.float32).unsqueeze(0)

    clock_seq = _parse_sequence(row.get("ClockSeq", []))
    clock_seq = [
        ((float(clock) if clock is not None else 0.0) - config["clocks_mean"])
        / config["clocks_std"]
        for clock in clock_seq[:length]
    ]
    while len(clock_seq) < length:
        clock_seq.append(0.0)
    clocks = torch.tensor(clock_seq[:length], dtype=torch.float32).unsqueeze(0)

    cpl_seq = [_clean_cpl(cpl) for cpl in _parse_sequence(row.get("cpl_seq", []))[:length]]
    cpls_norm = [
        (cpl - config["cpl_mean"]) / config["cpl_std"] for cpl in cpl_seq
    ]
    blunder_seq = _parse_sequence(row.get("blunder_seq", []))
    if blunder_seq:
        blunders = [1.0 if bool(flag) else 0.0 for flag in blunder_seq[:length]]
    else:
        blunders = [
            1.0 if cpl > config["blunder_threshold"] else 0.0 for cpl in cpl_seq
        ]
    while len(cpls_norm) < length:
        cpls_norm.append(0.0)
    while len(blunders) < length:
        blunders.append(0.0)

    cpls = torch.tensor(cpls_norm[:length], dtype=torch.float32).unsqueeze(0)
    blunders_t = torch.tensor(blunders[:length], dtype=torch.float32).unsqueeze(0)
    lengths = torch.tensor([length])
    return positions, clocks, cpls, blunders_t, lengths


def prepare_game_from_sequences(
    pgn: str,
    clock_times: Sequence[float],
    cpl_sequence: Sequence[float],
    blunder_flags: Sequence[int | bool],
    config: Mapping[str, Any],
):
    row = {
        "Moves": pgn,
        "ClockSeq": list(clock_times),
        "cpl_seq": list(cpl_sequence),
        "blunder_seq": list(blunder_flags),
    }
    return prepare_game(row, config)


class EloPredictor:
    def __init__(
        self,
        model_path: str | Path,
        config: Mapping[str, Any] | None = None,
        device: str = "cpu",
    ):
        _require_dependencies()
        self.model_path = Path(model_path)
        self.config = dict(config or CONFIG)
        self.device = torch.device(device)
        self.model = self._load_model()

    def _load_model(self) -> RatingNet:
        if not self.model_path.exists():
            raise PredictionError(f"ELO model file not found: {self.model_path}")
        model = RatingNet(
            conv_filters=self.config["conv_filters"],
            lstm_layers=self.config["lstm_layers"],
            lstm_hidden=self.config["lstm_hidden"],
            fc1_hidden=self.config["fc1_hidden"],
            dropout_rate=self.config["dropout_rate"],
            bidirectional=self.config["bidirectional"],
            use_cpl=self.config["use_cpl"],
            use_blunder=self.config["use_blunder"],
        ).to(self.device)
        checkpoint = torch.load(self.model_path, map_location=self.device)
        state_dict = (
            checkpoint["model_state_dict"]
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
            else checkpoint
        )
        model.load_state_dict(state_dict)
        model.eval()
        return model

    def predict(
        self,
        pgn: str,
        clock_times: Sequence[float],
        cpl_sequence: Sequence[float],
        blunder_flags: Sequence[int | bool],
    ) -> EloPrediction:
        positions, clocks, cpls, blunders, lengths = prepare_game_from_sequences(
            pgn=pgn,
            clock_times=clock_times,
            cpl_sequence=cpl_sequence,
            blunder_flags=blunder_flags,
            config=self.config,
        )
        positions = positions.to(self.device)
        clocks = clocks.to(self.device)
        cpls = cpls.to(self.device)
        blunders = blunders.to(self.device)
        lengths = lengths.to(self.device)

        with torch.no_grad():
            _, last_out = self.model(
                positions,
                clocks,
                lengths,
                cpls=cpls if self.config["use_cpl"] else None,
                blunders=blunders if self.config["use_blunder"] else None,
            )
            pred = last_out * self.config["ratings_std"] + self.config["ratings_mean"]

        white_raw = float(pred[0, 0].item())
        black_raw = float(pred[0, 1].item())
        return EloPrediction(
            white_elo=int(round(white_raw)),
            black_elo=int(round(black_raw)),
            white_elo_raw=white_raw,
            black_elo_raw=black_raw,
        )
