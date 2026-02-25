from PyInstaller.utils.hooks import collect_all

# Collect all pymatting data, binaries, and hidden imports
datas, binaries, hiddenimports = collect_all('pymatting')
