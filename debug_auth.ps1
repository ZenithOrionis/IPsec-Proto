$ErrorActionPreference = "Stop"
Write-Host "Diagnostic: Testing New-NetIPsecAuthProposal..."

try {
    $prop = New-NetIPsecAuthProposal -Machine -PreSharedKey "TestKey123"
    Write-Host "SUCCESS: Created Proposal object."
    $prop | Format-List *
}
catch {
    Write-Error "FAILURE: $_"
}
