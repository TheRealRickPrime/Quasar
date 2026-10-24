# Test Quasar in an Android emulator on D:

**Procedure for later only.** Preparing the app/release does not install,
create, start or modify an emulator, virtual device, Windows feature or phone.

## Recommended environment

Use Android Emulator directly on Windows, preferably with 16 GB host RAM and
15-25 GB free on D:. Give a test device 2-4 GB RAM. An x86_64 API 35 image is a
good starting point on Intel/AMD PCs; test an older supported API separately.
Test a 16 KB page-size image separately from an ordinary 4 KB image.

Check Task Manager > Performance > CPU > Virtualization. If disabled, enable
Intel VT-x/AMD SVM in firmware. Enable **Windows Hypervisor Platform** in
Windows Features and restart if requested. Do not weaken Windows security
features to use obsolete acceleration drivers.

An emulator is disposable test infrastructure, **not an isolation guarantee
against hostile software** or a replacement for physical ARM64/OEM testing.
It can access the network and host services.

## Configure D: locations when ready

```powershell
$env:ANDROID_HOME = "D:\Tools\android-sdk"
$env:ANDROID_USER_HOME = "D:\Tools\android-user"
$env:ANDROID_AVD_HOME = "D:\Tools\android-avd"
$env:GRADLE_USER_HOME = "D:\Tools\gradle-home"
$env:JAVA_HOME = "D:\Tools\jdk-17.0.20.1+1"
New-Item -ItemType Directory -Force $env:ANDROID_USER_HOME, $env:ANDROID_AVD_HOME | Out-Null
```

These affect the current terminal only. For persistence use Windows user
Environment Variables, then open a new terminal. Any `ANDROID_SDK_ROOT` must
point to the same SDK. Never move the release keystore into the virtual device.

## Install one image and create a disposable AVD

Only run these when you choose to begin; review Google's license prompts:

```powershell
$sdkmanager = "$env:ANDROID_HOME\cmdline-tools\latest\bin\sdkmanager.bat"
& $sdkmanager --sdk_root="$env:ANDROID_HOME" --licenses
& $sdkmanager --sdk_root="$env:ANDROID_HOME" `
    "emulator" "platform-tools" "system-images;android-35;google_apis;x86_64"
& "$env:ANDROID_HOME\emulator\emulator.exe" -accel-check
$avdmanager = "$env:ANDROID_HOME\cmdline-tools\latest\bin\avdmanager.bat"
& $avdmanager create avd -n "Quasar_API35" `
    -k "system-images;android-35;google_apis;x86_64" `
    -p "D:\Tools\android-avd\Quasar_API35.avd"
```

Answer no to a custom hardware profile or select a standard profile in Android
Studio's Device Manager. Do not overwrite existing AVDs. Android Studio using
the same D: locations is an alternative to these existing command-line tools.

Start in a terminal left open:

```powershell
& "$env:ANDROID_HOME\emulator\emulator.exe" `
    -avd "Quasar_API35" -gpu auto -memory 2048 -no-snapshot
```

Do not sign into a personal account or use real backups. No Play login is
needed for basic app tests.

## Install and exercise a verified release

First verify the downloaded ZIP and its Sigstore bundle using
[the exact release identity](RELEASING.md), then extract it on D:.

```powershell
$adb = "D:\Tools\android-sdk\platform-tools\adb.exe"
& $adb devices -l
& $adb -s emulator-5554 shell getprop ro.product.cpu.abilist
& $adb -s emulator-5554 shell getconf PAGE_SIZE
& $adb -s emulator-5554 install -r "D:\Quasar-Test\Quasar-Android-Free-0.4.0.apk"
& $adb -s emulator-5554 shell am start -n com.quasar.mobile/.MainActivity
```

Use the actual emulator serial and extracted file path. Always select the
emulator explicitly so a connected physical phone is untouched.
Same-package/same-signer updates keep app data. A debug-signed older app cannot
be updated by the release key; do not uninstall a real user's app without
protecting their data/receipt keys.

Test at normal and large text sizes; check all screens, contrast and scrolling.
Back up throwaway files in every format and restore into a new empty folder;
compare hashes, not just completion messages. Specifically exercise native
Zstd and encrypted Argon2id/XChaCha backup/restore on x86_64. Try a wrong
passphrase, truncated archive copies, offline activation/update failures,
declined permissions and insufficient space. Check quotas across edition
updates, paid ad suppression, intentional-only affiliate links and persistence
of activation/usage. Never simulate failures on irreplaceable data.

For crash diagnosis:

```powershell
& $adb -s emulator-5554 logcat -b crash -d
```

Review logs for filenames/account information before sharing. Closing the
emulator normally preserves guest data. Device Manager's Wipe Data deletes
that **test guest's** data/licenses; use it only on disposable test AVDs.

## Verification limits

An ordinary 4 KB image cannot prove 16 KB compatibility; APK ZIP alignment and
all native ELF LOAD/RELRO boundaries must pass static checks, followed by a
16 KB runtime test. x86_64 is not ARM64 hardware testing. USB/OEM behavior,
rooted imaging/recovery and physical-phone restore remain separate tests.
See each release's static APK report before assuming any configuration works.

Official references:
[variables](https://developer.android.com/tools/variables),
[Windows acceleration](https://developer.android.com/studio/run/emulator-acceleration),
[SDK Manager](https://developer.android.com/tools/sdkmanager),
[AVD Manager](https://developer.android.com/tools/avdmanager),
[emulator commands](https://developer.android.com/studio/run/emulator-commandline),
[16 KB pages](https://developer.android.com/guide/practices/page-sizes).
