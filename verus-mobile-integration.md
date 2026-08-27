# Verus Mobile integration

The current knowledge-base snapshot targets the official Android
[`v1.1.0-14`](https://github.com/VerusCoin/Verus-Mobile/releases/tag/v1.1.0-14)
release. See [the detailed capability record](docs/VERUS_MOBILE_V1.1.0-14.md).

`VerusMobileHelper` is a Testnet-only, offline helper for URI and deep-link
metadata. It does not encode the compact `GenericRequest` protocol payload,
sign requests, hold wallet keys, submit blockchain transactions, or approve a
request for the user.

## Safe activation

Use the `wallet_review` activation stage before exposing mobile request links
in another project. For that project, first declare its canonical data source,
actor model, privacy boundary, non-goals, and smallest capability set. Then:

1. use synthetic data and VRSCTEST;
2. generate an already encoded request link;
3. inspect it on the exact target device and wallet build;
4. verify requested scopes, signer, destination, amount, callback, and expiry;
5. let the wallet present the final user review;
6. validate the signed/encrypted response server-side;
7. keep the feature behind its project flag until the complete flow passes.

A QR code, deep link, successful decode, allowlist entry, or generated request
is not authorization.

## Supported helper surfaces

```python
from verus_agent.mobile import VerusMobileHelper

helper = VerusMobileHelper(agent_identity="SyntheticAgent@")

capabilities = helper.get_mobile_capabilities()

user_data = helper.generate_user_data_request_link(
    compact_payload="already-encoded-test-payload",
    response_endpoint="https://example.invalid/callback",
)

data_packet = helper.generate_data_packet_request_link(
    compact_payload="already-encoded-test-payload",
    response_endpoint="https://example.invalid/callback",
)
```

The release identifies User Data, Data Packet, and Identity Update request
routes as experimental. It does not establish current App Encryption support;
the legacy helper remains blocked from task activation until device-level
compatibility is reverified. HTTPS is required by default. The helper
allows HTTP only when the caller explicitly selects `allow_insecure_http=True`
and the process sets `VERUS_MOBILE_ALLOW_INSECURE_HTTP=true` while
`VERUS_RUNTIME_ENVIRONMENT` is `development`, `local`, or `test`. Production
always rejects HTTP.

## VerusPay V4 and Gift Cards

The release publishes VerusPay V4 invoices inside `GenericRequest`, smaller QR
codes, burn invoices, and expanded Gift Card flows. Version 0.5.0 records these
capabilities but does not construct or fund Gift Cards. Funding, burning,
identity update, signing, and broadcast are mutations and require the separate
Testnet mutation contract in `docs/CROSS_PROJECT_ACTIVATION.md`.

## Response handling

Treat every wallet response as untrusted input until protocol validation,
signature verification, request correlation, scope enforcement, expiry checks,
and replay prevention succeed. Encrypted GenericResponses reduce disclosure in
transport but do not remove the need for authorization, privacy minimization,
or secure server-side handling.

Never store or print credentials, WIFs, keys, seed phrases, identity
inventories, real participant data, private endpoints, or response plaintext in
logs, prompts, tests, fixtures, Git, or CI artifacts.
