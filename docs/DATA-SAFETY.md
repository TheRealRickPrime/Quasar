# Privacy, deletion and preservation

These notices are visible in both apps on **Privacy & data**, with additional
context before the existing destructive operations. No secure-wipe or
evidence-destruction functionality is provided.

## Local state is different from backups

Windows stores settings, activation, usage and history under `%APPDATA%\Quasar`.
Updates and editions share this location. Removing a license forgets local
activation; it does not cancel a purchase, delete backups or reset usage.
Close Quasar before managing local configuration/history with File Explorer.
Cloud credentials are separate Windows Credential Manager `QuasarWindows`
entries; remove/revoke them there and at the provider as needed.
Signing out of the optional backend removes the session, not the account or
server records. No server account-delete API exists; contact its operator.

Android keeps private activation and usage in its existing package storage.
Android Settings > Apps > Quasar > Storage > Clear storage, or uninstalling,
removes that local state. Keep receipt keys before doing so. The app opts out
of Android backup for private data; device migration behavior may differ.
Clear Sources removes a selection, not source files.

Manage Windows archives/images in their saved folders, and Android saved
archives/restored files through Files or the selected document provider.
Removing settings/uninstalling is not the same as deleting these backups.
Android backup leaves selected originals alone. Working cache files are
normally removed at the end of operations; Android can clear remaining cache.
Windows' explicit original-deletion option removes the unencrypted ADB backup
after encryption verification; compressed intermediate files may also be
removed. Android restore replaces matching file names; Windows partition
restore overwrites selected partitions. Both require confirmation.

Uploaded copies, synced files, trash, versions, snapshots and retention policies
must be managed through the relevant cloud provider. Quasar has no cloud-delete
control. Upload allowances are not storage capacity provided by Quasar, and the
Android app does not implement direct cloud upload.

## Deletion limitations and legal preservation

Deletion is **not guaranteed secure erase**. Other copies and provider retention
may remain. Verify usable backups and preserve required records first.

Do not delete or alter records subject to a legal hold, court order, audit or
investigation, or reasonably anticipated legal proceedings. Unlawful
destruction of evidence or obstruction depends on jurisdiction, context and
intent; normal authorized housekeeping is not automatically a crime.
This is general information, not legal advice.

## Network behavior

Gumroad receives receipt keys during activation/rechecks; successful checks
permit a 30-day offline grace, with rechecks due after 3 days. Refunds/disputes
revoke entitlement. Public release servers receive requested update checks and
downloads. Windows cloud/account connections use user-configured services.

Affiliate cards are local text/buttons, only in unactivated Free with Ads on
the secondary Privacy & data surface. No ad SDK, tracking pixel or remote image
is loaded. A deliberate click opens the provider's browser landing page, where
its own policies and cookies apply. Quasar Labs may earn a commission on
resulting purchases; no click or purchase is required or rewarded. No supplied
installer is automatically downloaded or executed.
