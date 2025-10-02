from __future__ import annotations

from typing import Tuple
import json

from langchain_openai import ChatOpenAI

from ev_rag_agent import get_ev_agent


EV_KEYWORDS = [
    "ev", "전기차", "배터리", "주행거리", "충전", "충전소", "슈퍼차저", "초급속",
    "테슬라", "리비안", "rivian", "tesla", "모델 y", "모델 3", "model y", "model 3",
    "r1t", "r1s", "heat pump", "오토파일럿", "fsd", "기가팩토리", "ot a", "ota"
]


class EVAgentOrchestrator:
    """Route between RAG and small-talk with a simple heuristic.
    - If question mentions EV entities/terms, use RAG; otherwise use LLM chat.
    """

    def __init__(self, model: str = "gpt-4o"):
        # 분류는 결정적이도록 temperature=0, 일반 대화는 0.7
        self.classifier_llm = ChatOpenAI(model=model, temperature=0)
        self.llm = ChatOpenAI(model=model, temperature=0.7)
        self.rag_agent = get_ev_agent()

    def _classify(self, q: str) -> Tuple[str, float]:
        """LLM 분류기: 'RAG' 또는 'CHAT' 라우팅 결정.
        Returns: (route, confidence)
        """
        sys = (
            "당신은 라우팅 분류기입니다. 다음 기준을 따르세요.\n"
            "- 전기차/배터리/충전/주행거리/모델명/브랜드(테슬라, 리비안) 등 EV 관련이면 무조건 'RAG'.\n"
            "- 일반 잡담/날씨/달력/수학/일상 질문이면 'CHAT'.\n"
            "오직 JSON만 출력하세요."
        )
        user = (
            "질문: " + (q or "") + "\n\n"
            "JSON 형식: {\"route\": \"RAG|CHAT\", \"confidence\": 0..1}"
        )
        try:
            out = self.classifier_llm.invoke([("system", sys), ("human", user)]).content
            data = json.loads(out)
            route = str(data.get("route", "CHAT")).upper()
            conf = float(data.get("confidence", 0.5))
            if route not in ("RAG", "CHAT"):
                route = "CHAT"
            return route, conf
        except Exception:
            # 실패 시 보수적으로 CHAT로 폴백
            return "CHAT", 0.0

    def chat(self, user_query: str) -> Tuple[str, list[dict]]:
        # 1) 키워드 선행 룰: EV 키워드가 포함되면 강제 RAG
        ql = (user_query or "").lower()
        if any(k in ql for k in EV_KEYWORDS):
            answer, cites = self.rag_agent.answer(user_query)
            return answer, cites

        # 2) LLM 분류기로 최종 결정
        route, _ = self._classify(user_query)
        if route == "RAG":
            answer, cites = self.rag_agent.answer(user_query)
            return answer, cites
        # small talk fallback
        sys = (
            "당신은 친절한 한국어 어시스턴트입니다. 전기차 관련 질문이 아닌 경우에는 일반적인 대화를 해주세요."
        )
        msg = [("system", sys), ("human", user_query)]
        ans = self.llm.invoke(msg).content
        return ans, []


