#!/usr/bin/env python3
"""
Skrypt startowy dla serwera FastAPI z systemem Kożu Ofiarny.
"""

import sys
import subprocess
import time
from pathlib import Path

def start_server():
    """Uruchamia serwer FastAPI"""
    print("=== Startowanie serwera FastAPI ===")
    print("URL serwera: http://localhost:8000")
    print("Dokumentacja Swagger: http://localhost:8000/docs")
    print("Dokumentacja ReDoc: http://localhost:8000/redoc")
    print()
    
    try:
        # Uruchom serwer
        cmd = [sys.executable, "-m", "uvicorn", "api:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
        subprocess.run(cmd, cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\nSerwer zatrzymany przez użytkownika")
    except Exception as e:
        print(f"Błąd uruchamiania serwera: {e}")
        return False
    
    return True

if __name__ == "__main__":
    start_server()
