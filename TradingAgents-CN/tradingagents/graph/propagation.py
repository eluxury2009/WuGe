# TradingAgents/graph/propagation.py

import os
from typing import Dict, Any

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, company_name: str, trade_date: str
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph."""
        from langchain_core.messages import HumanMessage

        # 🔥 修复：创建明确的分析请求消息，而不是只传递股票代码
        # 这样可以确保所有LLM（包括DeepSeek）都能理解任务
        analysis_request = f"请对股票 {company_name} 进行全面分析，交易日期为 {trade_date}。"

        # 价格锚定：仪表盘注入实时价，防止模型编造价格量级
        _anchor = os.getenv("TA_CURRENT_PRICE", "").strip()
        try:
            if _anchor and float(_anchor) > 0:
                analysis_request += (
                    f" 【价格锚定】该股当前最新成交价约为 {_anchor} 元。"
                    f"所有目标价、止损位、支撑/压力位都必须与该价格同一量级（偏离不超过±50%）；"
                    f"若你的数据或记忆与该量级冲突，一律以锚定价为准重新推理。"
                )
        except ValueError:
            pass

        # 数据纪律：数据缺失时禁止虚构数字
        analysis_request += (
            " 【数据纪律】若工具返回的数据为空或缺失，你必须明确声明“该项数据不可用”"
            "并显著降低结论置信度；严禁凭训练记忆编造任何财务指标(PE/PB/毛利率等)或价格数字。"
        )

        # 短线模式：由环境变量 TA_ANALYSIS_MODE=short 注入（五哥仪表盘短线开关）
        if os.getenv("TA_ANALYSIS_MODE", "").strip().lower() == "short":
            analysis_request += (
                " 这是短线交易分析：请聚焦最近5-10个交易日的量价表现、技术指标与资金流向，"
                "给出的操作建议、目标价与止损位应面向未来1-2周的短线操作，明确入场/离场价位与短线催化因素。"
            )

        return {
            "messages": [HumanMessage(content=analysis_request)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "investment_debate_state": InvestDebateState(
                {"history": "", "current_response": "", "count": 0}
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "history": "",
                    "current_risky_response": "",
                    "current_safe_response": "",
                    "current_neutral_response": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
        }

    def get_graph_args(self, use_progress_callback: bool = False) -> Dict[str, Any]:
        """Get arguments for the graph invocation.

        Args:
            use_progress_callback: If True, use 'updates' mode for node-level progress tracking.
                                  If False, use 'values' mode for complete state updates.
        """
        # 使用 'updates' 模式可以获取节点级别的更新，用于进度跟踪
        # 使用 'values' 模式可以获取完整的状态更新
        stream_mode = "updates" if use_progress_callback else "values"

        return {
            "stream_mode": stream_mode,
            "config": {"recursion_limit": self.max_recur_limit},
        }
