"""
Testy jednostkowe dla komponentów systemu Kożu Ofiarny.
Sprawdzają poszczególne funkcje i klasy w izolacji.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import modułów do testowania
import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from data_generator import generate_parquet, get_parquet_info, TimeProfiler, log_time
    from transformer import pivot_and_batch, get_batch_info
    import api
except ImportError as e:
    print(f"Błąd importu: {e}")
    print("Upewnij się, że jesteś w katalogu backend/")
    sys.exit(1)


class TestDataGenerator(unittest.TestCase):
    """Testy dla modułu generowania danych."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.test_dir = tempfile.mkdtemp(prefix="test_generator_")
        self.test_path = Path(self.test_dir)
    
    def tearDown(self):
        """Czyszczenie po każdym teście."""
        if self.test_path.exists():
            shutil.rmtree(self.test_path)
    
    def test_generate_parquet_basic(self):
        """Test podstawowego generowania Parquet."""
        filename = "test_basic.parquet"
        filepath = self.test_path / filename
        
        file_path = generate_parquet(
            rows=100,
            columns=10,
            output_path=str(filepath)
        )
        
        # Sprawdź wynik
        self.assertTrue(filepath.exists())
        self.assertEqual(file_path, str(filepath.absolute()))
        
        # Sprawdź plik
        df = pd.read_parquet(filepath)
        self.assertEqual(len(df), 100)
        self.assertEqual(len(df.columns), 10)
    
    def test_generate_parquet_column_types(self):
        """Test typów kolumn w generowanych danych."""
        filename = "test_types.parquet"
        filepath = self.test_path / filename
        
        generate_parquet(
            rows=1000,
            columns=20,
            output_path=str(filepath)
        )
        
        df = pd.read_parquet(filepath)
        
        # Policz typy kolumn
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        string_cols = df.select_dtypes(include=['object']).columns
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        
        # Sprawdź proporcje (z tolerancją)
        total_cols = len(df.columns)
        numeric_ratio = len(numeric_cols) / total_cols
        string_ratio = len(string_cols) / total_cols
        datetime_ratio = len(datetime_cols) / total_cols
        
        self.assertGreaterEqual(numeric_ratio, 0.5)    # Około 60% numeryczne
        self.assertGreaterEqual(string_ratio, 0.2)     # Około 30% stringi
        self.assertGreaterEqual(datetime_ratio, 0.05)  # Około 10% datetime
    
    def test_get_parquet_info(self):
        """Test pobierania informacji o pliku Parquet."""
        filename = "test_info.parquet"
        filepath = self.test_path / filename
        
        generate_parquet(
            rows=500,
            columns=15,
            output_path=str(filepath)
        )
        
        info = get_parquet_info(str(filepath))
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info["num_rows"], 500)
        self.assertEqual(info["num_columns"], 15)
        self.assertGreater(info["file_size_mb"], 0)
        self.assertIn("columns", info)
        self.assertEqual(len(info["columns"]), 15)
    
    def test_time_profiler(self):
        """Test profilera czasu."""
        import time
        
        with TimeProfiler() as profiler:
            time.sleep(0.1)  # Symulacja pracy
        
        self.assertGreaterEqual(profiler.elapsed_time, 0.1)
        self.assertLess(profiler.elapsed_time, 0.2)  # Nie powinno być dużo więcej
    
    def test_log_time_decorator(self):
        """Test dekoratora logowania czasu."""
        
        @log_time
        def test_function(x, y):
            import time
            time.sleep(0.05)
            return x + y
        
        # Bez dekoratora zwraca prostą wartość
        # Z dekoratorem też zwraca prostą wartość (nie zmienia return)
        result = test_function(3, 4)
        self.assertEqual(result, 7)


