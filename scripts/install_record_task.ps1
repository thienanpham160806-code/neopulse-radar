# Cài lịch tự ghi phiên: 8:55 thứ Hai-thứ Sáu, thêm lúc đăng nhập (máy bật muộn vẫn ghi phần còn lại của phiên;
# script tự thoát ngoài 08:30-14:45). Gỡ: Unregister-ScheduledTask -TaskName NeoPulseRecord -Confirm:$false
$Script = Join-Path $PSScriptRoot "run_record_session.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`"" `
    -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$Trigger = @(
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 8:55am),
    (New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME")
)
$Settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 7) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "NeoPulseRecord" -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "NeoPulse Radar: ghi dữ liệu SSI mỗi phiên giao dịch (8:55-15:05)" -Force | Out-Null
Get-ScheduledTask -TaskName "NeoPulseRecord" | Select-Object TaskName, State
