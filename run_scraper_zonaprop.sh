#!/bin/bash
# Wrapper para ejecutar el scraper de ZonaProp desde una routine Paperclip
# Llamado por el agente Arquitecto cuando la routine diaria dispara.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/scraper_zonaprop_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$SCRIPT_DIR/logs"

echo "=== Iniciando scraper ZonaProp $(date) ===" | tee "$LOG_FILE"
python3 "$SCRIPT_DIR/scraper_zonaprop.py" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "=== Terminado con código $EXIT_CODE ===" | tee -a "$LOG_FILE"
exit $EXIT_CODE
