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

An independent repeat run reproduced all four libsodium library SHA256s exactly:
https://github.com/TheRealRickPrime/Quasar/actions/runs/40131975788

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

## AndroidX graphics-path

`graphics-path-1.0.1-quasar.aar` preserves every original non-JNI member of
the official Google Maven 1.0.1 AAR. Its three native C++ files are built from
the exact release revision `8a05a22af450d589ef911d772a001a49dcb05b71`, linked
from Google's [1.0.1 release notes](https://developer.android.com/jetpack/androidx/releases/graphics#graphics-path-1.0.1).
NDK r28c uses both maximum/common page-size flags, RELRO/NOW and the unchanged
upstream symbol map. Each ABI must retain the identical exported JNI API.
No C++ source or Java binding is modified.

The official Gitiles tar download generates variable per-file timestamps.
`build_graphics.py` therefore pins the complete set of source filenames and each
file's SHA256, not those archive headers. The official baseline AAR is separately
SHA256-pinned. `graphics-provenance.json` records these pins, build flags, native
hashes, exports and segment values. The manual `android-graphics.yml` workflow
reproduces this native-only build; no signing credentials or device is involved.
The successful four-ABI build:
https://github.com/TheRealRickPrime/Quasar/actions/runs/40132804067
Download its successful `quasar-graphics-16kb` artifact, validate with
`python android\tools\build_graphics.py --verify --out <artifact-directory>`,
then copy the verified AAR and provenance to this directory. A regular unsigned
app CI build followed by original-key local signing/static checks is still
required; a native-only artifact is not a finished APK.

Zstd 1.5.7-4 and JNA 5.19.1 are still official Maven dependencies. Final APK
verification independently checks their packaged ELF boundaries and ZIP
alignment, as well as rebuilt libsodium. Zstd's arm64 library has no RELRO
segment, a hardening caveat rather than a boundary-alignment failure.

Final APKs must retain `com.quasar.mobile`, minSdk 26/targetSdk 35 and the
original private release signer. Passing static checks cannot certify Android
runtime, emulator or physical-device behavior; none was run for this release.
