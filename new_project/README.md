# 🤖 Agent QA 테스트 관리 시스템

LangSmith/LangChain Hub 기반의 AI Agent QA 테스트케이스 관리 및 GPT-4o 자동 평가 시스템입니다.

## ✨ 주요 기능

- 📋 **테스트케이스 관리**: Excel 파일을 LangSmith 데이터셋으로 자동 변환 및 관리
- 🤖 **GPT-4o 답변 생성**: 질문에 대한 실제 GPT-4o 답변 자동 생성
- ⚖️ **LLM-as-Judge 평가**: GPT-4o Judge를 사용한 0-5점 정확성 자동 평가
- 💾 **결과 저장**: 모든 평가 결과를 LangSmith 데이터셋에 체계적 저장
- 📈 **히스토리 추적**: 동일 테스트케이스의 여러 실행 결과 누적 추적
- 🔧 **프롬프트 관리**: LangChain Hub를 통한 중앙집중식 프롬프트 관리
- 🌐 **웹 인터페이스**: Gradio 기반 사용자 친화적 웹 UI
- 📊 **시각화**: 테스트 결과 시각화 및 비교 분석
- ⚙️ **서버 관리**: 웹 서버 시작/중지/상태 관리 도구

## 🏗️ 시스템 구조

```
new_project/
├── 📊 데이터 관리
│   ├── dataset_manager.py      # LangSmith 데이터셋 관리 및 평가 시스템
│   ├── real_implementation.py  # 실제 GPT-4o 질의 및 평가 구현
│   └── TestCase.xlsx          # 테스트케이스 Excel 파일
│
├── 🔧 시스템 관리
│   ├── prompt_manager.py       # LangChain Hub 프롬프트 관리
│   ├── server_manager.py       # 웹 서버 관리 도구
│   └── run.py                 # 통합 실행 스크립트
│
├── 🌐 사용자 인터페이스
│   ├── web_interface.py        # Gradio 웹 인터페이스
│   └── visualization.py       # 테스트 결과 시각화 도구
│
├── 📚 예시 및 문서
│   ├── example_usage.py        # 사용 예시 및 데모
│   └── README.md              # 이 파일
│
└── 📁 기타
    ├── __init__.py            # 패키지 초기화
    └── server_7861.log        # 서버 로그 파일
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경변수 파일 생성 (.env 파일을 프로젝트 루트에 생성)
# 필수 환경변수 설정
OPENAI_API_KEY=your_openai_api_key_here
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=your_project_name
```

### 2. 통합 실행 스크립트 사용

```bash
# 메인 실행 스크립트
python new_project/run.py
```

실행하면 다음 메뉴가 표시됩니다:
1. **웹 인터페이스 실행** - Gradio 웹 UI 시작
2. **프롬프트 관리** - LangChain Hub 프롬프트 생성/업데이트
3. **데이터셋에 TestCase 생성** - Excel → LangSmith 저장
4. **Judge 프롬프트 실행 후 평가** - GPT-4o 평가 실행
5. **서버 관리** - 웹 서버 시작/중지/상태 확인

### 3. 웹 인터페이스 직접 실행

```bash
python new_project/web_interface.py
```

브라우저에서 `http://localhost:7861`으로 접속하여 웹 인터페이스를 사용하세요.

## 📖 사용법

### 기본 워크플로우

1. **프롬프트 준비**: `accuracy_judge_prompt`를 LangChain Hub에 생성
2. **테스트케이스 준비**: `TestCase.xlsx` 파일에 case_id, question 컬럼으로 테스트케이스 작성
3. **데이터 저장**: Excel 파일을 LangSmith `Agent_QA_Scenario` 데이터셋에 저장
4. **평가 실행**: GPT-4o로 답변 생성 후 Judge로 평가하여 결과 저장
5. **결과 확인**: 웹 인터페이스에서 평가 결과 및 히스토리 확인

### 프로그래밍 방식 사용

```python
from dataset_manager import AgentQADatasetManager

# 데이터셋 매니저 초기화
manager = AgentQADatasetManager()

# 테스트케이스 추가
test_case_id = manager.add_test_case(
    question="대한민국의 수도는 어디야?",
    expected_answer="대한민국의 수도는 서울입니다."
)

# 답변 평가
result = manager.evaluate_answer(
    test_case_id=test_case_id,
    question="대한민국의 수도는 어디야?",
    actual_answer="서울입니다.",
    model_used="gpt-4o"
)

print(f"평가 점수: {result.judge_accuracy_score}/5")
print(f"평가 근거: {result.judge_reasoning}")
```

### 실제 GPT-4o 평가 시스템 사용

```python
from real_implementation import RealAgentQASystem

# 시스템 초기화
system = RealAgentQASystem()

# Excel에서 테스트케이스 로드
testcases = system.load_testcases_from_excel("TestCase.xlsx")

# LangSmith에 저장
system.save_testcases_to_langsmith(testcases)

# GPT-4o로 답변 생성 및 평가
stored_testcases = system.get_testcases_from_langsmith()
for tc in stored_testcases:
    answer = system.generate_answer_with_gpt4o(tc['question'])
    judge_result = system.judge_answer_with_gpt4o(tc['question'], answer)
    print(f"{tc['case_id']}: {judge_result['score']}/5점")
```

## 🎯 데이터 구조

### LangSmith 데이터셋

1. **Agent_QA_Scenario**: 테스트케이스 저장
   - inputs: `{"question": "질문 내용"}`
   - metadata: `{"case_id": "TC_001", "source": "TestCase.xlsx"}`

