"""
Agent QA Scenario Dataset Manager
LangSmith/LangFuse를 사용해서 테스트케이스를 관리하고 LLM-as-Judge로 평가하는 시스템
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json

from langsmith import Client as LangSmithClient
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from pathlib import Path

# 여러 경로에서 .env 파일 찾아서 로드
current_dir = Path(__file__).parent
env_paths = [
    current_dir / ".env",  # new_project/.env
    current_dir.parent / ".env",  # llm-3/.env (상위 디렉토리)
    Path.cwd() / ".env"  # 현재 실행 디렉토리
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

@dataclass
class TestCase:
    """테스트케이스 데이터 구조"""
    id: str
    question: str
    expected_answer: Optional[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class EvaluationResult:
    """평가 결과 데이터 구조"""
    test_case_id: str
    execution_id: str
    question: str
    actual_answer: str
    judge_accuracy_score: float
    judge_reasoning: str
    execution_time: str
    model_used: str
    
    def __post_init__(self):
        if not hasattr(self, 'execution_time') or self.execution_time is None:
            self.execution_time = datetime.now().isoformat()

class AgentQADatasetManager:
    """Agent QA 시나리오 데이터셋 관리자"""
    
    def __init__(self, 
                 dataset_name: str = "Agent_QA_Scenario_Judge_Result",
                 use_langsmith: bool = True):
        """
        Args:
            dataset_name: 데이터셋 이름
            use_langsmith: LangSmith 사용 여부
        """
        self.dataset_name = dataset_name
        self.use_langsmith = use_langsmith
        
        # LangSmith 클라이언트 초기화
        if self.use_langsmith:
            try:
                self.langsmith_client = LangSmithClient()
                self._ensure_langsmith_dataset()
            except Exception as e:
                print(f"LangSmith 초기화 실패: {e}")
                self.use_langsmith = False
        
        # LLM-as-Judge 초기화
        self.judge_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        )
        
        # 평가 프롬프트 설정 - LangSmith에서 가져오기
        try:
            # LangSmith에서 프롬프트 가져오기 시도
            self.accuracy_judge_prompt = self._load_prompt_from_langsmith("accuracy_judge_prompt")
            print("✅ LangSmith에서 accuracy_judge_prompt 로드 완료")
        except Exception as e:
            print(f"⚠️  LangSmith에서 프롬프트 로드 실패, 기본 프롬프트 사용: {e}")
            # 폴백: 기본 프롬프트 사용
            self.accuracy_judge_prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 QA 시스템의 답변을 평가하는 전문가입니다.
주어진 질문에 대한 답변의 정확성을 0-5점 사이로 평가해주세요.

평가 기준:
- 5점: 완벽히 정확하고 완전한 답변
- 4점: 대부분 정확하며 약간의 부족함이 있음
- 3점: 기본적으로 정확하나 중요한 정보가 누락됨
- 2점: 부분적으로 정확하나 오류나 부정확한 정보 포함
- 1점: 대부분 부정확하나 일부 관련된 정보 포함
- 0점: 완전히 부정확하거나 관련 없는 답변

평가 결과를 다음 JSON 형식으로 반환하세요:
{{"score": <0-5 사이의 점수>, "reasoning": "<평가 근거>"}}"""),
                ("human", "질문: {question}\n답변: {answer}\n\n위 답변을 평가해주세요.")
            ])
        
        self.judge_chain = self.accuracy_judge_prompt | self.judge_llm | StrOutputParser()
    
    def _load_prompt_from_langsmith(self, prompt_name: str):
        """
        LangSmith에서 프롬프트 로드
        
        Args:
            prompt_name: 프롬프트 이름
            
        Returns:
            ChatPromptTemplate: 로드된 프롬프트
        """
        try:
            # LangSmith에서 프롬프트 가져오기
            from langchain import hub
            prompt = hub.pull(prompt_name)
            return prompt
        except Exception as e:
            # hub에서 실패하면 직접 검색 시도
            try:
                prompts = list(self.langsmith_client.list_prompts())
                for p in prompts:
                    if p.name == prompt_name:
                        # 프롬프트 내용을 ChatPromptTemplate으로 변환
                        return ChatPromptTemplate.from_template(p.template)
                raise Exception(f"프롬프트 '{prompt_name}'을 찾을 수 없습니다")
            except Exception as inner_e:
                raise Exception(f"LangSmith에서 프롬프트 로드 실패: {inner_e}")
    
    def _ensure_langsmith_dataset(self):
        """LangSmith 데이터셋 존재 확인 및 생성"""
        try:
            # 기존 데이터셋 확인
            datasets = list(self.langsmith_client.list_datasets(dataset_name=self.dataset_name))
            if not datasets:
                # 데이터셋 생성
                self.langsmith_client.create_dataset(
                    dataset_name=self.dataset_name,
                    description="Agent QA 시나리오 테스트케이스와 평가 결과를 관리하는 데이터셋"
                )
                print(f"LangSmith 데이터셋 '{self.dataset_name}' 생성 완료")
            else:
                print(f"LangSmith 데이터셋 '{self.dataset_name}' 확인 완료")
        except Exception as e:
            print(f"LangSmith 데이터셋 설정 오류: {e}")
    
    
    def add_test_case(self, question: str, expected_answer: Optional[str] = None) -> str:
        """
        새로운 테스트케이스 추가
        
        Args:
            question: 질문
            expected_answer: 기대 답변 (선택사항)
            
        Returns:
            생성된 테스트케이스 ID
        """
        test_case_id = f"TC_{uuid.uuid4().hex[:8]}"
        test_case = TestCase(
            id=test_case_id,
            question=question,
            expected_answer=expected_answer
        )
        
        # LangSmith에 추가
        if self.use_langsmith:
            try:
                self.langsmith_client.create_example(
                    dataset_name=self.dataset_name,
                    inputs={"question": question},
                    outputs={"expected_answer": expected_answer} if expected_answer else None,
                    metadata={
                        "test_case_id": test_case_id,
                        "created_at": test_case.created_at
                    }
                )
                print(f"LangSmith에 테스트케이스 {test_case_id} 추가 완료")
            except Exception as e:
                print(f"LangSmith 테스트케이스 추가 오류: {e}")
        
        return test_case_id
    
    def evaluate_answer(self, test_case_id: str, question: str, actual_answer: str, model_used: str = "unknown") -> EvaluationResult:
        """
        답변을 LLM-as-Judge로 평가
        
        Args:
            test_case_id: 테스트케이스 ID
            question: 질문
            actual_answer: 실제 답변
            model_used: 사용된 모델명
            
        Returns:
            평가 결과
        """
        execution_id = f"EXEC_{uuid.uuid4().hex[:8]}"
        
        try:
            # LLM-as-Judge 평가 실행
            judge_result = self.judge_chain.invoke({
                "question": question,
                "answer": actual_answer
            })
            
            # JSON 파싱
            judge_data = json.loads(judge_result)
            score = float(judge_data.get("score", 0))
            reasoning = judge_data.get("reasoning", "평가 실패")
            
        except Exception as e:
            print(f"LLM-as-Judge 평가 오류: {e}")
            score = 0.0
            reasoning = f"평가 중 오류 발생: {str(e)}"
        
        # 평가 결과 생성
        result = EvaluationResult(
            test_case_id=test_case_id,
            execution_id=execution_id,
            question=question,
            actual_answer=actual_answer,
            judge_accuracy_score=score,
            judge_reasoning=reasoning,
            execution_time=datetime.now().isoformat(),
            model_used=model_used
        )
        
        # LangSmith에 결과 저장
        if self.use_langsmith:
            try:
                self.langsmith_client.create_run(
                    name=f"evaluation_{execution_id}",
                    run_type="llm",
                    inputs={"question": question},
                    outputs={
                        "actual_answer": actual_answer,
                        "judge_accuracy_score": score,
                        "judge_reasoning": reasoning
                    },
                    extra={
                        "test_case_id": test_case_id,
                        "execution_id": execution_id,
                        "model_used": model_used
                    },
                    tags=[self.dataset_name, test_case_id]
                )
                print(f"LangSmith에 평가 결과 {execution_id} 저장 완료")
            except Exception as e:
                print(f"LangSmith 평가 결과 저장 오류: {e}")
        
        
        return result
    
    
    def get_all_test_cases(self) -> List[Dict]:
        """모든 테스트케이스 조회"""
        test_cases = []
        
        if self.use_langsmith:
            try:
                examples = list(self.langsmith_client.list_examples(dataset_name=self.dataset_name))
                for example in examples:
                    test_cases.append({
                        "id": example.metadata.get("test_case_id") if example.metadata else example.id,
                        "question": example.inputs.get("question"),
                        "expected_answer": example.outputs.get("expected_answer") if example.outputs else None,
                        "created_at": example.metadata.get("created_at") if example.metadata else None
                    })
            except Exception as e:
                print(f"테스트케이스 조회 오류: {e}")
        
        return test_cases
