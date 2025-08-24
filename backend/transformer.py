"""
Moduł transformacji danych dla systemu Kożu Ofiarny.
Wykonuje pivotowanie danych i dzieli je na batchy row groups.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import wraps
import os
import shutil


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


@log_time
def load_parquet_data(input_path: str) -> pd.DataFrame:
    """
    Ładuje dane z pliku Parquet.
    
    Args:
        input_path: Ścieżka do pliku Parquet
    
    Returns:
        pd.DataFrame: Załadowane dane
    """
    if not Path(input_path).exists():
        raise FileNotFoundError(f"Plik {input_path} nie istnieje")
    
    with TimeProfiler(f"Ładowanie danych z {input_path}"):
        df = pd.read_parquet(input_path)
        logger.info(f"Załadowano dane o wymiarach: {df.shape}")
        logger.info(f"Pamięć używana przez DataFrame: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    return df


@log_time
def create_pivot_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tworzy pivotowane dane z oryginalnego DataFrame.
    
    Strategia pivotowania:
    1. Używa pierwszej kolumny jako index (zazwyczaj 'id')
    2. Tworzy pivot na podstawie kolumn kategoryjnych i numerycznych
    3. Agreguje dane przez sumowanie, średnią i liczenie
    
    Args:
        df: Oryginalny DataFrame
    
    Returns:
        pd.DataFrame: Pivotowane dane
    """
    
    with TimeProfiler("Analiza struktury danych dla pivotu"):
        # Znajdź kolumny różnych typów
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        string_columns = df.select_dtypes(include=['object']).columns.tolist()
        datetime_columns = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        logger.info(f"Kolumny numeryczne: {len(numeric_columns)}")
        logger.info(f"Kolumny tekstowe: {len(string_columns)}")
        logger.info(f"Kolumny datetime: {len(datetime_columns)}")
        
        # Sprawdź czy mamy odpowiednie kolumny do pivotu
        if len(numeric_columns) < 2:
            raise ValueError("Za mało kolumn numerycznych do utworzenia sensownego pivotu")
    
    with TimeProfiler("Przygotowanie danych do pivotu"):
        # Pierwsza kolumna numeryczna jako index (zazwyczaj 'id')
        index_col = numeric_columns[0]
        
        # Znajdź kolumnę kategoryczną do pivotu (pierwsza z małą liczbą unikalnych wartości)
        pivot_col = None
        for col in numeric_columns[1:10]:  # Sprawdź pierwsze kilka kolumn
            unique_count = df[col].nunique()
            if 5 <= unique_count <= 100:  # Optymalna liczba kategorii dla pivotu
                pivot_col = col
                break
        
        if pivot_col is None:
            # Jeśli nie ma odpowiedniej kolumny, utwórz kategorię na podstawie kwantyli
            pivot_col = 'pivot_category'
            value_col = numeric_columns[1] if len(numeric_columns) > 1 else numeric_columns[0]
            df[pivot_col] = pd.qcut(df[value_col], q=10, labels=[f'Q{i}' for i in range(1, 11)])
        
        # Kolumny do agregacji (wartości liczbowe)
        value_cols = [col for col in numeric_columns[1:6] if col != pivot_col]  # Maksymalnie 5 kolumn
        
        logger.info(f"Kolumna index: {index_col}")
        logger.info(f"Kolumna pivot: {pivot_col}")
        logger.info(f"Kolumny wartości: {value_cols}")
    
    with TimeProfiler("Wykonanie pivotu - suma"):
        # Pivot 1: Suma wartości
        pivot_sum = df.pivot_table(
            index=index_col,
            columns=pivot_col,
            values=value_cols,
            aggfunc='sum',
            fill_value=0
        )
        
        # Spłaszczenie nazw kolumn
        if isinstance(pivot_sum.columns, pd.MultiIndex):
            pivot_sum.columns = [f"{col[0]}_sum_{col[1]}" for col in pivot_sum.columns]
        else:
            pivot_sum.columns = [f"{col}_sum" for col in pivot_sum.columns]
    
    with TimeProfiler("Wykonanie pivotu - średnia"):
        # Pivot 2: Średnia wartości
        pivot_mean = df.pivot_table(
            index=index_col,
            columns=pivot_col,
            values=value_cols,
            aggfunc='mean',
            fill_value=0
        )
        
        if isinstance(pivot_mean.columns, pd.MultiIndex):
            pivot_mean.columns = [f"{col[0]}_mean_{col[1]}" for col in pivot_mean.columns]
        else:
            pivot_mean.columns = [f"{col}_mean" for col in pivot_mean.columns]
    
    with TimeProfiler("Wykonanie pivotu - liczba"):
        # Pivot 3: Liczba rekordów
        pivot_count = df.pivot_table(
            index=index_col,
            columns=pivot_col,
            values=value_cols[0] if value_cols else numeric_columns[1],
            aggfunc='count',
            fill_value=0
        )
        
        if isinstance(pivot_count.columns, pd.MultiIndex):
            pivot_count.columns = [f"count_{col[1]}" for col in pivot_count.columns]
        else:
            pivot_count.columns = [f"count_{col}" for col in pivot_count.columns]
    
    with TimeProfiler("Łączenie wyników pivotu"):
        # Połączenie wszystkich pivotów
        result = pd.concat([pivot_sum, pivot_mean, pivot_count], axis=1)
        result = result.reset_index()
        
        logger.info(f"Wymiary pivotowanych danych: {result.shape}")
        logger.info(f"Nowe kolumny: {list(result.columns[:10])}...")  # Pokaż pierwsze 10 kolumn
    
    return result


