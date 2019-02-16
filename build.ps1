$ErrorActionPreference = "Stop";
$env:HONDAECU_VERSION=git describe --tags
Write-Host "__VERSION__ = "$HONDAECU_VERSION | Out-File -FilePath .\src\version.py
$env:PYTHON_HOME\python -m PyInstaller --noconsole --onefile --clean --add-binary src/version.py;src --add-binary src/images/honda.ico;. --add-binary bins;bins --add-binary xdfs;xdfs --add-binary src/images/*;images --add-binary %LIBFTDI%;. src/__main__.py --name HondaECU_$env:HONDAECU_VERSION --icon=src/images/honda.ico
