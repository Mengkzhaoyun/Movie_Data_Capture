#!/bin/bash
set -e

rm -rf ./build/Movie_Data_Capture ./dist/Movie_Data_Capture

echo "VERSION = '${APP_VERSION:-dev}'" > src/__version__.py


echo "[*] Installing build dependencies..."
python3 -m pip install --no-cache-dir --upgrade pip pyinstaller

echo "[*] Installing requirements from requirements.txt..."
python3 -m pip install --no-cache-dir -r requirements.txt

echo "[*] Resolving package paths for PyInstaller (using find_spec)..."

# Helper function to get package path WITHOUT importing (avoids __init__.py crashes)
get_pkg_path() {
    python3 -c "import importlib.util; spec = importlib.util.find_spec('$1'); print(spec.submodule_search_locations[0] if spec and spec.submodule_search_locations else '')" 2>/dev/null || echo ""
}

CLOUD_PATH=$(get_pkg_path cloudscraper)
OPENCC_PATH=$(get_pkg_path opencc)

if [ -z "$CLOUD_PATH" ] || [ -z "$OPENCC_PATH" ]; then
    echo "[-] Error: Failed to resolve one or more package paths."
    echo "    cloudscraper: ${CLOUD_PATH:-MISSING}"
    echo "    opencc: ${OPENCC_PATH:-MISSING}"
    python3 -m pip list | grep -E "cloudscraper|opencc"
    exit 1
fi

echo "[+] Paths resolved:"
echo "    - cloudscraper: $CLOUD_PATH"
echo "    - opencc: $OPENCC_PATH"

echo "[+] Starting PyInstaller..."

pyinstaller \
  -D src/main.py \
  -n Movie_Data_Capture \
  -p src \
  --strip \
  --python-option u \
  --noconfirm \
  --hidden-import "image_processing.hog" \
  --hidden-import "image_processing.cnn" \
  --hidden-import "adc_function" \
  --hidden-import "core" \
  --hidden-import "config" \
  --hidden-import "__version__" \
  --add-data "${CLOUD_PATH}:cloudscraper" \
  --add-data "${OPENCC_PATH}:opencc" \
  --add-data "src/img:img" \
  --add-data "src/scrapinglib:scrapinglib" \
  --add-data "data/mappings:data/mappings"
