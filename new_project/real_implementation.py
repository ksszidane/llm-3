#!/usr/bin/env python3
"""
실제 Agent QA 시스템 구현
TestCase.xlsx 데이터를 사용하여 실제 GPT-4o로 질의하고 평가하는 시스템
"""

import pandas as pd
import json
import time
from typing import Dict, List, Optional
import re
from pathlib import Path
from datetime import datetime

from langsmith import Client as LangSmithClient
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
from langchain.callbacks.tracers.run_collector import RunCollectorCallbackHandler

# 환경변수 로드
load_dotenv()

class RealAgentQASystem:
    """실제 Agent QA 시스템 구현"""
    
    def __init__(self):
        """시스템 초기화"""
        self.langsmith_client = LangSmithClient()
        
        # GPT-4o 모델 초기화 (실제 질의용)
        self.gpt_model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7  # 답변 다양성을 위해 약간의 temperature 설정
        )
        
        # GPT-4o Judge 모델 초기화 (평가용)
        self.judge_model = ChatOpenAI(
            model="gpt-4o",
            temperature=0  # 평가의 일관성을 위해 temperature 0
        )
        
        # Judge 프롬프트 설정 - LangSmith에서 가져오기
        try:
            # LangSmith에서 프롬프트 가져오기 시도
            self.accuracy_judge_prompt = self._load_prompt_from_langsmith("accuracy_judge_prompt")
            print("✅ LangSmith에서 accuracy_judge_prompt 로드 완료")
        except Exception as e:
            print(f"⚠️  LangSmith에서 프롬프트 로드 실패, 기본 프롬프트 사용: {e}")
            # 폴백: 기본 프롬프트 사용
            self.accuracy_judge_prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 QA 시스템의 답변을 평가하는 전문 Judge입니다.
주어진 질문에 대한 답변의 정확성을 0-5점 사이의 정수로 평가해주세요.

평가 기준:
- 5점: 완벽히 정확하고 완전한 답변
- 4점: 대부분 정확하며 약간의 부족함이 있음
- 3점: 기본적으로 정확하나 중요한 정보가 누락됨
- 2점: 부분적으로 정확하나 오류나 부정확한 정보 포함
- 1점: 대부분 부정확하나 일부 관련된 정보 포함
- 0점: 완전히 부정확하거나 관련 없는 답변

평가 결과를 다음 JSON 형식으로 반환하세요:
{{"score": <0-5 사이의 정수>, "reasoning": "<평가 근거>"}}

