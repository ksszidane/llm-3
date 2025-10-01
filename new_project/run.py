1#!/usr/bin/env python3
"""
Agent QA 테스트 관리 시스템 실행 스크립트
"""

import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_environment():
    """환경 설정 확인"""
    # 여러 경로에서 .env 파일 찾기
    env_paths = [
        current_dir / ".env",  # new_project/.env
        current_dir.parent / ".env",  # llm-3/.env (상위 디렉토리)
        Path.cwd() / ".env"  # 현재 실행 디렉토리
    ]
    
    env_file = None
    for path in env_paths:
        if path.exists():
            env_file = path
            break
    
    if env_file is None:
        print("⚠️  .env 파일을 찾을 수 없습니다.")
        print("   다음 위치 중 하나에 .env 파일을 만들고 API 키를 설정해주세요:")
        for path in env_paths:
            print(f"   - {path}")
        print()
        print("   .env.example 파일을 참고하세요.")
        return False
    
    # 필수 환경변수 확인
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"✅ .env 파일 로드: {env_file}")
    
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  다음 환경변수가 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        return False
    
    print("✅ 환경 설정 확인 완료")
    return True

def main():
    """메인 실행 함수"""
    print("🤖 Agent QA 테스트 관리 시스템")
    print("=" * 50)
    print()
    
    if not check_environment():
        print("환경 설정을 완료한 후 다시 실행해주세요.")
        return
    
    print("실행할 모드를 선택하세요:")
    print("1. 웹 인터페이스 실행")
    print("2. 프롬프트 관리 (생성/업데이트)")
    print("3. 데이터셋에 TestCase 생성 및 업데이트")
    print("4. Judge 프롬프트 실행 후 평가 실행/저장")
    print("5. 서버 관리 (시작/중지/상태)")
    print("6. 프로그램 종료")
    print()
    
    while True:
        try:
            choice = input("선택 (1-6): ").strip()
            
            if choice == "1":
                print("\n🌐 웹 인터페이스를 시작합니다...")
                from web_interface import main as web_main
                web_main()
                break
                
            elif choice == "2":
                print("\n🔧 프롬프트 관리를 시작합니다...")
                try:
                    from prompt_manager import main as prompt_main
                    prompt_main()
                except ImportError:
                    print("❌ prompt_manager 모듈을 찾을 수 없습니다.")
                except Exception as e:
                    print(f"❌ 프롬프트 관리 실행 중 오류: {e}")
                # 메인 메뉴로 돌아가서 계속 루프
                print("\n" + "="*50)
                print("실행할 모드를 선택하세요:")
                print("1. 웹 인터페이스 실행")
                print("2. 프롬프트 관리 (생성/업데이트)")
                print("3. 데이터셋에 TestCase 생성 및 업데이트")
                print("4. Judge 프롬프트 실행 후 평가 실행/저장")
                print("5. 서버 관리 (시작/중지/상태)")
                print("6. 프로그램 종료")
                print()
                
            elif choice == "3":
                print("\n📥 데이터셋에 TestCase 생성 및 업데이트를 수행합니다...")
                try:
                    from real_implementation import save_testcases_only
                    save_testcases_only()
                except ImportError:
                    print("❌ real_implementation 모듈을 찾을 수 없습니다.")
                except Exception as e:
                    print(f"❌ 테스트케이스 저장 중 오류: {e}")
                break
                
            elif choice == "4":
                print("\n🚀 Judge 프롬프트 실행 후 평가 실행/저장을 진행합니다...")
                try:
                    from real_implementation import run_evaluation_only
                    run_evaluation_only()
                except ImportError:
                    print("❌ real_implementation 모듈을 찾을 수 없습니다.")
                except Exception as e:
                    print(f"❌ 평가 실행 중 오류: {e}")
                break
                
            elif choice == "5":
                print("\n🔧 서버 관리 모드입니다...")
                server_management()
                # 서버 관리 후 메인 메뉴 다시 표시
                print("\n" + "="*50)
                print("실행할 모드를 선택하세요:")
                print("1. 웹 인터페이스 실행")
                print("2. 프롬프트 관리 (생성/업데이트)")
                print("3. 데이터셋에 TestCase 생성 및 업데이트")
                print("4. Judge 프롬프트 실행 후 평가 실행/저장")
                print("5. 서버 관리 (시작/중지/상태)")
                print("6. 프로그램 종료")
                print()
                
            elif choice == "6":
                print("\n👋 프로그램을 종료합니다.")
                break
                
            else:
                print("올바른 선택이 아닙니다. 1-6 중에서 선택해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n👋 실행을 취소합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류가 발생했습니다: {e}")
            break

def server_management():
    """서버 관리 메뉴"""
    try:
        from server_manager import ServerManager
        manager = ServerManager()
        
        while True:
            print("\n🔧 서버 관리 메뉴")
            print("=" * 30)
            print("1. 서버 시작")
            print("2. 서버 중지") 
            print("3. 서버 상태 확인")
            print("4. 서버 로그 확인")
            print("5. 서버 재시작")
            print("6. 메인 메뉴로 돌아가기")
            print()
            
            try:
                choice = input("선택 (1-6): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n메인 메뉴로 돌아갑니다.")
                break
            
            if choice == "1":
                manager.start_server()
            elif choice == "2":
                manager.stop_server()
            elif choice == "3":
                manager.server_status()
            elif choice == "4":
                lines = input("표시할 로그 줄 수 (기본 20): ").strip()
                lines = int(lines) if lines.isdigit() else 20
                manager.show_logs(lines)
            elif choice == "5":
                print("🔄 서버를 재시작합니다...")
                manager.stop_server()
                import time
                time.sleep(2)
                manager.start_server()
            elif choice == "6":
                print("📋 메인 메뉴로 돌아갑니다...")
                break
            else:
                print("올바른 선택이 아닙니다. 1-6 중에서 선택해주세요.")
                
            if choice != "6":  # 메인 메뉴로 돌아가는 경우가 아닐 때만 대기
                input("\n계속하려면 Enter를 누르세요...")
            
    except ImportError:
        print("❌ server_manager 모듈을 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ 서버 관리 중 오류: {e}")

if __name__ == "__main__":
    main()
