"""
프롬프트 관리 모듈

LangSmith에 저장된 프롬프트를 생성, 업데이트, 관리하는 기능을 제공합니다.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional
import json as _json
import urllib.request as _urlreq
import urllib.parse as _urlparse


class PromptManager:
    """LangSmith 프롬프트 관리 클래스"""
    
    def __init__(self):
        """프롬프트 매니저 초기화"""
        # .env 파일 로드
        self._load_environment()
        
        # LangSmith 클라이언트 초기화
        try:
            self.client = Client()
            print("✅ LangSmith 클라이언트 초기화 완료")
        except Exception as e:
            print(f"❌ LangSmith 클라이언트 초기화 실패: {e}")
            raise
    
    def _load_environment(self):
        """환경 변수 로드"""
        current_dir = Path(__file__).parent
        for path in [current_dir, current_dir.parent, Path.cwd()]:
            env_path = path / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✅ .env 파일 로드: {env_path}")
                return
        print("⚠️  .env 파일을 찾을 수 없습니다.")
    
    def get_accuracy_judge_prompt_template(self) -> Dict:
        """
        accuracy_judge_prompt의 기본 템플릿 반환
        
        Returns:
            프롬프트 템플릿 딕셔너리
        """
        return {
            "name": "accuracy_judge_prompt",
            "description": "QA 시스템 답변의 정확성을 0-5점으로 평가하는 프롬프트",
            "messages": [
                {
                    "role": "system",
                    "content": """
# 역할 (Rule)
당신은 Agent의 답변을 평가하는 QA 전문가입니다.

## 조건 (condition)
accuracy는 Agent가 제공하는 정보의 정확성과 신뢰성은 기본입니다. 
정확성은 모델이 사용자 쿼리에 대해 사실적으로 정확하고 최신의 관련 응답을 제공하도록 보장합니다.
주어진 질문에 대한 답변의 정확성을 0-5점 사이로 평가해주세요.

## 평가 기준 (Check)
질문 의도, 맥락을 이해하고 적합한 결정, 방법 등을 제시 체크
- 5점: 완벽히 정확하고 완전한 답변
- 4점: 대부분 정확하며 약간의 부족함이 있음
- 3점: 기본적으로 정확하나 중요한 정보가 누락됨
- 2점: 부분적으로 정확하나 오류나 부정확한 정보 포함
- 1점: 대부분 부정확하나 일부 관련된 정보 포함
- 0점: 완전히 부정확하거나 관련 없는 답변

