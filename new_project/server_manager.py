#!/usr/bin/env python3
"""
Agent QA 웹 서버 관리 도구
서버 시작/중지/상태 확인 기능
"""

import os
import sys
import signal
import subprocess
import time
import requests
from pathlib import Path

class ServerManager:
    """웹 서버 관리 클래스"""
    
    def __init__(self, port=7861):
        self.port = port
        self.pid_file = Path(__file__).parent / f".server_{port}.pid"
        self.log_file = Path(__file__).parent / f"server_{port}.log"
    
    def is_server_running(self) -> bool:
        """서버가 실행 중인지 확인"""
        try:
            response = requests.get(f"http://localhost:{self.port}", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_server_pid(self) -> int:
        """저장된 PID 파일에서 서버 PID 가져오기"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            except:
                return None
        return None
    
    def save_server_pid(self, pid: int):
        """서버 PID를 파일에 저장"""
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))
    
    def remove_pid_file(self):
        """PID 파일 제거"""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def start_server(self) -> bool:
        """웹 서버 시작"""
        if self.is_server_running():
            print(f"⚠️  서버가 이미 포트 {self.port}에서 실행 중입니다.")
            return False
        
        print(f"🚀 웹 서버를 포트 {self.port}에서 시작합니다...")
        
        try:
            # 현재 디렉토리 설정
            current_dir = Path(__file__).parent
            
            # 서버 실행 명령
            cmd = [
                sys.executable, "-m", "uv", "run", "python", 
                str(current_dir / "web_interface.py")
            ]
            
            # 백그라운드에서 서버 실행
            with open(self.log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    cwd=current_dir.parent,  # llm-3 디렉토리에서 실행
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid  # 새로운 프로세스 그룹 생성
                )
            
            # PID 저장
            self.save_server_pid(process.pid)
            
            # 서버 시작 대기
            print("⏳ 서버 시작을 기다리는 중...")
            for i in range(30):  # 30초 대기
                time.sleep(1)
                if self.is_server_running():
                    print(f"✅ 서버가 성공적으로 시작되었습니다!")
                    print(f"🌐 웹 인터페이스: http://localhost:{self.port}")
                    return True
                print(f"   대기 중... ({i+1}/30)")
            
            print("❌ 서버 시작에 실패했습니다.")
            self.remove_pid_file()
            return False
            
        except Exception as e:
            print(f"❌ 서버 시작 중 오류: {e}")
            self.remove_pid_file()
            return False
    
    def stop_server(self) -> bool:
        """웹 서버 중지"""
        if not self.is_server_running():
            print("💡 서버가 실행되고 있지 않습니다.")
            self.remove_pid_file()
            return True
        
        print(f"🛑 포트 {self.port}의 서버를 중지합니다...")
        
        # PID 파일에서 프로세스 종료 시도
        pid = self.get_server_pid()
        if pid:
            try:
                # 프로세스 그룹 전체 종료
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(2)
                
                # 강제 종료가 필요한 경우
                if self.is_server_running():
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                    time.sleep(1)
                    
            except ProcessLookupError:
                pass  # 이미 종료된 프로세스
            except Exception as e:
                print(f"⚠️  PID로 종료 실패: {e}")
        
        # 포트 기반으로 프로세스 종료 시도
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{self.port}"],
                capture_output=True, text=True
            )
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                        # 강제 종료
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except (ValueError, ProcessLookupError):
                        pass
        except Exception:
            pass
        
        # 최종 확인
        time.sleep(2)
        if not self.is_server_running():
            print("✅ 서버가 성공적으로 중지되었습니다.")
            self.remove_pid_file()
            return True
        else:
            print("⚠️  서버 중지에 실패했습니다. 수동으로 프로세스를 확인해주세요.")
            return False
    
    def server_status(self):
        """서버 상태 확인"""
        print(f"📊 서버 상태 (포트 {self.port}):")
        
        if self.is_server_running():
            print("🟢 상태: 실행 중")
            print(f"🌐 URL: http://localhost:{self.port}")
            
            pid = self.get_server_pid()
            if pid:
                print(f"🔢 PID: {pid}")
            
            if self.log_file.exists():
                print(f"📄 로그 파일: {self.log_file}")
        else:
            print("🔴 상태: 중지됨")
            
            # PID 파일이 있지만 서버가 실행되지 않는 경우
            if self.pid_file.exists():
                print("⚠️  PID 파일이 존재하지만 서버가 응답하지 않습니다.")
                print("   'stop' 명령으로 정리하는 것을 권장합니다.")
    
    def show_logs(self, lines=20):
        """서버 로그 표시"""
        if not self.log_file.exists():
            print("📄 로그 파일이 없습니다.")
            return
        
        print(f"📄 서버 로그 (마지막 {lines}줄):")
        print("-" * 50)
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
                for line in log_lines[-lines:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"로그 읽기 실패: {e}")

def main():
    """메인 실행 함수"""
    manager = ServerManager()
    
    if len(sys.argv) < 2:
        print("🤖 Agent QA 웹 서버 관리 도구")
        print("=" * 40)
        print("사용법:")
        print("  python server_manager.py start   - 서버 시작")
        print("  python server_manager.py stop    - 서버 중지")
        print("  python server_manager.py status  - 서버 상태 확인")
        print("  python server_manager.py logs    - 서버 로그 확인")
        print("  python server_manager.py restart - 서버 재시작")
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        manager.start_server()
    elif command == "stop":
        manager.stop_server()
    elif command == "status":
        manager.server_status()
    elif command == "logs":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        manager.show_logs(lines)
    elif command == "restart":
        print("🔄 서버를 재시작합니다...")
        manager.stop_server()
        time.sleep(2)
        manager.start_server()
    else:
        print(f"❌ 알 수 없는 명령: {command}")
        print("사용 가능한 명령: start, stop, status, logs, restart")

if __name__ == "__main__":
    main()
