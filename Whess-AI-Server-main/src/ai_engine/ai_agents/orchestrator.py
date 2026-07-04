from __future__ import annotations

from src.ai_engine.ai_agents.data_miner import DataMinerAgent
from src.ai_engine.ai_agents.head_coach import HeadCoachAgent
from src.ai_engine.ai_agents.tactician import TacticianAgent
from src.ai_engine.core.config import AgentSettings
from src.ai_engine.services.llm_client import LLMClient, OpenAICompatibleLLMClient
from src.ai_engine.domain.schemas import AnalysisContext, MultiAgentReport


class MultiAgentAnalyst:
    """Step-3 orchestrator: Data Miner -> Tactician -> Head Coach."""

    def __init__(
        self,
        data_miner: DataMinerAgent,
        tactician: TacticianAgent,
        head_coach: HeadCoachAgent,
    ):
        self.data_miner = data_miner
        self.tactician = tactician
        self.head_coach = head_coach

    def run(self, context: AnalysisContext) -> MultiAgentReport:
        mined = self.data_miner.run(context)
        tactical_report = self.tactician.run(mined)
        explanation = self.head_coach.run(mined, tactical_report)
        return MultiAgentReport(
            eco=mined.eco,
            stats=mined.stats,
            explanation=explanation,
            critical_blunders=mined.critical_blunders,
            tactical_report=tactical_report,
            white_elo=mined.white_elo,
            black_elo=mined.black_elo,
        )


def build_default_pipeline(
    settings: AgentSettings | None = None,
    llm_client: LLMClient | None = None,
) -> MultiAgentAnalyst:
    if llm_client is None:
        settings = settings or AgentSettings.from_env()
        client = OpenAICompatibleLLMClient(settings)
    else:
        client = llm_client
    max_retries = settings.max_retries if settings else 2
    return MultiAgentAnalyst(
        data_miner=DataMinerAgent(),
        tactician=TacticianAgent(
            llm_client=client,
            max_retries=max_retries,
        ),
        head_coach=HeadCoachAgent(
            llm_client=client,
            max_retries=max_retries,
        ),
    )
