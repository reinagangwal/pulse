# Run this once from inside pulse-lambdas, after putting your real Groq key
# into secret-groq.json. Does everything: secret, IAM, zip, deploy, test.

$ErrorActionPreference = "Continue"

Write-Host "== Creating pulse/groq secret =="
aws secretsmanager create-secret --name pulse/groq --secret-string file://secret-groq.json --region us-east-1

Write-Host "== Updating IAM policies =="
aws iam put-role-policy --role-name bot-send-checkin-role-q2rzbatu --policy-name pulse-secrets-read --policy-document file://iam-policy-send-checkin.json --region us-east-1
aws iam put-role-policy --role-name bot-webhook-handler-role-qgy0srze --policy-name pulse-secrets-read --policy-document file://iam-policy-webhook-handler.json --region us-east-1

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
Write-Host "== If the above shows statusCode 200 with no errorMessage, check your WhatsApp now. =="
