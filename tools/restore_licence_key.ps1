# Tra key licence tu ban sao ve lai kho C:\AX NF ZZ.
# PHAI chay bang quyen Administrator, va PHAI dong TIA + ALM truoc.
#
#   powershell -ep Bypass -File tools\restore_licence_key.ps1
#
# Dung khi da lo go key ra ma chua co key thay the. Key cu von da hong nen
# tra ve chua chac dung duoc - nhung it ra tro lai dung trang thai truoc do,
# va co the ALM ban moi doc lai duoc.
$ErrorActionPreference = "Stop"
$store = "C:\AX NF ZZ"

$admin = ([Security.Principal.WindowsPrincipal] `
          [Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Phai chay bang quyen Administrator." -ForegroundColor Red
    exit 1
}

$busy = Get-Process -Name 'Siemens.Automation.Portal', 'almgui*', 'almapp*' -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "Dong may cua so nay truoc:" -ForegroundColor Yellow
    $busy | ForEach-Object { "   - $($_.Name)  (PID $($_.Id))" }
    exit 1
}

# Tim ban sao. File .ekb mang thuoc tinh AN nen bat buoc phai co -Force,
# thieu no thi Get-ChildItem lam nhu khong co file nao.
$places = @()
$places += Get-ChildItem "$env:USERPROFILE\Desktop\licence-backup-*" -Directory -ErrorAction SilentlyContinue |
           Sort-Object Name -Descending | ForEach-Object { $_.FullName }
$places += "$env:LOCALAPPDATA\Temp\claude\D--PLC\95cedb18-09a5-4224-8d6d-c0fa8c990503\scratchpad\licence-backup"

$src = $null
foreach ($d in $places) {
    if (-not (Test-Path $d)) { continue }
    $f = Get-ChildItem $d -Filter '*.ekb' -File -Force -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($f) { $src = $f; break }
}

if (-not $src) {
    Write-Host "Khong tim thay ban sao nao. Da tim o:" -ForegroundColor Red
    $places | ForEach-Object { "   $_" }
    exit 1
}
Write-Host "Ban sao: $($src.FullName)  ($($src.Length) byte)" -ForegroundColor Cyan

Write-Host "Dung dich vu Automation License Manager..."
Stop-Service almservice -Force
Start-Sleep -Seconds 2

if (-not (Test-Path $store)) { New-Item -ItemType Directory -Path $store -Force | Out-Null }
Copy-Item $src.FullName -Destination $store -Force
# Kho licence von la thu muc an + he thong, tra lai dung thuoc tinh
(Get-Item $store -Force).Attributes = 'Hidden, System, Directory'

Write-Host "Bat lai dich vu..."
Start-Service almservice
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Kho licence bay gio:" -ForegroundColor Green
Get-ChildItem $store -Force | Select-Object Name, Length | Format-Table -AutoSize
Write-Host "Mo lai Automation License Manager, chon o C:, xem cot Status." -ForegroundColor Cyan
Write-Host "Con dau X do thi key that su hong - phai xin licence tu Siemens." -ForegroundColor Yellow
