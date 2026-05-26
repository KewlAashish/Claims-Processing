# Manual API Curl Runbook

Use this runbook for repeatable manual checks against the running FastAPI service.
The commands are written for PowerShell and use `curl.exe` so they do not collide
with PowerShell's `curl` alias.

## Start The API

```powershell
uvicorn app.main:app --reload
```

In another terminal, set a base URL and a unique run ID:

```powershell
$BaseUrl = "http://localhost:8000"
$RunId = Get-Date -Format "yyyyMMddHHmmss"
```

## Health Check

```powershell
curl.exe "$BaseUrl/health"
```

## Happy Path: Approved Claim And Payment

Create a member:

```powershell
$Member = curl.exe -s -X POST "$BaseUrl/members" `
  -H "Content-Type: application/json" `
  -d "{""full_name"":""Manual Approved Member"",""date_of_birth"":""1990-01-01"",""external_member_id"":""MANUAL-APPROVED-$RunId""}" `
  | ConvertFrom-Json

$Member | ConvertTo-Json -Depth 10
```

Create a policy:

```powershell
$Policy = curl.exe -s -X POST "$BaseUrl/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_number"":""MANUAL-APPROVED-POL-$RunId"",""name"":""Manual Approved Plan"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json

$Policy | ConvertTo-Json -Depth 10
```

Add a covered OPD rule with no deductible:

```powershell
$CoverageRule = curl.exe -s -X POST "$BaseUrl/policies/$($Policy.id)/coverage-rules" `
  -H "Content-Type: application/json" `
  -d "{""coverage_type"":""OPD"",""annual_limit"":""10000"",""deductible_amount"":""0"",""covered"":true}" `
  | ConvertFrom-Json

$CoverageRule | ConvertTo-Json -Depth 10
```

Enroll the member in the policy:

```powershell
$Enrollment = curl.exe -s -X POST "$BaseUrl/members/$($Member.id)/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_id"":""$($Policy.id)"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json

$Enrollment | ConvertTo-Json -Depth 10
```

Submit a covered claim:

```powershell
$Claim = curl.exe -s -X POST "$BaseUrl/claims" `
  -H "Content-Type: application/json" `
  -d "{""member_id"":""$($Member.id)"",""policy_id"":""$($Policy.id)"",""diagnosis_code"":""J10"",""provider_name"":""City Clinic"",""line_items"":[{""coverage_type"":""OPD"",""service_date"":""2026-03-01"",""description"":""Consultation"",""submitted_amount"":""2000""}]}" `
  | ConvertFrom-Json

$Claim | ConvertTo-Json -Depth 10
```

Fetch the claim:

```powershell
$FetchedClaim = curl.exe -s "$BaseUrl/claims/$($Claim.id)" | ConvertFrom-Json
$FetchedClaim | ConvertTo-Json -Depth 10
```

Mark the approved claim as paid:

```powershell
$PaidClaim = curl.exe -s -X POST "$BaseUrl/claims/$($Claim.id)/pay" | ConvertFrom-Json
$PaidClaim | ConvertTo-Json -Depth 10
```

## Partial Approval: Deductible Applied

Create an isolated member and policy:

```powershell
$DeductibleMember = curl.exe -s -X POST "$BaseUrl/members" `
  -H "Content-Type: application/json" `
  -d "{""full_name"":""Manual Deductible Member"",""date_of_birth"":""1990-01-01"",""external_member_id"":""MANUAL-DEDUCTIBLE-$RunId""}" `
  | ConvertFrom-Json

$DeductiblePolicy = curl.exe -s -X POST "$BaseUrl/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_number"":""MANUAL-DEDUCTIBLE-POL-$RunId"",""name"":""Manual Deductible Plan"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json
```

Add an OPD rule with a `1000` deductible, then enroll:

