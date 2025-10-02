# 🤖 Agent QA 테스트 관리 시스템 (전기차 RAG Agent 통합)

LangSmith/LangChain Hub 기반의 AI Agent QA 테스트케이스 관리 및 전기차 도메인 RAG Agent + LLM-as-Judge 자동 평가 시스템입니다.

## ✨ 주요 기능

- 🚗 **전기차 RAG Agent**: 테슬라/리비안 문서 기반 지능형 질의응답 (하이브리드 검색 + 분류기)
- 🤖 **GPT-4o 통합**: RAG 기반 답변 생성 + 일상 대화 라우팅
- ⚖️ **LLM-as-Judge 평가**: GPT-4o Judge를 사용한 0-5점 정확성 자동 평가
- 📋 **테스트케이스 관리**: Excel 파일(다중 시트 지원) 업로드 및 LangSmith 데이터셋 자동 변환
- 💾 **결과 저장**: 모든 평가 결과를 LangSmith 데이터셋에 체계적 저장
- 📈 **히스토리 추적**: 동일 테스트케이스의 여러 실행 결과 누적 추적 및 실행 순번 기반 시각화
- 🔧 **프롬프트 관리**: LangChain Hub를 통한 중앙집중식 프롬프트 관리
- 🌐 **웹 인터페이스**: Gradio 기반 대화형 UI + 평가 파이프라인 통합
- 📊 **시각화**: 테스트 결과 시각화 및 비교 분석
- ⚙️ **서버 관리**: 웹 서버 시작/중지/상태 관리 도구

## 🏗️ 시스템 구조

```
new_project/
├── 🚗 전기차 RAG Agent
│   ├── ev_rag_agent.py             # RAG 엔진 (FAISS + 문서 검색 + GPT-4o)
│   ├── ev_agent_orchestrator.py    # RAG/CHAT 라우팅 오케스트레이터 (LLM 분류기 + 키워드 룰)
│   ├── 테슬라_KR.md                # 테슬라 전기차 도메인 지식 문서
│   ├── 리비안_KR.md                # 리비안 전기차 도메인 지식 문서
│   └── rag_store/                  # FAISS 인덱스 및 BM25 코퍼스 저장소
│
├── 📊 데이터 관리
│   ├── dataset_manager.py          # LangSmith 데이터셋 관리 및 평가 시스템
│   ├── real_implementation.py      # 실제 RAG Agent 질의 + Judge 평가 파이프라인
│   ├── TestCase.xlsx               # 테스트케이스 Excel 파일 (기본)
│   └── UPLOAD_GUIDE.md             # Excel 업로드 가이드
│
├── 🔧 시스템 관리
│   ├── prompt_manager.py           # LangChain Hub 프롬프트 관리
│   ├── server_manager.py           # 웹 서버 관리 도구
│   └── run.py                      # 통합 실행 스크립트 (CLI 메뉴)
│
├── 🌐 사용자 인터페이스
│   ├── web_interface.py            # Gradio 웹 인터페이스 (대화형 RAG + 평가 파이프라인)
│   └── visualization.py            # 테스트 결과 시각화 도구
│
├── 📚 예시 및 문서
│   ├── example_usage.py            # 사용 예시 및 데모
│   ├── README.md                   # 이 파일
│   └── 발표용_워크플로우.md        # 워크플로우 문서
│
└── 📁 기타
    ├── __init__.py                # 패키지 초기화
    └── server_7861.log            # 서버 로그 파일
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경변수 파일 생성 (.env 파일을 프로젝트 루트에 생성)
# 필수 환경변수 설정
OPENAI_API_KEY=your_openai_api_key_here
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=your_project_name
LANGSMITH_TRACING=true
```

### 2. 통합 실행 스크립트 사용

```bash
# 메인 실행 스크립트
python new_project/run.py
```

실행하면 다음 메뉴가 표시됩니다:
1. **웹 인터페이스 실행** - Gradio 웹 UI 시작 (대화형 RAG + 평가)
2. **프롬프트 관리** - LangChain Hub 프롬프트 생성/업데이트
3. **데이터셋에 TestCase 생성** - Excel → LangSmith 저장 (외부 파일 업로드 지원)
4. **Judge 프롬프트 실행 후 평가** - RAG Agent + Judge 평가 실행
5. **서버 관리** - 웹 서버 시작/중지/상태 확인
6. **프로그램 종료**

