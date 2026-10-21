param(
    [string]$PortName = 'COM4',
    [string]$ApiBase = 'http://127.0.0.1:8000',
    [string]$NodeKey = 'demo-key-change-me'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Ports
$serial = [System.IO.Ports.SerialPort]::new($PortName, 115200, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = 1500
$serial.DtrEnable = $false
$serial.RtsEnable = $false

try {
    $serial.Open()
    Write-Host "Listening on $PortName at 115200 baud; forwarding readings to $ApiBase. Press Ctrl+C to stop."
    while ($true) {
        try { $line = $serial.ReadLine().Trim() }
        catch [System.TimeoutException] { continue }
        if (-not $line.StartsWith('{')) {
            if ($line) { Write-Host $line }
            continue
        }
        try {
            $payload = $line | ConvertFrom-Json
            $body = $payload | ConvertTo-Json -Compress
            $result = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/readings" -Headers @{ 'X-Device-Key' = $NodeKey } -ContentType 'application/json' -Body $body -TimeoutSec 4
            $decision = $result.decision
            Write-Host ("LIVE {0} | MQ135 {1} | MQ4 {2} | {3} C | {4}% RH | risk {5}/100 ({6})" -f $payload.node_id, $payload.mq135, $payload.mq4, $payload.temperature, $payload.humidity, [math]::Round($decision.risk_score), $decision.label)
        }
        catch {
            Write-Warning "Reading not accepted by dashboard: $($_.Exception.Message)"
        }
    }
}
finally {
    if ($serial.IsOpen) { $serial.Close() }
}

