# Go key licence HONG ra khoi kho, de TIA co co hoi cap lai ban dung thu.
# PHAI chay bang quyen Administrator, va PHAI dong TIA Portal truoc.
#
#   powershell -ExecutionPolicy Bypass -File tools\reset_licence_store.ps1
#
# LUU Y: script nay KHONG tao ra licence. No chi don cho. Neu ban dung thu da
# bi tinh la tieu thu tren may nay thi TIA se khong cap lai, luc do phai lay
# licence tu tai khoan Siemens.
#
# File cu duoc sao luu truoc khi xoa.
$ErrorActionPreference = "Stop"

$store  = "C:\AX NF ZZ"
$backup = Join-Path $env:USERPROFILE "Desktop\licence-backup-$(Get-Date -Format yyyyMMdd-HHmmss)"

$admin = ([Security.Principal.WindowsPrincipal] `
          [Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Phai chay bang quyen Administrator." -ForegroundColor Red
    Write-Host "  Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File','$PSCommandPath'"
    exit 1
}

# Chi hai thu nay thuc su giu kho licence: cua so TIA va cua so ALM.
# May tien trinh phu (CrashDetector, FileStorage.Server) khong dung toi, va
# chung tu thoat sau khi TIA dong - khong chan vi chung cho met.
$busy = Get-Process -Name 'Siemens.Automation.Portal', 'almgui*', 'almapp*' `
        -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "Dong may cua so nay truoc roi chay lai:" -ForegroundColor Yellow
    $busy | ForEach-Object {
        $ten = switch -Wildcard ($_.Name) {
            'Siemens.Automation.Portal' { 'TIA Portal' }
            'almgui*'                   { 'Automation License Manager' }
            default                     { $_.Name }
        }
        "   - $ten  (PID $($_.Id))"
    }
    Write-Host "Nho LUU project truoc khi dong TIA." -ForegroundColor Cyan
    exit 1
}

$keys = Get-ChildItem $store -Force -File -ErrorAction SilentlyContinue
if (-not $keys) { Write-Host "Kho licence da rong, khong co gi de go." -ForegroundColor Green; exit 0 }

Write-Host "Se go nhung file sau:" -ForegroundColor Cyan
$keys | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

New-Item -ItemType Directory -Force $backup | Out-Null
$keys | Copy-Item -Destination $backup -Force
Write-Host "Da sao luu vao: $backup" -ForegroundColor Green

# almservice giu file mo, phai dung no roi moi xoa duoc
Write-Host "Dung dich vu Automation License Manager..."
Stop-Service almservice -Force
Start-Sleep -Seconds 2

$gone = 0
foreach ($k in $keys) {
    try { Remove-Item $k.FullName -Force -ErrorAction Stop; $gone++ }
    catch { Write-Host "  khong xoa duoc $($k.Name): $($_.Exception.Message)" -ForegroundColor Red }
}

Write-Host "Bat lai dich vu..."
Start-Service almservice
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Da go $gone / $($keys.Count) file." -ForegroundColor Green
$left = Get-ChildItem $store -Force -File -ErrorAction SilentlyContinue
Write-Host ("Kho licence bay gio: " + $(if ($left) { "$($left.Count) file con lai" } else { "RONG" }))
Write-Host ""
Write-Host "Gio mo lai TIA Portal. Neu no de nghi chay thu 21 ngay thi nhan dong y." -ForegroundColor Cyan
Write-Host "Khong thay de nghi nao thi ban dung thu da bi tinh la dung roi -" -ForegroundColor Yellow
Write-Host "phai lay licence tu tai khoan Siemens." -ForegroundColor Yellow
