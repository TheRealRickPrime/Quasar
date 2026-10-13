# Quasar for Windows

Desktop companion to the Android app. It walks you through an ADB backup of a USB-connected phone, then compresses, encrypts and uploads it, and measures every step.

## Features

- **Guided backup**: downloads Google's platform-tools, helps enable USB debugging, detects the phone live (including the "Allow USB debugging" prompt), runs `adb backup` and tells you what to tap on the phone.
- **Full phone image** (rooted or custom-recovery phones): reads every raw partition over ADB (`dd`), hashes and Zstd-compresses it, and writes a `quasar-image.json` manifest. Restore verifies the stored files, refuses the wrong device model, writes the partitions back and reads them back to compare hashes.
  - *Custom recovery (TWRP etc.)*: nothing is mounted, so the image is exactly consistent and everything can be restored. Use "Boot recovery image" (`fastboot boot`) to run one without flashing it.
  - *Magisk (phone stays on)*: Quasar pauses Android, syncs and remounts `/data` read-only while imaging, then resumes. If the remount is refused the image is only crash-consistent (the manifest says which). Android has no generic copy-on-write snapshot for `/data`. System partitions can only be restored from recovery.
  - Bootloader-chain partitions (xbl, abl, tz...) are skipped by default and blocked on restore unless explicitly allowed.
  - Image folders can be uploaded to the chosen cloud destination, optionally encrypting each file (`.qsr`) first. Downloading back from the cloud isn't built: fetch the files, decrypt, and point Restore at the folder.
  - Encrypted `/data` only unlocks on the same phone; keep `metadata` and `persist` in the image.
- **Compression**: Zstandard (levels 3/12/19/22), TAR+Gzip/Bzip2/XZ, ZIP, 7z.
- **Compression Lab**: runs any mix of formats/levels on the same file and compares size, saved %, compress speed and decompress time, with charts and CSV export.
- **Encryption**: AES-256-GCM, optionally wrapped in XChaCha20-Poly1305, scrypt-derived keys, chunk-authenticated. The result is verified before the unencrypted original is deleted.
- **Cloud upload**: Google Drive, Dropbox, OneDrive, AWS S3 and a local/synced folder. Upload speeds are logged so destinations can be compared. Secrets go to Windows Credential Manager.
- **Account**: sign in to the Quasar backend (`../backend`) to record sessions and get the profile link.
- **Android app**: installs the Quasar `.apk` on the phone. The current APK (0.3.1) is bundled in `assets\apk\`; you can also browse to another one.

## Run from source

```powershell
py -m pip install -r requirements.txt
py run_quasar.py
```

## Build the exe

```powershell
.\build.ps1        # produces dist\Quasar\Quasar.exe
```

## Tests

```powershell
py -m pytest -q
```

## Plans and licensing

| Plan | Price | Backups / month | Cloud upload / month |
|---|---|---|---|
| Free | $0 | 6 | 2 GB |
| Supporter | $10 | 15 | 30 GB |
| Pro | $25 (one-time) | unlimited | unlimited |

Backups count guided backups and full phone images; the Compression Lab and speed tests are never limited. Limits live in `quasar_win/licensing.py` (`TIERS`, `GUMROAD_PRODUCTS`, `SUPPORT_EMAIL`).

Licenses are sold on Gumroad. Buyers paste the per-sale key from their receipt into the License page; the app verifies it with Gumroad's license API (re-checked every few days, 30-day offline grace; refunded purchases stop working). Owner keys (`QSR1.…`, Ed25519-signed, via `tools/make_license.py`) still work offline. The **private key** (`D:\Quasar-licensing\private.key`) must never be committed. Limits are client-side, so they're an honest-user system, not DRM.

`python tools/release.py` (after `build.ps1`) writes `releases\Quasar-Windows-<version>.zip` (no key; upload to Gumroad) and `Quasar-Windows-OWNER-<version>.zip` (Pro key embedded: keep private).

## Limits to know about

- `adb backup` is deprecated. On Android 12+ many apps opt out and some phones produce a near-empty file. Quasar detects an empty result and says so. It cannot produce a root-level full disk image.
- Cloud providers other than S3 take an access token you paste in; a full OAuth sign-in flow is not implemented yet.
- adb backups are already deflate-compressed, so extra compression usually saves little. Use the Lab to measure.
