"""
Backend FastAPI dla systemu Kożu Ofiarny.
Udostępnia endpointy do generowania, transformacji i pobierania danych.
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from enum import Enum
import pandas as pd
import pyarrow.parquet as pq
import io
import zipfile
import json
import logging
import time
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import tempfile
import shutil

# Import naszych modułów
from data_generator import generate_parquet, get_parquet_info, log_time, TimeProfiler
from transformer import pivot_and_batch, get_batch_info, create_pivot_data


# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicjalizacja FastAPI
app = FastAPI(
    title="Kożucha Ofiarny - Scapegoat System",
    description="System generowania, transformacji i pobierania danych Parquet z pivotowaniem",
    version="1.0.0"
)

# Enums dla API
class FileFormat(str, Enum):
    """Dostępne formaty plików do pobrania."""
    csv = "csv"
    parquet = "parquet"
    zip = "zip"

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji ustaw konkretne domeny
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic modele
class GenerateRequest(BaseModel):
    rows: int = 10000
    columns: int = 100
    filename: Optional[str] = None

class TransformRequest(BaseModel):
    input_filename: str
    batch_size: int = 50000

class DownloadRequest(BaseModel):
    format: str = "csv"  # csv lub parquet
    pivoted: bool = False
    filename: Optional[str] = None

# Globalne zmienne dla ścieżek
DATA_DIR = Path("../data")
BATCH_DIR = Path("../data/batched_output")
TEMP_DIR = Path("../data/temp")

# Utworzenie katalogów
for directory in [DATA_DIR, BATCH_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Inicjalizacja aplikacji."""
    logger.info("Uruchamianie API Kożu Ofiarny")
    logger.info(f"Katalog danych: {DATA_DIR.absolute()}")
    logger.info(f"Katalog batchów: {BATCH_DIR.absolute()}")


@app.get("/")
async def root():
    """Endpoint główny z informacjami o API."""
    return {
        "message": "Kożucha Ofiarny - Scapegoat System API",
        "version": "1.0.0",
        "endpoints": {
            "generate": "/generate - Generowanie danych",
            "transform": "/transform - Pivotowanie i batchowanie",
            "download": "/download - Pobieranie danych",
            "files": "/files - Lista dostępnych plików",
            "status": "/status - Status systemu"
        }
    }


@app.post("/generate")
async def generate_data(request: GenerateRequest):
    """
    Endpoint do generowania danych testowych.
    """
    try:
        with TimeProfiler("Generowanie danych przez API"):
            # Nazwa pliku
            if request.filename:
                filename = request.filename
                if not filename.endswith('.parquet'):
                    filename += '.parquet'
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_data_{timestamp}.parquet"
            
            output_path = DATA_DIR / filename
            
            logger.info(f"Generowanie {request.rows} wierszy x {request.columns} kolumn")
            
            # Generowanie danych
            file_path = generate_parquet(
                rows=request.rows,
                columns=request.columns,
                output_path=str(output_path)
            )
            
            # Pobranie informacji o pliku
            file_info = get_parquet_info(file_path)
            
            return {
                "success": True,
                "message": "Dane wygenerowane pomyślnie",
                "file_info": file_info,
                "filename": filename
            }
    
    except Exception as e:
        logger.error(f"Błąd podczas generowania danych: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd generowania danych: {str(e)}")


