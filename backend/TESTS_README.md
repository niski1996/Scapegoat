# 🔬 Testy Systemu Kożu Ofiarny

Kompleksowy zestaw testów dla systemu obejmujący testy jednostkowe, integracyjne i wydajności.

## 📋 Przegląd Testów

### 1. Testy Jednostkowe (`test_units.py`)
- **TestDataGenerator**: Testuje generowanie plików Parquet
- **TestTransformer**: Testuje pivotowanie i batchowanie danych
- **TestAPIComponents**: Testuje komponenty API
- **TestErrorHandling**: Testuje obsługę błędów
- **TestPerformance**: Testuje wydajność podstawowych operacji

### 2. Testy Integracyjne (`test_api_integration.py`)
- **Kompletny flow**: Generowanie → Transformacja → Download
- **API endpoints**: Wszystkie endpointy REST API
- **Formaty plików**: CSV, ZIP, Parquet
- **Obsługa błędów**: Nieprawidłowe żądania i parametry

### 3. Runner Testów (`run_tests.py`)
- Automatyczna instalacja zależności
- Uruchamianie serwera API dla testów integracyjnych
- Testy wydajności
- Generowanie raportów

## 🚀 Uruchamianie Testów

### Szybkie uruchomienie wszystkich testów:
```bash
cd backend
python run_tests.py
```

### Uruchamianie poszczególnych typów testów:

#### Tylko testy jednostkowe:
```bash
python test_units.py
```

#### Tylko testy integracyjne (wymaga uruchomionego API):
```bash
# Terminal 1 - uruchom API
python api.py

# Terminal 2 - uruchom testy
python test_api_integration.py
```

#### Przy użyciu pytest:
```bash
# Zainstaluj zależności testowe
pip install -r requirements-test.txt

# Uruchom wszystkie testy
pytest test_*.py -v

# Uruchom z coverage
pytest test_*.py --cov=. --cov-report=html
```

## 📊 Scenariusze Testowe

### Test 1: Podstawowe generowanie danych
✅ Sprawdza czy `generate_parquet()` tworzy poprawny plik  
✅ Weryfikuje typy kolumn (30% int, 30% float, 30% string, 10% datetime)  
✅ Sprawdza rozmiar i strukturę pliku  

### Test 2: Transformacja Parquet → Batche
✅ Testuje `pivot_and_batch()` z różnymi rozmiarami  
✅ Sprawdza tworzenie manifesto JSON  
✅ Weryfikuje integralność danych po podziale  

### Test 3: API - Endpoint `/generate`
```bash
POST /generate
{
  "rows": 1000,
  "columns": 20,
  "filename": "test_data"
}
```
✅ Zwraca informacje o pliku  
✅ Tworzy plik w katalogu `data/`  
✅ Obsługuje błędy (ujemne wartości, brak parametrów)  

### Test 4: API - Endpoint `/transform`
```bash
POST /transform
{
  "input_filename": "test_data.parquet",
  "batch_size": 250
}
```
✅ Tworzy katalog batchów  
✅ Dzieli dane na równe części  
✅ Generuje manifest JSON  

### Test 5: API - Endpoint `/download`
```bash
GET /download?format=csv&filename=test_data.parquet
```
✅ Streaming CSV z nagłówkami  
✅ Proper Content-Type i Content-Disposition  
✅ Poprawne kodowanie UTF-8  

### Test 6: API - Download ZIP z batchów
```bash
GET /download?format=zip&pivoted=true&batch_dir=test_data_batches
```
✅ Archiwum ZIP z plikami Parquet  
✅ Wszystkie batche w archiwum  
✅ Poprawna struktura ZIP  

### Test 7: Kompletny flow integracyjny
1. **Generate**: 2000 wierszy, 30 kolumn → `integration_test.parquet`
2. **Status**: Sprawdź statystyki systemu
3. **Transform**: Batch size 500 → 4 batche
4. **Files**: Lista plików i batchów
5. **Download CSV**: Z oryginalnego pliku
6. **Download ZIP**: Z katalogu batchów
7. **Verify**: Sprawdź integralność danych

