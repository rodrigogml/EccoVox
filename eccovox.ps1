param(
    [Parameter(Position = 0)]
    [ValidateSet('install','start','stop','kill','restart','status','run','service-install','service-remove','service-start','service-stop')]
    [string]$Command = 'status',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
$manager = Join-Path $root 'scripts\manage.py'

if ($Command -eq 'install' -and -not (Test-Path -LiteralPath $venvPython)) {
    $bootstrapPython = (Get-Command python -ErrorAction Stop).Source
    & $bootstrapPython $manager $Command @Arguments
} else {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw 'EccoVox ainda não está instalado. Execute .\eccovox.ps1 install.'
    }
    & $venvPython $manager $Command @Arguments
}
exit $LASTEXITCODE
