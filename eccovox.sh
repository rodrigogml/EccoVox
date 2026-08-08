#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
venv_python="$root/.venv/bin/python"
manager="$root/scripts/manage.py"
command=${1:-status}

if [ "$#" -eq 0 ]; then
    set -- status
fi

if [ "$command" = "install" ] && [ ! -x "$venv_python" ]; then
    bootstrap_python=$(command -v python3 || true)
    if [ -z "$bootstrap_python" ]; then
        echo "Python 3 não encontrado no PATH." >&2
        exit 1
    fi
    exec "$bootstrap_python" "$manager" "$@"
fi

if [ ! -x "$venv_python" ]; then
    echo "EccoVox ainda não está instalado. Execute ./eccovox.sh install." >&2
    exit 1
fi

exec "$venv_python" "$manager" "$@"
