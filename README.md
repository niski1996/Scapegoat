# 🐐 Kożucha Ofiarny - Scapegoat System

Kompletny prototyp systemu do generowania, transformacji i pobierania danych Parquet z pivotowaniem i batchowaniem.

## 📋 Spis treści

- [🚀 Szybki start z Docker](#szybki-start-z-docker)
- [Opis systemu](#opis-systemu)
- [Architektura](#architektura)
- [Instalacja i uruchomienie](#instalacja-i-uruchomienie)
- [Funkcjonalności](#funkcjonalności)
- [API Documentation](#api-documentation)
- [Frontend](#frontend)
- [Profilowanie i logowanie](#profilowanie-i-logowanie)
- [Struktura projektu](#struktura-projektu)

## 🚀 Szybki start z Docker

### Wymagania
- Docker
- Docker Compose

### Uruchomienie systemu

```bash
# Uruchom skrypt automatyczny
./run-docker.sh

# Lub manualnie:
docker-compose up -d
```

### Dostępne adresy po uruchomieniu
- **Frontend Angular**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Docker Commands

```bash
# Budowanie
docker-compose build

# Uruchomienie w tle
docker-compose up -d

# Sprawdzenie statusu
docker-compose ps

# Logi w czasie rzeczywistym
docker-compose logs -f

# Restart systemu
docker-compose restart

# Zatrzymanie
docker-compose down

# Pełne czyszczenie (usuwa kontenery, wolumeny, obrazy)
docker-compose down -v --rmi all
```

## 📖 Opis systemu

System "Kożucha Ofiarny" (Scapegoat) to prototyp narzędzia do:

1. **Generowania danych testowych** - tworzenie plików Parquet z losowymi danymi według zahardkodowanego schematu
2. **Transformacji danych** - pivotowanie danych i podział na batchy row groups
3. **Pobierania danych** - streamowane CSV i batchy Parquet zgodne ze standardem
4. **Monitorowania** - wbudowane logowanie i profilowanie czasu każdej operacji

## 🏗️ Architektura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Frontend       │────│  Backend        │────│  Data Storage   │
│  (Angular)      │    │  (FastAPI)      │    │  (Parquet)      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                         │                         │
   ┌───▼───┐                ┌────▼────┐               ┌────▼────┐
   │ UI    │                │ API     │               │ Files   │
   │ Forms │                │ Routes  │               │ Batches │
   │ Status│                │ Logic   │               │ Temp    │
   └───────┘                └─────────┘               └─────────┘
```

### Komponenty:

- **Backend** (Python + FastAPI)
  - `data_generator.py` - generator danych testowych
  - `transformer.py` - transformacja i pivotowanie
  - `api.py` - endpoints REST API
  
- **Frontend** (Angular)
  - Interfejs użytkownika
  - Formularze operacji
  - Monitoring systemu
  
- **Data Storage**
  - Pliki oryginalne Parquet
  - Batche po transformacji
  - Pliki tymczasowe

## 🚀 Instalacja i uruchomienie

### Wymagania

- Python 3.8+
- Node.js 16+
- npm 8+

### Backend

```bash
cd backend

# Uruchomienie skryptu setup
chmod +x setup.sh
./setup.sh

# Lub manualnie:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Uruchomienie serwera
python api.py
```

Serwer będzie dostępny na: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend

# Instalacja zależności
npm install

# Uruchomienie development server
ng serve

# Lub build produkcyjny
ng build --prod
```

Frontend będzie dostępny na: `http://localhost:4200`

## ⚡ Funkcjonalności

### 1. Generowanie danych (`data_generator.py`)

```python
# Przykład użycia
from data_generator import generate_parquet

# Generowanie 100,000 wierszy x 100 kolumn
file_path = generate_parquet(
    rows=100000,
    columns=100,
    output_path="data/generated_data.parquet"
)
```

**Schemat kolumn (zahardkodowany):**
- 30% kolumn `int` (ID, liczniki, kategorie)
- 30% kolumn `float` (wartości liczbowe, procenty)
- 30% kolumn `string` (nazwy, opisy, kody - max 50 znaków)
- 10% kolumn `datetime` (daty, znaczniki czasu)

**Profilowanie:**
- Dekorator `@log_time` dla funkcji
- Context manager `TimeProfiler` dla bloków kodu
- Logowanie czasu każdej operacji

### 2. Transformacja (`transformer.py`)

```python
# Przykład użycia
from transformer import pivot_and_batch

# Pivotowanie i batchowanie
batch_files = pivot_and_batch(
    input_path="data/input.parquet",
    batch_size=50000,
    output_dir="data/batched_output"
)
```

**Proces transformacji:**
1. Ładowanie danych z pliku Parquet
2. Automatyczne wykrywanie kolumn do pivotu
3. Pivotowanie z agregacją (suma, średnia, liczba)
4. Podział na batche o określonym rozmiarze
5. Zapis każdego batchu jako osobny plik Parquet
6. Utworzenie manifestu z metadanymi

### 3. Backend API (`api.py`)

#### Endpointy:

| Endpoint | Metoda | Opis |
|----------|---------|------|
| `/` | GET | Informacje o API |
| `/generate` | POST | Generowanie danych |
| `/transform` | POST | Pivotowanie i batchowanie |
| `/download` | GET | Pobieranie danych |
| `/files` | GET | Lista dostępnych plików |
| `/status` | GET | Status systemu |
| `/cleanup` | DELETE | Czyszczenie plików tymczasowych |

#### Przykłady requestów:

```bash
# Generowanie danych
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"rows": 10000, "columns": 50, "filename": "test.parquet"}'

# Transformacja
curl -X POST "http://localhost:8000/transform" \
  -H "Content-Type: application/json" \
  -d '{"input_filename": "test.parquet", "batch_size": 5000}'

# Pobieranie CSV (streamowane)
curl "http://localhost:8000/download?format=csv&pivoted=false&filename=test.parquet"

# Pobieranie Parquet (ZIP z batchami)
curl "http://localhost:8000/download?format=parquet&pivoted=true"
```

### 4. Pobieranie danych

#### CSV (streamowane):
- Wiersz po wierszu do klienta
- `StreamingResponse` z chunkami
- Optymalizacja pamięci dla dużych plików

#### Parquet (batchy):
- ZIP z gotowymi plikami batchów
- Zgodność ze standardem Parquet
- Metadane i manifest w ZIP

### 5. Frontend (Angular)

#### Funkcjonalności UI:
- **Generowanie**: formularz z parametrami (wiersze, kolumny, nazwa)
- **Transformacja**: wybór pliku źródłowego i rozmiaru batchu
- **Pobieranie**: wybór formatu i typu danych (oryginalne/pivotowane)
- **Status**: monitoring systemu w czasie rzeczywistym
- **Logi**: historia operacji z kolorowym oznaczeniem

#### Komponenty:
- Responsywny design
- Walidacja formularzy
- Animacje ładowania
- Obsługa błędów
- Progress indicators

## 📊 Profilowanie i logowanie

### Narzędzia profilowania:

1. **Dekorator `@log_time`:**
```python
@log_time
def my_function():
    # Automatyczne logowanie czasu wykonania
    pass
```

2. **Context manager `TimeProfiler`:**
```python
with TimeProfiler("Nazwa operacji"):
    # Kod do profilowania
    pass
```

3. **Logowanie API:**
- Czas generacji danych
- Czas pivotowania
- Czas transferu plików
- Błędy i wyjątki

### Integracja z zewnętrznymi narzędziami:

Kod jest przygotowany do podpięcia pod:
- `cProfile`
- `pyinstrument`
- `line_profiler`
- Monitoring APM (New Relic, DataDog)

## 🗂️ Struktura projektu

```
Scapegoat/
├── backend/
│   ├── data_generator.py      # Generator danych testowych
│   ├── transformer.py         # Transformacja i pivotowanie  
│   ├── api.py                # FastAPI backend
│   ├── requirements.txt       # Zależności Python
│   └── setup.sh              # Skrypt instalacyjny
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.component.ts    # Główny komponent
│   │   │   ├── app.component.html  # Template UI
│   │   │   ├── app.component.css   # Style komponentu
│   │   │   └── app.config.ts       # Konfiguracja
│   │   ├── styles.css              # Globalne style
│   │   └── index.html              # Główny HTML
│   ├── package.json                # Zależności Node.js
│   └── angular.json                # Konfiguracja Angular
├── data/                           # Katalog danych
│   ├── batched_output/            # Batche po transformacji
│   └── temp/                      # Pliki tymczasowe
└── README.md                      # Ta dokumentacja
```

## 🛠️ Rozwój i rozszerzenia

### Możliwe rozszerzenia:

1. **Skalowanie:**
   - Celery dla asynchronicznych zadań
   - Redis/PostgreSQL jako backend
   - Docker containerization

2. **Monitoring:**
   - Prometheus + Grafana
   - Health checks
   - Metryki biznesowe

3. **Bezpieczeństwo:**
   - Autoryzacja JWT
   - Rate limiting
   - Input validation

4. **Optymalizacja:**
   - Caching z Redis
   - Compression algorytmy
   - Parallel processing

## 📝 Przykłady użycia

### Scenariusz 1: Generowanie danych testowych

1. Otwórz frontend (`http://localhost:4200`)
2. W sekcji "Generowanie danych":
   - Ustaw liczbę wierszy: `100000`
   - Ustaw liczbę kolumn: `100`
   - Kliknij "Generuj dane"
3. Poczekaj na wygenerowanie (logowanie w czasie rzeczywistym)

### Scenariusz 2: Pełny workflow

1. **Generuj dane:** 1M wierszy, 200 kolumn
2. **Transformuj:** batch size 50K
3. **Pobierz CSV:** streamowane dane pivotowane
4. **Pobierz Parquet:** ZIP z batchami

### Scenariusz 3: Monitoring wydajności

1. Sprawdź status systemu
2. Analizuj logi operacji
3. Monitoruj rozmiar plików
4. Czyść pliki tymczasowe

## 🐛 Debugging

### Typowe problemy:

1. **Backend nie startuje:**
   ```bash
   # Sprawdź czy port 8000 jest wolny
   lsof -i :8000
   
   # Sprawdź logi
   python api.py
   ```

2. **Frontend nie łączy się z API:**
   - Sprawdź CORS w `api.py`
   - Upewnij się że backend działa na porcie 8000

3. **Błędy generowania danych:**
   - Sprawdź dostępną pamięć RAM
   - Zmniejsz liczbę wierszy/kolumn

## 📄 Licencja

Projekt prototypowy - do celów edukacyjnych i testowych.

## 👥 Autorzy

Wygenerowane przez GitHub Copilot dla demonstracji systemu Kożucha Ofiarny.

---

**Uwaga:** To jest prototyp systemu. W środowisku produkcyjnym wymagane są dodatkowe optymalizacje, bezpieczeństwo i monitoring.
