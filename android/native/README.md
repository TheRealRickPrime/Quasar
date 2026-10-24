# Reproducible native compatibility rebuild

`lazysodium-android-5.1.0-quasar.aar` retains every non-JNI member (including the
unchanged Java 8 `classes.jar`) from Maven Central's original 5.1.0 AAR.
Only `jni/<ABI>/libsodium.so` is replaced, plus a bundled libsodium license.
This preserves the existing JNA API and Quasar's QSR1 archive format.

The official libsodium 1.0.22 release source is pinned by SHA256 and release
tag/commit; the baseline AAR is independently SHA256-pinned. The exact source,
NDK r28c, linker flags, all native hashes, export comparisons and ELF segment
values are recorded in `provenance.json`. No downloaded third-party replacement
binary or patched ELF header is used.

The successful build and actual Kotlin host-format regression run:
https://github.com/TheRealRickPrime/Quasar/actions/runs/40130234361

The build runs upstream host `make check`, cross-compiles API 26 libraries for
arm64-v8a, armeabi-v7a, x86_64 and x86, and verifies all 610 original exports
remain. All rebuilt libraries have 16 KB LOAD alignment and aligned RELRO ends.
`kotlin-test-results` records the non-skipped test of the app's actual QSR1
encryption/decryption, independent known vector, block boundaries, wrong keys,
truncation and tampering. These are Linux host tests, **not Android execution**.

To reproduce, manually dispatch `.github/workflows/android-native.yml`, download
the successful `quasar-native-16kb` artifact, then run:

```powershell
python android\tools\prepare_sodium.py <downloaded-artifact> --run-url <run-url>
```

The importer rechecks source/baseline pins, per-ABI hashes, export evidence,
ELF boundaries and non-skipped test results. It emits a deterministic ZIP/AAR.
Compare its SHA256 with `provenance.json`; reruns may have different native
bytes if the hosted runner toolchain changes, so review provenance before
updating the checked-in AAR. The pinned source/NDK and build scripts are retained.

Zstd 1.5.7-4 and JNA 5.19.1 are still official Maven dependencies. Final APK
verification independently checks their packaged ELF boundaries and ZIP
alignment, as well as rebuilt libsodium. Zstd's arm64 library has no RELRO
segment, a hardening caveat rather than a boundary-alignment failure.

Final APKs must retain `com.quasar.mobile`, minSdk 26/targetSdk 35 and the
original private release signer. Passing static checks cannot certify Android
runtime, emulator or physical-device behavior; none was run for this release.