@log_time
def save_batch_parquet(df: pd.DataFrame, output_path: str, batch_info: Dict[str, Any]) -> str:
    """
    Zapisuje batch danych jako plik Parquet zgodny ze standardem.
    
    Args:
        df: DataFrame do zapisania
        output_path: Ścieżka do pliku wyjściowego
        batch_info: Informacje o batchu (numer, rozmiar, etc.)
    
    Returns:
        str: Ścieżka do zapisanego pliku
    """
    
    with TimeProfiler(f"Zapis batchu {batch_info.get('batch_num', 'unknown')}"):
        # Tworzenie katalogu jeśli nie istnieje
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Konwersja do Arrow Table z metadanymi
        table = pa.Table.from_pandas(df)
        
        # Dodanie metadanych batchu
        metadata = {
            'batch_number': str(batch_info.get('batch_num', 0)),
            'total_batches': str(batch_info.get('total_batches', 1)),
            'batch_rows': str(len(df)),
            'created_at': str(pd.Timestamp.now()),
            'source_file': batch_info.get('source_file', 'unknown')
        }
        
        # Aktualizacja metadanych tabeli
        existing_metadata = table.schema.metadata or {}
        existing_metadata.update({k.encode(): v.encode() for k, v in metadata.items()})
        table = table.replace_schema_metadata(existing_metadata)
        
        # Zapis z odpowiednimi parametrami dla optymalnej wydajności
        pq.write_table(
            table,
            output_path,
            compression='snappy',
            row_group_size=min(50000, len(df)),  # Optymalny rozmiar row group
            use_dictionary=True,  # Kompresja słownikowa dla stringów
            write_statistics=True  # Statystyki dla lepszego query planning
        )
        
        file_size = output_path_obj.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"Batch zapisany: {output_path} ({file_size:.2f} MB, {len(df)} wierszy)")
    
    return str(output_path_obj.absolute())


