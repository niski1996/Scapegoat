#!/bin/bash

# Główny skrypt uruchomieniowy dla systemu Kożu Ofiarny

echo "🐐 Uruchamianie systemu Kożu Ofiarny - Scapegoat System"
echo "======================================================="

# Sprawdzenie czy Python jest dostępny
if ! command -v python3 &> /dev/null; then
    echo "❌ Błąd: Python3 nie jest zainstalowany"
    exit 1
fi

# Sprawdzenie czy Node.js jest dostępny
if ! command -v node &> /dev/null; then
    echo "❌ Błąd: Node.js nie jest zainstalowany"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"
echo "✅ Node.js: $(node --version)"
echo ""

# Funkcja do uruchamiania backendu
start_backend() {
    echo "🔧 Uruchamianie Backend (FastAPI)..."
    cd backend
    
    # Sprawdź czy środowisko wirtualne istnieje
    if [ ! -d "venv" ]; then
        echo "📦 Tworzenie środowiska wirtualnego..."
        python3 -m venv venv
    fi
    
    # Aktywuj środowisko wirtualne
    source venv/bin/activate
    
    # Instaluj wymagania jeśli nie są zainstalowane
    echo "📦 Instalowanie wymagań Python..."
    pip install -q -r requirements.txt
    
    # Utwórz katalogi jeśli nie istnieją
    mkdir -p ../data/{batched_output,temp}
    
    echo "🚀 Uruchamianie serwera FastAPI na porcie 8000..."
    echo "   API Docs: http://localhost:8000/docs"
    echo "   API Status: http://localhost:8000/status"
    echo ""
    
    # Uruchom serwer w tle
    python api.py &
    BACKEND_PID=$!
    cd ..
    
    # Sprawdź czy serwer się uruchomił
    sleep 3
    if curl -s http://localhost:8000/status > /dev/null; then
        echo "✅ Backend uruchomiony pomyślnie (PID: $BACKEND_PID)"
    else
        echo "❌ Błąd uruchamiania backendu"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
}

# Funkcja do uruchamiania frontendu
start_frontend() {
    echo "🔧 Uruchamianie Frontend (Angular)..."
    cd frontend
    
    # Sprawdź czy node_modules istnieją
    if [ ! -d "node_modules" ]; then
        echo "📦 Instalowanie pakietów npm..."
        npm install
    fi
    
    echo "🚀 Uruchamianie serwera Angular na porcie 4200..."
    echo "   Frontend: http://localhost:4200"
    echo ""
    
    # Uruchom serwer development w tle
    ng serve --host 0.0.0.0 &
    FRONTEND_PID=$!
    cd ..
    
    # Sprawdź czy serwer się uruchomił
    sleep 10
    if curl -s http://localhost:4200 > /dev/null; then
        echo "✅ Frontend uruchomiony pomyślnie (PID: $FRONTEND_PID)"
    else
        echo "❌ Błąd uruchamiania frontendu"
        kill $FRONTEND_PID 2>/dev/null
        exit 1
    fi
}

# Funkcja do zatrzymywania serwisów
stop_services() {
    echo ""
    echo "🛑 Zatrzymywanie serwisów..."
    
    # Zatrzymaj serwery na portach 8000 i 4200
    pkill -f "python api.py" 2>/dev/null
    pkill -f "ng serve" 2>/dev/null
    
    echo "✅ Serwisy zatrzymane"
    exit 0
}

# Obsługa sygnału CTRL+C
trap stop_services SIGINT SIGTERM

