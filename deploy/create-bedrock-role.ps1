# create-bedrock-role.ps1
# Creates the IAM instance role App Runner uses to call Bedrock with NO static keys.
# Run from the repo root with the AWS CLI configured (aws configure / SSO):
#   .\deploy\create-bedrock-role.ps1
#
# Output: the Role ARN to paste into App Runner's "Instance role" field.

param(
    [string]$RoleName = "LegalGroundBedrockRole",
    [string]$PolicyName = "LegalGroundBedrockInvoke"
)

$ErrorActionPreference = "Stop"
$deployDir = $PSScriptRoot
$trust  = Join-Path $deployDir "iam-instance-role-trust.json"
$policy = Join-Path $deployDir "iam-bedrock-invoke-policy.json"

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI not found. Install it, then run 'aws configure'."
}

# Create the role (ignore error if it already exists), then attach the inline policy.
$exists = aws iam get-role --role-name $RoleName 2>$null
if (-not $exists) {
    Write-Host "Creating role $RoleName ..." -ForegroundColor Cyan
    aws iam create-role `
        --role-name $RoleName `
        --assume-role-policy-document "file://$trust" `
        --description "App Runner instance role for Legal Ground -> Bedrock InvokeModel" | Out-Null
} else {
    Write-Host "Role $RoleName already exists — updating policy only." -ForegroundColor Yellow
}

Write-Host "Attaching Bedrock invoke policy ..." -ForegroundColor Cyan
aws iam put-role-policy `
    --role-name $RoleName `
    --policy-name $PolicyName `
    --policy-document "file://$policy" | Out-Null

$arn = (aws iam get-role --role-name $RoleName --query "Role.Arn" --output text)
Write-Host "`nDone. Instance role ARN (paste into App Runner):" -ForegroundColor Green
Write-Host "  $arn" -ForegroundColor Green
