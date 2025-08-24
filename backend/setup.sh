#!/bin/bash

# Skrypt startowy dla backendu systemu Kożu Ofiarny

echo "=== Uruchamianie Backend Kożu Ofiarny ==="

# Sprawdź czy Python3 jest dostępny
if ! command -v python3 &> /dev/null; then
    echo "Błąd: Python3 nie jest zainstalowany"
    exit 1
fi

# Sprawdź czy pip jest dostępny
if ! command -v pip3 &> /dev/null; then
    echo "Błąd: pip3 nie jest zainstalowany"
    exit 1
fi

# Utwórz środowisko wirtualne jeśli nie istnieje
if [ ! -d "venv" ]; then
    echo "Tworzenie środowiska wirtualnego..."
    python3 -m venv venv
fi

# Aktywuj środowisko wirtualne
echo "Aktywacja środowiska wirtualnego..."
source venv/bin/activate

# Instaluj wymagania
echo "Instalacja wymagań..."
pip install -r requirements.txt

# Utwórz katalogi jeśli nie istnieją
mkdir -p ../data/batched_output
mkdir -p ../data/temp

echo "Wszystko gotowe!"
echo ""
echo "Dostępne komendy:"
echo "1. Uruchomienie serwera API:"
echo "   python api.py"
echo ""
echo "2. Test generatora danych:"
echo "   python data_generator.py"
echo ""
echo "3. Test transformatora:"
echo "   python transformer.py"
echo ""
echo "4. Dokumentacja API (po uruchomieniu serwera):"
echo "   http://localhost:8000/docs"
