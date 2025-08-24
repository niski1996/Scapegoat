"""
Generator danych testowych dla systemu Kożu Ofiarny.
Generuje pliki Parquet z losowymi danymi według zahardkodowanego schematu.
"""

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import random
import string
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Optional


# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def log_time(func):
    """
    Dekorator do logowania czasu wykonania funkcji.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Rozpoczęcie wykonania funkcji: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Funkcja {func.__name__} wykonana w {execution_time:.2f} sekund")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Błąd w funkcji {func.__name__} po {execution_time:.2f} sekund: {str(e)}")
            raise
    
    return wrapper


class TimeProfiler:
    """
    Context manager do profilowania czasu wykonania bloków kodu.
    """
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"Rozpoczęcie operacji: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"Operacja '{self.operation_name}' zakończona w {execution_time:.2f} sekund")
        else:
            logger.error(f"Operacja '{self.operation_name}' przerwana po {execution_time:.2f} sekund: {exc_val}")


def generate_random_string(max_length: int = 50) -> str:
    """
    Generuje losowy string o maksymalnej długości max_length.
    """
    length = random.randint(1, max_length)
    return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))


def generate_random_datetime(start_year: int = 2020, end_year: int = 2024) -> datetime:
    """
    Generuje losową datę w zadanym przedziale lat.
    """
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    
    return start_date + timedelta(days=random_days)


@log_time
def generate_parquet(rows: int, columns: int = 100, output_path: str = "data/generated_data.parquet") -> str:
    """
    Generuje plik Parquet z losowymi danymi według zahardkodowanego schematu.
    
    Args:
        rows: Liczba wierszy do wygenerowania
        columns: Liczba kolumn (domyślnie 100)
        output_path: Ścieżka do pliku wyjściowego
    
    Returns:
        str: Ścieżka do wygenerowanego pliku
    
    Schema kolumn (zahardkodowany mix typów):
    - 30% kolumn int (ID, liczniki, kategorie)
    - 30% kolumn float (wartości liczbowe, procenty)
    - 30% kolumn string (nazwy, opisy, kody)
    - 10% kolumn datetime (daty, znaczniki czasu)
    """
    
    logger.info(f"Generowanie {rows} wierszy x {columns} kolumn")
    
    # Obliczenie liczby kolumn każdego typu
    int_cols = int(columns * 0.3)
    float_cols = int(columns * 0.3)
    string_cols = int(columns * 0.3)
    datetime_cols = columns - int_cols - float_cols - string_cols  # Reszta to datetime
    
    data = {}
    
    with TimeProfiler("Generowanie kolumn integer"):
        # Kolumny integer (ID, liczniki, kategorie)
        for i in range(int_cols):
            if i == 0:  # Pierwsza kolumna to ID
                data[f'id'] = range(1, rows + 1)
            elif i < 5:  # Kolejne kilka to kategorie (0-100)
                data[f'category_{i}'] = [random.randint(0, 100) for _ in range(rows)]
            else:  # Reszta to liczniki (0-1000000)
                data[f'counter_{i}'] = [random.randint(0, 1000000) for _ in range(rows)]
    
    with TimeProfiler("Generowanie kolumn float"):
        # Kolumny float (wartości liczbowe, procenty, wskaźniki)
        for i in range(float_cols):
            if i < 10:  # Procenty (0.0-100.0)
                data[f'percentage_{i}'] = [round(random.uniform(0.0, 100.0), 2) for _ in range(rows)]
            else:  # Wartości liczbowe (-1000.0 do 1000.0)
                data[f'value_{i}'] = [round(random.uniform(-1000.0, 1000.0), 4) for _ in range(rows)]
    
    with TimeProfiler("Generowanie kolumn string"):
        # Kolumny string (nazwy, opisy, kody)
        for i in range(string_cols):
            if i < 5:  # Krótkie kody (5-10 znaków)
                data[f'code_{i}'] = [generate_random_string(10) for _ in range(rows)]
            elif i < 15:  # Nazwy (10-25 znaków)
                data[f'name_{i}'] = [generate_random_string(25) for _ in range(rows)]
            else:  # Opisy (25-50 znaków)
                data[f'description_{i}'] = [generate_random_string(50) for _ in range(rows)]
    
    with TimeProfiler("Generowanie kolumn datetime"):
        # Kolumny datetime
        for i in range(datetime_cols):
            if i == 0:  # Główna data utworzenia
                data[f'created_at'] = [generate_random_datetime(2020, 2024) for _ in range(rows)]
            elif i == 1:  # Data modyfikacji
                data[f'updated_at'] = [generate_random_datetime(2022, 2024) for _ in range(rows)]
            else:  # Inne daty
                data[f'date_{i}'] = [generate_random_datetime() for _ in range(rows)]
    
    with TimeProfiler("Tworzenie DataFrame"):
        # Tworzenie DataFrame
        df = pd.DataFrame(data)
        logger.info(f"Utworzono DataFrame o wymiarach: {df.shape}")
        logger.info(f"Typy kolumn: {df.dtypes.value_counts().to_dict()}")
    
    with TimeProfiler("Zapis pliku Parquet"):
        # Tworzenie katalogu jeśli nie istnieje
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Zapis do pliku Parquet z kompresją
        table = pa.Table.from_pandas(df)
        pq.write_table(
            table, 
            output_path,
            compression='snappy',  # Kompresja dla lepszej wydajności
            row_group_size=50000   # Rozmiar row group dla optymalizacji
        )
        
        # Sprawdzenie rozmiaru pliku
        file_size = output_path_obj.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"Plik zapisany: {output_path} ({file_size:.2f} MB)")
    
    return str(output_path_obj.absolute())


def get_parquet_info(file_path: str) -> dict:
    """
    Zwraca informacje o pliku Parquet (metadane, rozmiar, liczba row groups).
    """
    try:
        parquet_file = pq.ParquetFile(file_path)
        
        info = {
            'file_path': file_path,
            'num_rows': parquet_file.metadata.num_rows,
            'num_columns': parquet_file.metadata.num_columns,
            'num_row_groups': parquet_file.metadata.num_row_groups,
            'file_size_mb': Path(file_path).stat().st_size / (1024 * 1024),
            'schema': str(parquet_file.schema),
            'created_by': parquet_file.metadata.created_by
        }
        
        logger.info(f"Informacje o pliku {file_path}: {info}")
        return info
        
    except Exception as e:
        logger.error(f"Błąd podczas odczytu informacji o pliku {file_path}: {str(e)}")
        raise


if __name__ == "__main__":
    # Test generatora danych
    print("=== Test Generatora Danych ===")
    
    # Generowanie małego pliku testowego
    test_file = generate_parquet(
        rows=1000, 
        columns=20, 
        output_path="../data/test_data.parquet"
    )
    
    # Sprawdzenie informacji o pliku
    info = get_parquet_info(test_file)
    print(f"\nWygenerowano plik testowy: {info}")
    
    # Generowanie większego pliku
    print("\n=== Generowanie większego pliku ===")
    large_file = generate_parquet(
        rows=100000, 
        columns=100, 
        output_path="../data/large_data.parquet"
    )
    
    info_large = get_parquet_info(large_file)
    print(f"\nWygenerowano duży plik: {info_large}")
