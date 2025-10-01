"""
Agent QA 테스트 시스템 사용 예시
"""

import os
from dataset_manager import AgentQADatasetManager
from visualization import TestHistoryVisualizer
import time

def demo_basic_usage():
    """기본 사용법 데모"""
    print("=== Agent QA 테스트 시스템 기본 사용법 데모 ===\n")
    
    # 데이터셋 매니저 초기화
    manager = AgentQADatasetManager()
    
    # 1. 테스트케이스 추가
    print("1. 테스트케이스 추가")
    test_cases = [
        {
            "question": "대한민국의 수도는 어디야?",
            "expected": "대한민국의 수도는 서울입니다."
        },
        {
            "question": "파이썬에서 리스트와 튜플의 차이점은 무엇인가요?",
            "expected": "리스트는 변경 가능(mutable)하고 튜플은 변경 불가능(immutable)합니다."
        },
        {
            "question": "머신러닝에서 과적합(overfitting)이란 무엇인가요?",
            "expected": "과적합은 모델이 훈련 데이터에 지나치게 적응하여 새로운 데이터에 대한 일반화 성능이 떨어지는 현상입니다."
        }
    ]
    
    tc_ids = []
    for tc in test_cases:
        tc_id = manager.add_test_case(tc["question"], tc["expected"])
        tc_ids.append(tc_id)
        print(f"  - 테스트케이스 {tc_id} 추가: {tc['question'][:30]}...")
    
    print(f"\n총 {len(tc_ids)}개의 테스트케이스 추가 완료\n")
    
    # 2. 테스트케이스 실행 및 평가
    print("2. 테스트케이스 실행 및 평가")
    
    # 시뮬레이션된 LLM 답변들 (다양한 품질)
    simulated_answers = [
        # TC 1에 대한 여러 답변
        [
            "대한민국의 수도는 서울입니다.",  # 완벽한 답변
            "서울이에요.",  # 간단한 답변
            "대한민국의 수도는 서울특별시입니다. 서울은 조선시대부터 수도였습니다.",  # 상세한 답변
            "부산입니다.",  # 잘못된 답변
        ],
        # TC 2에 대한 여러 답변
        [
            "리스트는 mutable이고 튜플은 immutable입니다.",
            "리스트는 []로 만들고 튜플은 ()로 만듭니다. 리스트는 변경할 수 있지만 튜플은 변경할 수 없습니다.",
            "둘 다 순서가 있는 자료구조입니다.",  # 부분적으로 맞음
        ],
        # TC 3에 대한 여러 답변
        [
            "훈련 데이터에만 잘 맞고 새로운 데이터에는 성능이 떨어지는 것입니다.",
            "과적합은 모델이 너무 복잡해서 발생하는 문제입니다. 훈련 정확도는 높지만 검증 정확도는 낮습니다.",
            "모델이 잘못 학습되는 것입니다.",  # 모호한 답변
        ]
    ]
    
    for i, tc_id in enumerate(tc_ids):
        question = test_cases[i]["question"]
        print(f"\n  테스트케이스 {tc_id}: {question[:50]}...")
        
        for j, answer in enumerate(simulated_answers[i], 1):
            print(f"    실행 {j}: {answer[:60]}...")
            
            result = manager.evaluate_answer(
                test_case_id=tc_id,
                question=question,
                actual_answer=answer,
                model_used=f"demo_model_v{j}"
            )
            
            print(f"      → 점수: {result.judge_accuracy_score:.1f}/5")
            time.sleep(0.5)  # 실제 API 호출 시뮬레이션
    
    print("\n모든 테스트케이스 평가 완료!\n")
    
    # 3. 평가 완료 요약
    print("3. 평가 완료 요약")
    print(f"✅ 총 {len(tc_ids)}개의 테스트케이스에 대해 평가를 완료했습니다.")
    print("📊 각 테스트케이스별로 여러 답변의 평가 점수를 확인했습니다.")
    print("💾 모든 결과가 LangSmith에 저장되었습니다.")
    
    print("\n=== 데모 완료 ===")
    print("웹 인터페이스를 실행하려면 'python web_interface.py'를 실행하세요.")


if __name__ == "__main__":
    print("Agent QA 테스트 시스템 예시 실행\n")
    print("1. 기본 사용법 데모")
    print("2. 웹 인터페이스 실행")
    
    choice = input("\n실행할 데모를 선택하세요 (1-2): ").strip()
    
    if choice == "1":
        demo_basic_usage()
    elif choice == "2":
        from web_interface import main
        main()
    else:
        print("올바른 선택이 아닙니다. 기본 데모를 실행합니다.")
        demo_basic_usage()
