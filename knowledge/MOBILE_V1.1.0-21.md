# Verus Mobile v1.1.0-21

Checked 2026-10-15. **Latest store release: v1.1.0-21.**

## Release evidence

| Channel | Observed version and evidence |
|---|---|
| Google Play | Live [official listing](https://play.google.com/store/apps/details?hl=en&id=org.autonomoussoftwarefoundation.verusmobile.android) HTML contains `1.1.0-21`; updated 2026-10-12. Search-engine cached pages can show older notes. |
| Apple | [App Store](https://apps.apple.com/us/app/verus-mobile/id6447361908) and [lookup metadata](https://itunes.apple.com/lookup?id=6447361908&country=us) expose marketing version `1.1.0`, release time `2026-10-12T19:45:54Z`, minimum iOS 15.1. The public metadata does not expose build suffix `-21`. |
| Announcement | [Veruscoin Announcements](https://t.me/TruthAndPrivacyForAll/422) explicitly names `v1.1.0-21` for both stores and matches the supplied announcement. |
| GitHub source | Latest [APK release v1.1.0-20](https://github.com/VerusCoin/Verus-Mobile/releases/tag/v1.1.0-20), published 2026-10-07, commit `e659a1c6aa17ebe633e3c66c79091594dda1454b`. No `-21` GitHub release was found. |

Implementation references below use that available `-20` commit. This does
not establish that it reproduces either `-21` store binary. Later master
`25515ffce77ca6b563d0456d4b1198039f6d347f` adds iOS UIScene lifecycle migration.
The [source lockfile](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/pnpm-lock.yaml)
pins primitives `3ffa9d77a3dd98c23fe4f66cf4368946906de780`, ID client
`933e8f8da1a51b99ba7533701dddb9914b7a06b7`, and RPC client
`e8ea8c21f8a3d845e20189440dcd820d16f00891`.

## Features recorded for -21

The announcement describes gift-card onboarding without manual 24-word
transcription; labeled/password-protected gift cards holding currencies,
identities, or both; compact VerusPay V4 and burn invoices; selective user-data
and credential requests; approved data-packet signing; identity updates;
encrypted signed responses; HTTPS-default response delivery; and broader
RPC/identity/currency/transaction/credential validation. It also records
navigation/animation performance improvements, identity-change display and
legacy-login display fixes, and Android 16 KB page-size support.

These are upstream release claims and source observations. This update did
not test a device, install a wallet, or perform any payment or identity action.

## Build a deeplink

Use the pinned primitives and ID client described in
[SDK and primitives](SDK_AND_PRIMITIVES.md). Construct typed ordinal details
in `GenericRequest`, authorize and sign an application request when required,
then call `request.toWalletDeeplinkUri()`. It returns
`verus://1/<Base64URL(request.toBuffer())>`. `toQrString()` returns only the
Base64URL payload. Parse with `GenericRequest.fromWalletDeeplinkUri(uri)`.
Hex used for Mobile's internal navigation is not the deeplink encoding.

[Mobile routing source](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/sagas/deeplink.js)
rejects URLs of length 2046 or more. This is a handler limit, not an on-chain
storage limit. Do not base64-encode arbitrary JSON and call it a protocol
request. Python's `generate_generic_request_link` only wraps an already encoded
payload; it neither validates its binary contents nor signs it. Its separate
`response_endpoint` argument is metadata/policy validation and does not modify
or verify the callback embedded in the encoded payload.

[Envelope validation](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/validator/envelopeValidator.js)
checks envelope and detail types, matching network/system, and delegated
signer rules. Unknown detail types fail. Unsigned details are limited to
invoice, spendable key, and backup requests, subject to additional envelope
and ordering restrictions. A declared app/delegated identity requires signing.
Application verification should reject unsigned requests by default.

Users must enable **Wallet Settings -> General Settings -> Enable experimental
deeplinks** for Identity Update, App Encryption, User Data, and Data Packet
details. See [exact gating source](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/experimentalDeeplinks.js).
Keep a consuming-project feature flag as well. Source support for App
Encryption does not remove this repository's blocked task-activation policy.

## Detail types and actual supported subsets

| Action | Typed detail/wrapper | Verified source behavior |
|---|---|---|
| Login | `AuthenticationRequestDetails` / `AuthenticationRequestOrdinalVDXFObject` | Include request ID, expiry and recipient constraints as appropriate. Legacy login remains a separate path. |
| Invoice | `VerusPayInvoiceDetails` / `VerusPayInvoiceDetailsOrdinalVDXFObject` | V4 details inside the request; testnet flags must match. |
| Identity update | `IdentityUpdateRequestDetails` / `IdentityUpdateRequestOrdinalVDXFObject` | Signed request, experimental setting, current identity UTXO and expiry checks, wallet content/control/payment review. |
| User data | `UserDataRequestDetails` / `UserDataRequestOrdinalVDXFObject` | Signed request; `CREDENTIAL` and `FULL_DATA` only; response-encryption address required. |
| Data packet | `DataPacketRequestDetails` / `DataPacketRequestOrdinalVDXFObject` | Signed request; `FLAG_FOR_USERS_SIGNATURE`; nonempty list of strings or `DataDescriptor` objects. Transmittal-to-user mode rejected. |
| Encryption | `AppEncryptionRequestDetails` / `AppEncryptionRequestOrdinalVDXFObject` | Experimental upstream route; local task activation remains blocked; never request secret spending material by default. |

User-data [validation](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/validator/userDataRequestValidator.js)
requires `searchDataKey` to be an array of single-key objects with Buffer hash
values, not raw personal fields. Credentials are filtered by key, validity,
and requesting app/delegated scope. Optional requested signer constrains the
response identity. The user selects which matching credentials to return.
The [response builder](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/userData/buildUserDataResponse.js)
returns a `DataResponseOrdinalVDXFObject` containing a `DataDescriptor` and
matching detail request ID; no selected credentials yields no data response.

Data-packet [validation](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/validator/dataPacketRequestValidator.js)
and [signing](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/dataPacket/signDataPacket.js)
use UTF-8 string bytes or descriptor serialization, SHA-256 and identity
signature data. Each object and statement is reviewed and signed; responses
can contain multiple returned signatures. Validate every returned item.

Identity-update [handler](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/handlers/identityUpdateRequestDetailsHandler.js)
fetches current state separately from accumulated content, rejects unsupported
active-currency/tokenized-control changes, checks key namespaces and expiry,
and defers transaction creation until wallet review. Credential plaintext must
not be sent through RPC JSON. Preserve all intended current-state entries and
serialize updates for each identity. Historical aggregation is a different read.

## VerusPay V4 and burns

The [invoice validator](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/validator/verusPayInvoiceDetailsValidator.js)
checks currency, accepted systems, preconvert state, height expiry, and network.
At this source baseline it rejects tagged invoices and Sapling destinations;
the primitives accepting a type does not prove Mobile accepts it.

[Burn-price validation](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/verusPayBurnChangePrice.js)
requires a nongateway token, its native payment system, and no conversion or
preconvert. An explicit destination must be P2PKH or an identity; an
any-destination burn resolves to the payer's own address. Treat the release's
price-impact language as a description of protocol mechanics, not a guaranteed
financial outcome. An invoice, wallet response, broadcast, and confirmed burn
are distinct states.

## Encrypted GenericResponses and callbacks

The [completion path](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/containers/DeepLink/GenericRequestComplete/GenericRequestComplete.js)
encrypts details when requested, prepares response metadata, signs with the
wallet-held key, verifies the response and then delivers it. Metadata includes
matching request ID, `request.getRawDataSha256()` as request hash, SHA-256 hash
type, created time, handler ID and Testnet state. Conflicting signer identity
or system across details is rejected.

Encryption wraps serialized details in one encrypted
`DataDescriptorOrdinalVDXFObject` and sets `FLAG_DETAILS_ARE_ENCRYPTED`.
Setting the flag alone does not encrypt data. Never return an unencrypted
extended spending key; Mobile has a specific guard for this case.

[Delivery policy source](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/deeplink/genericResponse/responseDeliverySecurity.js):

- POST uses `response.toBuffer()` and `Content-Type: application/octet-stream`.
- HTTPS is the default for POST. The Mobile build setting
  `ALLOW_HTTP_GENERIC_RESPONSE_POSTS` defaults false in both platform environment
  files. This guard specifically covers POST; do not infer it validates redirects.
- Redirect delivery places Base64URL response bytes under query key
  `GENERIC_RESPONSE_DEEPLINK_VDXF_KEY.vdxfid`.
- Authentication expiry is checked before signing and before delivery.

The Python helper's `VERUS_MOBILE_ALLOW_INSECURE_HTTP` plus
`VERUS_RUNTIME_ENVIRONMENT` development gate is a separate local policy;
it does not configure Mobile's build setting. Keep HTTPS for new integrations.
Callback applications must parse fresh instances, verify the signed envelope
on the expected network/identity, decrypt locally, compare request hash and
IDs, enforce scope and expiry, reject replay, and validate all details. SDK
signature verification alone does not implement application session policy or
prove a blockchain mutation completed.

## Gift cards, NFC, and onboarding

[Gift-card source](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/utils/giftCard/giftCard.js)
generates entropy/mnemonic material and a `SpendableKeyDetails` request. A gift
card is bearer spending material: its link, QR, serialized request, mnemonic,
password and backup must never enter public Git, prompts or logs.

Source functions separate `createGiftCard`, `verifyGiftCardAddresses`,
`preflightGiftCardFunding`, `broadcastGiftCardFunding`, and
`refreshGiftCardStatus`. Card states include `new`, `funded`, `redeemed`;
funding also distinguishes pending from confirmed. Re-funding a shared/claimed
or previously attempted card has additional restrictions. Never equate a
displayed funding status with confirmed ownership of a claimed identity.

`buildGiftCardNfcDeeplinkUri` orders backup details before spendable-key
details. The [backup review screen](https://github.com/VerusCoin/Verus-Mobile/blob/e659a1c6aa17ebe633e3c66c79091594dda1454b/src/containers/DeepLink/WalletBackupRequestInfo/WalletBackupRequestInfo.js)
offers claiming to an existing profile or backing up then claiming. The
supported backup request type is `NFC_NDEF_BACKUP`; NFC backup MIME is
`application/x-vrsc-wallet.backup`. NFC availability, writability, capacity,
existing backup and funded spending material must be checked before overwrite.

“24-word-less” means avoiding manual recovery-word transcription in the
onboarding flow. Seeds still exist and require secure backup. Claim discovery,
preflight and broadcast are separate stages; wallet confirmation and chain
confirmation remain essential. This repository does not implement card
funding/claims or NFC writing. None are authorized by this knowledge update.
