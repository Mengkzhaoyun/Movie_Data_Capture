#!/bin/bash
set -e

rm -rf ./build/Movie_Data_Capture ./dist/Movie_Data_Capture

echo "[*] Installing build dependencies..."
python3 -m pip install --upgrade pip setuptools pyinstaller

echo "[*] Installing requirements from requirements.txt..."
python3 -m pip install -r requirements.txt

echo "[*] Installing face_recognition (no-deps)..."
python3 -m pip install --no-deps face_recognition

echo "[*] Diagnostic: Checking for pkg_resources..."
python3 -c "import pkg_resources; print(f'pkg_resources version: {pkg_resources.__version__}')" || echo "[-] Warning: pkg_resources is STILL missing or broken."

echo "[*] Resolving package paths for PyInstaller (using find_spec)..."

# Helper function to get package path WITHOUT importing (avoids __init__.py crashes)
get_pkg_path() {
    python3 -c "import importlib.util; spec = importlib.util.find_spec('$1'); print(spec.submodule_search_locations[0] if spec and spec.submodule_search_locations else '')" 2>/dev/null || echo ""
}

CLOUD_PATH=$(get_pkg_path cloudscraper)
OPENCC_PATH=$(get_pkg_path opencc)
FACE_MODELS_PATH=$(get_pkg_path face_recognition_models)

# Fallback for face_recognition_models if find_spec fails (sometimes it's in site-packages directly)
if [ -z "$FACE_MODELS_PATH" ]; then
    FACE_MODELS_PATH=$(python3 -c "import site; import os; print(next((os.path.join(p, 'face_recognition_models') for p in site.getsitepackages() if os.path.exists(os.path.join(p, 'face_recognition_models'))), ''))" 2>/dev/null || echo "")
fi

if [ -z "$CLOUD_PATH" ] || [ -z "$OPENCC_PATH" ] || [ -z "$FACE_MODELS_PATH" ]; then
    echo "[-] Error: Failed to resolve one or more package paths."
    echo "    cloudscraper: ${CLOUD_PATH:-MISSING}"
    echo "    opencc: ${OPENCC_PATH:-MISSING}"
    echo "    face_recognition_models: ${FACE_MODELS_PATH:-MISSING}"
    python3 -m pip list | grep -E "cloudscraper|opencc|face-recognition-models"
    exit 1
fi

echo "[+] Paths resolved:"
echo "    - cloudscraper: $CLOUD_PATH"
echo "    - opencc: $OPENCC_PATH"
echo "    - face_recognition_models: $FACE_MODELS_PATH"

echo "[+] Starting PyInstaller..."

pyinstaller \
  -D src/main.py \
  -n Movie_Data_Capture \
  --python-option u \
  --noconfirm \
  --hidden-import "image_processing.cnn" \
  --hidden-import "adc_function" \
  --hidden-import "core" \
  --hidden-import "pkg_resources" \
  --hidden-import "setuptools" \
  --add-data "${CLOUD_PATH}:cloudscraper" \
  --add-data "${OPENCC_PATH}:opencc" \
  --add-data "${FACE_MODELS_PATH}:face_recognition_models" \
  --add-data "src/img:img" \
  --add-data "src/scrapinglib:scrapinglib"
