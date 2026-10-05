$paths = @('C:\Program Files (x86)\Inno Setup 6\ISCC.exe', 'C:\Program Files\Inno Setup 6\ISCC.exe')

$found = $null
foreach ($p in $paths) {
    if (Test-Path $p) {
        $found = $p
        break
    }
}

if ($found) {
    Write-Host "Using ISCC: $found"
    $proc = Start-Process -FilePath $found -ArgumentList 'C:\Users\ADN\Documents\edupaie\EduPaieSetup.iss' -Wait -PassThru -NoNewWindow
    Write-Host "Exit code: $($proc.ExitCode)"
} else {
    Write-Host "ISCC.exe introuvable dans les chemins standards."
    Write-Host "Vérifier que Inno Setup 6 est installé, puis relancer avec le chemin complet :"
    Write-Host '  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Users\ADN\Documents\edupaie\EduPaieSetup.iss"'
}
