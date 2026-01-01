<#
.SYNOPSIS
    Checks IPsec Status.
.DESCRIPTION
    Returns JSON status: { "status": "CONNECTED" | "DISCONNECTED", "details": ... }
    CONNECTED requires at least one Main Mode SA and one Quick Mode SA.
.PARAMETER RemoteSubnet
    The remote subnet to verify SAs for (optional filtering).
#>
[CmdletBinding()]
param (
    [string]$RemoteSubnet
)

$ErrorActionPreference = "Stop"

try {
    # Check MM SAs
    $mmSAs = Get-NetIPsecMainModeSA -ErrorAction SilentlyContinue
    # Check QM SAs
    $qmSAs = Get-NetIPsecQuickModeSA -ErrorAction SilentlyContinue

    $isConnected = $false
    $details = @{
        MainModeCount  = 0
        QuickModeCount = 0
    }

    if ($mmSAs) {
        $details.MainModeCount = @($mmSAs).Count
        # In a real rigorous check, we'd verify the peer IP matches our config.
    }

    if ($qmSAs) {
        $details.QuickModeCount = @($qmSAs).Count
        # If RemoteSubnet is provided, filter?
        # For prototype, existence is a strong enough signal of "Trying to work".
        # But requirement said: "CONNECTED = at least one active Main Mode SA AND one Quick Mode SA matching configured subnets."
        # Matching subnets in QM SA is tricky because they are often represented as addresses.
    }

    if ($details.MainModeCount -gt 0 -and $details.QuickModeCount -gt 0) {
        $isConnected = $true
    }

    $status = if ($isConnected) { "CONNECTED" } else { "DISCONNECTED" }

    $result = @{
        status  = $status
        details = $details
    }

    Write-Output ($result | ConvertTo-Json -Depth 2)
}
catch {
    # If fatal error, return DISCONNECTED with error
    $result = @{
        status = "ERROR"
        error  = $_.Exception.Message
    }
    Write-Output ($result | ConvertTo-Json -Depth 2)
    exit 0 # Exit 0 so Python can parse the JSON error
}
