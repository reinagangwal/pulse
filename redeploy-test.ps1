$ErrorActionPreference = "Continue"

Write-Host "== Zipping updated code =="
Push-Location bot-send-checkin
Compress-Archive -Path * -DestinationPath ..\bot-send-checkin-updated.zip -Force
Pop-Location
Push-Location bot-webhook-handler
Compress-Archive -Path * -DestinationPath ..\bot-webhook-handler-updated.zip -Force
Pop-Location

Write-Host "== Deploying code =="
aws lambda update-function-code --function-name bot-send-checkin --zip-file fileb://bot-send-checkin-updated.zip --region us-east-1 | Out-Null
aws lambda update-function-code --function-name bot-webhook-handler --zip-file fileb://bot-webhook-handler-updated.zip --region us-east-1 | Out-Null

Write-Host "== Waiting for deploy to finish =="
Start-Sleep -Seconds 15

Write-Host "== Testing bot-send-checkin =="
aws lambda invoke --function-name bot-send-checkin --payload file://payload.json --region us-east-1 out.json | Out-Null
Get-Content out.json

Write-Host ""
Write-Host "== If no errorMessage above, check your WhatsApp now. =="