# Menu główne
case "${1:-menu}" in
    "backend")
        start_backend
        echo "Backend uruchomiony. Naciśnij CTRL+C aby zatrzymać."
        wait
        ;;
    
    "frontend")
        start_frontend
        echo "Frontend uruchomiony. Naciśnij CTRL+C aby zatrzymać."
        wait
        ;;
    
    "full"|"all")
        start_backend
        start_frontend
        
        echo "🎉 System Kożu Ofiarny uruchomiony pomyślnie!"
        echo ""
        echo "📍 Dostępne adresy:"
        echo "   🌐 Frontend:  http://localhost:4200"
        echo "   🔧 API:       http://localhost:8000"
        echo "   📚 API Docs:  http://localhost:8000/docs"
        echo ""
        echo "⌨️  Naciśnij CTRL+C aby zatrzymać wszystkie serwisy"
        
        # Czekaj na sygnał zatrzymania
        wait
        ;;
    
    "test")
        echo "🧪 Uruchamianie testów systemu..."
        
        # Test backendu
        start_backend
        
        echo "📊 Testowanie API..."
        sleep 2
        
        # Test generowania danych
        echo "  - Test generowania danych..."
        curl -s -X POST "http://localhost:8000/generate" \
             -H "Content-Type: application/json" \
             -d '{"rows": 1000, "columns": 20, "filename": "test.parquet"}' \
             | grep -q "success" && echo "    ✅ Generowanie OK" || echo "    ❌ Generowanie błąd"
        
        # Test statusu
        echo "  - Test statusu systemu..."
        curl -s "http://localhost:8000/status" | grep -q "online" && \
             echo "    ✅ Status OK" || echo "    ❌ Status błąd"
        
        # Test listowania plików
        echo "  - Test listowania plików..."
        curl -s "http://localhost:8000/files" | grep -q "original_files" && \
             echo "    ✅ Listowanie OK" || echo "    ❌ Listowanie błąd"
        
        echo "✅ Testy zakończone"
        stop_services
        ;;
    
    "stop")
        stop_services
        ;;
    
    "status")
        echo "📊 Status serwisów:"
        
        if curl -s http://localhost:8000/status > /dev/null 2>&1; then
            echo "  ✅ Backend (port 8000): DZIAŁA"
        else
            echo "  ❌ Backend (port 8000): ZATRZYMANY"
        fi
        
        if curl -s http://localhost:4200 > /dev/null 2>&1; then
            echo "  ✅ Frontend (port 4200): DZIAŁA"
        else
            echo "  ❌ Frontend (port 4200): ZATRZYMANY"
        fi
        ;;
    
    "clean")
        echo "🧹 Czyszczenie plików tymczasowych..."
        rm -rf data/temp/*
        rm -rf backend/venv/__pycache__
        rm -rf backend/__pycache__
        echo "✅ Pliki wyczyszczone"
        ;;
    
    "help"|"--help"|"-h")
        echo "🐐 Kożucha Ofiarny - Scapegoat System"
        echo ""
        echo "Użycie: $0 [opcja]"
        echo ""
        echo "Opcje:"
        echo "  backend     Uruchom tylko backend (FastAPI)"
        echo "  frontend    Uruchom tylko frontend (Angular)"
        echo "  full, all   Uruchom cały system (backend + frontend)"
        echo "  test        Uruchom testy API"
        echo "  status      Sprawdź status serwisów"
        echo "  stop        Zatrzymaj wszystkie serwisy"
        echo "  clean       Wyczyść pliki tymczasowe"
        echo "  help        Pokaż tę pomoc"
        echo ""
        echo "Przykłady:"
        echo "  $0 full          # Uruchom cały system"
        echo "  $0 backend       # Tylko API"
        echo "  $0 test          # Uruchom testy"
        echo ""
        ;;
    
    *)
        echo "🚀 Wybierz opcję uruchomienia:"
        echo ""
        echo "1. full    - Uruchom cały system (backend + frontend)"
        echo "2. backend - Uruchom tylko backend (FastAPI)"
        echo "3. frontend- Uruchom tylko frontend (Angular)"
        echo "4. test    - Uruchom testy API"
        echo "5. status  - Sprawdź status"
        echo "6. help    - Pokaż pomoc"
        echo ""
        read -p "Wybierz opcję (1-6) lub naciśnij Enter dla opcji 1: " choice
        
        case $choice in
            1|"") $0 full ;;
            2) $0 backend ;;
            3) $0 frontend ;;
            4) $0 test ;;
            5) $0 status ;;
            6) $0 help ;;
            *) echo "❌ Nieprawidłowa opcja"; exit 1 ;;
        esac
        ;;
esac