### 3. 웹 인터페이스 직접 실행

```bash
python new_project/web_interface.py
```

브라우저에서 `http://localhost:7861`으로 접속하여 웹 인터페이스를 사용하세요.

## 📖 사용법

### 기본 워크플로우

1. **프롬프트 준비**: `accuracy_judge_prompt`를 LangChain Hub에 생성 (프롬프트 관리 탭)
2. **전기차 RAG 대화**: 첫 번째 탭에서 테슬라/리비안 관련 질문 → RAG 답변 확인 (출처 표시)
3. **테스트케이스 준비**: `TestCase.xlsx` 파일에 `case_id`, `question` 컬럼으로 테스트케이스 작성 (또는 웹 UI에서 직접 업로드)
4. **데이터 저장**: Excel 파일을 LangSmith `Agent_QA_Scenario` 데이터셋에 저장 (다중 시트 자동 병합)
5. **평가 실행**: RAG Agent로 답변 생성 → GPT-4o Judge로 평가 → 결과 저장
6. **결과 확인**: 웹 인터페이스에서 평가 결과, 히스토리, 점수 추이(실행 순번 기반 그래프) 확인

### 전기차 RAG Agent 특징

- **지능형 라우팅**: 
  - 키워드 매칭 우선: EV/배터리/충전/테슬라/리비안 등 → 즉시 RAG 경로
  - LLM 분류기 보조: 애매한 질문은 GPT-4o 분류기로 RAG/CHAT 결정
- **문서 기반 답변**: 테슬라_KR.md, 리비안_KR.md에서 컨텍스트 검색 후 답변 생성 (출처 번호 표시)
- **일상 대화 지원**: 전기차 비관련 질문은 GPT-4o 일반 대화 모드로 처리

### 프로그래밍 방식 사용 - 전기차 RAG Agent

```python
from ev_agent_orchestrator import EVAgentOrchestrator

# 오케스트레이터 초기화 (RAG + 일반 대화)
orchestrator = EVAgentOrchestrator()

# 전기차 관련 질문 (RAG 경로)
answer, citations = orchestrator.chat("테슬라 모델 Y의 주행거리는?")
print(answer)
for cite in citations:
    print(f"  [{cite['rank']}] {cite['source']} (chunk {cite['chunk_id']})")

# 일상 질문 (CHAT 경로)
answer, _ = orchestrator.chat("오늘 날씨 어때?")
print(answer)
```

### 실제 평가 파이프라인 사용

```python
from real_implementation import RealAgentQASystem

# 시스템 초기화 (RAG Agent 통합)
system = RealAgentQASystem()

# Excel에서 테스트케이스 로드 (다중 시트 병합 지원)
testcases = system.load_testcases_from_excel("TestCase.xlsx")

# LangSmith에 저장 (중복 방지)
system.save_testcases_to_langsmith(testcases)

# RAG Agent로 답변 생성 + Judge 평가
stored_testcases = system.get_testcases_from_langsmith()
for tc in stored_testcases:
    # 내부적으로 EVAgentOrchestrator 사용 (폴백: GPT-4o 직접)
    answer = system.generate_answer_with_rag_agent(tc['question'])
    judge_result = system.judge_answer_with_gpt4o(tc['question'], answer)
    print(f"{tc['case_id']}: {judge_result['score']}/5점 - {judge_result['reasoning'][:50]}...")
```

## 🎯 데이터 구조

### LangSmith 데이터셋

1. **Agent_QA_Scenario**: 테스트케이스 저장
   - inputs: `{"question": "질문 내용"}`
   - metadata: `{"case_id": "TC_001", "source": "TestCase.xlsx"}`

2. **Agent_QA_Scenario_Judge_Result**: 평가 결과 저장
   - inputs: `{"input": "질문 내용"}`
   - outputs: `{"answer": "RAG Agent 답변", "judge_accuracy_score": 4, "judge_reasoning": "평가 근거"}`
   - metadata: `{"case_id": "TC_001", "model_used": "gpt-4o", "trace_url": "..."}`

3. **Agent_QA_Scenario_Judge_History**: 히스토리 누적 저장
   - outputs: `{"scores": [4, 5, 3], "answers": [...], "reasons": [...], "timestamps": [...], "trace_urls": [...]}`

