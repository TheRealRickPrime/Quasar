# Quasar

Privacy-first backup tools from Quasar Labs: a Windows ADB backup/image companion
and a standalone Android file backup, compression and encryption app.

Product site and releases: **https://quasarli.github.io/quasar/**.
Source for both applications lives here; the separate
`QuasarLI/QuasarLI.github.io` repository owns the website and public release signing.

| Distribution | Price | Backups/month | Upload allowance/month |
|---|---|---|---|
| Free | $0 | 6 | 2 GB |
| Free with Ads | $0 | 10 | 2 GB |
| Supporter | $10 | 15 | 30 GB |
| Pro | $25 one-time | Unlimited | Unlimited |

An upload allowance is **not hosted storage**. Windows uploads to a destination
you configure; Android saves through the system document picker and does not
currently implement direct cloud uploads. Provider charges and retention apply.
Free without ads remains available. The ads edition's optional, disclosed
AdGuard affiliate cards appear only on **Privacy & data**, not backup/image/
restore screens. No ad SDK or affiliate network request is made until you
intentionally open an external link. A valid paid license suppresses all ads.

Supporter and Pro ZIPs are labeled distributions, **not activated licenses**.
Enter a genuine Gumroad receipt key on the License page. Packages never include
buyer or owner keys. Purchases:
[Supporter](https://quasarlabs3.gumroad.com/l/qygwf) /
[Pro](https://quasarlabs3.gumroad.com/l/qwjtj).

## Project layout

- `windows`: Python/PySide6 desktop app, tests, PyInstaller and release tools.
- `android`: Kotlin/Compose app, same `com.quasar.mobile` ID for all editions.
- `backend`: optional FastAPI account/session scaffold, not a supplied hosted service.
- `docs`: format/design references, [data safety](docs/DATA-SAFETY.md),
  [release contract](docs/RELEASING.md), and
  [future emulator procedure on D:](docs/ANDROID-EMULATOR.md).

Windows usage, configuration and activation remain in `%APPDATA%\Quasar`.
Android updates share the existing private preferences and release signer.
Switching packages or removing an activation does not reset monthly counters.
See [Windows instructions](windows/README.md) and [Android instructions](android/README.md).

Deletion is not secure erase. See **Privacy & data** in either app before
deleting files or restoring over existing data. Preserve records subject to a
legal hold, court order, audit/investigation or reasonably anticipated legal
proceedings. Whether destruction is unlawful depends on jurisdiction, context
and intent; ordinary authorized housekeeping is not automatically a crime.
This is general information, not legal advice.
