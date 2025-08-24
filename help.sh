#!/bin/bash

cat << 'EOF'
╭─────────────────────────────────────────────────────────────╮
│              🐐 Kożu Ofiarny - Scapegoat System             │
│                     Opcje uruchomienia                     │
╰─────────────────────────────────────────────────────────────╯

📋 DOSTĘPNE METODY URUCHOMIENIA:

🐳 1. DOCKER (Rekomendowane - wszystko w kontenerze)
   ./run-docker.sh
   
   Lub manualnie:
   docker-compose up -d
   
   Dostępne pod:
   • Frontend: http://localhost:4200
   • Backend:  http://localhost:8000
   • Docs:     http://localhost:8000/docs

💻 2. LOKALNIE (Python + Node.js na systemie)
   ./run-local.sh
   
   Wymagania:
   • Python 3.8+
   • Node.js 18+
   • npm

🔧 3. MANUALNIE (Osobno backend i frontend)
   
   Backend:
   cd backend
   pip install -r requirements.txt
   python api.py
   
   Frontend (nowy terminal):
   cd frontend
   npm install
   npm start

📊 4. MONITOROWANIE (sprawdzenie statusu)
   ./monitor.sh

🧪 5. TESTOWANIE
   cd backend
   python run_tests.py
   python test_swagger.py

╭─────────────────────────────────────────────────────────────╮
│                        Przydatne komendy                   │
╰─────────────────────────────────────────────────────────────╯

Docker:
• docker-compose ps              - Status kontenerów
• docker-compose logs -f         - Logi na żywo
• docker-compose restart         - Restart systemu
• docker-compose down            - Zatrzymanie

Lokalnie:
• lsof -i :8000                  - Co używa portu 8000
• lsof -i :4200                  - Co używa portu 4200
• pkill -f "python.*api.py"      - Zabij backend
• pkill -f "ng serve"            - Zabij frontend

EOF
