param(
    [Parameter(Mandatory = $true)][string]$InputLibrary,
    [Parameter(Mandatory = $true)][string]$OutputLibrary
)
$ErrorActionPreference = 'Stop'
$InputLibrary = [IO.Path]::GetFullPath($InputLibrary)
$OutputLibrary = [IO.Path]::GetFullPath($OutputLibrary)
$directory = Split-Path $OutputLibrary
New-Item -ItemType Directory -Force -Path $directory | Out-Null
Copy-Item $InputLibrary $OutputLibrary -Force
$members = @(& llvm-ar t $InputLibrary | Where-Object { $_ -match '[/\\]UnwindRegisters(Save|Restore)\.obj$|^UnwindRegisters(Save|Restore)\.obj$' })
if ($LASTEXITCODE -ne 0 -or $members.Count -ne 2) { throw 'Expected the two pinned libunwind register assembly objects' }
$scratch = Join-Path $directory 'safeseh-objects'
New-Item -ItemType Directory -Force -Path $scratch | Out-Null
Push-Location $scratch
try {
    & llvm-ar x $InputLibrary @members
    if ($LASTEXITCODE -ne 0) { throw 'Could not extract libunwind assembly objects' }
    foreach ($name in @('UnwindRegistersSave.obj', 'UnwindRegistersRestore.obj')) {
        $path = Join-Path $scratch $name
        [byte[]]$bytes = [IO.File]::ReadAllBytes($path)
        if ([BitConverter]::ToUInt16($bytes, 0) -ne 0x14c) { throw 'SafeSEH fix requires an ordinary x86 COFF object' }
        $sections = [BitConverter]::ToUInt16($bytes, 2)
        $sectionStart = 20 + [BitConverter]::ToUInt16($bytes, 16)
        $expectedCode = @{
            'UnwindRegistersSave.obj' = '3c22774cb39f33e0043619341e1ec2de0f6cfa310bfa1d9b6fdd15973fd08a69'
            'UnwindRegistersRestore.obj' = '36af0143b7f4d8e511e2a2d0179f5cf357a7ab91a1099c5fb16eaf5dca9ef397'
        }[$name]
        $codeChecked = $false
        for ($i = 0; $i -lt $sections; $i++) {
            $at = $sectionStart + 40 * $i
            $sectionName = [Text.Encoding]::ASCII.GetString($bytes, $at, 8).TrimEnd([char]0)
            if ($sectionName -eq '.sxdata') { throw 'Register assembly unexpectedly declares SEH handlers; review it first' }
            if ($sectionName -eq '.text') {
                $size = [BitConverter]::ToUInt32($bytes, $at + 16)
                $offset = [BitConverter]::ToUInt32($bytes, $at + 20)
                [byte[]]$code = New-Object byte[] $size
                [Array]::Copy($bytes, $offset, $code, 0, $size)
                $sha = [Security.Cryptography.SHA256]::Create()
                try { $hash = [BitConverter]::ToString($sha.ComputeHash($code)).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
                if ($hash -ne $expectedCode) { throw 'libunwind assembly changed; review its SEH behavior before updating the allowed hash' }
                $codeChecked = $true
            }
        }
        if (-not $codeChecked) { throw 'Missing audited register assembly code' }
        $symbols = [BitConverter]::ToUInt32($bytes, 8)
        $count = [BitConverter]::ToUInt32($bytes, 12)
        $stringTable = $symbols + 18 * $count
        if ($symbols -eq 0 -or $stringTable + 4 -gt $bytes.Length) { throw 'Invalid COFF symbol table' }
        for ($i = 0; $i -lt $count; $i++) {
            $at = $symbols + 18 * $i
            if ([Text.Encoding]::ASCII.GetString($bytes, $at, 8) -eq '@feat.00') { throw 'Unexpected existing feature metadata; review the new toolchain' }
            $i += $bytes[$at + 17]
        }
        # These two audited leaf assembly routines only save/restore registers;
        # neither installs an SEH handler. Bit 0 declares that fact to /SAFESEH.
        [byte[]]$symbol = New-Object byte[] 18
        [Text.Encoding]::ASCII.GetBytes('@feat.00').CopyTo($symbol, 0)
        [BitConverter]::GetBytes([uint32]1).CopyTo($symbol, 8)
        [BitConverter]::GetBytes([int16]-1).CopyTo($symbol, 12)
        $symbol[16] = 3 # static absolute symbol
        [byte[]]$updated = New-Object byte[] ($bytes.Length + 18)
        [Array]::Copy($bytes, 0, $updated, 0, $stringTable)
        [Array]::Copy($symbol, 0, $updated, $stringTable, 18)
        [Array]::Copy($bytes, $stringTable, $updated, $stringTable + 18, $bytes.Length - $stringTable)
        [BitConverter]::GetBytes([uint32]($count + 1)).CopyTo($updated, 12)
        [IO.File]::WriteAllBytes($path, $updated)
    }
    & llvm-ar r $OutputLibrary UnwindRegistersSave.obj UnwindRegistersRestore.obj
    if ($LASTEXITCODE -ne 0) { throw 'Could not replace libunwind assembly objects' }
    & llvm-ar s $OutputLibrary
    if ($LASTEXITCODE -ne 0) { throw 'Could not index libunwind archive' }
} finally { Pop-Location }
Write-Host 'Added x86 SafeSEH metadata to the two register-only libunwind assembly objects.'
