# PowerShell Script zum Senden einer Test-Syslog-Nachricht (UDP)
$Server = "127.0.0.1"
$Port = 5140
$Message = "ERROR: Disk failure detected on drive C! (Test-Alert)"

$UdpClient = New-Object System.Net.Sockets.UdpClient
$EncodedMessage = [System.Text.Encoding]::UTF8.GetBytes($Message)
$UdpClient.Send($EncodedMessage, $EncodedMessage.Length, $Server, $Port)
$UdpClient.Close()

Write-Host "Test-Syslog gesendet an $Server`:$Port : '$Message'" -ForegroundColor Red
