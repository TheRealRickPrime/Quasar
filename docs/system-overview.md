# Quasar System Overview

## Product goal

Quasar is a user-facing backup workflow app designed to help Android users securely create and store a full-device image backup in an encrypted form, then upload it to a chosen cloud provider and track the result via a profile dashboard.

## Primary user journey

1. Install and open the app
2. Create account or sign in
3. Onboard with privacy and backup warnings
4. Choose cloud provider
5. Complete ADB setup steps on the connected device
6. Generate encrypted full-device backup
7. Upload to selected storage provider
8. Receive a dashboard/profile link for later restore or status checking

## Core product components

### Android client

Responsibilities:
- onboarding and account flow
- cloud provider selection UI
- ADB instruction checklist and status tracking
- local encrypted backup generation assistance
- upload progress display
- link to the user dashboard

### Backend API

Responsibilities:
- user accounts and authentication
- cloud connection management
- backup sessions and upload metadata
- link generation and profile URLs
- status reads for app and web clients

### Data storage

- MongoDB for users, sessions, cloud credentials references, and backup metadata
- object storage (provider-based) for encrypted backup archives

## Design principles

- user-friendly and trustworthy
- explicit, guided steps
- privacy-forward without interfering with legal compliance
- provider-agnostic design with direct cloud integration capability
- simple profile-based status access

## Architecture summary

```
Android App -> Backend API -> MongoDB
                |-> Cloud Provider Integrations
                \-> User Dashboard / Profile Link
```

## Brand direction

The product name "Quasar" should suggest reliability, distance, and forward motion. Visual cues should include a subtle comet or star trail behind the wordmark to align with the name while maintaining a premium, privacy-oriented look.
