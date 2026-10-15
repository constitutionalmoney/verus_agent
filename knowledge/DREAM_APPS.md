# Structuring Verus DREAM applications

Checked 2026-10-15. Source facts come from the official
[DREAM model](https://verus.io/dream), [developer start page](https://verus.io/build/start),
and the pinned libraries in [SDK and primitives](SDK_AND_PRIMITIVES.md).

DREAM means Decentralized, Rights-preserving, Encrypted Application Model.
The app prepares a request, the user reviews it in their wallet, and the app
validates the signed response. Applications retain their own interfaces,
services and business logic; users may select different identities for
different contexts. Encrypted storage may be local, server hosted or associated
with an identity. Encrypted on-chain content still leaves observable updates.
The official page describes VerusSky and Verus Notes as apps in development;
that is not evidence of general production readiness.

## Proposed application boundaries

This structure is an integration proposal, not an upstream-required framework:

```text
dream/
  requests/       typed details, request order, pinned binary serialization
  transport/      QR/deeplink presentation and HTTPS binary callbacks
  verification/   expected network/signer, signed envelope, decrypted details
  sessions/       request hash/ID, expiry, consumed state and replay rejection
  vault/          client-side encryption and intentional ciphertext-only sync
  receipts/       consent result, broadcast state, verified chain outcomes
```

Before implementation, use the repository's cross-project activation contract:
declare canonical store, actor model, privacy boundary, non-goals, Testnet and
the smallest capability/RPC set. Keep business data canonical where the project
declares it; an identity entry does not automatically replace every database.
Separate permission to authenticate, disclose data, sign a statement, pay,
update an identity, and delegate authority.

## Request lifecycle

1. Define one bounded action, requesting app identity, expected Testnet system,
   minimum scopes, response identity policy and expiry.
2. Build typed ordinal details with pinned primitives. Prefer minimal details;
   respect backup/auth/action ordering and Mobile's URL-size/subset limits.
3. Prepare a response-encryption address where required. User-data credentials
   require one in the verified Mobile source. Do not expose spending material
   to the web page or callback service.
4. Authorize any application signing separately, then sign. Persist exact
   request bytes, request hash, IDs, expiry and outstanding/consumed state in
   the app's session store. Do not log full sensitive requests.
5. Present `toWalletDeeplinkUri()` as a mobile link or QR. The wallet performs
   visible human review. Show compatible wallet/build and experimental-setting
   requirements in the app before the handoff.
6. Receive POST bytes with a bounded `application/octet-stream` body. Use
   fresh parser objects; do not parse signed binary as arbitrary JSON. Verify
   envelope signature/network/signer, decrypt through the intended key boundary,
   validate each detail, match exact request ID/hash and expected scopes, enforce
   expiry, and atomically consume the session to prevent replay.
7. Store only the minimum permitted receipt. Follow up independently for
   operation status, transaction confirmation and current-state readback when
   the request involved a mutation. A signed response proves neither payment
   settlement nor confirmed ownership by itself.

The pinned ID client `verifyGenericResponse` verifies the signed envelope but
does not implement this app's outstanding-session/consumption policy. In
Mobile, response correlation uses `request.getRawDataSha256()`. See the
[mobile response guide](MOBILE_V1.1.0-21.md) for binary delivery, signing and
encryption boundaries.

## Feature design choices

| Use case | Suggested starting point | Additional contract |
|---|---|---|
| Sign in | Authentication detail and HTTPS callback | Identity/network policy, short-lived session, replay prevention |
| Encrypted app vault | Authentication plus App Encryption | Derivation scope, local key custody, encrypted response, backup/recovery UX; local agent task activation currently blocked |
| Credential collection | Scoped User Data request | CREDENTIAL/FULL_DATA subset, selective disclosure, encryption, credential validity and requested signer |
| Statement approval | Data Packet request | Review each statement/object, exact byte hash, signer and each returned signature |
| User-owned content update | Identity Update detail | Current UTXO, intended map preservation, namespace/authority checks, serial writes, confirmation/readback |
| Invoice | VerusPay V4 detail | Currency/network/expiry/destination checks, separate payment receipt and confirmation |
| Onboarding gift | Wallet-created gift card/backup flow | Bearer secret custody, funded/claimed state, wallet approval, NFC capacity and backup verification |

Use [Verus Notes](https://github.com/Meyse/verus-notes-testnet) as a Testnet
alpha reference for a locally verified encrypted vault, not a ready-to-deploy
template. Community projects use different/older SDK pins; reconcile them
before combining code. [Community records](COMMUNITY_PROJECTS.md) document
their actual source snapshots and limitations.

## Proposed acceptance checks for a future implementation

Use synthetic fixtures to cover expired/wrong-network/wrong-signer requests,
unsigned/scaffold-only signatures, callback substitutions, mismatched request
hash or detail IDs, partial multi-detail responses, ciphertext tampering,
duplicate callbacks, parser reuse and declined wallet actions. Verify local
and encrypted-cloud recovery without copying keys into a server or logs.
Then obtain separate authority for any device, external Testnet or mutation
test. This knowledge update implements retrieval and reference metadata; it
does not implement a DREAM server, custody service, or wallet approval flow.