```powershell
curl.exe -s -X POST "$BaseUrl/policies/$($DeductiblePolicy.id)/coverage-rules" `
  -H "Content-Type: application/json" `
  -d "{""coverage_type"":""OPD"",""annual_limit"":""10000"",""deductible_amount"":""1000"",""covered"":true}" `
  | ConvertFrom-Json `
  | ConvertTo-Json -Depth 10

curl.exe -s -X POST "$BaseUrl/members/$($DeductibleMember.id)/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_id"":""$($DeductiblePolicy.id)"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json `
  | ConvertTo-Json -Depth 10
```

Submit a claim where the deductible reduces payment:

```powershell
$DeductibleClaim = curl.exe -s -X POST "$BaseUrl/claims" `
  -H "Content-Type: application/json" `
  -d "{""member_id"":""$($DeductibleMember.id)"",""policy_id"":""$($DeductiblePolicy.id)"",""diagnosis_code"":""J10"",""provider_name"":""City Clinic"",""line_items"":[{""coverage_type"":""OPD"",""service_date"":""2026-03-01"",""description"":""Deductible consultation"",""submitted_amount"":""2000""}]}" `
  | ConvertFrom-Json

$DeductibleClaim | ConvertTo-Json -Depth 10
```

Expected behavior: claim status is `PARTIALLY_APPROVED`, with decision code
`PARTIAL_DEDUCTIBLE_APPLIED`.

## Partial Approval: Annual Limit Remaining

Create an isolated member and policy:

```powershell
$LimitMember = curl.exe -s -X POST "$BaseUrl/members" `
  -H "Content-Type: application/json" `
  -d "{""full_name"":""Manual Limit Member"",""date_of_birth"":""1990-01-01"",""external_member_id"":""MANUAL-LIMIT-$RunId""}" `
  | ConvertFrom-Json

$LimitPolicy = curl.exe -s -X POST "$BaseUrl/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_number"":""MANUAL-LIMIT-POL-$RunId"",""name"":""Manual Limit Plan"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json
```

Add a limited OPD rule, then enroll:

```powershell
curl.exe -s -X POST "$BaseUrl/policies/$($LimitPolicy.id)/coverage-rules" `
  -H "Content-Type: application/json" `
  -d "{""coverage_type"":""OPD"",""annual_limit"":""10000"",""deductible_amount"":""0"",""covered"":true}" `
  | ConvertFrom-Json `
  | ConvertTo-Json -Depth 10

curl.exe -s -X POST "$BaseUrl/members/$($LimitMember.id)/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_id"":""$($LimitPolicy.id)"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json `
  | ConvertTo-Json -Depth 10
```

Use most of the annual limit with the first claim:

```powershell
$FirstLimitClaim = curl.exe -s -X POST "$BaseUrl/claims" `
  -H "Content-Type: application/json" `
  -d "{""member_id"":""$($LimitMember.id)"",""policy_id"":""$($LimitPolicy.id)"",""diagnosis_code"":""J10"",""provider_name"":""City Clinic"",""line_items"":[{""coverage_type"":""OPD"",""service_date"":""2026-03-01"",""description"":""Large consultation package"",""submitted_amount"":""9000""}]}" `
  | ConvertFrom-Json

$FirstLimitClaim | ConvertTo-Json -Depth 10
```

Submit a second claim that exceeds the remaining limit:

```powershell
$SecondLimitClaim = curl.exe -s -X POST "$BaseUrl/claims" `
  -H "Content-Type: application/json" `
  -d "{""member_id"":""$($LimitMember.id)"",""policy_id"":""$($LimitPolicy.id)"",""diagnosis_code"":""J10"",""provider_name"":""City Clinic"",""line_items"":[{""coverage_type"":""OPD"",""service_date"":""2026-04-01"",""description"":""Follow-up consultation package"",""submitted_amount"":""2500""}]}" `
  | ConvertFrom-Json

$SecondLimitClaim | ConvertTo-Json -Depth 10
```

