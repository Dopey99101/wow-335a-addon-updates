param([string]$GameDirectory,[switch]$Quiet,[switch]$ValidateOnly)
$ErrorActionPreference='Stop'
function Hash([string]$Path) {
    $stream=[IO.File]::OpenRead($Path);$sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLower()}
    finally{$stream.Dispose();$sha.Dispose()}
}
function Safe-Path([string]$Root,[string]$Relative) {
    if([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)|:'){throw 'Invalid package path.'}
    $path=[IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if(-not $path.StartsWith($Root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Package path escapes the selected folder.'}
    $walk=$path
    while($walk.Length -ge $Root.Length) {
        if(Test-Path -LiteralPath $walk){if((Get-Item -LiteralPath $walk -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked install paths are not supported.'}}
        if($walk -eq $Root){break};$walk=Split-Path $walk -Parent
    }
    return $path
}
function Show-Message([string]$Message) {
    Write-Output $Message
    if(-not $Quiet){Add-Type -AssemblyName System.Windows.Forms;[void][Windows.Forms.MessageBox]::Show($Message,'RealmAddons')}
}
$written=New-Object Collections.Generic.List[object]
$backup=$null
try {
    if(-not $GameDirectory) {
        Add-Type -AssemblyName System.Windows.Forms
        $picker=New-Object Windows.Forms.FolderBrowserDialog
        $picker.Description='Choose your WoW folder containing Wow.exe and Data.'
        if(Test-Path 'C:\Games\WoW-3.3.5a\Wow.exe'){$picker.SelectedPath='C:\Games\WoW-3.3.5a'}
        if($picker.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){exit 0}
        $GameDirectory=$picker.SelectedPath;$picker.Dispose()
    }
    $gameRoot=[IO.Path]::GetFullPath($GameDirectory).TrimEnd('\')
    if(-not(Test-Path -LiteralPath (Join-Path $gameRoot 'Wow.exe')) -or -not(Test-Path -LiteralPath (Join-Path $gameRoot 'Data') -PathType Container)){throw 'Choose the game folder containing Wow.exe and Data.'}
    $running=Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.Path -and $_.Path.StartsWith($gameRoot+'\',[StringComparison]::OrdinalIgnoreCase) -and $_.ProcessName -like 'Wow*'}
    if($running){throw 'Close WoW completely before installing.'}
    $packageRoot=[IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
    $manifest=Get-Content -LiteralPath (Join-Path $packageRoot 'manifest.json') -Raw | ConvertFrom-Json
    if($manifest.product -ne 'RealmAddons' -or $manifest.clientBuild -ne 12340){throw 'Unrecognized package.'}
    $previousPath=Safe-Path $gameRoot 'RealmAddons/installed.json'
    $previous=$null
    if(Test-Path -LiteralPath $previousPath){$previous=Get-Content -LiteralPath $previousPath -Raw | ConvertFrom-Json}
    $plan=New-Object Collections.Generic.List[object]
    $seen=@{}
    foreach($file in $manifest.files) {
        $relative=[string]$file.path
        if($relative -notmatch '^Interface/AddOns/[^/]+/.+' -and $relative -notmatch '^Data/patch-[LMN]\.MPQ$'){throw 'Unexpected payload path.'}
        if($seen.ContainsKey($relative.ToLower())){throw 'Duplicate package path.'};$seen[$relative.ToLower()]=$true
        $source=Safe-Path $packageRoot $relative;$target=Safe-Path $gameRoot $relative
        if((Hash $source) -ne $file.sha256 -or (Get-Item -LiteralPath $source).Length -ne $file.bytes){throw ('Package damaged: '+$relative)}
        $exists=Test-Path -LiteralPath $target
        $current=if($exists){Hash $target}else{''}
        if($relative -match '^Data/' -and $exists -and $current -ne $file.sha256) {
            $known=@($manifest.clientSupport.knownPatchHashes.$relative)
            if($previous -and $previous.product -eq 'RealmAddons'){$known+=@($previous.files | Where-Object path -eq $relative | ForEach-Object {$_.sha256})}
            if($current -notin $known){throw ('A different '+$relative+' already exists. Ask the owner before replacing it.')}
        }
        if($current -ne $file.sha256){$plan.Add(@{Source=$source;Target=$target;Relative=$relative;Exists=$exists;Bytes=$null})}
    }
    # Validate exact executable family before installing custom GlueXML.
    $support=$manifest.clientSupport
    $exeCount=0
    $exeChecks=@()
    foreach($name in @('Wow.exe','Wow-HD.exe','Wow-UltraHD.exe')) {
        $exePath=Safe-Path $gameRoot $name
        if(-not(Test-Path -LiteralPath $exePath)){continue}
        $exeCount++
        $hash=Hash $exePath
        $variant=@($support.executables | Where-Object {$_.before -eq $hash -or $_.after -eq $hash}) | Select-Object -First 1
        if(-not $variant){throw ('Unsupported '+$name+'. No game files have been changed.')}
        $exeChecks+=@{Path=$exePath;Hash=$variant.after}
        if($hash -eq $variant.after){continue}
        $bytes=[IO.File]::ReadAllBytes($exePath)
        foreach($patch in $support.patches) {
            $next=[byte[]]@(for($i=0;$i -lt $patch.after.Length;$i+=2){[Convert]::ToByte($patch.after.Substring($i,2),16)})
            [Array]::Copy($next,0,$bytes,[int]$patch.offset,$next.Length)
        }
        $sha=[Security.Cryptography.SHA256]::Create()
        try{$computed=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLower()}finally{$sha.Dispose()}
        if($computed -ne $variant.after){throw 'Executable support verification failed.'}
        $plan.Add(@{Source=$null;Target=$exePath;Relative=$name;Exists=$true;Bytes=$bytes})
    }
    if(-not $exeCount){throw 'No supported executable found.'}
    if($ValidateOnly){Write-Output ('Validated '+$manifest.files.Count+' payload files and client support; no files changed.');exit 0}
    $backup=Safe-Path $gameRoot ('RealmAddons-Backups/'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach($item in $plan) {
        if($item.Exists){$saved=Safe-Path $backup $item.Relative;New-Item -ItemType Directory -Path (Split-Path $saved -Parent) -Force | Out-Null;Copy-Item -LiteralPath $item.Target -Destination $saved;if((Hash $saved) -ne (Hash $item.Target)){throw 'Backup verification failed.'}}
    }
    $manifestBackup=Safe-Path $backup 'RealmAddons/installed.json'
    $hadManifest=Test-Path -LiteralPath $previousPath
    if($hadManifest){New-Item -ItemType Directory -Path (Split-Path $manifestBackup -Parent) -Force | Out-Null;Copy-Item -LiteralPath $previousPath -Destination $manifestBackup}
    foreach($item in $plan) {
        New-Item -ItemType Directory -Path (Split-Path $item.Target -Parent) -Force | Out-Null
        $written.Add($item)
        if($null -ne $item.Bytes){[IO.File]::WriteAllBytes($item.Target,$item.Bytes)}else{Copy-Item -LiteralPath $item.Source -Destination $item.Target -Force}
    }
    foreach($file in $manifest.files){if((Hash (Safe-Path $gameRoot $file.path)) -ne $file.sha256){throw 'Installed file verification failed.'}}
    foreach($exe in $exeChecks){if((Hash $exe.Path) -ne $exe.Hash){throw 'Installed executable verification failed.'}}
    New-Item -ItemType Directory -Path (Split-Path $previousPath -Parent) -Force | Out-Null
    $written.Add(@{Target=$previousPath;Relative='RealmAddons/installed.json';Exists=$hadManifest})
    $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $previousPath -Encoding UTF8
    Show-Message ('RealmAddons '+$manifest.version+' installed. Open WoW normally. Backup: '+$backup)
} catch {
    $failure=$_.Exception.Message
    for($i=$written.Count-1;$i -ge 0;$i--) {
        $item=$written[$i]
        if($item.Exists){Copy-Item -LiteralPath (Safe-Path $backup $item.Relative) -Destination $item.Target -Force}
        elseif(Test-Path -LiteralPath $item.Target){Remove-Item -LiteralPath $item.Target -Force}
    }
    if($backup -and $manifestBackup -and (Test-Path -LiteralPath $manifestBackup)){Copy-Item -LiteralPath $manifestBackup -Destination $previousPath -Force}
    Show-Message ('Installation stopped. '+$failure)
    exit 1
}
