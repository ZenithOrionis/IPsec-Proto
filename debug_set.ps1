$ErrorActionPreference = "Stop"
Write-Host "Diagnostic: Testing New-NetIPsecPhase1AuthSet..."

try {
    $prop = New-NetIPsecAuthProposal -Machine -PreSharedKey "TestKey123"
    Write-Host "SUCCESS: Created Proposal."
    
    $set = New-NetIPsecPhase1AuthSet -DisplayName "TestSet" -Proposal $prop
    Write-Host "SUCCESS: Created Auth Set."
    
    $set | Format-List *
    
    # Cleanup
    Remove-NetIPsecPhase1AuthSet -Name "TestSet" -ErrorAction SilentlyContinue
}
catch {
    Write-Error "FAILURE: $_"
}
