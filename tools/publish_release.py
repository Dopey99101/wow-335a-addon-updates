"""Upload a checked version as a draft, verify server hashes, then publish it."""
import argparse,hashlib,json,subprocess,urllib.request
from pathlib import Path

REPO='Dopey99101/wow-335a-addon-updates'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main(a):
    gh=a.gh
    def call(*args):return subprocess.run([gh,*args],check=True,text=True,capture_output=True).stdout
    def api(path):return json.loads(call('api',path))
    folder=Path(a.directory).resolve()
    release=json.loads((folder/'release-manifest.json').read_text(encoding='utf-8-sig'))
    if release['product']!='RealmAddons':raise ValueError('Unexpected release product')
    if release['tag']!='realmaddons-'+release['version']:raise ValueError('Unexpected tag')
    if release['archive']!='RealmAddons-'+release['version']+'.rar':raise ValueError('Unexpected archive')
    archive=folder/release['archive']; package=folder/archive.stem
    if digest(archive)!=release['sha256'] or archive.stat().st_size!=release['bytes']:raise ValueError('Archive differs from verified build')
    if archive.stat().st_size>=2*1024**3:raise ValueError('Archive exceeds GitHub asset limit')
    checks=json.loads(Path(a.checks).read_text(encoding='utf-8-sig'))
    if checks['status']!='passed' or checks['installer_sha256']!=digest(package/'Install-RealmAddons.ps1'):raise ValueError('Matching installer checks required')
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8-sig'))
    for record in manifest['files']:
        p=package/record['path']
        if not p.resolve().is_relative_to(package.resolve()) or digest(p)!=record['sha256']:raise ValueError('Package manifest mismatch')
    user=api('user')
    if user['login'].lower()!='dopey99101':raise ValueError('Sign into the repository owner account')
    repository=api('repos/'+REPO)
    if not repository['permissions'].get('push'):raise PermissionError('Publishing access is required')
    prior=subprocess.run([gh,'release','view',release['tag'],'--repo',REPO,'--json','tagName'],text=True,capture_output=True)
    if prior.returncode==0:raise FileExistsError('Release already exists. Never overwrite a published version.')
    if 'not found' not in (prior.stderr+prior.stdout).lower():raise RuntimeError('Could not safely check for an existing release: '+prior.stderr)
    assets=[archive,folder/'release-manifest.json',folder/'SHA256SUMS.txt']
    expected={p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in assets}
    # CLI creates a draft first; incomplete uploads never become the latest release.
    print(call('release','create',release['tag'],*[str(p) for p in assets],
               '--repo',REPO,'--target',repository['default_branch'],'--draft',
               '--title','RealmAddons '+release['version'],'--notes-file',str(folder/'release-notes.md')))
    remote=api('repos/'+REPO+'/releases/tags/'+release['tag'])
    for name,wanted in expected.items():
        matches=[x for x in remote['assets'] if x['name']==name]
        if len(matches)!=1:raise RuntimeError('Missing uploaded asset: '+name)
        asset=matches[0]
        if asset['state']!='uploaded' or asset['size']!=wanted['bytes'] or asset.get('digest')!='sha256:'+wanted['sha256']:
            raise RuntimeError('Uploaded asset verification failed; release remains draft: '+name)
    call('release','edit',release['tag'],'--repo',REPO,'--draft=false','--latest')
    request=urllib.request.Request('https://api.github.com/repos/'+REPO+'/releases/latest',headers={'User-Agent':'RealmAddons-Publisher'})
    with urllib.request.urlopen(request,timeout=30) as response:public=json.load(response)
    if public['tag_name']!=release['tag'] or public['draft']:raise RuntimeError('Latest public release verification failed')
    result={**release,'status':'published','url':public['html_url'],
            'latestUrl':'https://github.com/'+REPO+'/releases/latest','verifiedAssets':expected}
    (folder/'published.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True);p.add_argument('--checks',required=True);p.add_argument('--gh',default='gh')
    main(p.parse_args())
