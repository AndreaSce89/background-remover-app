from PyInstaller.utils.hooks import collect_all

# Collect all rembg data, binaries, and hidden imports
datas, binaries, hiddenimports = collect_all('rembg')
