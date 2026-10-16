#!/usr/bin/env bash
# Execute with bash; no chmod or working-directory assumptions required.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_command="${PYTHON:-python3.13}"
reference_root="${COMBINATION_REFERENCE_ROOT:-$project_root/../RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI}"
dependencies=Core
system_deps=0
while (($#)); do
    case "$1" in
        --system-deps) system_deps=1 ;;
        --backend) dependencies=Backend ;;
        --optimization) dependencies=Optimization ;;
        --help|-h)
            printf '%s\n' 'Usage: bash scripts/install_ubuntu.sh [--system-deps] [--backend|--optimization]' \
                'PYTHON selects a Python 3.13 executable; COMBINATION_REFERENCE_ROOT selects the RI dependency checkout.'
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
if ((system_deps)); then
    sudo apt-get update
    sudo apt-get install -y build-essential cmake ninja-build pkg-config libgl1-mesa-dev \
        libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 \
        libxcb-shape0 libxcb-xinerama0 libxcb-randr0 libxcb-render-util0
fi
command -v "$python_command" >/dev/null || {
    printf '%s\n' 'Python 3.13 is required. Install Python 3.13 with matching venv/development headers for your Ubuntu release, then set PYTHON if needed.' >&2
    exit 1
}
command -v cmake >/dev/null || { printf '%s\n' 'CMake missing; install it or use --system-deps.' >&2; exit 1; }
command -v ninja >/dev/null || { printf '%s\n' 'Ninja missing; install it or use --system-deps.' >&2; exit 1; }
"$python_command" -c 'import sys,struct; assert sys.version_info[:2] == (3,13) and struct.calcsize("P") == 8, "Python 3.13 64-bit is required"'
for relative in external/glad/src/glad.c external/glm/glm/glm.hpp external/GLFW/deps/nuklear.h; do
    [[ -f "$reference_root/$relative" ]] || { printf 'Missing native dependency: %s\n' "$reference_root/$relative" >&2; exit 1; }
done
if [[ ! -x "$project_root/.venv/bin/python" ]]; then
    if [[ -e "$project_root/.venv" ]]; then
        printf '%s\n' 'Existing .venv is incomplete or belongs to another OS. Use a separate checkout/environment; it will not be overwritten.' >&2
        exit 1
    fi
    "$python_command" -m venv "$project_root/.venv"
fi
source "$project_root/.venv/bin/activate"
venv_python="$project_root/.venv/bin/python"
"$venv_python" -c 'import sys,struct; assert sys.version_info[:2] == (3,13) and struct.calcsize("P") == 8, "Existing .venv must use Python 3.13 64-bit"'
requirements=requirements.txt
case "$dependencies" in
    Backend) requirements=requirements-backend.txt ;;
    Optimization) requirements=requirements-optimization.txt ;;
esac
"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install -r "$project_root/$requirements"
"$venv_python" -m pip check
build_root="$project_root/build/ubuntu"
cmake -S "$project_root" -B "$build_root" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    "-DPython_EXECUTABLE=$venv_python" "-DCOMBINATION_REFERENCE_ROOT=$reference_root" -DCOMBINATION_BUILD_PYTHON=ON
cmake --build "$build_root" --parallel "${BUILD_JOBS:-2}"
ctest --test-dir "$build_root" --output-on-failure
export COMBINATION_CHARTS_DIR="$build_root"
"$venv_python" -B "$project_root/main.py" --check
printf '%s\n' 'Installation complete. Start the integrated simulation: bash scripts/run_ubuntu.sh' \
    'Full CST UI/control/database migration is still pending.' \
    "To activate this venv in your current shell: source \"$project_root/.venv/bin/activate\""
