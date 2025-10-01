"""
테스트 히스토리 시각화 및 비교 분석 도구
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime

class TestHistoryVisualizer:
    """테스트 히스토리 시각화 클래스"""
    
    def __init__(self):
        # 한글 폰트 설정
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'AppleGothic']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 컬러 팔레트 설정
        self.colors = px.colors.qualitative.Set3
    
    def create_history_comparison(self, test_case_histories: Dict[str, List[Dict]]) -> go.Figure:
        """
        여러 테스트케이스의 히스토리를 비교하는 대시보드 생성
        
        Args:
            test_case_histories: {test_case_id: [history_records]} 형태의 딕셔너리
            
        Returns:
            Plotly Figure 객체
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '테스트케이스별 정확성 점수 추이',
                '실행 횟수별 평균 점수',
                '모델별 성능 비교',
                '점수 분포'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        all_data = []
        for test_case_id, history in test_case_histories.items():
            for record in history:
                record['test_case_id'] = test_case_id
                all_data.append(record)
        
        df = pd.DataFrame(all_data)
        
        if df.empty:
            fig.add_annotation(
                text="데이터가 없습니다",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=20)
            )
            return fig
        
        # 실행 시간을 datetime으로 변환
        df['execution_datetime'] = pd.to_datetime(df['execution_time'])
        df = df.sort_values('execution_datetime')
        
        # 1. 테스트케이스별 정확성 점수 추이
        for i, test_case_id in enumerate(df['test_case_id'].unique()):
            case_data = df[df['test_case_id'] == test_case_id]
            fig.add_trace(
                go.Scatter(
                    x=case_data['execution_datetime'],
                    y=case_data['judge_accuracy_score'],
                    mode='lines+markers',
                    name=f'TC: {test_case_id}',
                    line=dict(color=self.colors[i % len(self.colors)]),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                 '시간: %{x}<br>' +
                                 '점수: %{y}<br>' +
                                 '<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 2. 실행 횟수별 평균 점수
        df['execution_order'] = df.groupby('test_case_id').cumcount() + 1
        avg_by_order = df.groupby('execution_order')['judge_accuracy_score'].mean().reset_index()
        
        fig.add_trace(
            go.Bar(
                x=avg_by_order['execution_order'],
                y=avg_by_order['judge_accuracy_score'],
                name='평균 점수',
                marker_color='lightblue',
                hovertemplate='실행 차수: %{x}<br>' +
                             '평균 점수: %{y:.2f}<br>' +
                             '<extra></extra>'
            ),
            row=1, col=2
        )
        
        # 3. 모델별 성능 비교
        if 'model_used' in df.columns and df['model_used'].notna().any():
            model_avg = df.groupby('model_used')['judge_accuracy_score'].agg(['mean', 'count']).reset_index()
            model_avg.columns = ['model', 'avg_score', 'count']
            
            fig.add_trace(
                go.Bar(
                    x=model_avg['model'],
                    y=model_avg['avg_score'],
                    name='모델별 평균',
                    marker_color='lightgreen',
                    text=[f'n={count}' for count in model_avg['count']],
                    textposition='auto',
                    hovertemplate='모델: %{x}<br>' +
                                 '평균 점수: %{y:.2f}<br>' +
                                 '실행 횟수: %{text}<br>' +
                                 '<extra></extra>'
                ),
                row=2, col=1
            )
        
        # 4. 점수 분포
        fig.add_trace(
            go.Histogram(
                x=df['judge_accuracy_score'],
                nbinsx=6,
                name='점수 분포',
                marker_color='orange',
                opacity=0.7,
                hovertemplate='점수 범위: %{x}<br>' +
                             '빈도: %{y}<br>' +
                             '<extra></extra>'
            ),
            row=2, col=2
        )
        
        # 레이아웃 업데이트
        fig.update_layout(
            height=800,
            title_text="Agent QA 테스트 히스토리 분석 대시보드",
            title_x=0.5,
            showlegend=True
        )
        
        # 축 레이블 설정
        fig.update_xaxes(title_text="실행 시간", row=1, col=1)
        fig.update_yaxes(title_text="정확성 점수", row=1, col=1)
        
        fig.update_xaxes(title_text="실행 차수", row=1, col=2)
        fig.update_yaxes(title_text="평균 점수", row=1, col=2)
        
        fig.update_xaxes(title_text="모델", row=2, col=1)
        fig.update_yaxes(title_text="평균 점수", row=2, col=1)
        
        fig.update_xaxes(title_text="정확성 점수", row=2, col=2)
        fig.update_yaxes(title_text="빈도", row=2, col=2)
        
        return fig
    
    def create_single_testcase_timeline(self, history: List[Dict], test_case_id: str) -> go.Figure:
        """
        단일 테스트케이스의 상세 타임라인 생성
        
        Args:
            history: 테스트케이스 히스토리 리스트
            test_case_id: 테스트케이스 ID
            
        Returns:
            Plotly Figure 객체
        """
        if not history:
            fig = go.Figure()
            fig.add_annotation(
                text=f"테스트케이스 {test_case_id}의 데이터가 없습니다",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        df = pd.DataFrame(history)
        df['execution_datetime'] = pd.to_datetime(df['execution_time'])
        df = df.sort_values('execution_datetime')
        df['execution_number'] = range(1, len(df) + 1)
        
        # 메인 플롯 생성
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                f'테스트케이스 {test_case_id} - 정확성 점수 추이',
                '실행별 상세 정보'
            ),
            row_heights=[0.6, 0.4],
            specs=[[{"secondary_y": True}], [{"type": "table"}]]
        )
        
        # 1. 점수 추이 라인 차트
        fig.add_trace(
            go.Scatter(
                x=df['execution_number'],
                y=df['judge_accuracy_score'],
                mode='lines+markers',
                name='정확성 점수',
                line=dict(color='blue', width=3),
                marker=dict(size=8),
                hovertemplate='<b>실행 #%{x}</b><br>' +
                             '점수: %{y}<br>' +
                             '시간: %{customdata}<br>' +
                             '<extra></extra>',
                customdata=df['execution_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
            ),
            row=1, col=1
        )
        
        # 평균선 추가
        avg_score = df['judge_accuracy_score'].mean()
        fig.add_hline(
            y=avg_score, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"평균: {avg_score:.2f}",
            row=1, col=1
        )
        
        # 2. 상세 정보 테이블
        table_data = []
        for _, row in df.iterrows():
            table_data.append([
                f"#{row['execution_number']}",
                row['execution_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                f"{row['judge_accuracy_score']:.1f}",
                row.get('model_used', 'Unknown'),
                row['judge_reasoning'][:100] + "..." if len(str(row['judge_reasoning'])) > 100 else row['judge_reasoning']
            ])
        
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['실행#', '실행시간', '점수', '모델', '평가근거'],
                    fill_color='lightblue',
                    align='left',
                    font=dict(size=12)
                ),
                cells=dict(
                    values=list(zip(*table_data)) if table_data else [[], [], [], [], []],
                    fill_color='white',
                    align='left',
                    font=dict(size=10)
                )
            ),
            row=2, col=1
        )
        
        # 레이아웃 업데이트
        fig.update_layout(
            height=800,
            title_text=f"테스트케이스 {test_case_id} 상세 분석",
            title_x=0.5,
            showlegend=True
        )
        
        fig.update_xaxes(title_text="실행 순서", row=1, col=1)
        fig.update_yaxes(title_text="정확성 점수 (0-5)", row=1, col=1)
        
        return fig
    
    def generate_summary_report(self, test_case_histories: Dict[str, List[Dict]]) -> Dict:
        """
        테스트 결과 요약 리포트 생성
        
        Args:
            test_case_histories: 테스트케이스 히스토리
            
        Returns:
            요약 통계 딕셔너리
        """
        all_data = []
        for test_case_id, history in test_case_histories.items():
            for record in history:
                record['test_case_id'] = test_case_id
                all_data.append(record)
        
        if not all_data:
            return {
                "total_executions": 0,
                "total_test_cases": 0,
                "overall_avg_score": 0,
                "score_std": 0,
                "min_score": 0,
                "max_score": 0,
                "best_performing_tc": {"id": "없음", "avg_score": 0, "execution_count": 0},
                "worst_performing_tc": {"id": "없음", "avg_score": 0, "execution_count": 0}
            }
        
        df = pd.DataFrame(all_data)
        
        # 기본 통계
        summary = {
            "total_executions": len(df),
            "total_test_cases": df['test_case_id'].nunique(),
            "overall_avg_score": df['judge_accuracy_score'].mean(),
            "score_std": df['judge_accuracy_score'].std(),
            "min_score": df['judge_accuracy_score'].min(),
            "max_score": df['judge_accuracy_score'].max()
        }
        
        # 테스트케이스별 성능
        tc_performance = df.groupby('test_case_id')['judge_accuracy_score'].agg(['mean', 'count', 'std']).reset_index()
        tc_performance.columns = ['test_case_id', 'avg_score', 'execution_count', 'score_std']
        
        if not tc_performance.empty:
            best_tc = tc_performance.loc[tc_performance['avg_score'].idxmax()]
            worst_tc = tc_performance.loc[tc_performance['avg_score'].idxmin()]
            
            summary.update({
                "best_performing_tc": {
                    "id": best_tc['test_case_id'],
                    "avg_score": best_tc['avg_score'],
                    "execution_count": best_tc['execution_count']
                },
                "worst_performing_tc": {
                    "id": worst_tc['test_case_id'],
                    "avg_score": worst_tc['avg_score'],
                    "execution_count": worst_tc['execution_count']
                },
                "tc_performance": tc_performance.to_dict('records')
            })
        
        # 모델별 성능 (있는 경우)
        if 'model_used' in df.columns and df['model_used'].notna().any():
            model_performance = df.groupby('model_used')['judge_accuracy_score'].agg(['mean', 'count']).reset_index()
            model_performance.columns = ['model', 'avg_score', 'execution_count']
            summary['model_performance'] = model_performance.to_dict('records')
        
        return summary
