# Publishing a checked player update

The player link stays the same:
https://github.com/Dopey99101/wow-335a-addon-updates/releases/latest

Each release is a new immutable package, for example RealmAddons-1.0.rar followed
by RealmAddons-1.1.rar. Never reuse a published version or replace its archive.

## Build

Use Python 3.12 or newer, WinRAR's Rar.exe, Windows PowerShell 5.1, and GitHub CLI.
Sign into GitHub CLI locally once. Do not paste access tokens into this repository
or store them in scripts. The normal GitHub CLI credential store handles access.

Run from this repository, substituting your paths and next version:

```powershell
python tools/build_release.py --version 1.1 --game "C:\Games\WoW-3.3.5a" --handbook "C:\path\Addons-Handbók-1.0.txt" --client-support tools/client-support.json --output dist/1.1 --rar "C:\Program Files\WinRAR\Rar.exe"
```

The game is read only. Only addon contents and the explicit custom patches L/M/N
are copied. Settings, backups, logs and account files are excluded. Each staged
payload file is hash-checked; the RAR is tested and must stay below 2 GiB.

The shared handbook keeps its own edition. Include its current published version
unchanged; create a new edition if its contents need updating.

## Check and publish

Exercise the installer in an isolated fixture first. Keep a local checks JSON
with status `passed` and `installer_sha256` matching the exact installer tested.
The owner's configured workflow records this outside the public repository.
Also check the release inventory and that matching realm/client features are
ready. Packaging or publishing does not install a pending server update.

```powershell
python tools/publish_release.py --directory dist/1.1 --checks "C:\path\installer-checks.json" --gh gh
```

The publisher rejects an existing release tag, creates a draft, uploads the RAR,
release-manifest.json and SHA256SUMS.txt, checks GitHub's SHA256 digests and sizes,
then publishes and verifies the public latest-release endpoint. A failed upload
or hash check stays a draft and does not replace the last good release. Inspect
the failure before retrying; never use `--clobber` to overwrite a release.

Publish finished, verified changes as part of the owner's update workflow. There
is no timer or folder watcher and no publication of unsaved/unfinished changes.
Other players still download and install the package. A client auto-updater is a
separate feature and is not installed by this setup.
