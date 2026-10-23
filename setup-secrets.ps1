# Run this from inside the pulse-lambdas folder.
# Fill in the two rotated secret values below FIRST.

$TwilioAuthToken = "6deb50ca24e1d40e62c31159c763a4d3"
$HFToken = "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"

Write-Host "Creating secrets..."
aws secretsmanager create-secret --name pulse/twilio --secret-string "{\"account_sid\":\"AC528ecd8feefe84fbabc0caea114028b8\",\"auth_token\":\"$TwilioAuthToken\"}" --region us-east-1
aws secretsmanager create-secret --name pulse/huggingface --secret-string "{\"token\":\"$HFToken\"}" --region us-east-1

Write-Host "Attaching IAM policies..."
aws iam put-role-policy --role-name bot-send-checkin-role-q2rzbatu --policy-name pulse-secrets-read --policy-document file://iam-policy-send-checkin.json --region us-east-1
aws iam put-role-policy --role-name bot-webhook-handler-role-qgy0srze --policy-name pulse-secrets-read --policy-document file://iam-policy-webhook-handler.json --region us-east-1

Write-Host "Zipping updated functions..."
Push-Location bot-send-checkin
Compress-Archive -Path * -DestinationPath ..\bot-send-checkin-updated.zip -Force
Pop-Location
Push-Location bot-webhook-handler
Compress-Archive -Path * -DestinationPath ..\bot-webhook-handler-updated.zip -Force
Pop-Location

Write-Host "Deploying code..."
aws lambda update-function-code --function-name bot-send-checkin --zip-file fileb://bot-send-checkin-updated.zip --region us-east-1
aws lambda update-function-code --function-name bot-webhook-handler --zip-file fileb://bot-webhook-handler-updated.zip --region us-east-1

Write-Host "Updating environment variables (removing plaintext secrets)..."
aws lambda update-function-configuration --function-name bot-send-checkin --environment file://env-send-checkin.json --region us-east-1
aws lambda update-function-configuration --function-name bot-webhook-handler --environment file://env-webhook-handler.json --region us-east-1

Write-Host "Waiting 10s for updates to finish propagating..."
Start-Sleep -Seconds 10

Write-Host "Testing bot-send-checkin..."
aws lambda invoke --function-name bot-send-checkin --cli-binary-format raw-in-base64-out --payload "{\"checkin_type\":\"morning\"}" --region us-east-1 out.json
Get-Content out.json

Write-Host "Done. Check out.json above for errors, and check your WhatsApp for the actual message."
