$baseUrl = "http://127.0.0.1:5000"

function Invoke-Post($uri, $body) {
    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -Body ($body | ConvertTo-Json -Depth 10) -ContentType "application/json"
        return $response
    } catch {
        Write-Host "Error calling $uri"
        Write-Host $_.Exception.Message
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host $reader.ReadToEnd()
        }
        return $null
    }
}

function Invoke-Get($uri) {
    try {
        return Invoke-RestMethod -Uri $uri -Method Get
    } catch {
        Write-Host "Error calling $uri"
        Write-Host $_.Exception.Message
        return $null
    }
}

Write-Host "1. Loading participants..."
$loadData = Invoke-Post "$baseUrl/load_data" @{ swiss_rounds = 4 }
if (-not $loadData.success) { Write-Host "Failed to load data"; exit }

Write-Host "`n2. Getting Round 1 tables..."
$tablesData = Invoke-Get "$baseUrl/get_tables/1"
if (-not $tablesData.success) { Write-Host "Failed to get tables"; exit }

$tables = $tablesData.tables
Write-Host "   Got $($tables.PSObject.Properties.Count) tables"

Write-Host "`n3. Submitting table results..."
foreach ($tableName in $tables.PSObject.Properties.Name) {
    $players = $tables.$tableName
    $results = @()
    
    # Points: 5, 0, 1, 1
    $points = @(5, 0, 1, 1)
    
    for ($i = 0; $i -lt $players.Count; $i++) {
        $player = $players[$i]
        # Use $playerId instead of $pid to avoid read-only variable error
        $playerId = if ($player."Player ID") { $player."Player ID" } else { $player.id }
        
        $results += @{
            player_id = $playerId
            points = $points[$i % 4]
        }
    }
    
    Write-Host "   Submitting $tableName..."
    $submitParams = @{
        round = 1
        table = $tableName
        results = $results
    }
    $resp = Invoke-Post "$baseUrl/submit_table_results" $submitParams
    if (-not $resp.success) { Write-Host "   Failed to submit $tableName" }
}

Write-Host "`n4. Finalizing Round 1..."
$finalizeParams = @{
    round = 1
    results = @()
}
$finalizeResp = Invoke-Post "$baseUrl/submit_player_results" $finalizeParams
Write-Host "   Response: $finalizeResp"