"## Output Format" +
- 반드시 아래 예시와 같이 각 평가 항목별 점수(정수, 0~4)를 열거하세요.
- 점수와 함께 반드시 10자 내외로 간단한 <평가 근거>를 적으세요(한국어).
- 평가 결과를 다음 JSON 형식으로 반환하세요:
{{"score": <0-5 사이의 점수>, "reasoning": "<평가 근거>"}}"""
                },
                {
                    "role": "user", 
                    "content": "질문: {question}\n답변: {answer}\n\n위 답변을 평가해주세요."
                }
            ],
            "tags": ["evaluation", "judge", "accuracy", "qa"],
            "variables": ["question", "answer"]
        }

    def _serialize_chat_prompt(self, prompt: ChatPromptTemplate) -> Dict:
        """비교를 위해 ChatPromptTemplate을 단순 딕셔너리로 직렬화"""
        try:
            messages: List[Dict] = []
            for m in getattr(prompt, "messages", []):
                # 각 message는 MessagePromptTemplate 계열
                role = getattr(m, "role", None) or m.__class__.__name__.replace("MessagePromptTemplate", "").lower()
                tmpl = getattr(m, "prompt", None)
                content = None
                if tmpl is not None and hasattr(tmpl, "template"):
                    content = tmpl.template
                elif hasattr(m, "template"):
                    content = getattr(m, "template")
                messages.append({
                    "role": role,
                    "content": (content or "").strip()
                })
            variables = list(getattr(prompt, "input_variables", []) or [])
            return {"messages": messages, "variables": sorted(variables)}
        except Exception:
            return {"messages": [], "variables": []}
    
    def create_or_update_accuracy_judge_prompt(self) -> bool:
        """
        accuracy_judge_prompt를 LangSmith에 생성하거나 업데이트
        
        Returns:
            성공 여부
        """
        try:
            template = self.get_accuracy_judge_prompt_template()
            
            print(f"🔄 '{template['name']}' 프롬프트 생성/업데이트 중...")
            
            # 1) LangChain Hub(API)를 통한 커밋 시도
            try:
                from langchain import hub
                
                # ChatPromptTemplate 구성
                messages = []
                for msg in template["messages"]:
                    messages.append((msg["role"], msg["content"]))
                prompt_template = ChatPromptTemplate.from_messages(messages)
                
                # 리포지토리 식별자 결정 (ENV 우선)
                repo_owner = os.getenv("LANGCHAIN_HUB_OWNER") or os.getenv("LANGCHAIN_HUB_USER")
                default_repo = f"{repo_owner}/{template['name']}" if repo_owner else template['name']
                repo_id = os.getenv("ACCURACY_JUDGE_PROMPT_ID", default_repo)
                
                print(f"🛰️ Hub로 푸시할 리포지토리: {repo_id}")
                print("   - 환경변수 'ACCURACY_JUDGE_PROMPT_ID'로 변경할 수 있습니다")
                
                # 변경 감지: 기존 프롬프트와 직렬화 결과 비교
                try:
                    existing = hub.pull(repo_id)
                    new_ser = self._serialize_chat_prompt(prompt_template)
                    old_ser = self._serialize_chat_prompt(existing)
                    if new_ser == old_ser:
                        print("ℹ️  변경 사항 없음: 최신 커밋과 동일합니다. 커밋을 생략합니다.")
                        return True
                except Exception:
                    # 기존이 없거나 비교 실패 시 계속 진행
                    pass
                
                hub.push(repo_id, prompt_template)
                print(f"✅ LangChain Hub로 프롬프트 커밋 완료: {repo_id}")
                print("   Hub에서 버전으로 관리됩니다.")
                return True
            except Exception as hub_error:
                print(f"⚠️  Hub 커밋 실패: {hub_error}")
            
            # 2) 대안: LangSmith 웹 인터페이스에서 수동 생성을 위한 정보 제공
            print(f"\n📝 LangSmith에서 다음 정보로 프롬프트를 생성하세요:")
            print(f"=" * 60)
            print(f"🏷️  프롬프트 이름: {template['name']}")
            print(f"📄 설명: {template['description']}")
            print(f"🏷️  태그: {', '.join(template['tags'])}")
            print(f"🔧 변수: {', '.join(template['variables'])}")
            
            print(f"\n📋 프롬프트 내용:")
            print(f"=" * 40)
            
            print(f"\n🔹 System Message:")
            print(f"-" * 20)
            print(template['messages'][0]['content'])
            
            print(f"\n🔹 User Message:")
            print(f"-" * 20) 
            print(template['messages'][1]['content'])
            
            print(f"\n💡 LangSmith 웹 인터페이스 단계:")
            print(f"=" * 40)
            print(f"1. https://smith.langchain.com/ 접속")
            print(f"2. 'Prompts' 메뉴 클릭")
            print(f"3. 'Create Prompt' 클릭")
            print(f"4. 프롬프트 이름: {template['name']}")
            print(f"5. 설명: {template['description']}")
            print(f"6. 위의 System Message와 User Message 내용 입력")
            print(f"7. Variables에 question, answer 추가")
            print(f"8. 저장")
            
            # 간단한 검증용 파일 생성
            prompt_content = f"""# {template['name']}

## 설명
{template['description']}

## 태그
{', '.join(template['tags'])}

## 변수
{', '.join(template['variables'])}

## System Message
{template['messages'][0]['content']}

