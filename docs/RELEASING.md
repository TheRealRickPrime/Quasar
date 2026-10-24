# Release 0.4.0 contract

Source lives in `TheRealRickPrime/Quasar`. Public distribution and Sigstore
publication belong to `QuasarLI/QuasarLI.github.io`. Never replace historical
assets/tags to publish a new release.

## Artifacts and identities

Eight ZIPs:

```text
Quasar-Windows-Free-0.4.0.zip
Quasar-Windows-Free-with-Ads-0.4.0.zip
Quasar-Windows-Supporter-0.4.0.zip
Quasar-Windows-Pro-0.4.0.zip
Quasar-Android-Free-0.4.0.zip
Quasar-Android-Free-with-Ads-0.4.0.zip
Quasar-Android-Supporter-0.4.0.zip
Quasar-Android-Pro-0.4.0.zip
```

Edition IDs: `free`, `free-ads`, `supporter`, `pro`. Each Windows ZIP has
`Quasar\Quasar.exe`, `Quasar\distribution.json` and the matching APK in bundled
assets. Android ZIPs have `Quasar-Android-<label>-0.4.0.apk` at their root.
Both include relevant README/license notices and payload `SHA256SUMS.txt`.
An outer `SHA256SUMS.txt` covers the final exact ZIP bytes.

Windows version 0.4.0; Android version 0.4.0/code 6, package
`com.quasar.mobile`, minSdk 26/targetSdk 35. All Android editions use the same
original private release signer (`D:\Quasar-licensing\quasar-release.jks`,
properties selected by `QUASAR_SIGNING_PROPERTIES`). Never copy properties,
private keys, owner licenses or buyer activations into artifacts.

The bundled edition never grants paid entitlement. Public paid packages use
Free limits until a genuine key is activated. Gumroad's exact public product
IDs are Supporter `7sQ_4QWbmr1Miy5LYzh-Bw==` and Pro
`9R_AkG7S8By0ZotuYyM1Lg==`; purchase permalinks remain
`https://quasarlabs3.gumroad.com/l/qygwf` and
`https://quasarlabs3.gumroad.com/l/qwjtj`. No real key is in tests.

## Build and stage on D:

Run Android tests and `:app:assembleRelease` as documented in `android\README.md`,
then Windows tests and `windows\build.ps1`. The Windows build checks exit codes,
not merely an old executable's existence.

```powershell
$python = "C:\Users\Inv11\AppData\Local\Programs\Python\Python312\python.exe"
& $python android\tools\verify_apk.py `
  android\app\build\outputs\apk\free\release\app-free-release.apk `
  android\app\build\outputs\apk\freeAds\release\app-freeAds-release.apk `
  android\app\build\outputs\apk\supporter\release\app-supporter-release.apk `
  android\app\build\outputs\apk\pro\release\app-pro-release.apk `
  --out release-staging\0.4.0\apk-verification.json
& $python windows\tools\release.py
& $python windows\tools\verify_release.py
```

The ignored staging directory is `D:\Quasar\release-staging\0.4.0`.
Packaging refuses existing ZIPs and never deletes historic releases.
After handoff, **do not modify ZIP bytes**. Give the website publisher
`artifacts.json`, `latest.json`, `SHA256SUMS.txt`, `apk-verification.json`,
`release-verification.json` and
the eight ZIPs. Repackaging requires new hashes and fresh signatures.

Static verification checks signer continuity, SDK/version/package metadata,
all four ABIs, every 64-bit ELF LOAD and GNU_RELRO boundary, and APK
`zipalign -c -P 16 4`. It cannot prove runtime/native/device compatibility.
Run no emulator or phone as part of packaging. Follow the separate emulator
guide only when the user is ready.

The 0.4.0 release gate blocks artifacts unless the static 16 KB checks pass.
Official libsodium 1.0.22 is rebuilt in pinned Linux/NDK CI with both
maximum/common 16 KB page-size flags and RELRO. The original lazysodium 5.1.0
Java binding and all baseline native exports are preserved. Host tests exercise
the actual Kotlin QSR1 code with an independent known vector and corruption/
boundary cases. See `android\native\README.md` and its provenance/test evidence.
AndroidX graphics-path 1.0.1's native code is also rebuilt from its exact official
release revision; Java/resources and the exported JNI API remain unchanged.
Both native provenance reports and third-party notices accompany every ZIP.
Zstd 1.5.7-4 preserves SDK 35 compatibility; 1.5.7-24 requires compile SDK 37.
Zstd arm64 has no RELRO segment (a hardening caveat, not a bad boundary).
Static verification is not Android runtime/device validation.

If compiling on the local host is impractically slow, the manual
`android-build.yml` workflow can compile all editions **unsigned**, with no
private credentials. Sign those intermediates locally with `SignApks.java`
and the original keystore, then run the identical verifier. Never distribute
unsigned intermediates or treat successful compilation as signature validation.

## Update manifest schema

Both `https://quasarli.github.io/latest.json` and
`https://quasarli.github.io/quasar/updates/latest.json` expose schema 2:

