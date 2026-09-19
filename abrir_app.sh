#!/usr/bin/env bash
# Abre el Migrador de Catálogos desde el código fuente (macOS / Linux).
# Para el ejecutable ya compilado no hace falta esto.
#
# Los mensajes van en los dos idiomas: este script corre antes que la app, y por
# lo tanto antes de que exista i18n, así que no hay de dónde sacar el idioma
# elegido. Se dicen las dos cosas en vez de suponer una.
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "No encontré Python 3. Instalalo desde https://www.python.org/downloads/"
  echo "Python 3 not found. Install it from https://www.python.org/downloads/"
  exit 1
fi

if ! "$PY" -c "import openpyxl" 2>/dev/null; then
  echo "Instalando dependencias por primera vez... / Installing dependencies for the first time..."
  "$PY" -m pip install -r requirements-app.txt
fi

echo "Abriendo el Migrador de Catálogos... / Opening Catalog Migrator..."
exec "$PY" app/launcher.py "$@"
