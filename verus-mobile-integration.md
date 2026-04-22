# Verus Mobile Integration (Current Capabilities)

This document tracks the Verus Mobile capabilities that should be modeled by `verus_agent` when helping design blockchain applications.

## Release Scope Incorporated

- iOS TestFlight release target: `1.0.1-1`
- Android GitHub APK release tag: `v1.1.0-1`

## Core Mobile Capability Upgrades

### 1. Shielded Wallet Parity (Android + iOS)

- Android now supports shielded (Sapling/Z) wallet operations via native lightwallet stack.
- Wallet users can configure/import a Z seed:
  - 24-word mnemonic reuse
  - 24-word Z seed import
  - Sapling extended spending key import
- Wallet can derive Z addresses, track private balances, and show private tx history.
- Z memo support is available for private recipients.
- Sending is blocked while shielded sync is incomplete.
- Private funds must confirm before spendability.

### 2. GenericRequest Deeplink Standard

- Preferred deeplink format is now:
  - `verus://1/<compact request payload>`
- This is now the primary envelope format for app-to-wallet request workflows.
- One request can carry multiple details.
- Legacy deeplinks are still supported:
  - `x-callback-url` VerusPay
  - legacy login/deeplink styles

### 3. Supported GenericRequest Detail Types

- `VerusPay v4 invoice` (includes private address support + compact payload)
- `AuthenticationRequest` (compact login/auth request, encrypted response support)
- `IdentityUpdateRequest` (experimental deeplinks toggle required)
- `AppEncryptionRequest` (experimental deeplinks toggle required)
- `DataPacketRequest` and `UserDataRequest` primitives are library-available but not fully exposed in wallet UI yet.

### 4. IdentityUpdateRequest Flow

Mobile wallet flow now includes:

- Request signer + target identity review
- Change summary with high-risk deltas
- Content changes review step
- Authority/recovery/revocation review step
- Payment confirmation and tx submit
- Resulting update txid display/copy

Credential protection behavior:

- If `vrsc::identity.credential` is included, credential plaintext is encrypted locally before transaction creation.
- Plaintext credential data is not sent to RPC server.
- Z-seed/private-address compatibility is required.

### 5. AppEncryptionRequest Flow

Mobile wallet can now process app encryption key-material requests:

- Shows requesting identity, signer system, signature time, derivation fields.
- Can return viewing/address information.
- Can optionally return extended spending key material only with explicit user approval.
- If response encryption address is provided, response detail may be encrypted into a `DataDescriptor`.
- Z seed is required for derivation.

### 6. UX / Reliability Updates

- iOS deeplink handling improved when app is already open.
- VerusPay and authentication screens reworked.
- Signer card, chain labels, timestamps, and technical detail UX improved.
- Wallet can open compatible requests in alternate installed handler app.
- Experimental request-type settings exposed.
- Shielded sync and send-state messaging improved.

## `verus_agent` Capability Mapping

The agent now models mobile capabilities through:

- `verus.mobile.payment_uri`
- `verus.mobile.login_consent`
- `verus.mobile.purchase_link`
- `verus.mobile.generic_request_link`
- `verus.mobile.identity_update_request_link`
- `verus.mobile.app_encryption_request_link`
- `verus.mobile.capabilities`

## Builder Guidance (Desktop vs Mobile)

Use Verus Mobile for:

- User-approved identity updates
- Login/auth consent and signed responses
- Compact VerusPay invoice/payment flows
- App-to-wallet encryption channel bootstrap flows
- Shielded send/receive workflows where mobile UX is preferred

Keep desktop/server-side components for:

- Heavy automation loops
- Backend policy/risk engines
- Batch operations requiring non-interactive execution
- Services that require deterministic CI/runtime environments

Design pattern:

1. Backend/service prepares signed GenericRequest payload.
2. App presents `verus://1/<payload>` deeplink or QR.
3. User reviews and approves in wallet.
4. Wallet returns signed GenericResponse (optionally encrypted).
5. Service verifies response and executes next step.

## Launching Verus Agent Without UAI

Standalone launch is supported via `docker-compose.verus-agent.yml`:

- `VERUS_UAI_INTEGRATION_ENABLED=false` disables swarm registration.
- Health endpoint is exposed on port `9124`.
- Startup sequence:
  1. dependency install
  2. smoke check (`run_verus_agent_task.py ... smoke`)
  3. long-running agent process (`python -m verus_agent.agent`)

Run:

```bash
docker compose -f docker-compose.verus-agent.yml up -d
```

Verify:

```bash
docker compose -f docker-compose.verus-agent.yml ps
```