## 🎯 Kryteria Sukcesu

### Testy Jednostkowe (test_units.py)
- [x] Generowanie plików z poprawnymi typami danych
- [x] Transformacja zachowuje liczbę wierszy
- [x] Walidacja parametrów wejściowych
- [x] Obsługa błędów (FileNotFoundError, ValueError)
- [x] Performance test: 50k wierszy < 30s

### Testy Integracyjne (test_api_integration.py)
- [x] Wszystkie endpointy zwracają status 200
- [x] Generowane pliki mają oczekiwany format
- [x] CSV download zawiera poprawne dane
- [x] ZIP download zawiera wszystkie batche
- [x] Error handling (400 dla nieprawidłowych parametrów)
- [x] Kompletny flow: Generate → Transform → Download

### Testy Wydajności
- [x] Generowanie 100k wierszy < 60s
- [x] Transformacja 50k wierszy < 30s
- [x] API response time < 2s dla podstawowych operacji

## 📈 Przykładowe Wyjście

```
🔬 SYSTEM TESTOWY KOŻU OFIARNY
===============================================================

=== Test 3: Generate Parquet Flow ===
✅ Wygenerowano plik: test_integration.parquet
   Wiersze: 1000
   Kolumny: 20
   Rozmiar: 0.85 MB
   Kolumny numeryczne: 12
   Kolumny tekstowe: 6
   Kolumny datetime: 2

=== Test 4: Transform to Batches ===
✅ Transformacja zakończona:
   Katalog batchów: test_integration_batches
   Liczba batchów: 4
   Łączne wiersze: 1000
   Pliki batchów: 4
   Manifest: OK

=== Test 9: Complete Integration Flow ===
✅ Kompletny flow zakończony pomyślnie:
   Wygenerowano plik: integration_test.parquet
   Utworzono batche: 4
   CSV: 2001 linii
   ZIP: 245678 bajtów
   Status finalny: 2.34 MB

===============================================================
PODSUMOWANIE KOŃCOWE
===============================================================
Czas wykonania: 45.7 sekund
Testy jednostkowe: ✅ PASS
Testy integracyjne: ✅ PASS  
Testy wydajności: ✅ PASS
Status ogólny: ✅ PASS

🎉 Wszystkie testy przeszły pomyślnie!
System Kożu Ofiarny gotowy do użycia.
```

## 🛠️ Konfiguracja

### Zmienne środowiskowe:
```bash
export DATA_DIR="/custom/data/path"  # Opcjonalny katalog danych
```

### Pliki tymczasowe:
- Testy używają `tempfile.mkdtemp()` 
- Automatyczne czyszczenie po testach
- Brak konfliktów między równoległymi testami

### Timeouty:
- Testy jednostkowe: 5 minut
- Testy integracyjne: 10 minut
- Startup API: 3 sekundy

## 🔧 Debugowanie

### Logi szczegółowe:
```bash
python run_tests.py --verbose
```

### Test pojedynczego komponentu:
```bash
python -m unittest test_units.TestDataGenerator.test_generate_parquet_basic -v
```

### Sprawdzenie pokrycia kodu:
```bash
coverage run --source=. -m pytest test_*.py
coverage report -m
coverage html  # Raport HTML w htmlcov/
```

## 📋 Lista kontrolna przed deployment

- [ ] Wszystkie testy jednostkowe przechodzą
- [ ] Wszystkie testy integracyjne przechodzą  
- [ ] Testy wydajności w akceptowalnych granicach
- [ ] API odpowiada na wszystkie endpointy
- [ ] Generowane pliki mają poprawny format
- [ ] Obsługa błędów działa prawidłowo
- [ ] System jest gotowy do produkcji

---

*Automatyczne testy zapewniają jakość i niezawodność systemu Kożu Ofiarny* 🎯
