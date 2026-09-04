#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
venv_python="$root/.venv/bin/python"
manager="$root/scripts/manage.py"
command=${1:-menu}

if [ "$#" -eq 0 ]; then
    set -- menu
fi

if [ ! -x "$venv_python" ]; then
    case "$command" in
        install|menu|doctor|configure|config-show|voices|ffmpeg-status|ffmpeg-detect) ;;
        *)
            echo "EccoVox ainda não está instalado. Execute ./eccovox.sh install." >&2
            exit 1
            ;;
    esac
    bootstrap_python=$(command -v python3 || true)
    if [ -z "$bootstrap_python" ]; then
        echo "Python 3 não encontrado no PATH." >&2
        exit 1
    fi
    exec "$bootstrap_python" "$manager" "$@"
fi

exec "$venv_python" "$manager" "$@"
