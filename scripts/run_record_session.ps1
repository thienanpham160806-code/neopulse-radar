# Chạy bộ ghi NeoPulse cho một phiên giao dịch (Task Scheduler gọi lúc 8:55 T2-T6).
# Không đọc/in .env; khóa SSI do neopulse tự nạp từ .env trong thư mục repo.
$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo
New-Item -ItemType Directory -Force -Path (Join-Path $Repo "out") | Out-Null
$Log = Join-Path $Repo ("out\record_" + (Get-Date -Format "yyyyMMdd") + ".log")
# Log luôn UTF-8 không BOM (PowerShell 5 mặc định ghi UTF-16/có BOM nên làm hỏng tiếng Việt)
function Write-Log([string]$Msg) {
    [IO.File]::AppendAllText($Log, "$(Get-Date -Format s) $Msg`r`n", (New-Object Text.UTF8Encoding($false)))
}

# Giữ máy thức trong suốt phiên (tự hết hiệu lực khi script kết thúc)
Add-Type -Namespace NP -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[NP.Power]::SetThreadExecutionState([uint32]"0x80000041") | Out-Null   # CONTINUOUS | SYSTEM_REQUIRED | AWAYMODE

$Py = Join-Path $Repo ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $Py) { Write-Log "LỖI: không tìm thấy python"; exit 1 }

Write-Log "Bắt đầu phiên, python=$Py"
$env:PYTHONIOENCODING = "utf-8"
# Pha A ghi dữ liệu thật từ SSI: ép chế độ/nguồn qua biến môi trường (thắng giá trị trong .env, không cần sửa .env)
$env:NEOPULSE_MODE = "live"
$env:NEOPULSE_SOURCE = "ssi"
# Bộ ghi tự dừng 15:05; nếu chết giữa phiên thì chạy lại tối đa 5 lần (khoảng mất dữ liệu có trong log)
for ($i = 1; $i -le 5; $i++) {
    # cmd chuyển hướng byte thô (UTF-8 do Python ghi) nên không bị PowerShell đổi mã hóa hay bọc stderr thành lỗi
    cmd.exe /c "`"$Py`" -m neopulse.cli --log-level INFO record --until 15:05 >> `"$Log`" 2>&1"
    if ((Get-Date).TimeOfDay -ge [TimeSpan]"15:04:00") { break }
    Write-Log "Bộ ghi dừng sớm (lần $i), chạy lại sau 30 giây"
    Start-Sleep -Seconds 30
}
Write-Log "Kết thúc phiên"
[NP.Power]::SetThreadExecutionState([uint32]"0x80000000") | Out-Null