```json
{
  "schemaVersion": 2,
  "version": "0.4.0",
  "windows": {
    "version": "0.4.0",
    "url": "<Free Windows ZIP HTTPS URL>",
    "sha256": "<Free Windows ZIP SHA256>",
    "editions": {
      "free": {"version": "0.4.0", "url": "<ZIP URL>", "sha256": "<ZIP SHA256>"},
      "free-ads": {"version": "0.4.0", "url": "<ZIP URL>", "sha256": "<ZIP SHA256>"},
      "supporter": {"version": "0.4.0", "url": "<ZIP URL>", "sha256": "<ZIP SHA256>"},
      "pro": {"version": "0.4.0", "url": "<ZIP URL>", "sha256": "<ZIP SHA256>"}
    }
  },
  "android": {
    "version": "0.3.2",
    "versionCode": 5,
    "url": "https://github.com/QuasarLI/QuasarLI.github.io/releases/download/v0.3.3/Quasar-Android-0.3.2.apk",
    "sha256": "6940b502a6d5449416dfce5d6db452a60ea58a1a39aca8c2828c5e9d5eaf0994",
    "editions": {
      "free": {
        "version": "0.4.0", "versionCode": 6,
        "url": "<Android Free ZIP HTTPS URL>", "sha256": "<ZIP SHA256>",
        "apkFile": "Quasar-Android-Free-0.4.0.apk", "apkSha256": "<APK SHA256>"
      }
    }
  }
}
```

Android `editions` also contains all three other IDs with the same shape.
Legacy Windows clients receive Free and keep paid activation in APPDATA.
Legacy Android flat fields remain code 5/raw APK: pre-0.4 clients cannot
extract ZIP updates. Their original parser used the global version, so its
version display cannot be repaired remotely without changing those clients;
code 5 is not offered as newer. Manually install the matching 0.4 ZIP's APK once.
New apps strictly select their bundled edition and use per-platform versions;
missing entries produce an explicit error, never a silent edition change.
New Android verifies ZIP hash, exact APK member/hash, package, version and
installed signer before opening the system installer.

Asset base:
`https://github.com/QuasarLI/QuasarLI.github.io/releases/download/v0.4.0/`.
The publisher may add `sigstoreBundle` URLs without changing package selection.

## Sigstore verification and publication boundary

The separate site's manual-only workflow `.github/workflows/release-quasar.yml`
on `main` signs the eight final ZIPs and `SHA256SUMS.txt` through GitHub OIDC.
Each has an adjacent `<filename>.sigstore.json`.

Expected certificate identity:

```text
https://github.com/QuasarLI/QuasarLI.github.io/.github/workflows/release-quasar.yml@refs/heads/main
```

Expected issuer: `https://token.actions.githubusercontent.com`.
Example with the Sigstore Python CLI installed:

```powershell
python -m sigstore verify identity `
  --bundle Quasar-Android-Free-0.4.0.zip.sigstore.json `
  --cert-identity "https://github.com/QuasarLI/QuasarLI.github.io/.github/workflows/release-quasar.yml@refs/heads/main" `
  --cert-oidc-issuer "https://token.actions.githubusercontent.com" `
  Quasar-Android-Free-0.4.0.zip
```

Verify the SHA256SUMS signature similarly before comparing hashes.
Sigstore authenticates those exact bytes and workflow identity. It is **not
Authenticode**, does not suppress SmartScreen, and does not replace APK
signing. The current in-app Windows updater validates HTTPS-delivered manifest
hashes, not Sigstore bundles; Android additionally checks the installed APK
signer. Do not claim Sigstore verification inside the apps.
Artifacts built/staged here are not declared Sigstore-signed or published until
the website workflow actually signs, verifies and publishes them.