### 테스트케이스 Excel 형식

| case_id | question | expected_answer (선택) |
|---------|----------|------------------------|
| TC_001 | 테슬라 Supercharger의 강점은? | (비워도 됨) |
| TC_002 | 리비안 R1T의 오프로드 성능은? | |
| TC_003 | 오늘 날씨 어때? | (일상 대화 - CHAT 경로) |

- 다중 시트 지원: 모든 시트를 자동 병합
- 결측치 로깅: case_id/question 없는 행은 제외하고 사유 출력

## 📊 평가 기준

LLM-as-Judge (GPT-4o)는 다음 기준으로 0-5점 사이의 **정수**로 평가합니다:

- **5점**: 완벽히 정확하고 완전한 답변
- **4점**: 대부분 정확하며 약간의 부족함이 있음  
- **3점**: 기본적으로 정확하나 중요한 정보가 누락됨
- **2점**: 부분적으로 정확하나 오류나 부정확한 정보 포함
- **1점**: 대부분 부정확하나 일부 관련된 정보 포함
- **0점**: 완전히 부정확하거나 관련 없는 답변

## 🌐 웹 인터페이스 기능

### 1. 🧠 전기차 RAG 대화 탭 (첫 번째)
- **대화형 Agent**: 전기차/일반 대화 자동 라우팅 (키워드 + LLM 분류기)
- **출처 표시**: RAG 답변 시 근거 문서 및 청크 ID 표시
- **Enter 제출**: 입력창에서 Enter로 즉시 전송
- **실시간 응답**: 스트리밍 없이 즉시 답변 표시

### 2. 🚀 메인 실행 탭
- **TestCase 업로드**: 로컬 Excel 파일 업로드 후 LangSmith 저장 (외부 파일 우선, 다중 시트 병합)
- **RAG 기반 평가 실행**: 전기차 RAG Agent로 답변 생성 → Judge 평가 → 결과 저장
- **실시간 로그 스트리밍**: 진행 상황 실시간 출력

### 3. 🔧 프롬프트 관리 탭
- `accuracy_judge_prompt` 생성/업데이트
- 현재 Hub 버전 조회
- LangChain Hub 연동

### 4. 📊 평가 결과 탭
- 최신 평가 결과 테이블 (case_id, question, answer, score)
- 요약 통계 (총 건수, 평균/최고/최저 점수)
- 점수 분포 현황 (0-5점별 건수)
- LangSmith 데이터셋 직접 링크

### 5. 📈 히스토리 조회 탭
- case_id별 히스토리 선택
- **점수 추이 그래프** (x축: 실행 순번, y축: 점수 0-5)
- 상세 히스토리 테이블 (timestamp, score, reason, trace 링크)
- Trace 열기 버튼 (LangSmith trace URL)

### 6. ⚙️ 서버 관리 탭
- 서버 상태 확인
- 서버 중지 기능
- 실시간 상태 업데이트

### 7. ℹ️ 시스템 정보 탭
- 시스템 개요 및 사용법
- 평가 기준 설명
- 연동 서비스 정보

## 🔧 고급 설정

### 전기차 RAG Agent 커스터마이징

```python
from ev_rag_agent import EVRAGAgent

# 문서 경로 지정
doc_paths = ["테슬라_KR.md", "리비안_KR.md", "custom_ev_doc.md"]
agent = EVRAGAgent(doc_paths, model="gpt-4o")

# 검색 k값 조정
answer, citations = agent.answer("질문", k=10)
```

### 라우팅 키워드 추가/수정

```python
# ev_agent_orchestrator.py 수정
EV_KEYWORDS = [
    "ev", "전기차", "배터리", "충전", "테슬라", "리비안",
    "your_custom_keyword"  # 추가
]
```

### Judge 모델 변경

```python
from langchain_openai import ChatOpenAI
from real_implementation import RealAgentQASystem

system = RealAgentQASystem()
system.judge_model = ChatOpenAI(model="gpt-4", temperature=0)
```

### 프롬프트 관리

```python
from prompt_manager import PromptManager

pm = PromptManager()
pm.create_or_update_accuracy_judge_prompt()  # Hub에 업로드
pm.list_prompts()  # 현재 버전 조회
```

## 📈 시각화 기능

### 히스토리 그래프 (실행 순번 기준)
- x축: 1, 2, 3... (시간이 아닌 순번)
- y축: 점수 0-5
- 제목: case_id + 질문 요약

