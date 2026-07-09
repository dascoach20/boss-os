@echo off
chcp 65001 >nul
title Khoi dong Boss OS
cd /d "%~dp0"

echo Bat Boss OS chay NEN - khong con cua so den (port 7777)...
REM Viec tat instance cu + chay server AN giao het cho start-boss.vbs (cua so an hoan toan).
REM Log ghi vao server\boss.log (mo file do neu can xem loi). Tat server: stop-boss.bat.
wscript //nologo start-boss.vbs

echo.
echo Da bat. Cho ~10 giay roi mo http://localhost:7777 va bam Ctrl+Shift+R.
echo (Tat server: chay stop-boss.bat. Xem loi: mo file server\boss.log)
timeout /t 4 >nul
