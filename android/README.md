# Quasar for Android

The standalone app backs up selected files/folders, compresses and optionally
encrypts archives, restores them with explicit overwrite confirmation, and runs
a compression comparison. No account, root or all-files permission is needed.
It is not the Windows ADB/full-partition image workflow.

## Build

Use the existing JDK 17 and Android SDK on D:. Preserve the private release
keystore outside source control:

```powershell
$env:JAVA_HOME = "D:\Tools\jdk-17.0.20.1+1"
$env:ANDROID_HOME = "D:\Tools\android-sdk"
$env:GRADLE_USER_HOME = "D:\Tools\gradle-home"
$env:QUASAR_SIGNING_PROPERTIES = "D:\Quasar-licensing\android-signing.properties"
.\gradlew.bat :app:testFreeReleaseUnitTest :app:assembleRelease --console=plain --max-workers=2
```

Flavors: `free`, `freeAds`, `supporter`, `pro`; APKs are under
`app\build\outputs\apk\<flavor>\release`. All retain application ID
`com.quasar.mobile`, version 0.4.0/code 6, minimum API 26 and target API 35.
There are no application-ID suffixes or debug-key release fallbacks.
The release signing configuration must match the original private release key.
Never print signing properties or commit the keystore/passwords.

The package's `BuildConfig.EDITION` is independent of validated Gumroad
entitlement. Paid packages prompt for a real receipt key and otherwise use Free
limits. Free with Ads has 10 backups/month with the unchanged 2 GB upload
allowance; cards appear only on Privacy & data and disappear for paid users.
Android currently saves through document providers, not a direct cloud-upload
workflow; no hosted storage is included.

Gumroad product IDs are public identifiers, not license keys:
Supporter `7sQ_4QWbmr1Miy5LYzh-Bw==` (`qygwf`),
Pro `9R_AkG7S8By0ZotuYyM1Lg==` (`qwjtj`).
Verification tests use synthetic keys and mocked responses, never buyer keys or
live activation requests.

## Compatibility and updates

The release gate requires 16 KB ELF LOAD/RELRO boundaries and APK ZIP alignment.
The original Java 8-compatible lazysodium 5.1.0 binding is unchanged; only its
native libraries are replaced by a pinned official libsodium 1.0.22 source
rebuild with NDK r28c. All original exported symbols are retained.
See [native provenance and reproduction](native/README.md).
Zstd is pinned to 1.5.7-4 for the existing compile SDK; 1.5.7-24 requires API 37.
Zstd's arm64 binary has no GNU_RELRO segment; this is a hardening limitation,
not a misaligned RELRO boundary. No binary-header workaround is applied.
Static checks and host archive-format regressions are not Android runtime
tests. No emulator/phone testing or universal compatibility is claimed.

Zstd, libsodium and JNA are native dependencies, included for arm64-v8a,
armeabi-v7a, x86_64 and x86. Run `tools\verify_apk.py` with the Windows Python
interpreter after building; it checks APK signatures against the historical
release, SDK/version metadata, all native ABIs, ELF LOAD/RELRO alignment and
16 KB APK ZIP alignment. A passing static report is not device testing.

For a secret-free Linux CI compile, manually run `android-build.yml`. Its
`-PunsignedRelease=true` outputs are **unsigned intermediates, not releases**.
Download that run's `quasar-unsigned-intermediates`, then sign locally using
the existing private properties (no passwords are put in command arguments):

```powershell
& "$env:JAVA_HOME\bin\java.exe" tools\SignApks.java `
  $env:QUASAR_SIGNING_PROPERTIES $env:ANDROID_HOME `
  <downloaded>\outputs\apk app\build\outputs\apk
```

Run the same static verifier on these signed APKs before packaging. CI never
receives the private signing key. Normal local `assembleRelease` still requires
the original release properties; there is no debug-signing fallback.

The updater selects the bundled edition's ZIP, verifies its SHA256, extracts
only the exact named APK, verifies that APK's SHA256/package/version/signer,
then opens Android's installer for explicit approval. Same-ID, same-key updates
retain private activation and usage preferences. Do not uninstall/clear storage
to switch editions. A previous debug-signed build cannot be updated in place
with the release signer.

See [release contract](../docs/RELEASING.md), [data safety](../docs/DATA-SAFETY.md)
and [emulator instructions for later](../docs/ANDROID-EMULATOR.md).
