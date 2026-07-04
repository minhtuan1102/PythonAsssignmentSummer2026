from __future__ import annotations

from fastapi import FastAPI

from src.ai_engine.api_models import (
    PredictEloRequest,
    PredictEloResponse,
    Step3AnalysisRequest,
    Step3AnalysisResponse,
)
from src.ai_engine.config import AgentConfigError
from src.ai_engine.errors import MultiAgentError
from src.ai_engine.full_pipeline import PredictEloPipeline, build_default_predict_elo_pipeline
from src.ai_engine.pipeline import MultiAgentAnalyst, build_default_pipeline


def create_app(
    pipeline: MultiAgentAnalyst | None = None,
    predict_elo_pipeline: PredictEloPipeline | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Chess AI Engine Server",
        version="0.1.0",
        description="Stockfish CPL, CNN-BiLSTM ELO prediction, and multi-agent chess explanation.",
    )
    app.state.pipeline = pipeline
    app.state.predict_elo_pipeline = predict_elo_pipeline

    @app.on_event("startup")
    def startup() -> None:
        if app.state.predict_elo_pipeline is None:
            app.state.predict_elo_pipeline = build_default_predict_elo_pipeline()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/multi-agent-analysis", response_model=Step3AnalysisResponse)
    def analyze_game(request: Step3AnalysisRequest) -> Step3AnalysisResponse:
        try:
            if app.state.pipeline is None:
                app.state.pipeline = build_default_pipeline()
            analyst = app.state.pipeline
            report = analyst.run(request.to_context())
            return Step3AnalysisResponse(
                success=True,
                data=report.to_api_data(include_debug=request.include_debug),
            )
        except (AgentConfigError, MultiAgentError, ValueError) as exc:
            return Step3AnalysisResponse(success=False, error=str(exc))

    @app.post("/api/predict-elo", response_model=PredictEloResponse)
    def predict_elo(request: PredictEloRequest) -> PredictEloResponse:
        try:
            if app.state.predict_elo_pipeline is None:
                app.state.predict_elo_pipeline = build_default_predict_elo_pipeline()
            full_pipeline = app.state.predict_elo_pipeline
            result = full_pipeline.run(
                pgn=request.pgn,
                clock_times=request.clock_times,
                result=request.result,
                time_control=request.time_control,
            )
            return PredictEloResponse(
                success=True,
                data=result.to_api_data(include_debug=request.include_debug),
            )
        except (AgentConfigError, MultiAgentError, ValueError) as exc:
            return PredictEloResponse(success=False, error=str(exc))

    return app


app = create_app()
