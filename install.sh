#!/usr/bin/env bash
set -euo pipefail

# Install yt-dlp + curl_cffi ke venv user
PIP_BIN="${PIP_BIN:-pip3}"

if ! command -v yt-dlp >/dev/null 2>&1; then
    echo "[*] Installing yt-dlp..."
    $PIP_BIN install --user -U yt-dlp curl_cffi
else
    echo "[*] yt-dlp udah ada: $(yt-dlp --version)"
fi

# Symlink scripts/ ke ~/.local/bin
mkdir -p ~/.local/bin
for script in scripts/*.py scripts/*.sh; do
    [ -f "$script" ] || continue
    base=$(basename "$script")
    ln -sf "$(pwd)/$script" "$HOME/.local/bin/$base"
    echo "[+] linked ~/.local/bin/$base"
done

echo ""
echo "Selesai. Pastikan ~/.local/bin ada di PATH:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
