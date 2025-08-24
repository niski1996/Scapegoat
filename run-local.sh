#!/bin/bash

echo "=== Uruchomienie systemu lokalnie (bez Docker) ==="

# Sprawdzenie czy Python i Node są dostępne
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nie jest zainstalowany!"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js nie jest zainstalowany!"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm nie jest zainstalowany!"
    exit 1
fi

echo "✅ Zależności systemowe dostępne"

# Instalacja zależności Python (jeśli potrzeba)
echo "📦 Sprawdzanie zależności Python..."
cd backend
if [ ! -d "venv" ]; then
    echo "Tworzenie środowiska wirtualnego..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "🚀 Uruchamianie backend na porcie 8000..."
python3 api.py &
BACKEND_PID=$!

# Przejdź do frontend
cd ../frontend

# Instalacja zależności Node (jeśli potrzeba)
echo "📦 Sprawdzanie zależności Node.js..."
if [ ! -d "node_modules" ]; then
    echo "Instalowanie zależności npm..."
    npm install
fi

echo "🌐 Uruchamianie frontend na porcie 4200..."
npm start &
FRONTEND_PID=$!

echo ""
echo "✅ System uruchomiony lokalnie!"
echo "🌐 Frontend: http://localhost:4200"
echo "🔗 Backend: http://localhost:8000"
echo "📚 Docs: http://localhost:8000/docs"
echo ""
echo "💡 Aby zatrzymać system, naciśnij Ctrl+C"

# Funkcja czyszczenia
cleanup() {
    echo ""
    echo "🛑 Zatrzymywanie systemu..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ System zatrzymany"
    exit
}

# Przechwycenie sygnałów
trap cleanup SIGTERM SIGINT

# Oczekiwanie
wait
