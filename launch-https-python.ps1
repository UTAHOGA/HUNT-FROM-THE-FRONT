$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Start-Process -WindowStyle Hidden -FilePath python -ArgumentList @('https_server.py') -WorkingDirectory $PSScriptRoot
Start-Sleep -Seconds 1
Get-NetTCPConnection -LocalPort 8443 -State Listen | Select-Object -First 1 LocalAddress,LocalPort,State,OwningProcess