@log_time
def pivot_and_batch(input_path: str, batch_size: int, output_dir: str) -> List[str]:
    """
    Główna funkcja: pivotuje dane i dzieli je na batchy row groups.
    
    Args:
        input_path: Ścieżka do pliku wejściowego Parquet
        batch_size: Rozmiar pojedynczego batchu (liczba wierszy)
        output_dir: Katalog na pliki wyjściowe
    
    Returns:
        List[str]: Lista ścieżek do wygenerowanych plików batchów
    """
    
    logger.info(f"Rozpoczęcie pivotowania pliku: {input_path}")
    logger.info(f"Rozmiar batchu: {batch_size} wierszy")
    logger.info(f"Katalog wyjściowy: {output_dir}")
    
    # Sprawdzenie czy plik istnieje
    if not Path(input_path).exists():
        raise FileNotFoundError(f"Plik wejściowy {input_path} nie istnieje")
    
    # Utworzenie katalogu wyjściowego
    output_dir_path = Path(output_dir)
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)  # Wyczyść istniejący katalog
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Krok 1: Załaduj dane
    df = load_parquet_data(input_path)
    
    # Krok 2: Wykonaj pivotowanie
    pivoted_df = create_pivot_data(df)
    
    # Krok 3: Podziel na batchy i zapisz
    with TimeProfiler("Podział na batchy i zapis"):
        batch_files = []
        total_rows = len(pivoted_df)
        total_batches = (total_rows + batch_size - 1) // batch_size  # Ceiling division
        
        logger.info(f"Dzielenie {total_rows} wierszy na {total_batches} batchów")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_rows)
            
            batch_df = pivoted_df.iloc[start_idx:end_idx].copy()
            
            # Nazwa pliku batchu
            batch_filename = f"batch_{batch_num:04d}_pivoted.parquet"
            batch_path = output_dir_path / batch_filename
            
            # Informacje o batchu
            batch_info = {
                'batch_num': batch_num,
                'total_batches': total_batches,
                'source_file': Path(input_path).name,
                'start_idx': start_idx,
                'end_idx': end_idx
            }
            
            # Zapis batchu
            saved_path = save_batch_parquet(batch_df, str(batch_path), batch_info)
            batch_files.append(saved_path)
            
            logger.info(f"Batch {batch_num + 1}/{total_batches}: {len(batch_df)} wierszy")
    
    # Utwórz plik manifestu z informacjami o batchach
    manifest_path = output_dir_path / "batch_manifest.json"
    manifest_info = {
        'source_file': input_path,
        'total_batches': total_batches,
        'batch_size': batch_size,
        'total_rows': total_rows,
        'created_at': str(pd.Timestamp.now()),
        'batch_files': [Path(f).name for f in batch_files]
    }
    
    import json
    with open(manifest_path, 'w') as f:
        json.dump(manifest_info, f, indent=2)
    
    logger.info(f"Manifest zapisany: {manifest_path}")
    logger.info(f"Wygenerowano {len(batch_files)} plików batchów")
    
    return batch_files


@log_time
def get_batch_info(batch_dir: str) -> Dict[str, Any]:
    """
    Zwraca informacje o batchach w danym katalogu.
    
    Args:
        batch_dir: Katalog z plikami batchów
    
    Returns:
        Dict: Informacje o batchach
    """
    batch_dir_path = Path(batch_dir)
    
    if not batch_dir_path.exists():
        raise FileNotFoundError(f"Katalog {batch_dir} nie istnieje")
    
    # Sprawdź czy istnieje manifest
    manifest_path = batch_dir_path / "batch_manifest.json"
    if manifest_path.exists():
        import json
        with open(manifest_path, 'r') as f:
            return json.load(f)
    
    # Jeśli nie ma manifestu, skanuj pliki
    batch_files = list(batch_dir_path.glob("batch_*.parquet"))
    
    total_rows = 0
    total_size = 0
    
    for batch_file in batch_files:
        try:
            parquet_file = pq.ParquetFile(batch_file)
            total_rows += parquet_file.metadata.num_rows
            total_size += batch_file.stat().st_size
        except Exception as e:
            logger.warning(f"Błąd odczytu pliku {batch_file}: {str(e)}")
    
    return {
        'batch_dir': str(batch_dir_path),
        'total_batches': len(batch_files),
        'total_rows': total_rows,
        'total_size_mb': total_size / (1024 * 1024),
        'batch_files': [f.name for f in batch_files]
    }


if __name__ == "__main__":
    # Test transformacji
    print("=== Test Transformacji i Batchowania ===")
    
    # Zakładając, że mamy wygenerowany plik testowy
    input_file = "../data/test_data.parquet"
    output_directory = "../data/batched_output"
    
    try:
        # Test pivotowania i batchowania
        batch_files = pivot_and_batch(
            input_path=input_file,
            batch_size=500,  # Małe batche dla testu
            output_dir=output_directory
        )
        
        print(f"\nWygenerowano {len(batch_files)} plików batchów:")
        for i, batch_file in enumerate(batch_files[:5], 1):  # Pokaż pierwsze 5
            print(f"{i}. {Path(batch_file).name}")
        
        # Sprawdź informacje o batchach
        batch_info = get_batch_info(output_directory)
        print(f"\nInformacje o batchach: {batch_info}")
        
    except FileNotFoundError:
        print("Plik testowy nie istnieje. Najpierw uruchom data_generator.py")
    except Exception as e:
        print(f"Błąd podczas testowania: {str(e)}")