class TestTransformer(unittest.TestCase):
    """Testy dla modułu transformacji danych."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.test_dir = tempfile.mkdtemp(prefix="test_transformer_")
        self.test_path = Path(self.test_dir)
        
        # Utwórz testowy plik Parquet
        self.test_file = self.test_path / "test_input.parquet"
        self._create_test_parquet()
    
    def tearDown(self):
        """Czyszczenie po każdym teście."""
        if self.test_path.exists():
            shutil.rmtree(self.test_path)
    
    def _create_test_parquet(self):
        """Tworzy testowy plik Parquet."""
        generate_parquet(
            rows=1000,
            columns=20,
            output_path=str(self.test_file)
        )
    
    def test_pivot_and_batch_basic(self):
        """Test podstawowego pivotowania i batchowania."""
        output_dir = self.test_path / "batches"
        
        result = pivot_and_batch(
            input_file=str(self.test_file),
            batch_size=250,
            output_dir=str(output_dir)
        )
        
        # Sprawdź wynik
        self.assertIsInstance(result, dict)
        self.assertIn("batch_count", result)
        self.assertIn("total_rows", result)
        self.assertEqual(result["batch_count"], 4)  # 1000/250 = 4
        self.assertEqual(result["total_rows"], 1000)
        
        # Sprawdź pliki
        self.assertTrue(output_dir.exists())
        
        batch_files = list(output_dir.glob("batch_*.parquet"))
        self.assertEqual(len(batch_files), 4)
        
        # Sprawdź manifest
        manifest_file = output_dir / "batch_manifest.json"
        self.assertTrue(manifest_file.exists())
        
        with open(manifest_file) as f:
            manifest = json.load(f)
            self.assertEqual(manifest["total_batches"], 4)
            self.assertEqual(manifest["batch_size"], 250)
    
    def test_pivot_and_batch_irregular_size(self):
        """Test batchowania z nieregularnym rozmiarem."""
        output_dir = self.test_path / "batches_irregular"
        
        result = pivot_and_batch(
            input_file=str(self.test_file),
            batch_size=333,  # 1000/333 = 3.003...
            output_dir=str(output_dir)
        )
        
        # Powinny być 4 batche (3 pełne + 1 niepełny)
        self.assertEqual(result["batch_count"], 4)
        
        batch_files = list(output_dir.glob("batch_*.parquet"))
        self.assertEqual(len(batch_files), 4)
        
        # Sprawdź rozmiary batchów
        total_rows = 0
        for batch_file in sorted(batch_files):
            df = pd.read_parquet(batch_file)
            total_rows += len(df)
            
        self.assertEqual(total_rows, 1000)
    
    def test_get_batch_info(self):
        """Test pobierania informacji o batchach."""
        output_dir = self.test_path / "batches_info"
        
        # Utwórz batche
        pivot_and_batch(
            input_file=str(self.test_file),
            batch_size=200,
            output_dir=str(output_dir)
        )
        
        # Pobierz informacje
        info = get_batch_info(str(output_dir))
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info["batch_count"], 5)  # 1000/200 = 5
        self.assertEqual(info["total_rows"], 1000)
        self.assertGreater(info["total_size_mb"], 0)
        self.assertIn("batch_files", info)
        self.assertEqual(len(info["batch_files"]), 5)


class TestAPIComponents(unittest.TestCase):
    """Testy dla komponentów API."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.test_dir = tempfile.mkdtemp(prefix="test_api_")
        self.test_path = Path(self.test_dir)
    
    def tearDown(self):
        """Czyszczenie po każdym teście."""
        if self.test_path.exists():
            shutil.rmtree(self.test_path)
    
    @patch('api.DATA_DIR', new_callable=lambda: None)
    def test_get_data_directory(self, mock_data_dir):
        """Test funkcji pobierania katalogu danych."""
        mock_data_dir.return_value = str(self.test_path)
        
        # Import API po ustawieniu mock
        import importlib
        importlib.reload(api)
        
        # Test gdy katalog nie istnieje
        data_dir = api.get_data_directory()
        self.assertTrue(Path(data_dir).exists())
    
    def test_validate_filename(self):
        """Test walidacji nazw plików."""
        # Poprawne nazwy
        self.assertTrue(api.validate_filename("test.parquet"))
        self.assertTrue(api.validate_filename("my_file_123.parquet"))
        
        # Niepoprawne nazwy
        self.assertFalse(api.validate_filename("../test.parquet"))
        self.assertFalse(api.validate_filename("/etc/passwd"))
        self.assertFalse(api.validate_filename("test.txt"))
    
    def test_format_file_size(self):
        """Test formatowania rozmiarów plików."""
        self.assertEqual(api.format_file_size(1024), "1.00 KB")
        self.assertEqual(api.format_file_size(1024*1024), "1.00 MB")
        self.assertEqual(api.format_file_size(1024*1024*1024), "1.00 GB")
    
    def test_get_system_statistics(self):
        """Test pobierania statystyk systemu."""
        # Utwórz testowe pliki
        data_dir = self.test_path / "data"
        data_dir.mkdir()
        
        # Plik testowy
        test_file = data_dir / "test.parquet"
        generate_parquet(10, 5, str(test_file))
        
        # Katalog batchów
        batch_dir = data_dir / "test_batches"
        batch_dir.mkdir()
        
        with patch('api.DATA_DIR', str(data_dir)):
            stats = api.get_system_statistics()
            
            self.assertIsInstance(stats, dict)
            self.assertIn("original_files_count", stats)
            self.assertIn("batch_directories_count", stats)
            self.assertIn("total_size_mb", stats)


