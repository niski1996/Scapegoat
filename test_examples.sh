#!/bin/bash

# Przykładowe testy dla systemu Kożu Ofiarny

echo "🧪 Przykłady testowe dla systemu Kożu Ofiarny"
echo "=============================================="

# Sprawdź czy backend działa
check_backend() {
    if curl -s http://localhost:8000/status > /dev/null; then
        echo "✅ Backend działa"
        return 0
    else
        echo "❌ Backend nie działa. Uruchom najpierw: ./start.sh backend"
        return 1
    fi
}

# Test 1: Generowanie małego pliku testowego
test_generate_small() {
    echo "📊 Test 1: Generowanie małego pliku (1000 wierszy, 20 kolumn)..."
    
    response=$(curl -s -X POST "http://localhost:8000/generate" \
        -H "Content-Type: application/json" \
        -d '{"rows": 1000, "columns": 20, "filename": "small_test.parquet"}')
    
    if echo "$response" | grep -q "success"; then
        echo "  ✅ Wygenerowano mały plik testowy"
        echo "$response" | jq '.file_info.num_rows' 2>/dev/null || echo "  Rows: $(echo "$response" | grep -o '"num_rows":[0-9]*' | cut -d: -f2)"
    else
        echo "  ❌ Błąd generowania: $response"
    fi
}

# Test 2: Generowanie średniego pliku
test_generate_medium() {
    echo "📊 Test 2: Generowanie średniego pliku (50,000 wierszy, 100 kolumn)..."
    
    response=$(curl -s -X POST "http://localhost:8000/generate" \
        -H "Content-Type: application/json" \
        -d '{"rows": 50000, "columns": 100, "filename": "medium_test.parquet"}')
    
    if echo "$response" | grep -q "success"; then
        echo "  ✅ Wygenerowano średni plik testowy"
        echo "$response" | jq '.file_info.file_size_mb' 2>/dev/null || echo "  Size: $(echo "$response" | grep -o '"file_size_mb":[0-9.]*' | cut -d: -f2) MB"
    else
        echo "  ❌ Błąd generowania: $response"
    fi
}

# Test 3: Transformacja danych
test_transform() {
    echo "🔄 Test 3: Transformacja danych (pivotowanie + batchowanie)..."
    
    response=$(curl -s -X POST "http://localhost:8000/transform" \
        -H "Content-Type: application/json" \
        -d '{"input_filename": "small_test.parquet", "batch_size": 500}')
    
    if echo "$response" | grep -q "success"; then
        echo "  ✅ Transformacja zakończona pomyślnie"
        echo "$response" | jq '.batch_count' 2>/dev/null || echo "  Batches: $(echo "$response" | grep -o '"batch_count":[0-9]*' | cut -d: -f2)"
    else
        echo "  ❌ Błąd transformacji: $response"
    fi
}

# Test 4: Pobieranie listy plików
test_list_files() {
    echo "📋 Test 4: Lista dostępnych plików..."
    
    response=$(curl -s "http://localhost:8000/files")
    
    if echo "$response" | grep -q "original_files"; then
        echo "  ✅ Lista plików pobrana"
        file_count=$(echo "$response" | jq '.original_files | length' 2>/dev/null || echo "N/A")
        batch_count=$(echo "$response" | jq '.batch_directories | length' 2>/dev/null || echo "N/A")
        echo "  Pliki oryginalne: $file_count"
        echo "  Katalogi batchów: $batch_count"
    else
        echo "  ❌ Błąd pobierania listy: $response"
    fi
}

# Test 5: Status systemu
test_status() {
    echo "📈 Test 5: Status systemu..."
    
    response=$(curl -s "http://localhost:8000/status")
    
    if echo "$response" | grep -q "online"; then
        echo "  ✅ System online"
        total_size=$(echo "$response" | jq '.statistics.total_size_mb' 2>/dev/null || echo "N/A")
        echo "  Rozmiar danych: $total_size MB"
    else
        echo "  ❌ Błąd statusu: $response"
    fi
}

