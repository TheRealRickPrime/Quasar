# Quasar

Quasar is a privacy-first Android backup application that guides users through a secure, authenticated backup workflow, cloud selection, and upload status tracking.

This repository contains:
- Android app scaffolding for onboarding and backup setup
- Python backend API architecture for auth, user profiles, backup sessions, and upload status
- MongoDB-oriented data model and route design
- Product design notes for the Quasar brand and workflow

## Repository structure

- `android/` — Android app skeleton (Kotlin + Jetpack Compose)
- `backend/` — Python API skeleton (FastAPI + MongoDB-ready models)
- `docs/` — product, system, and API design references

## Intended flow

1. User signs up or logs in
2. User selects their preferred cloud provider
3. User follows the guided ADB backup workflow on Android
4. Encrypted backup is created and uploaded
5. Upload status is tracked and shown to the user in a profile/dashboard link
6. User can later access backup metadata and link it to their profile

## Current status

This is an initial scaffold and direction-setting implementation, not a complete production app.
