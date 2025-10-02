"""
EV RAG Agent
- Uses two markdown files: 테슬라_KR.md, 리비안_KR.md
- Builds in-memory FAISS index with OpenAI embeddings
- Retrieves top chunks and generates answer with GPT-4o including citations
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import os as _os_env
_os_env.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
_os_env.environ.setdefault("OMP_NUM_THREADS", "1")
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


_AGENT_SINGLETON = None


class EVRAGAgent:
    def __init__(self, doc_paths: List[str], model: str = "gpt-4o"):
        load_dotenv()
        self.doc_paths = [str(Path(p)) for p in doc_paths]
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        self.vs: FAISS | None = None
        self._build_index()

    def _read_text(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return p.read_text(errors="ignore")

    def _build_index(self) -> None:
        docs: List[Document] = []
        for path in self.doc_paths:
            text = self._read_text(path)
            if not text:
                continue
            base = {"source": Path(path).name}
            chunks = self.splitter.split_text(text)
            for i, chunk in enumerate(chunks):
                meta = dict(base)
                meta["chunk_id"] = i
                docs.append(Document(page_content=chunk, metadata=meta))
        if docs:
            self.vs = FAISS.from_documents(docs, self.embeddings)
        else:
            self.vs = None

    def answer(self, query: str, k: int = 6) -> Tuple[str, List[dict]]:
        if not self.vs:
            return "지식 베이스가 비어 있습니다.", []
        docs = self.vs.similarity_search(query, k=k)
        context = "\n\n".join([f"[{i+1}] {d.page_content}" for i, d in enumerate(docs)])
        citations = [
            {"rank": i + 1, "source": d.metadata.get("source", "-"), "chunk_id": d.metadata.get("chunk_id", -1)}
            for i, d in enumerate(docs)
        ]
        system = (
            "당신은 전기 자동차 도메인의 RAG 기반 조수입니다. 주어진 컨텍스트에서만 답하며, "
            "근거가 없으면 모른다고 말하세요. 답변 끝에 참고한 출처 번호를 대괄호로 표기하세요. 예: [1][2]"
        )
        user = f"질문: {query}\n\n컨텍스트:\n{context}"
        msg = [("system", system), ("human", user)]
        ans = self.llm.invoke(msg).content
        return ans, citations


def get_ev_agent() -> EVRAGAgent:
    global _AGENT_SINGLETON
    if _AGENT_SINGLETON is None:
        base_dir = Path(__file__).parent
        doc_paths = [str(base_dir / "테슬라_KR.md"), str(base_dir / "리비안_KR.md")]
        _AGENT_SINGLETON = EVRAGAgent(doc_paths)
    return _AGENT_SINGLETON


