[CmdletBinding()]
param([switch]$RefreshRuntime, [switch]$PrintRuntime, [switch]$PrintRuntimeId)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = [Console]::OutputEncoding
if (-not $env:PATHEXT) { $env:PATHEXT = '.COM;.EXE;.BAT;.CMD' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$pluginRoot = Split-Path $PSScriptRoot -Parent
$manifest = Get-Content -LiteralPath (Join-Path $pluginRoot 'runtime\manifest.json') -Raw | ConvertFrom-Json
$architecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
if ($architecture -ne 'AMD64' -or $manifest.platform -ne 'win-x64') { throw 'unsupported_runtime_platform_win_x64_required' }
if ($manifest.schema -ne 1 -or $manifest.runtime_id -notmatch '^win-x64-[a-zA-Z0-9.-]+$' -or $manifest.sha256 -notmatch '^[a-f0-9]{64}$') {
  throw 'invalid_runtime_manifest'
}
if ($manifest.archive -ne 'quantdinger-runtime-win-x64.zip') { throw 'invalid_runtime_archive_name' }
$root = Join-Path $env:LOCALAPPDATA 'QuantDinger\Connector'
$versions = Join-Path $root 'runtimes'
$target = Join-Path $versions $manifest.runtime_id
$archive = Join-Path $pluginRoot ('runtime\' + $manifest.archive)
New-Item -ItemType Directory -Force -Path $versions | Out-Null

function Get-SafeChild([string]$Parent, [string]$Relative) {
  if ([IO.Path]::IsPathRooted($Relative) -or $Relative.Contains(':')) { throw 'invalid_archive_entry' }
  $prefix = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
  $child = [IO.Path]::GetFullPath((Join-Path $Parent $Relative))
  if (-not $child.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'archive_path_escape' }
  return $child
}

function Test-Runtime([string]$Directory, [switch]$Full) {
  try {
    $inventoryFile = Join-Path $Directory 'inventory.json'
    if (-not (Test-Path -LiteralPath $inventoryFile)) { return $false }
    if ((Get-FileHash -LiteralPath $inventoryFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.inventory_sha256) { return $false }
    $inventory = Get-Content -LiteralPath $inventoryFile -Raw | ConvertFrom-Json
    $critical = @('python/python.exe', 'python/python313.dll', 'python/python313.zip', 'python/python313._pth', 'app/connector.py', 'app/connector-tools.json', 'app/runtime-check.py')
    foreach ($entry in $inventory.PSObject.Properties) {
      if (-not $Full -and $critical -notcontains $entry.Name) { continue }
      $file = Get-SafeChild $Directory $entry.Name
      if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { return $false }
      if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { return $false }
    }
    foreach ($name in $critical) {
      if (-not $inventory.PSObject.Properties[$name]) { return $false }
    }
    return $true
  } catch { return $false }
}

$installLock = $null
$deadline = [DateTime]::UtcNow.AddSeconds(120)
while ($null -eq $installLock) {
  try {
    $installLock = [IO.File]::Open((Join-Path $root 'offline-install.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
  } catch [IO.IOException] {
    if ([DateTime]::UtcNow -gt $deadline) { throw 'runtime_installation_in_progress' }
    Start-Sleep -Milliseconds 250
  }
}
try {
  $ready = Test-Path -LiteralPath (Join-Path $target '.complete')
  if (-not $ready -or -not (Test-Runtime $target -Full:$RefreshRuntime)) {
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256) { throw 'runtime_archive_hash_mismatch' }
    $stage = Join-Path $versions ('staging-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
      foreach ($entry in $zip.Entries) {
        $destination = Get-SafeChild $stage $entry.FullName
        if ($entry.FullName.EndsWith('/')) {
          New-Item -ItemType Directory -Force -Path $destination | Out-Null
        } else {
          New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
          [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destination, $false)
        }
      }
    } finally { $zip.Dispose() }
    if (-not (Test-Runtime $stage -Full)) { throw 'runtime_file_hash_mismatch' }
    $python = Join-Path $stage 'python\python.exe'
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $python
    $start.Arguments = '-I "' + (Join-Path $stage 'app\runtime-check.py') + '"'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $check = New-Object System.Diagnostics.Process
    $check.StartInfo = $start
    try {
      if (-not $check.Start()) { throw 'runtime_self_check_start_failed' }
      $stdout = $check.StandardOutput.ReadToEndAsync()
      $stderr = $check.StandardError.ReadToEndAsync()
      if (-not $check.WaitForExit(30000)) {
        $check.Kill()
        throw 'runtime_self_check_timeout'
      }
      $check.WaitForExit()
      if ($check.ExitCode -ne 0) { throw 'runtime_self_check_failed' }
    } finally { $check.Dispose() }
    [IO.File]::WriteAllText((Join-Path $stage '.complete'), $manifest.sha256)
    if (Test-Path -LiteralPath $target) {
      $quarantine = Join-Path $versions ('quarantine-' + [Guid]::NewGuid().ToString('N'))
      $checkedSource = Get-SafeChild $versions $manifest.runtime_id
      $checkedTarget = Get-SafeChild $versions (Split-Path $quarantine -Leaf)
      Move-Item -LiteralPath $checkedSource -Destination $checkedTarget
    }
    $checkedStage = Get-SafeChild $versions (Split-Path $stage -Leaf)
    $checkedFinal = Get-SafeChild $versions $manifest.runtime_id
    Move-Item -LiteralPath $checkedStage -Destination $checkedFinal
  }
} finally {
  $installLock.Dispose()
}
if ($PrintRuntime) { Write-Output $target }
if ($PrintRuntimeId) { Write-Output $manifest.runtime_id }
