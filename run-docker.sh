#!/bin/bash

echo "=== Budowanie i uruchamianie systemu Kożu Ofiarny ==="

# Sprawdzenie czy Docker jest zainstalowany
if ! command -v docker &> /dev/null; then
    echo "❌ Docker nie jest zainstalowany!"
    echo "Zainstaluj Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Sprawdzenie czy Docker Compose jest zainstalowany
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose nie jest zainstalowany!"
    echo "Zainstaluj Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Utworzenie katalogów danych
echo "📁 Tworzenie katalogów danych..."
mkdir -p data/temp data/batched_output logs

# Budowanie i uruchamianie
echo "🔨 Budowanie obrazu Docker..."
docker-compose build

echo "🚀 Uruchamianie systemu..."
docker-compose up -d

echo ""
echo "✅ System uruchomiony pomyślnie!"
echo ""
echo "=== Dostępne adresy ==="
echo "🌐 Frontend Angular: http://localhost:4200"
echo "🔗 Backend API: http://localhost:8000"
echo "📚 Swagger Docs: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo ""

# Sprawdzenie statusu
echo "🔍 Sprawdzanie statusu kontenerów..."
docker-compose ps

echo ""
echo "=== Przydatne komendy ==="
echo "📊 Sprawdź logi:        docker-compose logs -f"
echo "🔄 Restart systemu:     docker-compose restart"
echo "🛑 Zatrzymaj system:    docker-compose down"
echo "🗑️  Usuń wszystko:      docker-compose down -v --rmi all"
