"""Build an immutable, checked RAR from explicitly selected player files only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

PATCHES=('patch-L.MPQ','patch-M.MPQ','patch-N.MPQ')
EXCLUDED_DIRS={'.git','.svn','__pycache__','savedvariables','wtf','cache','logs','screenshots'}
EXCLUDED_SUFFIXES={'.bak','.log','.pyc','.dmp','.sql','.tmp','.pfx','.pem','.key'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def safe_relative(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:
        raise ValueError('Unsafe path: '+name)
    return p

def build(a):
    if not re.fullmatch(r'\d+\.\d+',a.version):raise ValueError('Use a version such as 1.0')
    repo=Path(__file__).resolve().parent.parent
    game=Path(a.game).resolve(); addon_root=game/'Interface/AddOns'
    handbook=Path(a.handbook).resolve()
    support=json.loads(Path(a.client_support).read_text(encoding='utf-8-sig'))
    output=Path(a.output).resolve(); output.mkdir(parents=True,exist_ok=True)
    root=output/('RealmAddons-'+a.version); archive=output/(root.name+'.rar')
    if root.exists() or archive.exists():raise FileExistsError('Version already built; choose a new version')
    if not (game/'Wow.exe').is_file() or not addon_root.is_dir():raise ValueError('Invalid game folder')
    root.mkdir(); records=[]
    for src in sorted(addon_root.rglob('*')):
        if src.is_symlink() or src.is_junction():raise ValueError('Linked addon path is not allowed: '+str(src))
        if not src.is_file():continue
        rel=src.relative_to(addon_root)
        if any(p.lower() in EXCLUDED_DIRS for p in rel.parts) or src.suffix.lower() in EXCLUDED_SUFFIXES:continue
        target=root/'Interface/AddOns'/rel
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,target)
        h=digest(target)
        if h!=digest(src):raise RuntimeError('Source changed while snapshotting: '+str(rel))
        records.append({'path':target.relative_to(root).as_posix(),'bytes':target.stat().st_size,'sha256':h})
    for name in PATCHES:
        src=game/'Data'/name; target=root/'Data'/name
        target.parent.mkdir(exist_ok=True);shutil.copy2(src,target)
        h=digest(target)
        if h!=digest(src):raise RuntimeError('Patch changed during build')
        records.append({'path':'Data/'+name,'bytes':target.stat().st_size,'sha256':h})
    (root/'Guides').mkdir(); shutil.copy2(handbook,root/'Guides'/handbook.name)
    shutil.copy2(repo/'tools/Install-RealmAddons.ps1',root/'Install-RealmAddons.ps1')
    (root/'START-INSTALL.cmd').write_text('@echo off\npowershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install-RealmAddons.ps1"\nif errorlevel 1 pause\n',encoding='ascii')
    folders=sorted(p.name for p in (root/'Interface/AddOns').iterdir() if p.is_dir()); addons=[]
    for name in folders:
        version='not declared'
        for toc in (root/'Interface/AddOns'/name).glob('*.toc'):
            m=re.search(r'^##\s*Version:\s*(.+)$',toc.read_text(encoding='utf-8-sig',errors='replace'),re.M|re.I)
            if m:version=m.group(1).strip();break
        addons.append({'name':name,'version':version})
    manifest={'product':'RealmAddons','version':a.version,'clientBuild':12340,
              'createdAt':datetime.now(timezone.utc).isoformat(),'files':records,'addons':addons,
              'clientSupport':support}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    readme=f'''REALMADDONS {a.version} - READ ME FIRST

1. Fully close WoW. Do not install while the game is running.
2. Extract the entire RAR into a temporary folder. Do not run from inside WinRAR.
3. Double-click START-INSTALL.cmd.
4. Choose your main WoW folder, such as C:\\Games\\WoW-3.3.5a. It must contain Wow.exe and Data.
5. Wait for "RealmAddons {a.version} installed". If it stops, keep the message and ask the owner.
6. Launch WoW normally. At character selection click AddOns and enable the addons you want.

UPDATING: Follow the same steps. Existing WTF settings are left alone.
Replaced files are backed up under RealmAddons-Backups in your game folder.
Your extra addons are not deleted. Installing addons does not grant staff permissions.

CONTENTS: {len(folders)} addon folders and the matching custom patches L, M and N.
The installer checks the exact supported WoW executable and applies only the known
interface compatibility bytes needed by RealmGuard. It does not download an executable.
Unknown executables and conflicting custom MPQs stop installation before game files change.
This package has no full game files, HD graphics, login details or personal settings.

COMMANDS:
/chauffeur - summon the chauffeur.
/chauffeur setup - restore the ride button.
/chauffeur status - show Chauffeur version information.
/hunterforge - check HunterForge server support.
RealmNotices works automatically and has no slash commands. MPQ patches have no commands.
See Guides/{handbook.name} for the other addon controls and examples.

LATEST DOWNLOAD:
https://github.com/Dopey99101/wow-335a-addon-updates/releases/latest

Third-party addon credits/licenses are preserved inside their folders.
Interface compatibility patch reference: https://github.com/suprsokr/allow-custom-gluexml-mithril
'''
    (root/'READ-ME-FIRST.txt').write_text(readme,encoding='utf-8-sig')
    for f in records:
        name=f['path'];safe_relative(name)
        if not (name.startswith('Interface/AddOns/') or name in ['Data/'+p for p in PATCHES]):raise ValueError('Unexpected payload path')
        if digest(root/name)!=f['sha256']:raise RuntimeError('Snapshot hash mismatch')
    subprocess.run([a.rar,'a','-ma5','-m3','-md32m','-mt2','-idq',str(archive),root.name],cwd=output,check=True)
    subprocess.run([a.rar,'t','-idq',str(archive)],check=True)
    if archive.stat().st_size>=2*1024**3:raise ValueError('Release exceeds GitHub per-file limit')
    release={'product':'RealmAddons','version':a.version,'tag':'realmaddons-'+a.version,
             'archive':archive.name,'bytes':archive.stat().st_size,'sha256':digest(archive),
             'addonCount':len(folders),'payloadFiles':len(records),
             'handbook':handbook.name,'patches':list(PATCHES),'createdAt':manifest['createdAt']}
    (output/'release-manifest.json').write_text(json.dumps(release,indent=2),encoding='utf-8')
    (output/'SHA256SUMS.txt').write_text(release['sha256']+'  '+archive.name+'\n',encoding='ascii')
    (output/'release-notes.md').write_text(f'''RealmAddons {a.version}

Complete player update: {len(folders)} addon folders plus matching patches L/M/N.
Includes installation instructions and {handbook.name}. Close WoW, extract the RAR
and run START-INSTALL.cmd. Select the game folder containing Wow.exe and Data.

Personal settings, account files, full game files and HD graphics are not included.
See README for custom slash commands. Older releases remain available.
''',encoding='utf-8')
    print(json.dumps(release,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('version','game','handbook','client-support','output','rar'):p.add_argument('--'+arg,required=True)
    build(p.parse_args())
