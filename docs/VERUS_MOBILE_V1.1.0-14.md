# Verus Mobile v1.1.0-14 capability snapshot

Source fact verified 2026-08-26: the official Android release
[`v1.1.0-14`](https://github.com/VerusCoin/Verus-Mobile/releases/tag/v1.1.0-14)
was published on 2026-08-25 from signed tag commit
`3614a720aba25525f3907bdfefd8f1e271f06a62`. The release asset is an Android
APK. The release page does not establish an equivalent iOS version.

## Published capabilities

- Gift Cards can be labeled, optionally claim-password protected, funded with
  currencies, VerusIDs, or both, monitored for funding, and shared by QR code,
  link, or NFC. The release describes one-time-use keys.
- VerusPay V4 places invoice details inside a `GenericRequest`, reduces QR size,
  and supports burn invoices.
- experimental User Data requests show scopes and credential details, allow a
  selective response, and produce signed validated responses;
- experimental Data Packet requests support review and signing of approved
  packets and multi-detail responses;
- experimental Identity Update requests support wallet review and submission
  from a deep link or QR code;
- response endpoints default to HTTPS; HTTP requires an explicit environment
  option;
- GenericResponses can be encrypted and include signer selection,
  verification, and secure delivery;
- validation was expanded across RPC, currency, identity, transaction,
  broadcast, gift-card, credential, and multi-detail request surfaces.

These are release claims, not proof that every device, platform, server, or
application integration behaves correctly. Keep experimental deep links behind
a project feature flag and validate on the exact wallet build and target device.
The release page does not establish current App Encryption request support, so
that legacy helper is not task-activatable in version 0.5.0.

## Agent support

`VerusMobileHelper` remains an offline link/metadata helper. It does not build
or sign protocol payloads, access wallet keys, submit transactions, or simulate
user approval.

Version 0.5.0 adds:

- a Testnet-only helper default;
- metadata for Gift Cards, VerusPay V4, encrypted GenericResponses, and the
  expanded validation surface;
- `generate_user_data_request_link` and
  `generate_data_packet_request_link` wrappers for already encoded payloads;
- HTTPS response-endpoint enforcement unless insecure HTTP is enabled both by
  the request and the environment-level gate in development/local/test;
- an explicit `wallet_review_required` result marker.

Do not include credentials, participant data, private endpoints, wallet
material, or production response URLs in test payloads, logs, prompts, or Git.