### 테스트 히스토리 시각화

```python
from visualization import TestHistoryVisualizer

visualizer = TestHistoryVisualizer()

# 단일 테스트케이스 타임라인
fig = visualizer.create_single_testcase_timeline(history, test_case_id)
fig.show()

# 전체 비교 대시보드
dashboard = visualizer.create_history_comparison(all_histories)
dashboard.show()
```

## 🔍 예시 시나리오

### 시나리오 1: 전기차 RAG 대화
1. 웹 UI 첫 탭 "전기차 RAG 대화" 열기
2. "테슬라 Supercharger 네트워크의 장점은?" 입력 → Enter
3. 답변 확인 + 우측 출처 표(rank, source, chunk_id) 확인
4. "오늘 날씨 어때?" 입력 → 일반 대화 모드로 답변 (출처 없음)

### 시나리오 2: TestCase 평가 파이프라인
1. Excel 파일 준비 (TC_001~TC_008)
2. 메인 실행 탭 → 파일 업로드 → "TestCase → LangSmith 저장"
3. "RAG 기반 평가 실행/저장" 클릭
4. 로그에서 각 TC의 RAG 답변 + Judge 점수 확인
5. 평가 결과 탭 → 요약 통계/점수 분포 확인
6. 히스토리 조회 탭 → case_id 선택 → 점수 추이 그래프 확인

### 시나리오 3: 프로그래밍 방식 사용
```python
# 예시 코드 실행
python new_project/example_usage.py
```

## 🛠️ 확장 가능성

### 추가 도메인 문서 통합
- `ev_rag_agent.py`의 doc_paths에 새 .md 파일 추가
- FAISS 인덱스 자동 재구성

### 커스텀 평가 메트릭 추가
- `real_implementation.py`의 `judge_answer_with_gpt4o` 메서드 확장
- 추가 평가 기준 (관련성, 완전성 등) 구현

### 다양한 모델 지원
- GPT-4o 외 다른 LLM 모델 연동
- 모델별 성능 비교 분석

### 하이브리드 검색 강화
- BM25 + Dense 검색 가중치 조정
- Cross-Encoder Re-ranking 추가

## 🐛 문제 해결

### 일반적인 문제들

1. **API 키 오류**
   - `.env` 파일의 API 키가 올바른지 확인
   - LangSmith 계정 상태 및 프로젝트 설정 확인

2. **OpenMP 충돌 (macOS)**
   - 증상: `libomp.dylib already initialized` 오류
   - 해결: `ev_rag_agent.py`에 KMP_DUPLICATE_LIB_OK=TRUE 설정 적용됨 (자동)

3. **Excel 로드 오류**
   - 컬럼명 확인: `case_id`, `question` 필수
   - 다중 시트: 모든 시트 자동 병합 (로그에서 시트 수 확인)
   - 결측치: 로그에서 제외된 행 사유 확인

4. **RAG 답변이 일반 LLM으로 빠지는 경우**
   - 키워드 목록 확장 (`ev_agent_orchestrator.py` → `EV_KEYWORDS`)
   - 분류 프롬프트 강화

5. **웹 인터페이스 오류**
   - 포트 7861이 사용 중인지 확인
   - 서버 로그 파일 확인 (`server_7861.log`)

### 로그 확인
```bash
# 서버 로그 확인
python new_project/server_manager.py logs

# 디버그 모드 실행
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from real_implementation import RealAgentQASystem
system = RealAgentQASystem()
"
```

## 🔗 연동 서비스

- **LangSmith**: 데이터셋 관리, 실행 추적, 평가 결과 저장
- **LangChain Hub**: 중앙집중식 프롬프트 관리 및 버전 관리
- **OpenAI GPT-4o**: RAG Agent 답변 생성, 분류기, LLM-as-Judge 평가
- **FAISS**: 벡터 유사도 검색 (in-memory)
- **Gradio**: 웹 인터페이스 프레임워크
- **Plotly**: 시각화 및 대시보드

## 🤝 기여하기

1. Fork 프로젝트
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.

## 🙋‍♂️ 지원

문제가 있거나 기능 요청이 있으시면 GitHub Issues를 통해 문의해주세요.

---

**Happy Testing with EV RAG Agent! 🚗⚡🎉**
