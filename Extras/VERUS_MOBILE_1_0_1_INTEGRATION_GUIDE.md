# Verus Mobile 1.0.1 Integration Guide

This document captures the Verus Mobile 1.0.1 capability update so the Verus Development Agent can guide app builders on when mobile can replace desktop workflows.

## Release Targets

- iOS TestFlight: `1.0.1-1`
- Android APK release tag: `v1.1.0-1`

## Mobile Capability Additions

- Android now supports shielded address operations and private Z transactions using the native lightwallet stack.
- The new compact GenericRequest deeplink format is supported: `verus://1/<compact_payload>`.
- Supported GenericRequest detail types in this release:
  - `VerusPay v4 invoice`
  - `AuthenticationRequest`
  - `IdentityUpdateRequest` (experimental deeplink setting required)
  - `AppEncryptionRequest` (experimental deeplink setting required)
- `DataPacketRequest` and `UserDataRequest` primitives exist in libraries and are expected to be exposed more fully in app UI later.
- Legacy `x-callback-url` VerusPay/login links remain supported.

## Z Wallet Constraints to Model in App UX

- Z seed must be configured before shielded workflows can run.
- Sending is blocked while shielded sync is in progress.
- Pending private funds are not spendable until confirmations complete.
- Memo support applies when sending to private recipients.

## IdentityUpdateRequest Notes

- Mobile now supports guided review and submit flows for identity updates.
- If `vrsc::identity.credential` data is present, plaintext is encrypted locally before transaction creation.
- Credential encryption flow requires Z seed compatibility with the identity private address.

## AppEncryptionRequest Notes

- Mobile can derive app encryption key material after user approval.
- Responses can include viewing key/address material and optionally secret key material if explicitly requested and approved.
- When an encryption response address is included, response detail can be encrypted into `DataDescriptor`.
- App encryption derivation depends on Sapling material from the user Z seed.

## Builder Guidance

- Prefer GenericRequest (`verus://1/...`) for all new wallet-app request flows.
- Keep legacy deeplink support for backward compatibility while migrating.
- Gate experimental request types in product UI and onboarding docs, because wallet users must enable experimental deeplinks.
- For private send and update flows, surface sync and confirmation state in your app before asking users to approve actions in wallet.