Expected behavior: second claim status is `PARTIALLY_APPROVED`, with decision
code `PARTIAL_LIMIT_REMAINING`.

## Denial: Coverage Not Covered

Create an isolated member and policy:

```powershell
$DeniedMember = curl.exe -s -X POST "$BaseUrl/members" `
  -H "Content-Type: application/json" `
  -d "{""full_name"":""Manual Denied Member"",""date_of_birth"":""1990-01-01"",""external_member_id"":""MANUAL-DENIED-$RunId""}" `
  | ConvertFrom-Json

$DeniedPolicy = curl.exe -s -X POST "$BaseUrl/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_number"":""MANUAL-DENIED-POL-$RunId"",""name"":""Manual Denied Plan"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json
```

Add an uncovered dental rule, then enroll:

```powershell
curl.exe -s -X POST "$BaseUrl/policies/$($DeniedPolicy.id)/coverage-rules" `
  -H "Content-Type: application/json" `
  -d "{""coverage_type"":""DENTAL"",""annual_limit"":""0"",""deductible_amount"":""0"",""covered"":false}" `
  | ConvertFrom-Json `
  | ConvertTo-Json -Depth 10

curl.exe -s -X POST "$BaseUrl/members/$($DeniedMember.id)/policies" `
  -H "Content-Type: application/json" `
  -d "{""policy_id"":""$($DeniedPolicy.id)"",""effective_start_date"":""2026-01-01"",""effective_end_date"":""2026-12-31""}" `
  | ConvertFrom-Json `
  | ConvertTo-Json -Depth 10
```

Submit a dental claim:

```powershell
$DeniedClaim = curl.exe -s -X POST "$BaseUrl/claims" `
  -H "Content-Type: application/json" `
  -d "{""member_id"":""$($DeniedMember.id)"",""policy_id"":""$($DeniedPolicy.id)"",""diagnosis_code"":""K08"",""provider_name"":""Dental Clinic"",""line_items"":[{""coverage_type"":""DENTAL"",""service_date"":""2026-03-01"",""description"":""Dental cleaning"",""submitted_amount"":""1500""}]}" `
  | ConvertFrom-Json

$DeniedClaim | ConvertTo-Json -Depth 10
```

Expected behavior: claim status is `DENIED`, with decision code
`DENIED_NOT_COVERED`.

## Dispute A Decided Claim

Use any existing decided claim ID from the previous sections, then create a dispute:

```powershell
$Dispute = curl.exe -s -X POST "$BaseUrl/claims/$($DeniedClaim.id)/disputes" `
  -H "Content-Type: application/json" `
  -d "{""reason"":""Member believes the provider submitted additional records.""}" `
  | ConvertFrom-Json

$Dispute | ConvertTo-Json -Depth 10
```

Fetch the disputed claim:

```powershell
$DisputedClaim = curl.exe -s "$BaseUrl/claims/$($DeniedClaim.id)" | ConvertFrom-Json
$DisputedClaim | ConvertTo-Json -Depth 10
```

Expected behavior: dispute status is `OPEN` and claim status is `DISPUTED`.

## Useful Error Checks

Fetch a missing claim:

```powershell
curl.exe -i "$BaseUrl/claims/not-a-real-claim-id"
```

Submit a claim with duplicate line items:

```powershell
curl.exe -i -X POST "$BaseUrl/claims" `
  -H "Content-Type: application/json" `
  -d "{""member_id"":""$($Member.id)"",""policy_id"":""$($Policy.id)"",""diagnosis_code"":""J10"",""provider_name"":""City Clinic"",""line_items"":[{""coverage_type"":""OPD"",""service_date"":""2026-03-01"",""description"":""Duplicate item"",""submitted_amount"":""100""},{""coverage_type"":""OPD"",""service_date"":""2026-03-01"",""description"":""Duplicate item"",""submitted_amount"":""100""}]}"
```

Expected behavior: response status is `422`.