# Test 6: Pobieranie danych (symulacja)
test_download() {
    echo "📥 Test 6: Test URL pobierania..."
    
    # Test URL dla CSV
    csv_url="http://localhost:8000/download?format=csv&pivoted=false&filename=small_test.parquet"
    if curl -s -I "$csv_url" | grep -q "200 OK"; then
        echo "  ✅ URL pobierania CSV działa"
    else
        echo "  ❌ URL pobierania CSV nie działa"
    fi
    
    # Test URL dla Parquet
    parquet_url="http://localhost:8000/download?format=parquet&pivoted=true"
    if curl -s -I "$parquet_url" | grep -q "200 OK"; then
        echo "  ✅ URL pobierania Parquet działa"
    else
        echo "  ❌ URL pobierania Parquet nie działa"
    fi
}

# Test wydajności
test_performance() {
    echo "⚡ Test 7: Test wydajności - generowanie większego pliku..."
    
    start_time=$(date +%s)
    
    response=$(curl -s -X POST "http://localhost:8000/generate" \
        -H "Content-Type: application/json" \
        -d '{"rows": 100000, "columns": 150, "filename": "performance_test.parquet"}')
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if echo "$response" | grep -q "success"; then
        echo "  ✅ Wygenerowano w $duration sekund"
        file_size=$(echo "$response" | jq '.file_info.file_size_mb' 2>/dev/null || echo "N/A")
        echo "  Rozmiar pliku: $file_size MB"
    else
        echo "  ❌ Błąd generowania: $response"
    fi
}

# Funkcja czyszczenia po testach
cleanup_tests() {
    echo "🧹 Czyszczenie plików testowych..."
    curl -s -X DELETE "http://localhost:8000/cleanup" > /dev/null
    echo "  ✅ Pliki tymczasowe wyczyszczone"
}

# Menu główne
case "${1:-all}" in
    "1"|"generate-small")
        check_backend && test_generate_small
        ;;
    
    "2"|"generate-medium") 
        check_backend && test_generate_medium
        ;;
    
    "3"|"transform")
        check_backend && test_transform
        ;;
    
    "4"|"list")
        check_backend && test_list_files
        ;;
    
    "5"|"status")
        check_backend && test_status
        ;;
    
    "6"|"download")
        check_backend && test_download
        ;;
    
    "7"|"performance")
        check_backend && test_performance
        ;;
    
    "cleanup"|"clean")
        check_backend && cleanup_tests
        ;;
    
    "all"|"full")
        echo "🚀 Uruchamianie wszystkich testów..."
        echo ""
        
        if ! check_backend; then
            exit 1
        fi
        
        test_generate_small
        echo ""
        test_generate_medium  
        echo ""
        test_transform
        echo ""
        test_list_files
        echo ""
        test_status
        echo ""
        test_download
        echo ""
        test_performance
        echo ""
        cleanup_tests
        
        echo ""
        echo "🎉 Wszystkie testy zakończone!"
        ;;
    
    "help"|"--help"|"-h")
        echo "🧪 Skrypt testowy dla systemu Kożu Ofiarny"
        echo ""
        echo "Użycie: $0 [test]"
        echo ""
        echo "Dostępne testy:"
        echo "  1, generate-small   Generowanie małego pliku (1K wierszy)"
        echo "  2, generate-medium  Generowanie średniego pliku (50K wierszy)"
        echo "  3, transform        Transformacja i batchowanie"
        echo "  4, list             Lista dostępnych plików"
        echo "  5, status           Status systemu"
        echo "  6, download         Test URL pobierania"
        echo "  7, performance      Test wydajności (100K wierszy)"
        echo "  cleanup, clean      Czyszczenie plików testowych"
        echo "  all, full           Wszystkie testy"
        echo ""
        echo "Przykłady:"
        echo "  $0 all              # Wszystkie testy"
        echo "  $0 1                # Tylko test generowania małego pliku"
        echo "  $0 performance      # Test wydajności"
        echo ""
        echo "Uwaga: Backend musi być uruchomiony przed testami!"
        echo "       Uruchom: ./start.sh backend"
        ;;
    
    *)
        echo "❌ Nieznany test: $1"
        echo "Użyj: $0 help aby zobaczyć dostępne opcje"
        exit 1
        ;;
esac
