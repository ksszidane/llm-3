"""
Gradio 기반 웹 인터페이스
Agent QA 시스템 - LangSmith 기반 테스트케이스 관리 및 평가
"""

import gradio as gr
import pandas as pd
import subprocess
import os
import sys
import threading
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import plotly.graph_objects as go

from real_implementation import save_testcases_only, run_evaluation_only
from langchain import hub
from langsmith import Client as LangSmithClient

class AgentQAWebInterface:
    """Agent QA 웹 인터페이스"""
    
    def __init__(self):
        pass
    
    
    def create_interface(self):
        """Gradio 인터페이스 생성"""
        # 데이터셋 상세 페이지 URL을 미리 계산 (UUID 기반)
        def _get_base_web_url() -> str:
            raw = os.getenv("LANGSMITH_WEB_URL") or os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT") or "https://smith.langchain.com"
            base = raw.rstrip('/')
            if base.startswith("http"):
                base = base.replace("api.", "").replace("/api", "")
            else:
                base = "https://smith.langchain.com"
            return base

        base_web = _get_base_web_url()
        source_ds_url = f"{base_web}/datasets"
        result_ds_url = f"{base_web}/datasets"
        try:
            client_for_urls = LangSmithClient()
            try:
                src_ds = client_for_urls.read_dataset(dataset_name="Agent_QA_Scenario")
                source_ds_url = f"{base_web}/datasets/{src_ds.id}"
            except Exception:
                pass
            try:
                res_ds = client_for_urls.read_dataset(dataset_name="Agent_QA_Scenario_Judge_Result")
                result_ds_url = f"{base_web}/datasets/{res_ds.id}"
            except Exception:
                pass
        except Exception:
            pass

        with gr.Blocks(title="Agent QA 시스템", theme=gr.themes.Soft()) as app:
            gr.Markdown("# 🤖 Agent QA 시스템")
            gr.Markdown("LangSmith 기반 테스트케이스 관리 및 GPT-4o 자동 평가")
            
            with gr.Tabs():
                # EV RAG 챗봇 탭 (첫 번째)
                with gr.Tab("🧠 전기차 RAG 대화"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 전기차 RAG Agent와 대화하기")
                            ev_chatbot = gr.Chatbot(label="Agent", type="messages", height=420)
                            ev_query = gr.Textbox(label="질문", placeholder="전기차 관련해서 무엇이든 물어보세요")
                            ev_send = gr.Button("질문 보내기", variant="primary")
                        with gr.Column(scale=1):
                            gr.Markdown("### 참고 출처")
                            ev_citations = gr.Dataframe(headers=["rank", "source", "chunk_id"], interactive=False)

                    # EV RAG 핸들러
                    def _ev_chat(history: list[dict], query: str):
                        try:
                            from ev_agent_orchestrator import EVAgentOrchestrator
                            orchestrator = EVAgentOrchestrator()
                            answer, citations = orchestrator.chat(query)
                            new_history = (history or []) + [{"role": "user", "content": query}, {"role": "assistant", "content": answer}]
                            rows = [[c["rank"], c["source"], c["chunk_id"]] for c in citations]
                            return new_history, "", rows
                        except Exception as e:
                            new_history = (history or []) + [{"role": "assistant", "content": f"오류: {e}"}]
                            return new_history, query, []

                    ev_send.click(_ev_chat, inputs=[ev_chatbot, ev_query], outputs=[ev_chatbot, ev_query, ev_citations])
                    # Enter 제출 지원
                    ev_query.submit(_ev_chat, inputs=[ev_chatbot, ev_query], outputs=[ev_chatbot, ev_query, ev_citations])

                # 메인 실행 탭
                with gr.Tab("🚀 메인 실행"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 3. 데이터셋에 TestCase 생성 및 업데이트")
                            
                            # 3. 데이터셋 설명
                            gr.Markdown("`TestCase.xlsx` 파일의 내용을 LangSmith `Agent_QA_Scenario` 데이터셋에 저장합니다.")
                            
                            # 1. 버튼
                            save_tc_btn = gr.Button("TestCase → LangSmith 저장", variant="primary", size="lg")
                            
                            # 4. 실행 결과
                            save_tc_log = gr.Textbox(
                                label="실행 결과", 
                                lines=8, 
                                interactive=False, 
                                max_lines=20,
                                autoscroll=True
                            )
                            
                            # 2. 파일 업로드
                            with gr.Row():
                                file_upload = gr.File(
                                    label="📤 Excel 파일 업로드 (선택사항)",
                                    file_types=[".xlsx", ".xls"],
                                    type="filepath"
                                )
                            
                            gr.Markdown("📝 **참고**: 파일을 업로드하지 않으면 기본 `TestCase.xlsx` 파일을 사용합니다.")

                        with gr.Column(scale=1):
                            gr.Markdown("### 4. Judge 프롬프트 실행 후 평가 실행/저장")
                            gr.Markdown("LangSmith에서 테스트케이스를 가져와 전기차 RAG Agent로 답변 생성 후 평가 결과를 저장합니다.")
                            run_eval_btn = gr.Button("RAG 기반 평가 실행/저장", variant="primary", size="lg")
                            run_eval_log = gr.Textbox(
                                label="실행 결과", 
                                lines=8, 
                                interactive=False, 
                                max_lines=20,
                                autoscroll=True
                            )
                            
                            # 전체 실행 순서를 우측 하단으로 이동
                            gr.Markdown("---")
                            gr.Markdown("### 📋 전체 실행 순서")
                            gr.Markdown("""
                            1. **프롬프트 관리**: 메뉴 2번에서 `accuracy_judge_prompt` 생성/업데이트
                            2. **데이터 준비**: 위 3번 버튼으로 TestCase.xlsx → LangSmith 저장
                            3. **평가 실행**: 위 4번 버튼으로 GPT-4o 평가 및 결과 저장
                            4. **결과 확인**: 아래 평가 결과 섹션에서 확인
                            """)

                # 프롬프트 관리 탭
                with gr.Tab("🔧 프롬프트 관리"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            create_prompt_btn = gr.Button("프롬프트 생성/업데이트", variant="secondary", size="lg")
                            gr.Markdown("LangChain Hub에 `accuracy_judge_prompt`를 생성하거나 업데이트합니다.")
                            create_prompt_log = gr.Textbox(label="결과", lines=10, interactive=False)

                        with gr.Column(scale=1):
                            refresh_prompt_btn = gr.Button("현재 버전 조회", variant="secondary", size="lg")
                            gr.Markdown("현재 Hub의 최신 커밋 버전을 조회합니다.")
                            prompt_version = gr.Textbox(label="현재 버전 정보", lines=10, interactive=False)

                # 평가 결과 탭
                with gr.Tab("📊 평가 결과"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 최신 평가 결과")
                            with gr.Row():
                                refresh_results_btn = gr.Button("결과 새로고침", variant="secondary")
                                open_result_dataset_btn = gr.Button("🔗 평가 결과 데이터셋 열기", variant="primary", link=result_ds_url)
                            results_df = gr.Dataframe(
                                label="Agent_QA_Scenario_Judge_Result",
                                interactive=False,
                                wrap=True
                            )

                        with gr.Column(scale=1):
                            gr.Markdown("### 요약 통계")
                            summary_box = gr.Textbox(label="통계 정보", lines=4, interactive=False)
                            
                            gr.Markdown("### 점수 분포")
                            score_distribution = gr.Textbox(label="점수별 건수", lines=8, interactive=False)
                            
                            gr.Markdown("### 🔗 직접 링크")
                            gr.HTML(f"""
                            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                <p><strong>LangSmith 데이터셋:</strong></p>
                                <p>• <a href="{base_web}/datasets" target="_blank">📁 전체 데이터셋 목록</a></p>
                                <p>• <a href="{source_ds_url}" target="_blank">📋 테스트케이스 데이터셋</a></p>
                                <p>• <a href="{result_ds_url}" target="_blank">📊 평가 결과 데이터셋</a></p>
                            </div>
                            """)

                # 히스토리 조회 탭
                with gr.Tab("📈 히스토리 조회"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            history_case_dropdown = gr.Dropdown(label="case_id 선택", choices=[], value=None)
                            history_refresh_btn = gr.Button("목록 새로고침", variant="secondary")
                            history_load_btn = gr.Button("히스토리 로드", variant="primary")
                            history_summary = gr.Textbox(label="요약", lines=3, interactive=False)
                        with gr.Column(scale=2):
                            history_plot = gr.Plot(label="점수 추이")
                            history_df = gr.Dataframe(label="히스토리 상세", interactive=False, wrap=True)
                            history_table = gr.HTML("")

                # 서버 관리 탭 (원복)
                with gr.Tab("⚙️ 서버 관리"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            check_status_btn = gr.Button("상태 새로고침", variant="secondary", size="lg")
                            gr.Markdown("현재 서버 상태를 조회합니다.")
                            server_status = gr.Textbox(label="현재 서버 상태", lines=10, interactive=False)

                        with gr.Column(scale=1):
                            stop_server_btn = gr.Button("서버 중지", variant="stop", size="lg")
                            gr.Markdown("⚠️ 서버 중지 시 현재 웹 인터페이스 연결이 끊어집니다.")
                            server_control_log = gr.Textbox(
                                label="제어 결과", 
                                lines=10, 
                                interactive=False,
                                max_lines=15,
                                autoscroll=True
                            )

                # 시스템 정보 탭
                with gr.Tab("ℹ️ 시스템 정보"):
                    gr.Markdown("""
                    ## 🤖 Agent QA 시스템
                    
                    ### ✨ 주요 기능
                    - 📋 **TestCase 관리**: Excel 파일을 LangSmith 데이터셋으로 자동 변환
                    - 🤖 **GPT-4o 평가**: 질문에 대한 자동 답변 생성
                    - ⚖️ **LLM-as-Judge**: 답변 정확성을 0-5점으로 자동 평가
                    - 💾 **결과 저장**: 모든 평가 결과를 LangSmith에 체계적 저장
                    - 🔧 **프롬프트 관리**: LangChain Hub를 통한 중앙집중식 프롬프트 관리
                    
                    ### 📊 평가 기준 (정확성 0-5점)
                    - **5점**: 완벽히 정확하고 완전한 답변
                    - **4점**: 대부분 정확하며 약간의 부족함이 있음  
                    - **3점**: 기본적으로 정확하나 중요한 정보가 누락됨
                    - **2점**: 부분적으로 정확하나 오류나 부정확한 정보 포함
                    - **1점**: 대부분 부정확하나 일부 관련된 정보 포함
                    - **0점**: 완전히 부정확하거나 관련 없는 답변
                    
                    ### 🔗 연동 서비스
                    - **LangSmith**: 데이터셋 관리, 실행 추적, 평가 결과 저장
                    - **LangChain Hub**: 중앙집중식 프롬프트 관리 및 버전 관리
                    - **OpenAI GPT-4o**: 답변 생성 및 LLM-as-Judge 평가
                    
                    ### 🗂️ 데이터셋 구조
                    - **Agent_QA_Scenario**: 테스트케이스 저장 (case_id, question)
                    - **Agent_QA_Scenario_Judge_Result**: 평가 결과 저장 (question, answer, judge_accuracy_score, reasoning)
                    """)
            
            # 이벤트 핸들러 설정
            
            # 메인 실행 핸들러 - 실시간 로그 스트리밍 (-u로 자식 프로세스 버퍼링 해제)
            def _save_tc_stream(uploaded_file):
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                
                # 업로드된 파일 경로를 환경변수로 전달
                if uploaded_file:
                    env["UPLOADED_EXCEL_PATH"] = uploaded_file
                    file_info = f"업로드된 파일: {os.path.basename(uploaded_file)}"
                else:
                    file_info = "기본 TestCase.xlsx 사용"
                
                # 업로드 경로를 직접 인자로 전달하여 로그의 파일명이 정확히 표시되도록 조정
                arg_code = (
                    "import sys, os; sys.path.append('new_project'); "
                    "from real_implementation import save_testcases_only; "
                    "p=os.getenv('UPLOADED_EXCEL_PATH'); "
                    "save_testcases_only(p)"
                )
                proc = subprocess.Popen(
                    [sys.executable, "-u", "-c", arg_code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd="/Users/1112049/llm-3",
                    env=env,
                )
                lines = [
                    f"🚀 TestCase 저장 실행 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
                    f"📁 {file_info}",
                    "="*60
                ]
                yield "\n".join(lines)
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    lines.append(line.rstrip())
                    yield "\n".join(lines[-200:])
                return_code = proc.wait()
                if return_code == 0:
                    lines.append("✅ TestCase 저장 완료!")
                else:
                    lines.append(f"❌ TestCase 저장 실패! (종료 코드: {return_code})")
                yield "\n".join(lines[-200:])

            def _run_eval_stream():
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                proc = subprocess.Popen(
                    [sys.executable, "-u", "-c", "import sys; sys.path.append('new_project'); from real_implementation import run_evaluation_only; run_evaluation_only()"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd="/Users/1112049/llm-3",
                    env=env,
                )
                lines = [f"🚀 GPT-4o 평가 실행 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})", "="*60]
                yield "\n".join(lines)
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    lines.append(line.rstrip())
                    yield "\n".join(lines[-200:])
                return_code = proc.wait()
                if return_code == 0:
                    lines.append("✅ GPT-4o 평가 완료!")
                else:
                    lines.append(f"❌ GPT-4o 평가 실패! (종료 코드: {return_code})")
                yield "\n".join(lines[-200:])

            save_tc_btn.click(_save_tc_stream, inputs=[file_upload], outputs=[save_tc_log])
            run_eval_btn.click(_run_eval_stream, outputs=[run_eval_log])

            # 프롬프트 관리 핸들러
            def _create_prompt():
                try:
                    result = subprocess.run([
                        sys.executable, "-c",
                        "import sys; sys.path.append('new_project'); from prompt_manager import PromptManager; pm=PromptManager(); pm.create_or_update_accuracy_judge_prompt()"
                    ], capture_output=True, text=True, cwd="/Users/1112049/llm-3")
                    
                    if result.returncode == 0:
                        return f"✅ 프롬프트 생성/업데이트 완료!\n\n{result.stdout}"
                    else:
                        return f"❌ 프롬프트 생성/업데이트 실패!\n\n{result.stderr}"
                except Exception as e:
                    return f"❌ 실행 오류: {e}"

            def _check_prompt_version():
                try:
                    result = subprocess.run([
                        sys.executable, "-c",
                        "import sys; sys.path.append('new_project'); from prompt_manager import PromptManager; pm=PromptManager(); pm.list_prompts()"
                    ], capture_output=True, text=True, cwd="/Users/1112049/llm-3")
                    
                    if result.returncode == 0:
                        return f"✅ 프롬프트 버전 조회 완료!\n\n{result.stdout}"
                    else:
                        return f"❌ 프롬프트 버전 조회 실패!\n\n{result.stderr}"
                except Exception as e:
                    return f"❌ 실행 오류: {e}"

            create_prompt_btn.click(fn=_create_prompt, outputs=[create_prompt_log])
            refresh_prompt_btn.click(fn=_check_prompt_version, outputs=[prompt_version])

            # 평가 결과 핸들러
            # 평가결과 탭: Trace 열/버튼 비활성화 (요청으로 제거)

            def _load_results():
                try:
                    client = LangSmithClient()
                    dataset = "Agent_QA_Scenario_Judge_Result"
                    rows = []
                    
                    for ex in client.list_examples(dataset_name=dataset):
                        case_id = ex.metadata.get("case_id") if ex.metadata else None
                        question = ex.inputs.get("input", "")
                        answer = ex.outputs.get("answer", "") if ex.outputs else ""
                        score = ex.outputs.get("judge_accuracy_score") if ex.outputs else None
                        
                        rows.append({
                            "case_id": case_id,
                            "question": question[:100] + "..." if len(question) > 100 else question,
                            "answer": answer[:100] + "..." if len(answer) > 100 else answer,
                            "score": score
                        })
                    
                    df = pd.DataFrame(rows)
                    
                    if len(df) == 0:
                        return df, "데이터 없음", "점수 데이터 없음"
                    
                    # 요약 통계
                    scores = [float(s) for s in df["score"] if s is not None]
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        max_score = max(scores)
                        min_score = min(scores)
                        summary = f"총 {len(df)}건\n평균: {avg_score:.2f}점\n최고: {max_score:.0f}점\n최저: {min_score:.0f}점"
                        
                        # 점수 분포
                        score_counts = {}
                        for s in scores:
                            s_int = int(s)
                            score_counts[s_int] = score_counts.get(s_int, 0) + 1
                        
                        distribution = "\n".join([f"{s}점: {count}건" for s, count in sorted(score_counts.items())])
                    else:
                        summary = "점수 데이터 없음"
                        distribution = "점수 데이터 없음"
                    
                    # HTML 테이블 구성 (Trace 열 포함)
                    rows_html = [
                        "<tr><th>case_id</th><th>question</th><th>answer</th><th>score</th><th>Trace</th></tr>"
                    ]
                    for _, row in df.iterrows():
                        btn = f'<a href="{row.get("trace_url", "")}" target="_blank"><button>Trace 열기</button></a>' if row.get("trace_url") else "-"
                        q = (row.get("question") or "").replace("<","&lt;").replace(">","&gt;")
                        a = (row.get("answer") or "").replace("<","&lt;").replace(">","&gt;")
                        rows_html.append(f"<tr><td>{row.get('case_id','')}</td><td style='max-width:360px;overflow:auto'>{q}</td><td style='max-width:360px;overflow:auto'>{a}</td><td>{row.get('score','')}</td><td>{btn}</td></tr>")
                    table_html = "<div style='margin-top:8px'><table style='width:100%;border-collapse:collapse'>" + "".join(rows_html) + "</table></div>"
                    table_html += "<style>table, th, td {border:1px solid #ddd;padding:6px;} th{background:#fafafa;text-align:left}</style>"
                    
                    return df, summary, distribution
                    
                except Exception as e:
                    empty_df = pd.DataFrame(columns=["case_id", "question", "answer", "score"])
                    return empty_df, f"로드 실패: {e}", "로드 실패"

            refresh_results_btn.click(fn=_load_results, outputs=[results_df, summary_box, score_distribution])

            # Dataframe 행 선택 시, 해당 행의 실제 trace_url을 조회하여 버튼 링크로 설정
            # 평가결과 탭 trace 선택/열기 기능 제거됨

            # 히스토리 유틸
            def _history_list_case_ids():
                try:
                    client = LangSmithClient()
                    ids = []
                    for ex in client.list_examples(dataset_name="Agent_QA_Scenario_Judge_History"):
                        if ex.metadata and ex.metadata.get("case_id"):
                            ids.append(ex.metadata["case_id"])
                    return sorted(list(set(ids)))
                except Exception:
                    return []

            def _history_load_case(case_id: str):
                try:
                    client = LangSmithClient()
                    target = None
                    for ex in client.list_examples(dataset_name="Agent_QA_Scenario_Judge_History"):
                        if ex.metadata and ex.metadata.get("case_id") == case_id:
                            target = ex
                            break
                    if not target:
                        return go.Figure(), pd.DataFrame(), "데이터 없음", ""
                    outs = target.outputs or {}
                    scores = list(outs.get("scores", []))
                    times = list(outs.get("timestamps", []))
                    reasons = list(outs.get("reasons", []))
                    answers = list(outs.get("answers", []))
                    traces = list(outs.get("trace_urls", []))
                    # 질문 내용은 inputs.input에서 가져옴
                    raw_question = ""
                    try:
                        raw_question = target.inputs.get("input", "") if target.inputs else ""
                    except Exception:
                        raw_question = ""
                    # 길이 보정 (누락된 trace를 빈 문자열로 채움)
                    while len(traces) < len(scores):
                        traces.append("")
                    # 그래프는 시간축 대신 실행 순번 기준으로 표시
                    run_indices = list(range(1, len(scores) + 1))
                    df = pd.DataFrame({"run": run_indices, "timestamp": times, "score": scores, "reason": reasons, "answer": answers})
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df["run"], y=df["score"], mode="lines+markers"))
                    # 타이틀에 질문 요약 추가
                    short_q = (raw_question[:120] + "...") if isinstance(raw_question, str) and len(raw_question) > 120 else raw_question
                    title_text = f"{case_id} 점수 추이" + (f"<br><sub>{short_q}</sub>" if short_q else "")
                    fig.update_layout(yaxis=dict(range=[-0.1,5.1]), xaxis_title="실행 순번", title=title_text)
                    summary = f"횟수: {len(scores)} | 최근: {scores[-1] if scores else '-'} / 평균: {df['score'].mean():.2f}"
                    # HTML 테이블 렌더링 (각 행에 Trace 열기 버튼)
                    rows_html = [
                        "<tr><th>#</th><th>Timestamp</th><th>Score</th><th>Reason</th><th>Trace</th></tr>"
                    ]
                    for idx, (t, s, r, url) in enumerate(zip(times, scores, reasons, traces), start=1):
                        btn = f'<a href="{url}" target="_blank"><button>Trace 열기</button></a>' if url else "-"
                        safe_reason = (r or "").replace("<", "&lt;").replace(">", "&gt;")
                        rows_html.append(f"<tr><td>{idx}</td><td>{t}</td><td>{s}</td><td style='max-width:420px;overflow:auto;'>{safe_reason}</td><td>{btn}</td></tr>")
                    table_html = "<div style='margin-top:8px'><table style='width:100%;border-collapse:collapse'>" + "".join(rows_html) + "</table></div>"
                    # 간단 스타일
                    table_html += "<style>table, th, td {border:1px solid #ddd;padding:6px;} th{background:#fafafa;text-align:left}</style>"
                    return fig, df, summary, table_html
                except Exception as e:
                    return go.Figure(), pd.DataFrame(), f"로드 실패: {e}", ""

            history_refresh_btn.click(fn=_history_list_case_ids, outputs=[history_case_dropdown])
            history_load_btn.click(fn=_history_load_case, inputs=[history_case_dropdown], outputs=[history_plot, history_df, history_summary, history_table])

            # 동적 링크 요소 제거(바로 이동)

            # 서버 관리 핸들러
            def _check_server_status():
                try:
                    result = subprocess.run([
                        sys.executable, "-c",
                        "import sys; sys.path.append('new_project'); from server_manager import ServerManager; sm=ServerManager(); sm.server_status()"
                    ], capture_output=True, text=True, cwd="/Users/1112049/llm-3", timeout=30)
                    
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if result.returncode == 0:
                        return f"🔍 상태 확인 완료 ({current_time})\n\n{result.stdout}"
                    else:
                        return f"❌ 상태 확인 실패 ({current_time})\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                except subprocess.TimeoutExpired:
                    return "⏰ 상태 확인 시간 초과"
                except Exception as e:
                    return f"❌ 실행 오류: {e}"

            def _stop_server():
                try:
                    result = subprocess.run([
                        sys.executable, "-c",
                        "import sys; sys.path.append('new_project'); from server_manager import ServerManager; sm=ServerManager(); sm.stop_server()"
                    ], capture_output=True, text=True, cwd="/Users/1112049/llm-3", timeout=30)
                    
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if result.returncode == 0:
                        control_msg = f"✅ 서버 중지 완료 ({current_time})\n\n{result.stdout}"
                    else:
                        control_msg = f"❌ 서버 중지 실패 ({current_time})\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                    
                    # 상태 자동 갱신
                    time.sleep(1)
                    status_result = _check_server_status()
                    return control_msg, status_result
                    
                except subprocess.TimeoutExpired:
                    return "⏰ 서버 중지 시간 초과", "⏰ 상태 확인 시간 초과"
                except Exception as e:
                    return f"❌ 실행 오류: {e}", f"❌ 상태 확인 오류: {e}"

            check_status_btn.click(fn=_check_server_status, outputs=[server_status])
            stop_server_btn.click(fn=_stop_server, outputs=[server_control_log, server_status])

            # 초기 데이터 로드
            def _init_load():
                rdf, rsum, rdist = _load_results()
                prompt_version_info = _check_prompt_version()
                ids = _history_list_case_ids()
                default_id = ids[0] if ids else None
                if default_id:
                    fig, hdf, hsum, hhtml = _history_load_case(default_id)
                else:
                    fig, hdf, hsum, hhtml = go.Figure(), pd.DataFrame(), "데이터 없음", ""
                return rdf, rsum, rdist, prompt_version_info, gr.update(choices=ids, value=default_id), fig, hdf, hsum, hhtml

            app.load(fn=_init_load, outputs=[results_df, summary_box, score_distribution, prompt_version, history_case_dropdown, history_plot, history_df, history_summary, history_table])
            # 스트리밍/동시성 활성화
            app.queue()
        
        return app

def main():
    """메인 실행 함수"""
    interface = AgentQAWebInterface()
    app = interface.create_interface()
    
    print("🚀 Agent QA 테스트 관리 시스템 시작")
    print("📋 핵심 기능:")
    print("  - 테스트케이스 추가 및 관리")
    print("  - LLM-as-Judge 자동 평가")
    print("  - LangSmith 연동")
    print("  - 실시간 평가 결과 확인")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,  # 다른 포트 사용
        share=False,
        inbrowser=True
    )

if __name__ == "__main__":
    main()
