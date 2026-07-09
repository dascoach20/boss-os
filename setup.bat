@echo off
chcp 65001 >nul
title Boss OS
echo.
echo  ==========================================
echo   BOSS OS
echo  ==========================================
echo.

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
  echo [LOI] Python chua cai. Tai tai python.org roi tick "Add to PATH".
  echo.
  pause
  exit /b 1
)

REM Tao venv neu chua co
if not exist ".venv" (
  echo [1/3] Tao virtual environment...
  python -m venv .venv
)

REM Cai dependencies
echo [2/3] Kiem tra dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q

REM Giai phong port 7777 neu dang bi chiem
echo [3/3] Giai phong port 7777...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7777" ^| findstr "LISTENING"') do (
  echo     Dang tat tien trinh cu PID %%a
  taskkill /F /PID %%a >nul 2>&1
)

echo.
echo  ==========================================
echo   Boss OS dang chay tai: http://localhost:7777
echo   (Dung Claude Code CLI - khong can API key)
echo   Nhan Ctrl+C de dung.
echo  ==========================================
echo.

cd server
python main.py

REM Neu python thoat (loi), giu cua so de doc loi
echo.
echo  [!] Server da dung. Xem loi o tren (neu co).
pause
