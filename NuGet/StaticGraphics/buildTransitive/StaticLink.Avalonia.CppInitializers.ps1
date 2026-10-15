param(
    [Parameter(Mandatory = $true)][string]$InputLibrary,
    [Parameter(Mandatory = $true)][string]$OutputLibrary
)
$ErrorActionPreference = 'Stop'
[byte[]]$bytes = [IO.File]::ReadAllBytes([IO.Path]::GetFullPath($InputLibrary))
$ascii = [Text.Encoding]::ASCII
if ($ascii.GetString($bytes, 0, 8) -ne "!<arch>`n") { throw 'Expected an ordinary LLVM archive' }
$member = 8
$converted = 0
while ($member + 60 -le $bytes.Length) {
    $size = [int]::Parse($ascii.GetString($bytes, $member + 48, 10).Trim())
    $start = $member + 60
    $end = $start + $size
    if ($end -gt $bytes.Length) { throw 'Invalid archive member size' }
    $machine = if ($size -ge 20) { [BitConverter]::ToUInt16($bytes, $start) } else { 0 }
    if ($machine -in @(0x14c, 0x8664, 0xaa64)) {
        $sections = [BitConverter]::ToUInt16($bytes, $start + 2)
        $sectionStart = $start + 20 + [BitConverter]::ToUInt16($bytes, $start + 16)
        $symbols = [BitConverter]::ToUInt32($bytes, $start + 8)
        $count = [BitConverter]::ToUInt32($bytes, $start + 12)
        $strings = $start + $symbols + 18 * $count
        for ($i = 0; $i -lt $sections; $i++) {
            $at = $sectionStart + 40 * $i
            if ($at + 40 -gt $end) { throw 'Invalid COFF section table' }
            $name = $ascii.GetString($bytes, $at, 8).TrimEnd([char]0)
            $longName = -1
            if ($name.StartsWith('/')) {
                $longName = $strings + [int]::Parse($name.Substring(1))
                if ($longName -ge $end) { throw 'Invalid COFF section name' }
                $last = $longName
                while ($last -lt $end -and $bytes[$last] -ne 0) { $last++ }
                $name = $ascii.GetString($bytes, $longName, $last - $longName)
            }
            if (-not $name.StartsWith('.ctors')) { continue }
            # LLVM's libc++ uses priority 101 for iostream and Win7's clock
            # fallback. MSVC startup walks .CRT$XC*, not MinGW's .ctors list.
            $newName = switch ($name) {
                '.ctors' { '.CRT$XCU' }
                '.ctors.65435' { '.CRT$XCT' }
                default { throw "New constructor priority $name requires review" }
            }
            $ascii.GetBytes($newName).CopyTo($bytes, $at)
            if ($longName -ge 0) {
                # Section symbols also refer to this string-table entry. Keep
                # every offset/member size unchanged, including archive indexes.
                for ($j = 0; $j -lt $name.Length; $j++) { $bytes[$longName + $j] = 0 }
                $ascii.GetBytes($newName).CopyTo($bytes, $longName)
            }
            $converted++
        }
    }
    $member = $end + ($size % 2)
}
$OutputLibrary = [IO.Path]::GetFullPath($OutputLibrary)
New-Item -ItemType Directory -Force -Path (Split-Path $OutputLibrary) | Out-Null
[IO.File]::WriteAllBytes($OutputLibrary, $bytes)
Write-Host "Registered $converted libc++ constructor sections with MSVC startup."