class TestErrorHandling(unittest.TestCase):
    """Testy obsługi błędów."""
    
    def test_generate_parquet_invalid_params(self):
        """Test generowania z nieprawidłowymi parametrami."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Ujemna liczba wierszy
            with self.assertRaises(ValueError):
                generate_parquet(-1, 10, str(Path(temp_dir) / "test.parquet"))
            
            # Zero kolumn
            with self.assertRaises(ValueError):
                generate_parquet(100, 0, str(Path(temp_dir) / "test.parquet"))
    
    def test_get_parquet_info_nonexistent_file(self):
        """Test pobierania info o nieistniejącym pliku."""
        with self.assertRaises(FileNotFoundError):
            get_parquet_info("/nieistniejacy/plik.parquet")
    
    def test_pivot_and_batch_invalid_input(self):
        """Test transformacji z nieprawidłowymi danymi."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Nieistniejący plik wejściowy
            with self.assertRaises(FileNotFoundError):
                pivot_and_batch(
                    "/nieistniejacy/plik.parquet",
                    1000,
                    str(Path(temp_dir) / "output")
                )
            
            # Nieprawidłowy rozmiar batcha
            test_file = Path(temp_dir) / "test.parquet"
            generate_parquet(100, 10, str(test_file))
            
            with self.assertRaises(ValueError):
                pivot_and_batch(
                    str(test_file),
                    0,  # Nieprawidłowy rozmiar
                    str(Path(temp_dir) / "output")
                )


class TestPerformance(unittest.TestCase):
    """Testy wydajności."""
    
    def test_large_file_generation_performance(self):
        """Test wydajności generowania dużych plików."""
        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = datetime.now()
            
            result = generate_parquet(
                rows=50000,
                columns=50,
                output_path=str(Path(temp_dir) / "large.parquet")
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Sprawdź czy wykonanie nie trwało zbyt długo (max 30 sekund)
            self.assertLess(execution_time, 30.0)
            self.assertIn("execution_time", result)
    
    def test_batch_processing_performance(self):
        """Test wydajności przetwarzania batchowego."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Wygeneruj plik testowy
            input_file = Path(temp_dir) / "input.parquet"
            generate_parquet(10000, 30, str(input_file))
            
            start_time = datetime.now()
            
            result = pivot_and_batch(
                str(input_file),
                2000,
                str(Path(temp_dir) / "batches")
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Sprawdź czy wykonanie nie trwało zbyt długo (max 20 sekund)
            self.assertLess(execution_time, 20.0)
            self.assertEqual(result["batch_count"], 5)  # 10000/2000 = 5


def run_unit_tests():
    """Uruchamia wszystkie testy jednostkowe."""
    print("=" * 60)
    print("TESTY JEDNOSTKOWE KOMPONENTÓW SYSTEMU")
    print("=" * 60)
    
    # Lista klas testowych
    test_classes = [
        TestDataGenerator,
        TestTransformer,
        TestAPIComponents,
        TestErrorHandling,
        TestPerformance
    ]
    
    total_tests = 0
    total_errors = 0
    total_failures = 0
    
    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        total_errors += len(result.errors)
        total_failures += len(result.failures)
        
        if result.errors:
            for test, error in result.errors:
                print(f"BŁĄD w {test}: {error}")
        
        if result.failures:
            for test, failure in result.failures:
                print(f"NIEPOWODZENIE w {test}: {failure}")
    
    print("\n" + "=" * 60)
    print("PODSUMOWANIE TESTÓW JEDNOSTKOWYCH")
    print("=" * 60)
    print(f"Łączna liczba testów: {total_tests}")
    print(f"Błędy: {total_errors}")
    print(f"Niepowodzenia: {total_failures}")
    
    success_rate = (total_tests - total_errors - total_failures) / total_tests * 100 if total_tests > 0 else 0
    print(f"Poziom sukcesu: {success_rate:.1f}%")
    
    return total_errors == 0 and total_failures == 0


if __name__ == "__main__":
    success = run_unit_tests()
    exit(0 if success else 1)
