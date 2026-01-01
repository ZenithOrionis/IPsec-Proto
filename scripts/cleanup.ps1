<#
.SYNOPSIS
    Cleans up IPsec Policy created by Unified Agent.
.DESCRIPTION
    Removes all rules, crypto sets, and auth sets associated with the 'UnifiedIPsecAgent' group.
#>
[CmdletBinding()]
param ()

$ErrorActionPreference = "Continue" # Don't stop on individual failure, try to clean everything

$GroupName = "UnifiedIPsecAgent"

Write-Host "Cleaning up IPsec policies for group: $GroupName"

# Remove Rule
try {
    Remove-NetIPsecRule -Group $GroupName -ErrorAction SilentlyContinue
    Write-Host "Removed IPsec Rules."
}
catch {
    Write-Warning "Failed to remove IPsec Rules."
}

# Remove Phase 1 Auth
try {
    Remove-NetIPsecPhase1AuthSet -Group $GroupName -ErrorAction SilentlyContinue
    Write-Host "Removed Phase 1 Auth Sets."
}
catch {
    Write-Warning "Failed to remove Phase 1 Auth Sets."
}

# Remove Main Mode Crypto
try {
    Remove-NetIPsecMainModeCryptoSet -Group $GroupName -ErrorAction SilentlyContinue
    Write-Host "Removed Main Mode Crypto Sets."
}
catch {
    Write-Warning "Failed to remove Main Mode Crypto Sets."
}

# Remove Quick Mode Crypto
try {
    Remove-NetIPsecQuickModeCryptoSet -Group $GroupName -ErrorAction SilentlyContinue
    Write-Host "Removed Quick Mode Crypto Sets."
}
catch {
    Write-Warning "Failed to remove Quick Mode Crypto Sets."
}

Write-Host "Cleanup Complete."
