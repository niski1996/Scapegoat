"""
Główny skrypt do uruchamiania wszystkich testów systemu Kożu Ofiarny.
Instaluje wymagane zależności i uruchamia testy jednostkowe oraz integracyjne.
"""

import subprocess
import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime


def install_test_dependencies():
    """Instaluje wymagane biblioteki do testowania."""
    print("=" * 60)
    print("INSTALACJA ZALEŻNOŚCI TESTOWYCH")
    print("=" * 60)
    
    dependencies = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "httpx>=0.24.0",
        "coverage>=7.0.0",
        "pytest-cov>=4.0.0"
    ]
    
    for dep in dependencies:
        print(f"Instalacja: {dep}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True, text=True)
            print(f"✅ {dep} - OK")
        except subprocess.CalledProcessError as e:
            print(f"❌ {dep} - BŁĄD: {e.stderr}")
            return False
    
    print("✅ Wszystkie zależności zainstalowane")
    return True


def check_environment():
    """Sprawdza środowisko testowe."""
    print("\n" + "=" * 60)
    print("SPRAWDZANIE ŚRODOWISKA")
    print("=" * 60)
    
    # Sprawdź Python
    python_version = sys.version_info
    print(f"Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("❌ Wymagany Python 3.8+")
        return False
    print("✅ Wersja Python OK")
    
    # Sprawdź wymagane moduły
    required_modules = [
        "pandas", "pyarrow", "fastapi", "uvicorn"
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} - dostępny")
        except ImportError:
            print(f"❌ {module} - BRAK")
            return False
    
    # Sprawdź strukture katalogów
    current_dir = Path.cwd()
    required_files = [
        "data_generator.py",
        "transformer.py", 
        "api.py",
        "test_units.py",
        "test_api_integration.py"
    ]
    
    for file in required_files:
        if (current_dir / file).exists():
            print(f"✅ {file} - znaleziony")
        else:
            print(f"❌ {file} - BRAK")
            return False
    
    print("✅ Środowisko gotowe do testów")
    return True


def run_unit_tests():
    """Uruchamia testy jednostkowe."""
    print("\n" + "=" * 60)
    print("URUCHAMIANIE TESTÓW JEDNOSTKOWYCH")
    print("=" * 60)
    
    try:
        # Uruchom testy jednostkowe
        result = subprocess.run([
            sys.executable, "test_units.py"
        ], capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Testy jednostkowe przekroczyły limit czasu (5 min)")
        return False
    except Exception as e:
        print(f"❌ Błąd uruchamiania testów jednostkowych: {e}")
        return False


def start_api_server():
    """Uruchamia serwer API w tle dla testów integracyjnych."""
    print("\n" + "=" * 40)
    print("URUCHAMIANIE SERWERA API")
    print("=" * 40)
    
    try:
        # Uruchom serwer w tle
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "api:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "warning"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Poczekaj na uruchomienie serwera
        print("Oczekiwanie na uruchomienie serwera...")
        time.sleep(3)
        
        # Sprawdź czy serwer działa
        try:
            import requests
            response = requests.get("http://127.0.0.1:8000/", timeout=5)
            if response.status_code == 200:
                print("✅ Serwer API uruchomiony")
                return process
        except:
            pass
        
        # Jeśli nie udało się połączyć, zabij proces
        process.terminate()
        print("❌ Nie udało się uruchomić serwera API")
        return None
        
    except Exception as e:
        print(f"❌ Błąd uruchamiania serwera: {e}")
        return None


def run_integration_tests():
    """Uruchamia testy integracyjne."""
    print("\n" + "=" * 60)
    print("URUCHAMIANIE TESTÓW INTEGRACYJNYCH")
    print("=" * 60)
    
    # Uruchom serwer API
    api_process = start_api_server()
    if not api_process:
        print("❌ Nie można uruchomić testów integracyjnych bez serwera API")
        return False
    
    try:
        # Uruchom testy integracyjne
        result = subprocess.run([
            sys.executable, "test_api_integration.py"
        ], capture_output=True, text=True, timeout=600)  # 10 minut
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Testy integracyjne przekroczyły limit czasu (10 min)")
        success = False
    except Exception as e:
        print(f"❌ Błąd uruchamiania testów integracyjnych: {e}")
        success = False
    finally:
        # Zatrzymaj serwer API
        if api_process:
            api_process.terminate()
            api_process.wait()
            print("🛑 Serwer API zatrzymany")
    
    return success


def run_performance_tests():
    """Uruchamia testy wydajności."""
    print("\n" + "=" * 60)
    print("TESTY WYDAJNOŚCI")
    print("=" * 60)
    
    # Test generowania danych
    print("Test 1: Generowanie 100k wierszy...")
    start_time = time.time()
    
    try:
        from data_generator import generate_parquet
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            result = generate_parquet(100000, 50, f.name)
            end_time = time.time()
            
            execution_time = end_time - start_time
            print(f"✅ Wygenerowano 100k wierszy w {execution_time:.2f}s")
            print(f"   Rozmiar: {result['file_info']['file_size_mb']:.2f} MB")
            
            # Usuń plik testowy
            os.unlink(f.name)
            
    except Exception as e:
        print(f"❌ Błąd testu wydajności: {e}")
        return False
    
    # Test transformacji
    print("\nTest 2: Transformacja do batchów...")
    start_time = time.time()
    
    try:
        from transformer import pivot_and_batch
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Wygeneruj plik testowy
            input_file = os.path.join(temp_dir, "input.parquet")
            generate_parquet(50000, 30, input_file)
            
            # Transformuj
            output_dir = os.path.join(temp_dir, "batches")
            result = pivot_and_batch(input_file, 10000, output_dir)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            print(f"✅ Transformacja 50k wierszy w {execution_time:.2f}s")
            print(f"   Batche: {result['batch_count']}")
            
    except Exception as e:
        print(f"❌ Błąd testu transformacji: {e}")
        return False
    
    print("✅ Testy wydajności zakończone")
    return True


def generate_test_report(unit_success, integration_success, performance_success):
    """Generuje raport z testów."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "working_directory": str(Path.cwd())
        },
        "test_results": {
            "unit_tests": "PASS" if unit_success else "FAIL",
            "integration_tests": "PASS" if integration_success else "FAIL", 
            "performance_tests": "PASS" if performance_success else "FAIL"
        },
        "overall_status": "PASS" if all([unit_success, integration_success, performance_success]) else "FAIL"
    }
    
    # Zapisz raport
    report_file = Path("test_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Raport zapisany: {report_file}")
    return report


def main():
    """Główna funkcja uruchamiająca wszystkie testy."""
    print("🔬 SYSTEM TESTOWY KOŻU OFIARNY")
    print("Kompleksowe testowanie API i komponentów")
    print("=" * 60)
    
    start_time = time.time()
    
    # Sprawdź środowisko
    if not check_environment():
        print("❌ Środowisko nie spełnia wymagań")
        return 1
    
    # Zainstaluj zależności testowe
    if not install_test_dependencies():
        print("❌ Nie udało się zainstalować zależności")
        return 1
    
    # Uruchom testy
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()
    performance_success = run_performance_tests()
    
    # Wygeneruj raport
    report = generate_test_report(unit_success, integration_success, performance_success)
    
    # Podsumowanie
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "=" * 60)
    print("PODSUMOWANIE KOŃCOWE")
    print("=" * 60)
    print(f"Czas wykonania: {total_time:.1f} sekund")
    print(f"Testy jednostkowe: {'✅ PASS' if unit_success else '❌ FAIL'}")
    print(f"Testy integracyjne: {'✅ PASS' if integration_success else '❌ FAIL'}")
    print(f"Testy wydajności: {'✅ PASS' if performance_success else '❌ FAIL'}")
    print(f"Status ogólny: {'✅ PASS' if report['overall_status'] == 'PASS' else '❌ FAIL'}")
    
    if report['overall_status'] == 'PASS':
        print("\n🎉 Wszystkie testy przeszły pomyślnie!")
        print("System Kożu Ofiarny gotowy do użycia.")
        return 0
    else:
        print("\n⚠️  Niektóre testy nie powiodły się.")
        print("Sprawdź logi powyżej i popraw błędy.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