반드시 정수 점수만 사용하고, 소수점은 사용하지 마세요."""),
                ("human", "질문: {question}\n답변: {answer}\n\n위 답변을 평가해주세요.")
            ])
        
        self.judge_chain = self.accuracy_judge_prompt | self.judge_model | StrOutputParser()
        
        # OpenEvals 관련은 현재 비활성화 (메뉴에서 제거됨)
        
        # 데이터셋 이름 설정
        self.source_dataset = "Agent_QA_Scenario"
        self.result_dataset = "Agent_QA_Scenario_Judge_Result"
        self.history_dataset = "Agent_QA_Scenario_Judge_History"
        self.base_web_url = self._get_base_web_url()
        # LangSmith tracing 기본값 보장
        if not os.getenv("LANGSMITH_PROJECT"):
            os.environ["LANGSMITH_PROJECT"] = "llm-practice"
        if not os.getenv("LANGSMITH_TRACING"):
            os.environ["LANGSMITH_TRACING"] = "true"
        
        # 데이터셋 초기화
        self._ensure_datasets()
    
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
                    if hasattr(p, 'name') and p.name == prompt_name:
                        # 프롬프트 내용을 ChatPromptTemplate으로 변환
                        return ChatPromptTemplate.from_template(p.template)
                raise Exception(f"프롬프트 '{prompt_name}'을 찾을 수 없습니다")
            except Exception as inner_e:
                raise Exception(f"LangSmith에서 프롬프트 로드 실패: {inner_e}")
    
    def _ensure_datasets(self):
        """LangSmith 데이터셋 존재 확인 및 생성"""
        datasets = [self.source_dataset, self.result_dataset, self.history_dataset]
        
        for dataset_name in datasets:
            try:
                existing_datasets = list(self.langsmith_client.list_datasets(dataset_name=dataset_name))
                if not existing_datasets:
                    self.langsmith_client.create_dataset(
                        dataset_name=dataset_name,
                        description=f"Agent QA 시스템 데이터셋: {dataset_name}"
                    )
                    print(f"✅ LangSmith 데이터셋 '{dataset_name}' 생성 완료")
                else:
                    print(f"✅ LangSmith 데이터셋 '{dataset_name}' 확인 완료")
            except Exception as e:
                print(f"❌ 데이터셋 '{dataset_name}' 설정 오류: {e}")

    def _resolve_run_url_from_handler(self, handler) -> Optional[str]:
        """RunCollector에서 수집한 run들로부터 접근 가능한 추적 URL을 계산합니다.
        - 우선 name == 'RunnableSequence'를 선택
        - run.parent_run_id를 따라 루트 run까지 올라간 후 run.url 사용
        - run.url이 없으면 projects 경로로 폴백
        """
        try:
            selected = None
            # 우선 RunnableSequence 우선 탐색
            for r in reversed(getattr(handler, "traced_runs", []) or []):
                if getattr(r, "name", "") == "RunnableSequence":
                    selected = r
                    break
            # 대안: 마지막 run 사용
            if selected is None and getattr(handler, "traced_runs", None):
                selected = handler.traced_runs[-1]
            if not selected:
                return None
            run_id = getattr(selected, "id", None)
            if not run_id:
                return None
            # 루트 run까지 상승
            # run이 저장되기까지 약간의 지연이 발생할 수 있으므로 재시도
            run = None
            for _ in range(10):
                try:
                    run = self.langsmith_client.read_run(run_id)
                    if run:
                        break
                except Exception:
                    pass
                time.sleep(0.3)
            if not run:
                return None
            # 루트 run까지 상승
            while getattr(run, "parent_run_id", None):
                run = self.langsmith_client.read_run(run.parent_run_id)
            # url 확보 재시도 (비동기 반영 대비)
            for _ in range(10):
                url = getattr(run, "url", None)
                if url:
                    return url
                time.sleep(0.3)
            # url이 비어있다면 프로젝트 기반 폴백
            project = os.getenv("LANGSMITH_PROJECT", "llm-practice")
            return f"{self.base_web_url}/projects/{project}/runs/{run.id}"
        except Exception:
            return None
    
    @staticmethod
    def _sort_testcases_by_case_id(testcases: List[Dict]) -> List[Dict]:
        """case_id에 포함된 숫자 기준 오름차순으로 정렬"""
        def key(tc: Dict) -> int:
            m = re.search(r"(\d+)", str(tc.get("case_id", "")))
            try:
                return int(m.group(1)) if m else 10**9
            except Exception:
                return 10**9
        return sorted(testcases, key=key)

    def _count_history_examples(self) -> int:
        try:
            return len(list(self.langsmith_client.list_examples(dataset_name=self.history_dataset)))
        except Exception:
            return 0
    
    def check_history_status(self):
        """히스토리 데이터셋 상태 확인"""
        try:
            examples = list(self.langsmith_client.list_examples(dataset_name=self.history_dataset))
            print(f"\n📈 히스토리 데이터셋 상태: {len(examples)}개 케이스")
            
            for ex in examples:
                try:
                    case_id = ex.metadata.get("case_id") if ex.metadata else "Unknown"
                    scores = ex.outputs.get("scores", []) if ex.outputs else []
                    print(f"  - {case_id}: {len(scores)}회 실행")
                except Exception:
                    pass
                
        except Exception:
            pass

    def backfill_history_from_results(self) -> int:
        """
        기존 결과 데이터셋에서 히스토리 데이터셋으로 누적 백필
        Returns: 반영한 예제 수
        """
        try:
            examples = list(self.langsmith_client.list_examples(dataset_name=self.result_dataset))
            applied = 0
            for ex in examples:
                case_id = ex.metadata.get("case_id") if ex.metadata else None
                question = ex.inputs.get("input") if ex.inputs else None
                outputs = ex.outputs or {}
                if not case_id or not question:
                    continue
                result = {
                    "case_id": case_id,
                    "question": question,
                    "answer": outputs.get("answer", ""),
                    "judge_accuracy_score": outputs.get("judge_accuracy_score", 0),
                    "reasoning": outputs.get("judge_reasoning", ""),
                }
                if self.save_result_to_history(result):
                    applied += 1
            if applied > 0:
                print(f"♻️ 히스토리 백필 완료: {applied}개 결과 반영")
            return applied
        except Exception as e:
            print(f"⚠️ 히스토리 백필 중 오류: {e}")
            return 0

    def load_testcases_from_excel(self, excel_path: str) -> List[Dict]:
        """
        TestCase.xlsx에서 테스트케이스 로드
        
        Args:
            excel_path: Excel 파일 경로
            
        Returns:
            테스트케이스 리스트 [{"case_id": str, "question": str}, ...]
        """
        try:
            # 여러 시트를 모두 읽어 병합
            all_sheets = pd.read_excel(excel_path, sheet_name=None)
            if isinstance(all_sheets, dict):
                frames = []
                for sheet_name, sdf in all_sheets.items():
                    if sdf is None or len(sdf) == 0:
                        continue
                    sdf["__sheet__"] = str(sheet_name)
                    frames.append(sdf)
                if not frames:
                    print("⚠️  모든 시트가 비어 있습니다.")
                    return []
                df = pd.concat(frames, ignore_index=True)
                print(f"📊 Excel 파일 로드 완료: {len(df)}개 행 | 시트 수: {len(all_sheets)}")
            else:
                df = all_sheets
                print(f"📊 Excel 파일 로드 완료: {len(df)}개 행 | 시트 수: 1")
            print(f"컬럼: {list(df.columns)}")
            
            # 컬럼명 정규화 (대소문자, 공백 처리)
            df.columns = df.columns.str.strip().str.lower()
            
            # 필요한 컬럼 확인
            required_columns = ['case_id', 'question', 'input']
            available_columns = df.columns.tolist()
            
            # 컬럼 매핑 확인 (정확매칭 우선, 없으면 유사 매칭)
            case_id_col = 'case_id' if 'case_id' in available_columns else None
            question_col = 'question' if 'question' in available_columns else None
            if question_col is None:
                for cand in ['input', 'query']:
                    if cand in available_columns:
                        question_col = cand
                        break
            if case_id_col is None:
                for col in available_columns:
                    if 'case' in col or 'id' in col:
                        case_id_col = col
                        break
            if question_col is None:
                for col in available_columns:
                    if 'question' in col or 'input' in col or 'query' in col:
                        question_col = col
                        break
            
            print(f"🔍 감지된 컬럼 - case_id: {case_id_col}, question: {question_col}")
            
            if not case_id_col or not question_col:
                print(f"⚠️  필요한 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {available_columns}")
                # 첫 번째와 두 번째 컬럼을 기본으로 사용
                case_id_col = available_columns[0]
                question_col = available_columns[1] if len(available_columns) > 1 else available_columns[0]
                print(f"💡 기본 컬럼 사용 - case_id: {case_id_col}, question: {question_col}")
            
            # 완전 공백 행 제거
            df = df.dropna(how='all')

            testcases = []
            missing_case_id = 0
            missing_question = 0
            for _, row in df.iterrows():
                case_id = str(row.get(case_id_col, '')).strip()
                question = str(row.get(question_col, '')).strip()
                
                if not case_id or case_id.lower() == 'nan' or case_id == 'None':
                    missing_case_id += 1
                    continue
                if not question or question.lower() == 'nan' or question == 'None':
                    missing_question += 1
                    continue
                testcases.append({
                    "case_id": case_id,
                    "question": question
                })
            
            print(f"✅ 유효한 테스트케이스 {len(testcases)}개 로드 완료")
            dropped = missing_case_id + missing_question
            if dropped > 0:
                print(f"ℹ️  제외된 행 수: {dropped} (case_id 없음: {missing_case_id}, question 없음: {missing_question})")
            return testcases
            
        except Exception as e:
            print(f"❌ Excel 파일 로드 실패: {e}")
            return []
    
    def get_existing_case_ids(self) -> set:
        """
        LangSmith Agent_QA_Scenario 데이터셋에서 기존 case_id 목록 조회
        
        Returns:
            기존 case_id 집합
        """
        try:
            examples = list(self.langsmith_client.list_examples(dataset_name=self.source_dataset))
            existing_case_ids = set()
            
            for example in examples:
                if example.metadata and "case_id" in example.metadata:
                    existing_case_ids.add(example.metadata["case_id"])
            
            print(f"📋 기존 데이터셋에서 {len(existing_case_ids)}개 케이스 발견: {sorted(list(existing_case_ids))}")
            return existing_case_ids
            
        except Exception as e:
            print(f"⚠️  기존 케이스 조회 실패 (새 데이터셋일 수 있음): {e}")
            return set()
    
    def save_testcases_to_langsmith(self, testcases: List[Dict]) -> bool:
        """
        테스트케이스를 LangSmith Agent_QA_Scenario 데이터셋에 저장 (중복 방지)
        
        Args:
            testcases: 테스트케이스 리스트
            
        Returns:
            성공 여부
        """
        try:
            # 기존 케이스 ID 조회
            existing_case_ids = self.get_existing_case_ids()
            
            # 새로운 케이스만 필터링
            new_testcases = [tc for tc in testcases if tc["case_id"] not in existing_case_ids]
            
            if not new_testcases:
                print(f"✅ 모든 테스트케이스가 이미 데이터셋에 존재합니다. (총 {len(testcases)}개)")
                return True
            
            print(f"\n📝 {len(new_testcases)}개 새로운 테스트케이스를 LangSmith에 저장 중...")
            print(f"   (전체 {len(testcases)}개 중 {len(testcases) - len(new_testcases)}개는 이미 존재)")
            
            for i, tc in enumerate(new_testcases, 1):
                self.langsmith_client.create_example(
                    dataset_name=self.source_dataset,
                    inputs={"question": tc["question"]},
                    outputs=None,
                    metadata={
                        "case_id": tc["case_id"],
                        "source": "TestCase.xlsx"
                    }
                )
                print(f"  [{i}/{len(new_testcases)}] {tc['case_id']}: {tc['question'][:50]}...")
                time.sleep(0.1)  # API 부하 방지
            
            print(f"✅ {len(new_testcases)}개 새로운 테스트케이스가 '{self.source_dataset}' 데이터셋에 저장 완료")
            return True
            
        except Exception as e:
            print(f"❌ 테스트케이스 저장 실패: {e}")
            return False
    
    def get_testcases_from_langsmith(self) -> List[Dict]:
        """
        LangSmith Agent_QA_Scenario 데이터셋에서 테스트케이스 조회
        
        Returns:
            테스트케이스 리스트
        """
        try:
            examples = list(self.langsmith_client.list_examples(dataset_name=self.source_dataset))
            testcases = []
            
            for example in examples:
                case_id = example.metadata.get("case_id") if example.metadata else str(example.id)
                question = example.inputs.get("question", "")
                
                if question:
                    testcases.append({
                        "case_id": case_id,
                        "question": question,
                        "example_id": str(example.id)
                    })
            
            print(f"📋 LangSmith에서 {len(testcases)}개 테스트케이스 조회 완료")
            
            # case_id 기준 오름차순 정렬
            testcases = self._sort_testcases_by_case_id(testcases)
            return testcases
            
        except Exception as e:
            print(f"❌ 테스트케이스 조회 실패: {e}")
            return []
    
    def generate_answer_with_gpt4o(self, question: str) -> str:
        """
        GPT-4o를 사용하여 질문에 답변 생성
        
        Args:
            question: 질문
            
        Returns:
            GPT-4o 답변
        """
        try:
            handler = RunCollectorCallbackHandler()
            response = self.gpt_model.invoke(question, config={"callbacks": [handler]})
            answer = response.content.strip()
            return answer
        except Exception as e:
            print(f"❌ GPT-4o 답변 생성 실패: {e}")
            return "답변 생성에 실패했습니다."
    
    def judge_answer_with_gpt4o(self, question: str, answer: str) -> Dict:
        """
        GPT-4o Judge를 사용하여 답변 평가
        
        Args:
            question: 질문
            answer: 답변
            
        Returns:
            {"score": int, "reasoning": str}
        """
        try:
            handler = RunCollectorCallbackHandler()
            judge_result = self.judge_chain.invoke({
                "question": question,
                "answer": answer
            }, config={"callbacks": [handler]})
            
            # JSON 파싱
            judge_data = json.loads(judge_result)
            score = int(judge_data.get("score", 0))  # 정수로 변환
            reasoning = judge_data.get("reasoning", "평가 실패")
            
            # 점수 범위 검증
            if not (0 <= score <= 5):
                print(f"⚠️  점수 범위 오류 ({score}), 0으로 설정")
                score = 0
            
            # Judge RunnableSequence 트레이스 URL 추출 (루트 run 기준)
            trace_url = self._resolve_run_url_from_handler(handler)
            if not trace_url:
                # 마지막 수단: handler 내 run_id를 로그로 남기고 저장은 생략
                if getattr(handler, "traced_runs", None):
                    try:
                        rid = getattr(handler.traced_runs[-1], "id", None)
                        if rid:
                            print(f"(debug) judge run_id: {rid}")
                    except Exception:
                        pass
            return {"score": score, "reasoning": reasoning, "trace_url": trace_url}
            
        except Exception as e:
            print(f"❌ Judge 평가 실패: {e}")
            return {"score": 0, "reasoning": f"평가 중 오류 발생: {str(e)}"}
    
    
    def save_results_to_langsmith(self, results: List[Dict]) -> bool:
        """
        평가 결과를 LangSmith 결과 데이터셋에 저장
        
        Args:
            results: 결과 리스트 [{"case_id", "question", "answer", "judge_accuracy_score", "reasoning"}, ...]
            
        Returns:
            성공 여부
        """
        try:
            print(f"\n💾 {len(results)}개 평가 결과를 LangSmith에 저장 중...")
            
            for i, result in enumerate(results, 1):
                # LangSmith 데이터 구조: input을 단일 키로 설정하여 question 내용이 주요 표시되도록 함
                self.langsmith_client.create_example(
                    dataset_name=self.result_dataset,
                    inputs={
                        "input": result["question"]  # "input"이라는 단일 키 사용
                    },
                    outputs={
                        "answer": result["answer"],
                        "judge_accuracy_score": result["judge_accuracy_score"],
                        "judge_reasoning": result.get("reasoning", ""),
                        **({"trace_url": result.get("trace_url")} if result.get("trace_url") else {})
                    },
                    metadata={
                        "case_id": result["case_id"],
                        "question": result["question"],
                        "judge_accuracy_score": result["judge_accuracy_score"],
                        "model_used": "gpt-4o",
                        "judge_model": "gpt-4o",
                        "evaluation_type": "judge_accuracy"
                    }
                )
                print(f"  [{i}/{len(results)}] {result['case_id']}: {result['judge_accuracy_score']}/5점")
                time.sleep(0.1)  # API 부하 방지
            
            print(f"✅ 모든 평가 결과가 '{self.result_dataset}' 데이터셋에 저장 완료")
            return True
            
        except Exception as e:
            print(f"❌ 평가 결과 저장 실패: {e}")
            return False

    def save_single_result_to_langsmith(self, result: Dict) -> bool:
        """
        단일 평가 결과를 LangSmith에 즉시 저장
        """
        try:
            created = self.langsmith_client.create_example(
                dataset_name=self.result_dataset,
                inputs={
                    "input": result["question"]
                },
                outputs={
                    "answer": result["answer"],
                    "judge_accuracy_score": result["judge_accuracy_score"],
                    "judge_reasoning": result.get("reasoning", ""),
                    **({"trace_url": result.get("trace_url")} if result.get("trace_url") else {})
                },
                metadata={
                    "case_id": result["case_id"],
                    "question": result["question"],
                    "judge_accuracy_score": result["judge_accuracy_score"],
                    "model_used": "gpt-4o",
                    "judge_model": "gpt-4o",
                    "evaluation_type": "judge_accuracy"
                }
            )
            # 데이터셋 링크 출력 제거 (요청에 따라)
            print(f"  - 저장 완료: {result['case_id']} ({result['judge_accuracy_score']}/5점)")
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"  - 저장 실패: {e}")
            return False

    def _get_base_web_url(self) -> str:
        """LangSmith 웹 URL 기본값 계산 (API 엔드포인트를 웹 도메인으로 정규화)"""
        import os
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        # 웹 도메인으로 정규화
        endpoint = endpoint.replace("https://api.", "https://").replace("/api", "")
        if not endpoint.startswith("http"):
            endpoint = "https://smith.langchain.com"
        return endpoint.rstrip("/")

    def save_result_to_history(self, result: Dict) -> bool:
        """
        동일 case_id 히스토리를 배열로 누적 저장하는 전용 데이터셋 관리 함수
        outputs 필드에 scores/answers/reasons/timestamps 배열을 유지합니다.
        """
        try:
            # case_id에 해당하는 기존 예제 탐색
            examples = list(self.langsmith_client.list_examples(dataset_name=self.history_dataset))
            target_example = None
            for ex in examples:
                if ex.metadata and ex.metadata.get("case_id") == result["case_id"]:
                    target_example = ex
                    break

            now_iso = datetime.now().isoformat()

            if target_example is None:
                # 새 예제로 배열 초기화
                created = self.langsmith_client.create_example(
                    dataset_name=self.history_dataset,
                    inputs={"input": result["question"]},
                    outputs={
                        "scores": [int(result["judge_accuracy_score"])],
                        "answers": [result["answer"]],
                        "reasons": [result.get("reasoning", "")],
                        "timestamps": [now_iso],
                        **({"trace_urls": [result.get("trace_url")] } if result.get("trace_url") else {}),
                    },
                    metadata={
                        "case_id": result["case_id"],
                        "model_used": "gpt-4o",
                        "judge_model": "gpt-4o",
                        "evaluation_type": "judge_accuracy",
                    },
                )
                # 데이터셋 링크 출력 제거 (요청에 따라) - 아무 것도 출력하지 않음
            else:
                # 기존 예제를 배열 append로 업데이트
                outs = target_example.outputs or {}
                outs["scores"] = list(outs.get("scores", [])) + [int(result["judge_accuracy_score"]) ]
                outs["answers"] = list(outs.get("answers", [])) + [ result["answer"] ]
                outs["reasons"] = list(outs.get("reasons", [])) + [ result.get("reasoning", "") ]
                outs["timestamps"] = list(outs.get("timestamps", [])) + [ now_iso ]
                if result.get("trace_url"):
                    outs["trace_urls"] = list(outs.get("trace_urls", [])) + [ result.get("trace_url") ]

                updated = self.langsmith_client.update_example(
                    example_id=str(target_example.id),
                    outputs=outs,
                )
                # 데이터셋 링크 출력 제거

            time.sleep(0.1)
            return True
        except Exception as e:
            return False
    
    def run_full_evaluation(self, excel_path: str) -> bool:
        """
        전체 평가 프로세스 실행
        
        Args:
            excel_path: TestCase.xlsx 파일 경로
            
        Returns:
            성공 여부
        """
        print("🚀 실제 Agent QA 평가 시스템 시작")
        print("=" * 60)
        
        # 1. TestCase.xlsx에서 데이터 로드
        print("\n1️⃣  TestCase.xlsx에서 테스트케이스 로드")
        testcases = self.load_testcases_from_excel(excel_path)
        if not testcases:
            print("❌ 테스트케이스 로드 실패")
            return False
        
        # 2. Agent_QA_Scenario 데이터셋에 저장
        print(f"\n2️⃣  LangSmith '{self.source_dataset}' 데이터셋에 저장")
        if not self.save_testcases_to_langsmith(testcases):
            print("❌ 테스트케이스 저장 실패")
            return False
        
        # 3. 저장된 데이터 조회
        print(f"\n3️⃣  LangSmith에서 테스트케이스 조회")
        stored_testcases = self.get_testcases_from_langsmith()
        if not stored_testcases:
            print("❌ 테스트케이스 조회 실패")
            return False
        
        # 4. GPT-4o로 질의 및 평가
        print(f"\n4️⃣  GPT-4o로 질의 및 Judge 평가 실행")
        results = []
        
        for i, tc in enumerate(stored_testcases, 1):
            print(f"\n[{i}/{len(stored_testcases)}] 처리 중: {tc['case_id']}")
            print(f"❓ 질문: {tc['question']}")
            
            # GPT-4o로 답변 생성
            answer = self.generate_answer_with_gpt4o(tc['question'])
            
            # GPT-4o Judge로 평가
            judge_result = self.judge_answer_with_gpt4o(tc['question'], answer)
            
            # 결과 저장
            result = {
                "case_id": tc['case_id'],
                "question": tc['question'],
                "answer": answer,
                "judge_accuracy_score": judge_result['score'],
                "reasoning": judge_result['reasoning'],
                "trace_url": judge_result.get('trace_url')
            }
            results.append(result)
            
            print(f"💡 답변: {answer[:100]}...")
            print(f"📊 평가 요약: {judge_result['score']}/5점 - {judge_result['reasoning'][:100]}...")
            
            # API 부하 방지를 위한 대기
            time.sleep(1)
        
        # 5. 결과를 결과 데이터셋에 저장
        print(f"\n5️⃣  LangSmith '{self.result_dataset}' 데이터셋에 결과 저장")
        if not self.save_results_to_langsmith(results):
            print("❌ 결과 저장 실패")
            return False
        
        # 6. 최종 요약
        print(f"\n✅ 전체 평가 프로세스 완료!")
        print("=" * 60)
        print(f"📊 처리 통계:")
        print(f"  - 총 테스트케이스: {len(results)}개")
        print(f"  - 평균 점수: {sum(r['judge_accuracy_score'] for r in results) / len(results):.2f}/5")
        print(f"  - 최고 점수: {max(r['judge_accuracy_score'] for r in results)}/5")
        print(f"  - 최저 점수: {min(r['judge_accuracy_score'] for r in results)}/5")
        
        return True

def main():
    """메인 실행 함수"""
    excel_path = Path(__file__).parent / "TestCase.xlsx"
    
    if not excel_path.exists():
        print(f"❌ TestCase.xlsx 파일을 찾을 수 없습니다: {excel_path}")
        return
    
    try:
        system = RealAgentQASystem()
        success = system.run_full_evaluation(str(excel_path))
        
        if success:
            print("\n🎉 모든 작업이 성공적으로 완료되었습니다!")
            print("🔍 LangSmith에서 다음 데이터셋을 확인하세요:")
            print(f"  - 원본 테스트케이스: Agent_QA_Scenario")
            print(f"  - 평가 결과: {system.result_dataset}")
        else:
            print("\n❌ 작업 중 오류가 발생했습니다.")
            
    except Exception as e:
        print(f"❌ 시스템 실행 중 오류: {e}")

def save_testcases_only(uploaded_excel_path: Optional[str] = None):
    """
    3. TestCase.xlsx를 Agent_QA_Scenario 데이터셋에 저장하는 기능만 실행
    """
    # 우선순위: 인자 > 환경변수 > 기본 파일
    env_path = os.getenv("UPLOADED_EXCEL_PATH")
    if uploaded_excel_path and os.path.exists(uploaded_excel_path):
        excel_path = Path(uploaded_excel_path)
        print(f"📤 업로드된 파일 사용: {excel_path.name}")
        print(f"   경로: {excel_path}")
    elif env_path and os.path.exists(env_path):
        excel_path = Path(env_path)
        print(f"📤 업로드된 파일 사용: {excel_path.name}")
        print(f"   경로: {excel_path}")
    else:
        excel_path = Path(__file__).parent / "TestCase.xlsx"
        print(f"📁 기본 파일 사용: TestCase.xlsx")
        print(f"   경로: {excel_path}")
    
    if not excel_path.exists():
        print(f"❌ Excel 파일을 찾을 수 없습니다: {excel_path}")
        return
    
    try:
        print("📥 TestCase → Agent_QA_Scenario 데이터셋 저장 시작")
        print("="*60)
        
        system = RealAgentQASystem()
        
        # 1. Excel에서 테스트케이스 로드
        print(f"1️⃣  Excel 파일에서 테스트케이스 로드: {excel_path.name}")
        testcases = system.load_testcases_from_excel(str(excel_path))
        
        if not testcases:
            print("❌ 유효한 테스트케이스를 찾을 수 없습니다.")
            return
        
        # 2. LangSmith에 저장 (중복 방지)
        print("\n2️⃣  LangSmith 'Agent_QA_Scenario' 데이터셋에 저장")
        success = system.save_testcases_to_langsmith(testcases)
        
        if success:
            print("\n✅ 테스트케이스 저장 완료!")
            print("🔍 LangSmith에서 'Agent_QA_Scenario' 데이터셋을 확인하세요.")
        else:
            print("\n❌ 테스트케이스 저장 실패")
            
    except Exception as e:
        print(f"❌ 테스트케이스 저장 중 오류: {e}")

def run_evaluation_only():
    """
    4. Agent_QA_Scenario 데이터셋에서 GPT-4o 평가만 실행
    """
    try:
        print("🚀 Agent_QA_Scenario → GPT-4o 평가 실행 시작")
        print("="*60)
        
        system = RealAgentQASystem()
        
        # 1. LangSmith에서 테스트케이스 조회
        print("1️⃣  LangSmith에서 테스트케이스 조회")
        testcases = system.get_testcases_from_langsmith()
        
        if not testcases:
            print("❌ Agent_QA_Scenario 데이터셋에서 테스트케이스를 찾을 수 없습니다.")
            print("💡 먼저 '3. TestCase.xlsx → Agent_QA_Scenario 데이터셋 저장'을 실행해주세요.")
            return
        
        # 테스트케이스 정렬: case_id의 숫자 오름차순 (예: TC_001, TC_002 ...)
        testcases = system._sort_testcases_by_case_id(testcases)
        
        print(f"📋 정렬된 테스트케이스 순서: {[tc['case_id'] for tc in testcases]}")
        
        
        # 2. 전기차 RAG Agent를 통한 질의 및 Judge 평가 실행
        print(f"\n2️⃣  전기차 RAG Agent로 질의 및 Judge 평가 실행")
        results = []
        
        for i, tc in enumerate(testcases, 1):
            print(f"\n[{i}/{len(testcases)}] 처리 중: {tc['case_id']}")
            print(f"❓ 질문: {tc['question']}")
            
            # 전기차 RAG Agent로 답변 생성
            try:
                from ev_rag_agent import get_ev_agent
                agent = get_ev_agent()
                answer, _ = agent.answer(tc["question"]) 
            except Exception as e:
                print(f"RAG Agent 오류로 GPT-4o 직접 답변으로 폴백: {e}")
                answer = system.generate_answer_with_gpt4o(tc["question"]) 
            
            # Judge로 평가
            judge_result = system.judge_answer_with_gpt4o(tc["question"], answer)
            
            # 요약 출력 (답변 먼저, 평가 요약 나중에)
            print(f"💡 답변: {answer[:100]}...")
            print(f"⚖️ 평가 요약: {judge_result['score']}/5점 - {judge_result.get('reasoning', '')[:100]}...")
            
            
            single_result = {
                "case_id": tc["case_id"],
                "question": tc["question"],
                "answer": answer,
                "judge_accuracy_score": judge_result["score"],
                "reasoning": judge_result["reasoning"],
                "trace_url": judge_result.get("trace_url")
            }
            
            # 즉시 저장
            print("💾 결과 즉시 저장 중...")
            system.save_single_result_to_langsmith(single_result)
            # 히스토리에도 누적
            system.save_result_to_history(single_result)
            results.append(single_result)
            
            # API 부하 방지를 위한 대기
            time.sleep(1)
        
        # 3. 처리 통계 요약
        success = len(results) > 0
        # 히스토리 데이터셋이 비어있다면 기존 결과를 백필하여 일관성 유지
        if self := system:  # 명시적 참조 회피용
            try:
                if system._count_history_examples() == 0:
                    system.backfill_history_from_results()
            except Exception:
                pass
        
        if success:
            print("\n✅ 평가 완료!")
            print("="*60)
            print(f"📊 처리 통계:")
            print(f"  - 총 테스트케이스: {len(results)}개")
            print(f"  - 평균 점수: {sum(r['judge_accuracy_score'] for r in results) / len(results):.2f}/5")
            print(f"  - 최고 점수: {max(r['judge_accuracy_score'] for r in results)}/5")
            print(f"  - 최저 점수: {min(r['judge_accuracy_score'] for r in results)}/5")
            print("\n🎉 GPT-4o 평가가 성공적으로 완료되었습니다!")
            print("🔍 LangSmith에서 다음 데이터셋을 확인하세요:")
            print(f"  - 평가 결과: {system.result_dataset}")
        else:
            print("\n❌ 평가 결과 저장 실패")
            
    except Exception as e:
        print(f"❌ 평가 실행 중 오류: {e}")

# OpenEvals 실행 로직 제거됨 (메뉴에서 삭제)

if __name__ == "__main__":
    main()