2. **Agent_QA_Scenario_Judge_Result**: 평가 결과 저장
   - inputs: `{"input": "질문 내용"}`
   - outputs: `{"answer": "LLM 답변", "judge_accuracy_score": 4, "judge_reasoning": "평가 근거"}`
   - metadata: `{"case_id": "TC_001", "model_used": "gpt-4o"}`

3. **Agent_QA_Scenario_Judge_History**: 히스토리 누적 저장
   - outputs: `{"scores": [4, 5, 3], "answers": [...], "reasons": [...], "timestamps": [...]}`

### 테스트케이스 (TestCase)
```python
@dataclass
class TestCase:
    id: str                    # 테스트케이스 고유 ID
    question: str              # 질문
    expected_answer: str       # 기대 답변 (선택사항)
    created_at: str           # 생성 시간
```

### 평가 결과 (EvaluationResult)
```python
@dataclass
class EvaluationResult:
    test_case_id: str          # 테스트케이스 ID
    execution_id: str          # 실행 고유 ID
    question: str              # 질문
    actual_answer: str         # 실제 답변
    judge_accuracy_score: float # 정확성 점수 (0-5)
    judge_reasoning: str       # 평가 근거
    execution_time: str        # 실행 시간
    model_used: str           # 사용된 모델명
```

## 📊 평가 기준

LLM-as-Judge는 다음 기준으로 0-5점 사이로 평가합니다:

- **5점**: 완벽히 정확하고 완전한 답변
- **4점**: 대부분 정확하며 약간의 부족함이 있음  
- **3점**: 기본적으로 정확하나 중요한 정보가 누락됨
- **2점**: 부분적으로 정확하나 오류나 부정확한 정보 포함
- **1점**: 대부분 부정확하나 일부 관련된 정보 포함
- **0점**: 완전히 부정확하거나 관련 없는 답변

## 🌐 웹 인터페이스 기능

### 1. 메인 실행 탭
- TestCase.xlsx → LangSmith 저장
- GPT-4o 평가 실행/저장
- 실시간 로그 스트리밍

### 2. 프롬프트 관리 탭
- accuracy_judge_prompt 생성/업데이트
- 현재 버전 조회
- LangChain Hub 연동

### 3. 평가 결과 탭
- 최신 평가 결과 테이블
- 요약 통계 (평균, 최고, 최저 점수)
- 점수 분포 현황
- LangSmith 데이터셋 직접 링크

### 4. 히스토리 조회 탭
- case_id별 히스토리 선택
- 점수 타임라인 그래프
- 상세 히스토리 테이블
- Trace 링크 제공

### 5. 서버 관리 탭
- 서버 상태 확인
- 서버 중지 기능
- 실시간 상태 업데이트

### 6. 시스템 정보 탭
- 시스템 개요 및 사용법
- 평가 기준 설명
- 연동 서비스 정보

## 🔧 고급 설정

### 커스텀 Judge 모델
```python
from langchain_openai import ChatOpenAI

manager = AgentQADatasetManager()
manager.judge_llm = ChatOpenAI(model="gpt-4", temperature=0)
```

### 프롬프트 관리
```python
from prompt_manager import PromptManager

pm = PromptManager()
# 프롬프트 생성/업데이트
pm.create_or_update_accuracy_judge_prompt()
# 현재 버전 조회
pm.list_prompts()
```

### 서버 관리
```python
from server_manager import ServerManager

sm = ServerManager(port=7861)
sm.start_server()    # 서버 시작
sm.server_status()   # 상태 확인
sm.stop_server()     # 서버 중지
```

## 📈 시각화 기능

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

# 요약 리포트 생성
summary = visualizer.generate_summary_report(test_case_histories)
```

## 🔍 예시 시나리오

### 시나리오 1: 기본 QA 테스트
1. `TestCase.xlsx`에 질문 작성
2. 웹 인터페이스에서 "TestCase.xlsx → LangSmith 저장" 실행
3. "GPT-4o 평가 실행/저장" 실행
4. 평가 결과 탭에서 결과 확인

### 시나리오 2: 프로그래밍 방식 사용
```python
# 예시 코드 실행
python new_project/example_usage.py
```

### 시나리오 3: 서버 관리
```bash
# 서버 시작
python new_project/server_manager.py start

# 서버 상태 확인
python new_project/server_manager.py status

# 서버 중지
python new_project/server_manager.py stop
```

## 🛠️ 확장 가능성

### 커스텀 평가 메트릭 추가
- `real_implementation.py`의 `judge_answer_with_gpt4o` 메서드 확장
- 추가 평가 기준 (관련성, 완전성 등) 구현

### 배치 평가 기능
- 여러 테스트케이스 동시 처리
- 병렬 처리를 통한 성능 최적화

### 다양한 모델 지원
- GPT-4o 외 다른 LLM 모델 연동
- 모델별 성능 비교 분석

## 🐛 문제 해결

### 일반적인 문제들

1. **API 키 오류**
   - `.env` 파일의 API 키가 올바른지 확인
   - LangSmith 계정 상태 및 프로젝트 설정 확인

2. **데이터셋 접근 오류**
   - LangSmith 프로젝트 권한 확인
   - 네트워크 연결 상태 확인

3. **평가 실패**
   - OpenAI API 한도 및 크레딧 확인
   - Judge 프롬프트 설정 확인

4. **웹 인터페이스 오류**
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
from dataset_manager import AgentQADatasetManager
manager = AgentQADatasetManager()
"
```

## 🔗 연동 서비스

- **LangSmith**: 데이터셋 관리, 실행 추적, 평가 결과 저장
- **LangChain Hub**: 중앙집중식 프롬프트 관리 및 버전 관리
- **OpenAI GPT-4o**: 답변 생성 및 LLM-as-Judge 평가
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

**Happy Testing! 🎉**