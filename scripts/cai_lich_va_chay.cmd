@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Cai lich NeoPulseRecord (8:55 T2-T6)...
schtasks /Create /TN "NeoPulseRecord" /XML "%~dp0NeoPulseRecord_task.xml" /F
echo.
echo Chay ngay cho phien hom nay...
schtasks /Run /TN "NeoPulseRecord"
echo.
schtasks /Query /TN "NeoPulseRecord" /V /FO LIST | findstr /I "TaskName Status Next Last"
echo.
echo Xong. Log: out\record_ngay.log
timeout /t 20
