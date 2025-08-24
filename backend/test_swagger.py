#!/usr/bin/env python3
"""
Test ulepszonej dokumentacji Swagger z dropdown dla formatów plików.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_swagger_enhancements():
    """Test ulepszeń dokumentacji Swagger"""
    print("=== Test ulepszonej dokumentacji Swagger ===")
    
    # 1. Test endpointu /files z nowymi polami batch_dir
    print("\n1. Test endpoint /files z batch_dir info:")
    try:
        response = requests.get(f"{BASE_URL}/files")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            
            # Sprawdź batch_directories
            if "batch_directories" in data:
                print(f"Znaleziono {len(data['batch_directories'])} katalogów batchów:")
                for batch in data['batch_directories'][:3]:  # Pokaż pierwsze 3
                    print(f"  - {batch.get('directory', 'N/A')}")
                    print(f"    batch_dir: {batch.get('batch_dir', 'N/A')}")
                    print(f"    full_path: {batch.get('full_path', 'N/A')}")
                    print(f"    batches: {batch.get('batch_count', 0)}")
            else:
                print("❌ Brak pola 'batch_directories'")
        else:
            print(f"❌ Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd: {e}")

    # 2. Test endpointu /download z różnymi formatami
    print("\n2. Test endpoint /download z enum formatami:")
    formats = ["csv", "parquet", "zip"]
    
    for format_type in formats:
        try:
            # Test tylko zapytania HEAD żeby sprawdzić czy endpoint przyjmuje parametr
            response = requests.head(f"{BASE_URL}/download?format={format_type}")
            status_emoji = "✅" if response.status_code in [200, 404] else "❌"
            print(f"  {status_emoji} Format {format_type}: Status {response.status_code}")
        except Exception as e:
            print(f"  ❌ Format {format_type}: Błąd {e}")

    # 3. Test dostępu do dokumentacji Swagger
    print("\n3. Test dostępu do dokumentacji:")
    endpoints = [
        ("/docs", "Swagger UI"),
        ("/redoc", "ReDoc"),
        ("/openapi.json", "OpenAPI Schema")
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            status_emoji = "✅" if response.status_code == 200 else "❌"
            print(f"  {status_emoji} {name}: Status {response.status_code}")
            
            if endpoint == "/openapi.json" and response.status_code == 200:
                # Sprawdź czy schema zawiera enum dla FileFormat
                schema = response.json()
                paths = schema.get("paths", {})
                download_path = paths.get("/download", {})
                get_params = download_path.get("get", {}).get("parameters", [])
                
                format_param = None
                for param in get_params:
                    if param.get("name") == "format":
                        format_param = param
                        break
                
                if format_param:
                    schema_ref = format_param.get("schema", {})
                    if "$ref" in schema_ref:
                        # Znajdź definicję enum w components
                        ref_path = schema_ref["$ref"].split("/")[-1]
                        components = schema.get("components", {}).get("schemas", {})
                        enum_def = components.get(ref_path, {})
                        enum_values = enum_def.get("enum", [])
                        print(f"    📋 FileFormat enum: {enum_values}")
                    else:
                        print(f"    📋 Format schema: {schema_ref}")
                else:
                    print("    ❌ Nie znaleziono parametru 'format'")
        except Exception as e:
            print(f"  ❌ {name}: Błąd {e}")

    print("\n=== Test zakończony ===")
    print("Sprawdź dokumentację Swagger pod adresem: http://localhost:8000/docs")

if __name__ == "__main__":
    test_swagger_enhancements()
