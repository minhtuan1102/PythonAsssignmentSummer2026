from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv

from src.ai_engine.core.config import AgentSettings
from src.ai_engine.ai_agents.orchestrator import MultiAgentAnalyst, build_default_pipeline
from src.ai_engine.inference.elo_predictor import CONFIG, EloPredictor
from src.ai_engine.domain.schemas import AnalysisContext, MultiAgentReport
from src.ai_engine.services.stockfish import StockfishAnalyzer


@dataclass(frozen=True)
class PredictEloResult:
    white_elo: int
    black_elo: int
    cpl_sequence: tuple[float, ...]
    blunder_flags: tuple[int, ...]
    report: MultiAgentReport

    def to_api_data(self, include_debug: bool = False) -> dict[str, Any]:
        data = self.report.to_api_data(include_debug=include_debug)
        data["white_elo"] = self.white_elo
        data["black_elo"] = self.black_elo
        if include_debug:
            data["cpl_sequence"] = list(self.cpl_sequence)
            data["blunder_flags"] = list(self.blunder_flags)
        return data


class PredictEloPipeline:
    """Full plan orchestrator: Stockfish -> ELO model -> multi-agent analyst."""

    def __init__(
        self,
        stockfish_analyzer: StockfishAnalyzer,
        elo_predictor: EloPredictor,
        analyst: MultiAgentAnalyst,
    ):
        self.stockfish_analyzer = stockfish_analyzer
        self.elo_predictor = elo_predictor
        self.analyst = analyst

    def run(
        self,
        pgn: str,
        clock_times: Sequence[float],
        result: str | None = None,
        time_control: str | None = None,
    ) -> PredictEloResult:
        stockfish_result = self.stockfish_analyzer.analyze(pgn)
        prediction = self.elo_predictor.predict(
            pgn=pgn,
            clock_times=clock_times,
            cpl_sequence=stockfish_result.cpl_sequence,
            blunder_flags=stockfish_result.blunder_flags,
        )
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
        return PredictEloResult(
            white_elo=prediction.white_elo,
            black_elo=prediction.black_elo,
            cpl_sequence=stockfish_result.cpl_sequence,
            blunder_flags=stockfish_result.blunder_flags,
            report=report,
        )


def _repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def build_default_predict_elo_pipeline(
    analyst: MultiAgentAnalyst | None = None,
) -> PredictEloPipeline:
    load_dotenv()
    stockfish_path = _repo_path(
        os.getenv("STOCKFISH_PATH", "stockfish/stockfish-windows-x86-64-avx2.exe")
    )
    model_path = _repo_path(os.getenv("ELO_MODEL_PATH", "models/Hikaru_Nakamura_V1"))
    depth = int(os.getenv("STOCKFISH_DEPTH", "12"))
    agent_settings = AgentSettings.from_env(load_env_file=False)
    return PredictEloPipeline(
        stockfish_analyzer=StockfishAnalyzer(
            engine_path=stockfish_path,
            depth=depth,
            blunder_threshold=float(CONFIG["blunder_threshold"]),
        ),
        elo_predictor=EloPredictor(model_path=model_path, config=CONFIG),
        analyst=analyst or build_default_pipeline(settings=agent_settings),
    )
