"""
Testy integracyjne dla API systemu Kożu Ofiarny.
Sprawdzają kompletny flow: generowanie Parquet -> transformacja -> eksport CSV.
"""

import unittest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from fastapi.testclient import TestClient
import json
import zipfile
import io

# Import aplikacji
import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from api import app
    from data_generator import generate_parquet, get_parquet_info
    from transformer import pivot_and_batch, get_batch_info
except ImportError as e:
    print(f"Błąd importu: {e}")
    print("Upewnij się, że jesteś w katalogu backend/")
    sys.exit(1)


class TestAPIIntegration(unittest.TestCase):
    """
    Testy integracyjne dla całego flow API.
    """
    
    @classmethod
    def setUpClass(cls):
        """Konfiguracja przed wszystkimi testami."""
        cls.client = TestClient(app)
        
        # Utwórz tymczasowe katalogi dla testów
        cls.test_dir = tempfile.mkdtemp(prefix="scapegoat_test_")
        cls.data_dir = Path(cls.test_dir) / "data"
        cls.data_dir.mkdir()
        
        # Ustaw zmienne środowiskowe dla testów
        os.environ['DATA_DIR'] = str(cls.data_dir)
        
        print(f"Katalog testowy: {cls.test_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """Czyszczenie po wszystkich testach."""
        if Path(cls.test_dir).exists():
            shutil.rmtree(cls.test_dir)
        print(f"Usunięto katalog testowy: {cls.test_dir}")
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        # Wyczyść katalog danych
        for item in self.data_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    def test_01_health_check(self):
        """Test 1: Sprawdzenie zdrowia API."""
        print("\n=== Test 1: Health Check ===")
        
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("Kożu Ofiarny", data["message"])
        print(f"✅ API odpowiada: {data['message']}")
    
    def test_02_status_endpoint(self):
        """Test 2: Endpoint statusu systemu."""
        print("\n=== Test 2: Status Endpoint ===")
        
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("statistics", data)
        
        stats = data["statistics"]
        self.assertIn("original_files_count", stats)
        self.assertIn("total_size_mb", stats)
        print(f"✅ Status: {data['status']}")
        print(f"   Pliki oryginalne: {stats['original_files_count']}")
    
    def test_03_generate_parquet_flow(self):
        """Test 3: Kompletny flow generowania danych Parquet."""
        print("\n=== Test 3: Generate Parquet Flow ===")
        
        # Dane wejściowe
        request_data = {
            "rows": 1000,
            "columns": 20,
            "filename": "test_integration"
        }
        
        # Wywołanie API
        response = self.client.post("/generate", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("filename", data)
        self.assertIn("file_info", data)
        
        filename = data["filename"]
        file_info = data["file_info"]
        
        print(f"✅ Wygenerowano plik: {filename}")
        print(f"   Wiersze: {file_info['num_rows']}")
        print(f"   Kolumny: {file_info['num_columns']}")
        print(f"   Rozmiar: {file_info['file_size_mb']:.2f} MB")
        
        # Sprawdź czy plik istnieje
        file_path = self.data_dir / filename
        self.assertTrue(file_path.exists())
        
        # Sprawdź zawartość pliku
        df = pd.read_parquet(file_path)
        self.assertEqual(len(df), 1000)
        self.assertEqual(len(df.columns), 20)
        
        # Sprawdź typy kolumn (30% int, 30% float, 30% string, 10% datetime)
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        string_cols = df.select_dtypes(include=['object']).columns
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        
        self.assertGreaterEqual(len(numeric_cols), 10)  # Przynajmniej 60% to numeryczne
        self.assertGreaterEqual(len(string_cols), 4)    # Około 30% to stringi
        self.assertGreaterEqual(len(datetime_cols), 1)  # Około 10% to datetime
        
        print(f"   Kolumny numeryczne: {len(numeric_cols)}")
        print(f"   Kolumny tekstowe: {len(string_cols)}")
        print(f"   Kolumny datetime: {len(datetime_cols)}")
        
        return filename
    
    def test_04_transform_parquet_to_batches(self):
        """Test 4: Transformacja Parquet do batchów."""
        print("\n=== Test 4: Transform to Batches ===")
        
        # Najpierw wygeneruj dane
        filename = self.test_03_generate_parquet_flow()
        
        # Dane transformacji
        transform_data = {
            "input_filename": filename,
            "batch_size": 250  # 4 batche dla 1000 wierszy
        }
        
        # Wywołanie API transformacji
        response = self.client.post("/transform", json=transform_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("batch_directory", data)
        self.assertIn("batch_count", data)
        self.assertIn("total_rows", data)
        
        batch_dir = data["batch_directory"]
        batch_count = data["batch_count"]
        
        print(f"✅ Transformacja zakończona:")
        print(f"   Katalog batchów: {batch_dir}")
        print(f"   Liczba batchów: {batch_count}")
        print(f"   Łączne wiersze: {data['total_rows']}")
        
        # Sprawdź czy katalog batchów istnieje
        batch_path = self.data_dir / batch_dir
        self.assertTrue(batch_path.exists())
        
        # Sprawdź pliki batchów
        batch_files = list(batch_path.glob("batch_*.parquet"))
        self.assertEqual(len(batch_files), batch_count)
        
        # Sprawdź manifest
        manifest_path = batch_path / "batch_manifest.json"
        self.assertTrue(manifest_path.exists())
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            self.assertEqual(manifest["total_batches"], batch_count)
            self.assertEqual(manifest["batch_size"], 250)
        
        print(f"   Pliki batchów: {len(batch_files)}")
        print(f"   Manifest: OK")
        
        return batch_dir
    
    def test_05_download_csv_from_original(self):
        """Test 5: Download CSV z oryginalnego pliku Parquet."""
        print("\n=== Test 5: Download CSV from Original ===")
        
        # Wygeneruj dane
        filename = self.test_03_generate_parquet_flow()
        
        # Pobierz CSV
        params = {
            "format": "csv",
            "pivoted": "false",
            "filename": filename
        }
        
        response = self.client.get("/download", params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/csv; charset=utf-8")
        
        # Sprawdź nagłówek Content-Disposition
        content_disp = response.headers.get("content-disposition", "")
        self.assertIn("attachment", content_disp)
        self.assertIn(".csv", content_disp)
        
        # Sprawdź zawartość CSV
        csv_content = response.content.decode('utf-8')
        lines = csv_content.strip().split('\n')
        
        # Pierwsza linia to nagłówki
        headers = lines[0].split(',')
        self.assertEqual(len(headers), 20)  # 20 kolumn
        
        # Pozostałe linie to dane
        data_lines = lines[1:]
        self.assertEqual(len(data_lines), 1000)  # 1000 wierszy
        
        print(f"✅ CSV wygenerowany poprawnie:")
        print(f"   Nagłówki: {len(headers)} kolumn")
        print(f"   Dane: {len(data_lines)} wierszy")
        print(f"   Rozmiar: {len(csv_content)} znaków")
    
    def test_06_download_zip_from_batches(self):
        """Test 6: Download ZIP z batchów Parquet."""
        print("\n=== Test 6: Download ZIP from Batches ===")
        
        # Wygeneruj i przekształć dane
        batch_dir = self.test_04_transform_parquet_to_batches()
        
        # Pobierz ZIP
        params = {
            "format": "zip",
            "pivoted": "true",
            "batch_dir": batch_dir
        }
        
        response = self.client.get("/download", params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        
        # Sprawdź nagłówek Content-Disposition
        content_disp = response.headers.get("content-disposition", "")
        self.assertIn("attachment", content_disp)
        self.assertIn(".zip", content_disp)
        
        # Sprawdź zawartość ZIP
        zip_content = io.BytesIO(response.content)
        
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Powinny być pliki batch_XXXX.parquet
            parquet_files = [f for f in file_list if f.endswith('.parquet')]
            self.assertGreater(len(parquet_files), 0)
            
            # Sprawdź jeden z plików
            first_file = parquet_files[0]
            with zip_file.open(first_file) as f:
                # Sprawdź czy to poprawny Parquet
                content = f.read()
                self.assertGreater(len(content), 0)
                # Parquet zawsze zaczyna się od "PAR1"
                self.assertTrue(content.endswith(b'PAR1'))
        
        print(f"✅ ZIP wygenerowany poprawnie:")
        print(f"   Pliki w archiwum: {len(file_list)}")
        print(f"   Pliki Parquet: {len(parquet_files)}")
        print(f"   Rozmiar ZIP: {len(response.content)} bajtów")
    
    def test_07_files_endpoint(self):
        """Test 7: Endpoint listowania plików."""
        print("\n=== Test 7: Files Endpoint ===")
        
        # Wygeneruj dane i batche
        filename = self.test_03_generate_parquet_flow()
        batch_dir = self.test_04_transform_parquet_to_batches()
        
        # Pobierz listę plików
        response = self.client.get("/files")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("original_files", data)
        self.assertIn("batch_directories", data)
        
        original_files = data["original_files"]
        batch_directories = data["batch_directories"]
        
        # Sprawdź oryginalny plik
        self.assertEqual(len(original_files), 1)
        file_info = original_files[0]
        self.assertEqual(file_info["filename"], filename)
        self.assertGreater(file_info["size_mb"], 0)
        self.assertIn("modified", file_info)
        
        # Sprawdź katalogi batchów
        self.assertEqual(len(batch_directories), 1)
        batch_info = batch_directories[0]
        self.assertEqual(batch_info["directory"], batch_dir)
        self.assertGreater(batch_info["batch_count"], 0)
        self.assertGreater(batch_info["total_rows"], 0)
        
        print(f"✅ Lista plików OK:")
        print(f"   Pliki oryginalne: {len(original_files)}")
        print(f"   Katalogi batchów: {len(batch_directories)}")
    
    def test_08_error_handling(self):
        """Test 8: Obsługa błędów."""
        print("\n=== Test 8: Error Handling ===")
        
        # Test 1: Generowanie z nieprawidłowymi parametrami
        response = self.client.post("/generate", json={"rows": -1, "columns": 0})
        self.assertEqual(response.status_code, 400)
        print("✅ Błąd generowania z nieprawidłowymi parametrami: OK")
        
        # Test 2: Transformacja nieistniejącego pliku
        response = self.client.post("/transform", json={
            "input_filename": "nieistniejacy.parquet",
            "batch_size": 1000
        })
        self.assertEqual(response.status_code, 400)
        print("✅ Błąd transformacji nieistniejącego pliku: OK")
        
        # Test 3: Download nieistniejącego pliku
        response = self.client.get("/download", params={
            "format": "csv",
            "filename": "nieistniejacy.parquet"
        })
        self.assertEqual(response.status_code, 400)
        print("✅ Błąd pobierania nieistniejącego pliku: OK")
    
    def test_09_complete_integration_flow(self):
        """Test 9: Kompletny flow integracyjny."""
        print("\n=== Test 9: Complete Integration Flow ===")
        
        # Krok 1: Generowanie danych
        print("Krok 1: Generowanie danych...")
        generate_response = self.client.post("/generate", json={
            "rows": 2000,
            "columns": 30,
            "filename": "integration_test"
        })
        self.assertEqual(generate_response.status_code, 200)
        filename = generate_response.json()["filename"]
        
        # Krok 2: Sprawdzenie statusu
        print("Krok 2: Sprawdzenie statusu...")
        status_response = self.client.get("/status")
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        self.assertEqual(status_data["statistics"]["original_files_count"], 1)
        
        # Krok 3: Transformacja do batchów
        print("Krok 3: Transformacja do batchów...")
        transform_response = self.client.post("/transform", json={
            "input_filename": filename,
            "batch_size": 500  # 4 batche
        })
        self.assertEqual(transform_response.status_code, 200)
        batch_dir = transform_response.json()["batch_directory"]
        
        # Krok 4: Lista plików
        print("Krok 4: Lista plików...")
        files_response = self.client.get("/files")
        self.assertEqual(files_response.status_code, 200)
        files_data = files_response.json()
        self.assertEqual(len(files_data["original_files"]), 1)
        self.assertEqual(len(files_data["batch_directories"]), 1)
        
        # Krok 5: Download CSV z oryginalnego
        print("Krok 5: Download CSV z oryginalnego...")
        csv_response = self.client.get("/download", params={
            "format": "csv",
            "pivoted": "false",
            "filename": filename
        })
        self.assertEqual(csv_response.status_code, 200)
        csv_lines = csv_response.content.decode('utf-8').strip().split('\n')
        self.assertEqual(len(csv_lines), 2001)  # nagłówek + 2000 wierszy
        
        # Krok 6: Download ZIP z batchów
        print("Krok 6: Download ZIP z batchów...")
        zip_response = self.client.get("/download", params={
            "format": "zip", 
            "pivoted": "true",
            "batch_dir": batch_dir
        })
        self.assertEqual(zip_response.status_code, 200)
        
        # Sprawdź ZIP
        zip_file = zipfile.ZipFile(io.BytesIO(zip_response.content))
        parquet_files = [f for f in zip_file.namelist() if f.endswith('.parquet')]
        self.assertEqual(len(parquet_files), 4)  # 4 batche
        
        print(f"✅ Kompletny flow zakończony pomyślnie:")
        print(f"   Wygenerowano plik: {filename}")
        print(f"   Utworzono batche: {len(parquet_files)}")
        print(f"   CSV: {len(csv_lines)} linii")
        print(f"   ZIP: {len(zip_response.content)} bajtów")
        
        # Krok 7: Finalny status
        final_status = self.client.get("/status")
        final_data = final_status.json()
        print(f"   Status finalny: {final_data['statistics']['total_size_mb']:.2f} MB")


def run_integration_tests():
    """Uruchamia wszystkie testy integracyjne."""
    print("=" * 60)
    print("TESTY INTEGRACYJNE API KOŻU OFIARNY")
    print("=" * 60)
    
    # Konfiguracja testów
    unittest.TestLoader.sortTestMethodsUsing = lambda _, x, y: (
        -1 if x < y else 1 if x > y else 0
    )
    
    # Uruchomienie testów
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAPIIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("PODSUMOWANIE TESTÓW")
    print("=" * 60)
    print(f"Wykonano testów: {result.testsRun}")
    print(f"Błędy: {len(result.errors)}")
    print(f"Niepowodzenia: {len(result.failures)}")
    
    if result.errors:
        print("\nBŁĘDY:")
        for test, error in result.errors:
            print(f"- {test}: {error}")
    
    if result.failures:
        print("\nNIEPOWODZENIA:")
        for test, failure in result.failures:
            print(f"- {test}: {failure}")
    
    success_rate = (result.testsRun - len(result.errors) - len(result.failures)) / result.testsRun * 100
    print(f"\nPoziom sukcesu: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
