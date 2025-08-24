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
from transformer import pivot_and_batch, get_batch_info


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
    """Dostępne formaty plików do pobierania."""
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


@app.get("/download")
async def download_data(
    format: FileFormat = Query(FileFormat.csv, description="Format pliku do pobrania"),
    pivoted: bool = Query(False, description="Czy pobierać dane pivotowane (z batchów)"),
    filename: Optional[str] = Query(None, description="Nazwa pliku oryginalnego (jeśli pivoted=False)"),
    batch_dir: Optional[str] = Query(None, description="Nazwa katalogu batchów (jeśli pivoted=True)")
):
    """
    Endpoint do pobierania danych w różnych formatach.
    
    Args:
        format: Format pliku (csv lub parquet)
        pivoted: Czy pobierać dane pivotowane (z batchów)
        filename: Nazwa konkretnego pliku (dla danych niepivotowanych)
        batch_dir: Katalog z batchami (dla danych pivotowanych)
    """
    try:
        with TimeProfiler(f"Pobieranie danych w formacie {format.value}"):
            
            if pivoted:
                # Pobieranie danych pivotowanych (z batchów)
                return await download_pivoted_data(format, batch_dir)
            else:
                # Pobieranie danych oryginalnych
                return await download_original_data(format, filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd podczas pobierania danych: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd pobierania danych: {str(e)}")


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
        return await stream_parquet_as_csv(file_path)
    elif format == FileFormat.parquet:
        # Pobieranie Parquet
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/octet-stream"
        )


async def download_pivoted_data(format: FileFormat, batch_dir: Optional[str]):
    """
    Pobiera pivotowane dane (z batchów).
    """
    if not batch_dir:
        # Znajdź najnowszy katalog z batchami
        batch_dirs = [d for d in BATCH_DIR.iterdir() if d.is_dir()]
        if not batch_dirs:
            raise HTTPException(status_code=404, detail="Brak dostępnych batchów")
        
        batch_dir = max(batch_dirs, key=lambda x: x.stat().st_mtime).name
    
    batch_path = BATCH_DIR / batch_dir
    
    if not batch_path.exists():
        raise HTTPException(status_code=404, detail=f"Katalog batchów {batch_dir} nie istnieje")
    
    if format == FileFormat.csv:
        # Zipowane CSV z wszystkich batchów
        return await create_batched_csv_zip(batch_path)
    elif format == FileFormat.zip:
        # Zipowane pliki Parquet
        return await create_batched_parquet_zip(batch_path)
    else:  # FileFormat.parquet
        # Pojedynczy plik Parquet z połączonymi batchami
        return await create_merged_parquet(batch_path)


async def stream_parquet_as_csv(file_path: Path):
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
    
    filename = file_path.stem + ".csv"
    
    return StreamingResponse(
        generate_csv_stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def create_batched_csv_zip(batch_path: Path):
    """
    Tworzy ZIP z plikami CSV z wszystkich batchów.
    """
    zip_filename = f"{batch_path.name}_csv.zip"
    temp_zip_path = TEMP_DIR / zip_filename
    
    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        batch_files = sorted(batch_path.glob("batch_*.parquet"))
        
        for batch_file in batch_files:
            # Konwersja każdego batchu do CSV
            df = pd.read_parquet(batch_file)
            csv_name = batch_file.stem + ".csv"
            
            # Dodaj CSV do ZIP
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            zipf.writestr(csv_name, csv_buffer.getvalue())
        
        # Dodaj manifest
        manifest_path = batch_path / "batch_manifest.json"
        if manifest_path.exists():
            zipf.write(manifest_path, "batch_manifest.json")
    
    return FileResponse(
        path=str(temp_zip_path),
        filename=zip_filename,
        media_type="application/zip"
    )


async def create_batched_parquet_zip(batch_path: Path):
    """
    Tworzy ZIP z plikami Parquet z wszystkich batchów.
    """
    zip_filename = f"{batch_path.name}_parquet.zip"
    temp_zip_path = TEMP_DIR / zip_filename
    
    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        batch_files = sorted(batch_path.glob("batch_*.parquet"))
        
        for batch_file in batch_files:
            zipf.write(batch_file, batch_file.name)
        
        # Dodaj manifest
        manifest_path = batch_path / "batch_manifest.json"
        if manifest_path.exists():
            zipf.write(manifest_path, "batch_manifest.json")
    
    return FileResponse(
        path=str(temp_zip_path),
        filename=zip_filename,
        media_type="application/zip"
    )


async def create_merged_parquet(batch_path: Path):
    """
    Łączy wszystkie batche w jeden plik Parquet.
    """
    merged_filename = f"{batch_path.name}_merged.parquet"
    temp_merged_path = TEMP_DIR / merged_filename
    
    # Znajdź wszystkie pliki batch
    batch_files = sorted(batch_path.glob("batch_*.parquet"))
    
    if not batch_files:
        raise HTTPException(status_code=404, detail="Brak plików batch w katalogu")
    
    # Połącz wszystkie DataFrame
    dfs = []
    for batch_file in batch_files:
        df = pd.read_parquet(batch_file)
        dfs.append(df)
    
    # Połącz w jeden DataFrame
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # Zapisz jako Parquet
    merged_df.to_parquet(temp_merged_path, compression='snappy')
    
    return FileResponse(
        path=str(temp_merged_path),
        filename=merged_filename,
        media_type="application/octet-stream"
    )


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