## User Message  
{template['messages'][1]['content']}
"""
            
            # 검증용 파일 저장
            prompt_file = f"{template['name']}_template.md"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt_content)
            
            print(f"\n✅ 프롬프트 템플릿이 '{prompt_file}' 파일에 저장되었습니다.")
            print(f"🔍 이 파일을 참고하여 LangSmith에 프롬프트를 생성하세요.")
            
            return True
                
        except Exception as e:
            print(f"❌ 프롬프트 생성/업데이트 실패: {e}")
            return False
    
    def list_prompts(self) -> List[Dict]:
        """
        accuracy_judge_prompt 현재 버전만 요약 표시
        
        Returns:
            [{"name": str, "version": str}] 리스트 (항상 길이 1 목표)
        """
        try:
            from langchain import hub
            # 리포지토리 식별자 규칙 재사용
            repo_owner = os.getenv("LANGCHAIN_HUB_OWNER") or os.getenv("LANGCHAIN_HUB_USER")
            default_repo = f"{repo_owner}/accuracy_judge_prompt" if repo_owner else "accuracy_judge_prompt"
            repo_id = os.getenv("ACCURACY_JUDGE_PROMPT_ID", default_repo)
            
            prompt = hub.pull(repo_id)
            # 1) Hub 객체 메타에서 버전 힌트 시도
            version: Optional[str] = None
            meta = getattr(prompt, "metadata", None)
            if isinstance(meta, dict):
                version = meta.get("revision") or meta.get("version") or meta.get("hash") or meta.get("id")
            version = version or getattr(prompt, "revision", None) or getattr(prompt, "version", None) or getattr(prompt, "id", None)

            # 2) 마지막 커밋 해시 직접 조회 (정확한 커밋 표시)
            def _fetch_latest_commit(repo: str) -> Optional[str]:
                try:
                    base = os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT") or "https://api.smith.langchain.com"
                    url = f"{base.rstrip('/')}/commits/-/{repo}"
                    query = _urlparse.urlencode({"limit": 1})
                    req = _urlreq.Request(f"{url}?{query}")
                    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
                    if api_key:
                        req.add_header("x-api-key", api_key)
                    with _urlreq.urlopen(req, timeout=10) as resp:
                        data = resp.read().decode("utf-8")
                        try:
                            payload = _json.loads(data)
                        except Exception:
                            return None
                        # 다양한 형태 대응: {"commits":[{...}]} | [{...}] | {"commit":{...}}
                        commit_obj = None
                        if isinstance(payload, dict):
                            if "commits" in payload and isinstance(payload["commits"], list) and payload["commits"]:
                                commit_obj = payload["commits"][0]
                            elif "commit" in payload and isinstance(payload["commit"], dict):
                                commit_obj = payload["commit"]
                        elif isinstance(payload, list) and payload:
                            commit_obj = payload[0]
                        if not commit_obj:
                            return None
                        commit_hash = commit_obj.get("commit_hash") or commit_obj.get("hash") or commit_obj.get("id")
                        if commit_hash:
                            return str(commit_hash)[:8]  # 짧은 버전명 표시
                        return None
                except Exception:
                    return None

            commit_version = _fetch_latest_commit(repo_id)
            version_str = commit_version or (str(version) if version is not None else "latest")
            print(f"  - {repo_id}  (version: {version_str})")
            return [{"name": repo_id, "version": version_str}]
        except Exception as e:
            print(f"❌ Hub에서 프롬프트 조회 실패: {e}")
            return []
    
    # validate_prompt 기능은 요구사항에 따라 제거되었습니다.


def main():
    """메인 함수 - 프롬프트 관리 인터페이스"""
    try:
        print("🔧 프롬프트 관리 시스템")
        print("=" * 50)
        
        manager = PromptManager()
        
        while True:
            print("\n프롬프트 관리 작업을 선택하세요:")
            print("1. accuracy_judge_prompt 생성/업데이트")
            print("2. 프롬프트 목록 조회")
            print("3. 돌아가기")
            
            choice = input("\n선택 (1-3): ").strip()
            
            if choice == "1":
                print("\n1️⃣ accuracy_judge_prompt 생성/업데이트")
                success = manager.create_or_update_accuracy_judge_prompt()
                if success:
                    print("✅ 프롬프트 생성/업데이트 완료")
                else:
                    print("❌ 프롬프트 생성/업데이트 실패")
                    
            elif choice == "2":
                print("\n2️⃣ 프롬프트 목록 조회")
                prompts = manager.list_prompts()
                if not prompts:
                    print("프롬프트가 없습니다.")
                    
            elif choice == "3":
                print("👋 프롬프트 관리를 종료합니다.")
                break
                
            else:
                print("올바른 선택이 아닙니다. 1-3 중에서 선택해주세요.")
                
    except KeyboardInterrupt:
        print("\n\n👋 프롬프트 관리를 취소합니다.")
    except Exception as e:
        print(f"❌ 프롬프트 관리 중 오류: {e}")


if __name__ == "__main__":
    main()
