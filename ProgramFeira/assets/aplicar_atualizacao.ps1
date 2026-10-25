# Helper local. Não recebe comandos do servidor e não toca na pasta de dados.
param([Parameter(Mandatory=$true)][string]$Parametros, [switch]$SemDialogo)
$ErrorActionPreference = 'Stop'
$stage = Split-Path -Parent $Parametros
$anterior = $null
$trocou = $false
$moveuAnterior = $false
$novoProcesso = $null
function SemLinks([string]$caminho) {
    $item = Get-Item -LiteralPath $caminho -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Pasta redirecionada. Atualizacao cancelada.'
        }
        $item = $item.Parent
    }
}
function Mover([string]$origem, [string]$destino) {
    for ($i = 0; $i -lt 30; $i++) {
        try {
            SemLinks $origem
            SemLinks (Split-Path -Parent $destino)
            [IO.Directory]::Move($origem, $destino)
            return
        } catch {
            if ($i -eq 29) { throw }
            Start-Sleep -Milliseconds 200
        }
    }
}
try {
    SemLinks $stage
    $p = Get-Content -LiteralPath $Parametros -Raw -Encoding UTF8 | ConvertFrom-Json
    $pai = Split-Path -Parent $p.alvo
    if ((Split-Path -Parent $stage) -ne $pai -or
        (Split-Path -Leaf $stage) -notlike '.feira-atualizacao-*' -or
        $p.nova -ne (Join-Path $stage 'nova\GestaoDaFeira') -or
        $p.versao -notmatch '^\d+\.\d+\.\d+$') { throw 'Parametros invalidos.' }
    SemLinks $p.alvo
    SemLinks $p.nova
    $anterior = $p.alvo + '.anterior-' + (Split-Path -Leaf $stage).Replace('.feira-atualizacao-', '')
    if (Test-Path -LiteralPath $anterior) { throw 'A pasta anterior ja existe.' }
    # O aplicativo só fecha depois deste sinal. Políticas que bloqueiam o
    # PowerShell deixam a versão em uso aberta e intacta.
    [IO.File]::WriteAllText((Join-Path $stage 'pronto'), 'ok')
    $antigoProcesso = Get-Process -Id $p.pid -ErrorAction SilentlyContinue
    if ($antigoProcesso -and -not $antigoProcesso.WaitForExit(120000)) {
        throw 'O programa ainda esta aberto. Nenhum arquivo foi trocado.'
    }
    $exeAntigo = Join-Path $p.alvo 'GestaoDaFeira.exe'
    if (Get-Process | Where-Object { $_.Path -eq $exeAntigo }) {
        throw 'Outra instancia esta aberta. Feche-a e tente novamente.'
    }
    # Outra instância pode estar aberta. Nesse caso o Windows recusa a mudança
    # dos arquivos em uso; a versão anterior não é apagada.
    Mover $p.alvo $anterior
    $moveuAnterior = $true
    Mover $p.nova $p.alvo
    $trocou = $true
    $recibo = Join-Path $stage 'abriu.json'
    $exe = Join-Path $p.alvo 'GestaoDaFeira.exe'
    $novoProcesso = Start-Process -FilePath $exe -WorkingDirectory $p.alvo -ArgumentList @('--confirmar-atualizacao', ('"' + $recibo + '"')) -PassThru
    $limite = [DateTime]::UtcNow.AddSeconds(60)
    $confirmado = $false
    while ([DateTime]::UtcNow -lt $limite) {
        if (Test-Path -LiteralPath $recibo) {
            try {
                $r = Get-Content -LiteralPath $recibo -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($r.versao -eq $p.versao -and $r.pid -eq $novoProcesso.Id) { $confirmado = $true; break }
            } catch { } # Aguarda a escrita terminar.
        }
        if ($novoProcesso.HasExited) { break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $confirmado) { throw 'A nova versao nao confirmou a abertura. Recuperando a anterior.' }
    [IO.File]::WriteAllText((Join-Path $stage 'resultado.txt'), "Atualizacao concluida. Versao anterior: $anterior`r`nBackup: $($p.backup)")
    # O ZIP já foi conferido e extraído. Preservamos o script, recibos e logs.
    Remove-Item -LiteralPath (Join-Path $stage 'GestaoDaFeira-Windows-x64.zip') -ErrorAction SilentlyContinue
    exit 0
} catch {
    $erro = $_.Exception.Message
    try {
        if ($novoProcesso -and -not $novoProcesso.HasExited) {
            $novoProcesso.Kill()
            if (-not $novoProcesso.WaitForExit(10000)) { throw 'A nova versao nao encerrou.' }
        }
        if ($trocou) { Mover $p.alvo (Join-Path $stage 'versao-recusada') }
        if ($moveuAnterior) {
            Mover $anterior $p.alvo
            Start-Process -FilePath (Join-Path $p.alvo 'GestaoDaFeira.exe') -WorkingDirectory $p.alvo
        }
    } catch { $erro += ' Recuperacao automatica pendente: ' + $_.Exception.Message }
    [IO.File]::WriteAllText((Join-Path $stage 'resultado.txt'), $erro)
    if (-not $SemDialogo) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(($erro + "`r`n`r`nSeus dados nao foram substituidos. Detalhes: " + $stage), 'Atualizacao nao concluida', 'OK', 'Warning') | Out-Null
    }
    exit 1
}