@app.post("/transform")
async def transform_data(request: TransformRequest):
    """
    Endpoint do pivotowania i batchowania danych.
    """
    try:
        with TimeProfiler("Transformacja danych przez API"):
            input_path = DATA_DIR / request.input_filename
            
            if not input_path.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Plik {request.input_filename} nie istnieje"
                )
            
            logger.info(f"Transformacja pliku: {request.input_filename}")
            logger.info(f"Rozmiar batchu: {request.batch_size}")
            
            # Tworzenie katalogu dla batchów z nazwą bazowaną na pliku źródłowym
            source_name = Path(request.input_filename).stem
            batch_output_dir = BATCH_DIR / f"{source_name}_batched"
            
            # Pivotowanie i batchowanie
            batch_files = pivot_and_batch(
                input_path=str(input_path),
                batch_size=request.batch_size,
                output_dir=str(batch_output_dir)
            )
            
            # Informacje o batchach
            batch_info = get_batch_info(str(batch_output_dir))
            
            return {
                "success": True,
                "message": "Dane przetransformowane pomyślnie",
                "batch_info": batch_info,
                "batch_count": len(batch_files),
                "batch_directory": str(batch_output_dir.relative_to(DATA_DIR.parent))
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd podczas transformacji danych: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd transformacji danych: {str(e)}")


# Pomocnicze funkcje
def get_parquet_schema(file_path: Path) -> List[Dict[str, str]]:
    """Zwraca listę kolumn i ich typów z pliku Parquet."""
    pf = pq.ParquetFile(file_path)
    schema = pf.schema_arrow
    return [{"name": f.name, "type": str(f.type)} for f in schema]


def flatten_columns(cols) -> List[str]:
    """Spłaszcza kolumny MultiIndex do nazw czytelnych w CSV."""
    if hasattr(cols, 'levels') or any(isinstance(c, tuple) for c in cols):
        out = []
        for c in cols:
            if isinstance(c, tuple):
                # np. (value_col, pivot_value)
                out.append(f"{c[0]}_{c[1]}")
            else:
                out.append(str(c))
        return out
    return [str(c) for c in cols]


def pivot_dataframe(df: pd.DataFrame, pivot_column: Optional[str]) -> pd.DataFrame:
    """Wykonuje pivot danych. Gdy pivot_column nie podany, używa domyślnej strategii z transformer.create_pivot_data."""
    if pivot_column is None:
        return create_pivot_data(df)

    if pivot_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Kolumna pivot '{pivot_column}' nie istnieje w danych")

    # Wybierz kolumnę indeksu (preferuj pierwszą numeryczną, inaczej pierwszą kolumnę)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    index_col = None
    for c in df.columns:
        if c == pivot_column:
            continue
        if c in numeric_cols:
            index_col = c
            break
    if index_col is None:
        # brak kolumny numerycznej poza pivotem – użyj pierwszej różnej od pivotu
        index_col = next((c for c in df.columns if c != pivot_column), df.columns[0])

    # Kolumny wartości (numeryczne, bez pivotu i indexu)
    value_cols = [c for c in numeric_cols if c not in {pivot_column, index_col}]

    if value_cols:
        pivoted = df.pivot_table(index=index_col, columns=pivot_column, values=value_cols, aggfunc='sum', fill_value=0)
        # Spłaszcz nazwy kolumn
        if isinstance(pivoted.columns, pd.MultiIndex):
            pivoted.columns = [f"{c[0]}_{c[1]}" for c in pivoted.columns]
        else:
            pivoted.columns = flatten_columns(pivoted.columns)
    else:
        # Brak wartości numerycznych – policz wystąpienia
        tmp_col = df.columns[0]
        pivoted = df.pivot_table(index=index_col, columns=pivot_column, values=tmp_col, aggfunc='count', fill_value=0)
        pivoted.columns = [f"count_{c}" for c in pivoted.columns]

    return pivoted.reset_index()


def stream_df_as_csv(df: pd.DataFrame, download_name: str = "result.csv") -> StreamingResponse:
    """Streamuje DataFrame do CSV bez trzymania całego stringa w pamięci."""
    def gen():
        # nagłówek
        header = ",".join(map(str, df.columns)) + "\n"
        yield header.encode()
        # dane w chunkach
        chunk_size = 100_000
        total = len(df)
        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            buf = io.StringIO()
            df.iloc[start:end].to_csv(buf, index=False, header=False)
            yield buf.getvalue().encode()

    return StreamingResponse(gen(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={download_name}"})


@app.get("/file-schema")
async def file_schema(filename: str = Query(..., description="Nazwa pliku Parquet w katalogu danych")):
    """Zwraca listę kolumn (nazwa, typ) dla wskazanego pliku Parquet."""
    file_path = (Path(filename) if Path(filename).is_absolute() else DATA_DIR / filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Plik {filename} nie istnieje")
    try:
        columns = get_parquet_schema(file_path)
        return {"filename": filename, "columns": columns}
    except Exception as e:
        logger.error(f"Błąd odczytu schematu {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd odczytu schematu: {e}")


@app.get("/download")
async def download_data(
    format: FileFormat = Query(FileFormat.csv, description="Format pliku do pobrania"),
    pivoted: bool = Query(False, description="Czy pivotować dane"),
    filename: Optional[str] = Query(None, description="Nazwa pliku oryginalnego"),
    batch_dir: Optional[str] = Query(None, description="(opcjonalnie) Katalog batchów – tryb kompatybilności"),
    pivot_column: Optional[str] = Query(None, description="(opcjonalnie) Kolumna do pivotowania")
):
    """
    Endpoint do pobierania danych w różnych formatach.

    Gdy pivoted=True:
      - Jeżeli podano batch_dir: zachowany dotychczasowy tryb pobierania z katalogu batchów.
      - W przeciwnym razie: pivot on-the-fly na wskazanym pliku (filename) z opcjonalnym pivot_column.
    """
    try:
        with TimeProfiler(f"Pobieranie danych w formacie {format.value}"):
            if pivoted:
                if batch_dir:
                    # tryb kompatybilności – pobieranie z batchów
                    return await download_pivoted_data(format, batch_dir)
                # pivot on-the-fly na pojedynczym pliku
                # wybór pliku
                if not filename:
                    parquet_files = list(DATA_DIR.glob("*.parquet"))
                    if not parquet_files:
                        raise HTTPException(status_code=404, detail="Brak dostępnych plików")
                    filename = max(parquet_files, key=lambda x: x.stat().st_mtime).name
                file_path = DATA_DIR / filename
                if not file_path.exists():
                    raise HTTPException(status_code=404, detail=f"Plik {filename} nie istnieje")

                df = pd.read_parquet(file_path)
                pivoted_df = pivot_dataframe(df, pivot_column)

                if format == FileFormat.csv:
                    return stream_df_as_csv(pivoted_df, download_name="result.csv")
                else:  # parquet
                    temp_path = TEMP_DIR / "result.parquet"
                    pivoted_df.to_parquet(temp_path, compression='snappy')
                    return FileResponse(path=str(temp_path), filename="result.parquet", media_type="application/octet-stream")
            else:
                # Pobieranie danych oryginalnych (bez pivotu)
                return await download_original_data(format, filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd podczas pobierania danych: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd pobierania danych: {str(e)}")


@app.get("/files")
async def list_files():
    """
    Zwraca listę dostępnych plików i batchów.
    
    Returns:
        dict: Zawiera:
            - original_files: Lista plików Parquet z metadanymi
            - batch_directories: Lista katalogów batchów z informacjami o batch_dir
    """
    try:
        # Pliki oryginalne
        original_files = []
        for file_path in DATA_DIR.glob("*.parquet"):
            file_info = {
                "filename": file_path.name,
                "size_mb": file_path.stat().st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            original_files.append(file_info)
        
        # Katalogi z batchami
        batch_dirs = []
        for dir_path in BATCH_DIR.iterdir():
            if dir_path.is_dir():
                try:
                    batch_info = get_batch_info(str(dir_path))
                    batch_dirs.append({
                        "directory": dir_path.name,
                        "batch_dir": dir_path.name,  # Dodatkowe pole dla zgodności z parametrem API
                        "full_path": str(dir_path.relative_to(Path.cwd())),
                        "batch_count": batch_info.get("total_batches", 0),
                        "total_rows": batch_info.get("total_rows", 0),
                        "total_size_mb": batch_info.get("total_size_mb", 0),
                        "source_file": batch_info.get("source_file", "unknown"),
                        "modified": datetime.fromtimestamp(dir_path.stat().st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Błąd odczytu informacji o katalogu {dir_path}: {str(e)}")
        
        return {
            "original_files": sorted(original_files, key=lambda x: x["modified"], reverse=True),
            "batch_directories": sorted(batch_dirs, key=lambda x: x["modified"], reverse=True)
        }
    
    except Exception as e:
        logger.error(f"Błąd podczas listowania plików: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd listowania plików: {str(e)}")


@app.get("/status")
async def get_status():
    """
    Zwraca status systemu i statystyki.
    """
    try:
        # Statystyki katalogów
        original_count = len(list(DATA_DIR.glob("*.parquet")))
        batch_dirs_count = len([d for d in BATCH_DIR.iterdir() if d.is_dir()])
        
        # Rozmiar katalogów
        def get_directory_size(path: Path) -> float:
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / (1024 * 1024)
        
        data_size = get_directory_size(DATA_DIR)
        batch_size = get_directory_size(BATCH_DIR)
        
        return {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "original_files_count": original_count,
                "batch_directories_count": batch_dirs_count,
                "data_directory_size_mb": round(data_size, 2),
                "batch_directory_size_mb": round(batch_size, 2),
                "total_size_mb": round(data_size + batch_size, 2)
            },
            "paths": {
                "data_directory": str(DATA_DIR.absolute()),
                "batch_directory": str(BATCH_DIR.absolute()),
                "temp_directory": str(TEMP_DIR.absolute())
            }
        }
    
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statusu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd pobierania statusu: {str(e)}")


@app.delete("/cleanup")
async def cleanup_temp_files():
    """
    Czyści tymczasowe pliki.
    """
    try:
        cleaned_files = 0
        cleaned_size = 0
        
        for temp_file in TEMP_DIR.glob("*"):
            if temp_file.is_file():
                file_size = temp_file.stat().st_size
                temp_file.unlink()
                cleaned_files += 1
                cleaned_size += file_size
        
        return {
            "success": True,
            "message": f"Wyczyszczono {cleaned_files} plików tymczasowych",
            "cleaned_size_mb": round(cleaned_size / (1024 * 1024), 2)
        }
    
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia plików tymczasowych: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd czyszczenia: {str(e)}")


async def download_original_data(format: FileFormat, filename: Optional[str]):
    """
    Pobiera oryginalne (niepivotowane) dane.
    """
    if not filename:
        # Znajdź najnowszy plik
        parquet_files = list(DATA_DIR.glob("*.parquet"))
        if not parquet_files:
            raise HTTPException(status_code=404, detail="Brak dostępnych plików")
        
        # Sortuj według czasu modyfikacji
        filename = max(parquet_files, key=lambda x: x.stat().st_mtime).name
    
    file_path = DATA_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Plik {filename} nie istnieje")
    
    if format == FileFormat.csv:
        # Streamowanie CSV
        return await stream_parquet_as_csv(file_path, download_name="result.csv")
    elif format == FileFormat.parquet:
        # Pobieranie Parquet
        return FileResponse(
            path=str(file_path),
            filename="result.parquet",
            media_type="application/octet-stream"
        )


async def stream_parquet_as_csv(file_path: Path, download_name: str = "result.csv"):
    """
    Streamuje plik Parquet jako CSV wiersz po wierszu.
    """
    def generate_csv_stream():
        try:
            # Czytaj plik w chunkach dla efektywności pamięci
            parquet_file = pq.ParquetFile(file_path)
            
            # Header CSV
            first_batch = parquet_file.read_row_group(0, columns=None).to_pandas()
            header = ",".join(first_batch.columns) + "\n"
            yield header.encode()
            
            # Dane w chunkach
            for i in range(parquet_file.metadata.num_row_groups):
                batch_df = parquet_file.read_row_group(i).to_pandas()
                
                # Konwersja do CSV bez nagłówka
                csv_buffer = io.StringIO()
                batch_df.to_csv(csv_buffer, index=False, header=False)
                csv_data = csv_buffer.getvalue()
                yield csv_data.encode()
                
        except Exception as e:
            logger.error(f"Błąd podczas streamowania CSV: {str(e)}")
            yield f"Błąd: {str(e)}".encode()
    
    return StreamingResponse(
        generate_csv_stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )


if __name__ == "__main__":
    import uvicorn
    
    print("=== Uruchamianie serwera FastAPI ===")
    print("Dostępne endpointy:")
    print("- http://localhost:8000 - główny")
    print("- http://localhost:8000/docs - dokumentacja API")
    print("- http://localhost:8000/generate - generowanie danych")
    print("- http://localhost:8000/transform - pivotowanie")
    print("- http://localhost:8000/download - pobieranie")
    print("- http://localhost:8000/files - lista plików")
    print("- http://localhost:8000/status - status systemu")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload podczas rozwoju
        log_level="info"
    )
