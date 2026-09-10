# Gan lai IP tinh cho card mang noi PLC. PHAI chay bang quyen Administrator.
#
# Windows reset mang, go driver, hay doi cong USB deu lam mat IP tinh. Luc do
# card tu phong dia chi 169.254.x.x va khong noi duoc voi PLC nua: TIA bao
# "An additional project-specific IP address is required", con dashboard bao
# mat ket noi.
#
#   powershell -ExecutionPolicy Bypass -File tools\set_plc_ip.ps1
#   powershell -ExecutionPolicy Bypass -File tools\set_plc_ip.ps1 -Iface "Ethernet 4"
param(
    [string]$Iface = "Ethernet 3",
    [string]$IP    = "192.168.0.5",
    [int]   $Prefix = 24,
    [string]$Plc   = "192.168.0.10"
)

$ErrorActionPreference = "Stop"

$admin = ([Security.Principal.WindowsPrincipal] `
          [Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Phai chay bang quyen Administrator." -ForegroundColor Red
    Write-Host "Mo Terminal (Admin) roi chay lai, hoac dung lenh:" -ForegroundColor Yellow
    Write-Host "  Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File','$PSCommandPath'"
    exit 1
}

$card = Get-NetAdapter -Name $Iface -ErrorAction SilentlyContinue
if (-not $card) {
    Write-Host "Khong thay card '$Iface'. Cac card dang co:" -ForegroundColor Red
    Get-NetAdapter | Select-Object Name, Status, InterfaceDescription | Format-Table -AutoSize
    exit 1
}
if ($card.Status -ne "Up") {
    Write-Host "Card '$Iface' dang $($card.Status) - kiem lai day cam truoc." -ForegroundColor Yellow
}

# Xoa het dia chi cu, ke ca 169.254.x.x tu phong, roi tat DHCP
Get-NetIPAddress -InterfaceAlias $Iface -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetRoute -InterfaceAlias $Iface -Confirm:$false -ErrorAction SilentlyContinue
Set-NetIPInterface -InterfaceAlias $Iface -Dhcp Disabled

New-NetIPAddress -InterfaceAlias $Iface -IPAddress $IP -PrefixLength $Prefix | Out-Null
Write-Host "Da gan $IP/$Prefix cho '$Iface'" -ForegroundColor Green

Start-Sleep -Seconds 3
Get-NetIPAddress -InterfaceAlias $Iface -AddressFamily IPv4 |
    Select-Object IPAddress, PrefixLength, PrefixOrigin | Format-Table -AutoSize

# Kiem thong duong toi PLC: ping, cong 102 cho TIA, cong 502 cho dashboard
Write-Host "Kiem duong toi PLC $Plc" -ForegroundColor Cyan
$ping = Test-Connection $Plc -Count 3 -Quiet -ErrorAction SilentlyContinue
Write-Host ("  ping            : " + $(if ($ping) { "OK" } else { "khong tra loi" }))

foreach ($p in @(@(102, "TIA nap chuong trinh"), @(502, "dashboard Modbus"))) {
    try {
        $s = New-Object Net.Sockets.TcpClient
        $s.Connect($Plc, $p[0]); $s.Close()
        Write-Host ("  cong {0,-4} ({1}) : MO" -f $p[0], $p[1]) -ForegroundColor Green
    } catch {
        Write-Host ("  cong {0,-4} ({1}) : dong" -f $p[0], $p[1]) -ForegroundColor Red
    }
}
