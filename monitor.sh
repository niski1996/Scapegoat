#!/bin/bash

echo "=== Monitor systemu Kożu Ofiarny ==="

while true; do
    echo "$(date): Sprawdzanie statusu..."
    
    # Sprawdź czy kontenery działają
    RUNNING=$(docker-compose ps -q)
    
    if [ -n "$RUNNING" ]; then
        echo "✅ Kontenery uruchomione:"
        docker-compose ps
        
        echo ""
        echo "🔍 Sprawdzanie dostępności serwisów:"
        
        # Test backend
        if curl -s http://localhost:8000/status > /dev/null; then
            echo "✅ Backend: http://localhost:8000 - DZIAŁA"
        else
            echo "❌ Backend: http://localhost:8000 - NIEDOSTĘPNY"
        fi
        
        # Test frontend (sprawdź czy port odpowiada)
        if nc -z localhost 4200 2>/dev/null; then
            echo "✅ Frontend: http://localhost:4200 - DZIAŁA"
        else
            echo "❌ Frontend: http://localhost:4200 - NIEDOSTĘPNY"
        fi
        
        echo ""
        echo "📊 Logi (ostatnie 10 linii):"
        docker-compose logs --tail=10
        
        break
    else
        echo "⏳ Kontenery jeszcze się uruchamiają..."
    fi
    
    sleep 5
done

echo ""
echo "=== System gotowy! ==="
echo "🌐 Frontend: http://localhost:4200"
echo "🔗 API: http://localhost:8000"
echo "📚 Docs: http://localhost:8000/docs"
