# WoW 3.3.5a addon updates

Addons and matching custom realm patches for our WoW 3.3.5a realm.

**[Download the latest version](https://github.com/Dopey99101/wow-335a-addon-updates/releases/latest)**

Bookmark that link. It always opens the newest published player package. Download
the **RealmAddons-version.rar** attachment, not GitHub's Source code downloads.

## Install or update

1. Fully close every WoW window.
2. Download the RAR and extract it completely to a temporary folder.
3. Open the extracted RealmAddons folder and read READ-ME-FIRST.txt.
4. Double-click START-INSTALL.cmd and choose your WoW folder, containing Wow.exe
   and Data. Select the game folder, not Interface, AddOns or Data.
5. Wait for the success message, then launch your game normally.
6. At character selection, use AddOns to enable the addons you want.

The installer checks package hashes before making changes, backs up files it
replaces, and keeps your WTF settings and account details. It installs the addon
collection and patches L/M/N, including required custom login-interface support.
It stops on an unsupported executable or conflicting custom patch.

The addon command guide is included in each release. Main custom controls:

| Command | What it does |
| --- | --- |
| `/chauffeur` | Summon the chauffeur |
| `/chauffeur setup` | Restore the ride button |
| `/chauffeur status` | Show Chauffeur version information |
| `/hunterforge` | Check HunterForge server support |

RealmNotices works automatically and has no slash commands. MPQ patches have no
slash commands. See the included Addons-Handbók for the other addon controls.
GM permissions are controlled by the server, not granted by installing addons.

## What is included

RealmAddons is a snapshot of the owner's installed addon collection plus the
required custom realm patches. The inventory in each release lists the exact
addons, file hashes and versions. Third-party credits and licenses remain inside
their folders; this repository does not apply a new license to them.

This package does not include the full game, HD graphics packs, account settings,
passwords, server files, saved variables or database backups. It is intended for
this realm and a compatible WoW 3.3.5a build 12340 client.

## Updates

New versions are published as separate releases. Old versions remain available.
This link does not install anything automatically on your PC: download and run
the new package when an update is available.

Publishing follows a finished, checked update. No folder watcher publishes
unfinished edits. This repository does not read a player's game folder or send
their account information anywhere.

## For the owner

See [PUBLISHING.md](PUBLISHING.md) for build and upload commands. Packages are
attached to Releases; large game files never go into Git history.
