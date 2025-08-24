#!/bin/bash

echo "=== Startowanie systemu Kożu Ofiarny ==="

# Uruchomienie serwera FastAPI w tle
echo "Uruchamianie serwera FastAPI na porcie 8000..."
cd /app/backend
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Oczekiwanie na uruchomienie backend
echo "Oczekiwanie na backend..."
sleep 5

# Sprawdzenie czy backend działa
until curl -f http://localhost:8000/status > /dev/null 2>&1; do
    echo "Oczekiwanie na backend..."
    sleep 2
done

echo "✅ Backend uruchomiony pomyślnie!"

# Uruchomienie serwera Angular
echo "Uruchamianie serwera Angular na porcie 4200..."
cd /app/frontend
npm start &
FRONTEND_PID=$!

echo "✅ Frontend uruchomiony pomyślnie!"

echo ""
echo "=== System gotowy ==="
echo "🌐 Frontend: http://localhost:4200"
echo "🔗 Backend API: http://localhost:8000"
echo "📚 Swagger Docs: http://localhost:8000/docs"
echo ""

# Funkcja czyszczenia przy wyjściu
cleanup() {
    echo "Zatrzymywanie systemu..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Przechwycenie sygnałów
trap cleanup SIGTERM SIGINT

# Oczekiwanie na sygnał zatrzymania
wait
