#!/bin/bash
set -e

echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo ""
echo "=== Ejecutando análisis de tendencias ==="
# Usa --demo para datos simulados si Google Trends no está accesible
python peru_trends.py "$@"

echo ""
echo "=== Listo ==="
echo "Archivos generados en output/"
ls -la output/
