# SDK commits and VerusCoin 1.2.18 compatibility work

Public source inspected 2026-10-15. Full commits identify this snapshot; the
clients retain old manifest version numbers despite substantial changes.

| Component | Branch / package version | Commit |
|---|---|---|
| [verusid-ts-client](https://github.com/VerusCoin/verusid-ts-client/commits/master/) | master / 0.1.0 | `933e8f8da1a51b99ba7533701dddb9914b7a06b7` (2026-09-22) |
| [verusd-rpc-ts-client](https://github.com/VerusCoin/verusd-rpc-ts-client/commits/main/) | main / 0.1.0 | `e8ea8c21f8a3d845e20189440dcd820d16f00891` (2026-09-17) |
| [verus-typescript-primitives](https://github.com/VerusCoin/verus-typescript-primitives) | master / 1.0.0 | `3ffa9d77a3dd98c23fe4f66cf4368946906de780` (2026-09-17) |
| [VerusCoin v1.2.18](https://github.com/VerusCoin/VerusCoin/releases/tag/v1.2.18) | release, published 2026-09-17 | `d4cbace35e570b4ce0b2413ab018cafd779f13a9` |
| [VerusCoin master](https://github.com/VerusCoin/VerusCoin/tree/5ec1d83b16253aa56abda5588be76ce2d84dee8f) | master at inspection | `5ec1d83b16253aa56abda5588be76ce2d84dee8f` |

Both client manifests pin primitives `3ffa9d77...`; the ID client also pins
RPC client `e8ea8c21...` and BitGoJS
`2d3240429b7664fb01ca3f0f9e1c2b6da803f68d`. Mobile's available `-20`
lockfile agrees on these three Verus library pins. Use exact reviewed commits
and a lockfile in a consuming TypeScript project. This change installs no JS
dependencies and does not change the Python daemon floor (`1.2.17-6`).

## Locate the primitives compatibility update

[PR 45](https://github.com/VerusCoin/verus-typescript-primitives/pull/45)
merged 2026-09-11 as `7a7b01db697222cd68507a9dbf15f289615ea890`;
[content commit](https://github.com/VerusCoin/verus-typescript-primitives/commit/0e76a90ca7636571034c60f1139b932b5954a482)
is `0e76a90ca7636571034c60f1139b932b5954a482`. It updates protocol
compatibility and serialization consistency across descriptors, credentials,
partial sign data, identities, destination/script encoding, signatures,
CompactSize/VARINT and MMR proofs. Legacy `SignedSessionObject` construction
is disabled. Deserializers are single-use across `fromBuffer`, `fromDataBuffer`
and `fromBufferOptionalType`, including failed attempts: create a fresh object
for every new input or retry.

The subsequent [3ffa9d77 fix](https://github.com/VerusCoin/verus-typescript-primitives/commit/3ffa9d77a3dd98c23fe4f66cf4368946906de780)
uses the nested parser's returned offset in `DataResponseDetails.fromBuffer`
and preserves defined falsy ordinal values in `VdxfUniValue` (for example zero
and false). These changes matter for multi-detail response decoding.

**Qualification boundary:** this is the relevant compatibility work to review
for daemon 1.2.18, not proof of complete 1.2.18 binary interoperability.
The upstream [MMR fixture provenance](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/__tests__/fixtures/mmr/veruscoin-v1.json)
names daemon **1.2.17-6**, protocol 170010. PR 45 does not declare complete
1.2.18 qualification. No upstream JS tests, daemon operations or round trips
were executed in this knowledge update.

Compare exact daemon [MMR serialization](https://github.com/VerusCoin/VerusCoin/blob/d4cbace35e570b4ce0b2413ab018cafd779f13a9/src/mmr.h)
and [PBaaS RPC source](https://github.com/VerusCoin/VerusCoin/blob/d4cbace35e570b4ce0b2413ab018cafd779f13a9/src/rpc/pbaasrpc.cpp)
when building fixtures. Do not silently reserialize historical signed bytes
using new serializers; review persisted payloads, hashes and signatures first.

## ID client migration

[Current implementation](https://github.com/VerusCoin/verusid-ts-client/blob/933e8f8da1a51b99ba7533701dddb9914b7a06b7/src/VerusIdInterface.ts)
provides `createGenericRequest`, `createGenericResponse`, `signGenericRequest`,
`signGenericResponse`, `verifyGenericRequest` and `verifyGenericResponse`.
Old login and standalone invoice helpers are deprecated in favor of typed
details within GenericRequest/GenericResponse.

Notable commits to consult:

| Commit | Change and integration consequence |
|---|---|
| [379db177](https://github.com/VerusCoin/verusid-ts-client/commit/379db177d13c2a54334b77d77280fca33e4f9548), Sep 14 | Correct funded identity-output content map validation. Current-output entries and historical aggregates have different roles. |
| [e13438fe](https://github.com/VerusCoin/verusid-ts-client/commit/e13438fe4b79536b754649f62342b7c0b1123380), Jun 8 | Expose `createUnfundedCurrencyTransferTransaction`. |
| [2eec86c7](https://github.com/VerusCoin/verusid-ts-client/commit/2eec86c7f06d13c8b04ddc1473fce32c450d2a31), Jun 4 | Currency-transfer sweeps and fee fixes. |
| [dc8b7490](https://github.com/VerusCoin/verusid-ts-client/commit/dc8b74906f9fd8114bdf28cb4c813e96969fd58b), Jun 3 | Validate funded identity updates, sweep transactions and previous outputs. |
| [58a31a3a](https://github.com/VerusCoin/verusid-ts-client/commit/58a31a3a8ab024eeb615e4d46a780fae67c8889e), May 2 | Backup detail may precede authentication. |
| [8691941f](https://github.com/VerusCoin/verusid-ts-client/commit/8691941f814ae92353c34d176e799eda357d6745), May 2 | Backup detail validation. |
| [da5c2d8b](https://github.com/VerusCoin/verusid-ts-client/commit/da5c2d8b35af6c53b93f0f9ae5f83e6b699aadc2), Mar 2 | Explicit `acceptUnsigned` verification option. |

The September identity comparison rejects unexpected new content map entries
when omitted from a partial update and excludes the old per-transaction map
from unchanged-field comparison. Do not confuse that SDK funding validator
with the Python manager's current-state preservation policy, or copy an entire
historical aggregate into every new snapshot.

## RPC client migration

[September migration 58689ea5](https://github.com/VerusCoin/verusd-rpc-ts-client/commit/58689ea52500a6a6e4aa741e5d2ed41d7bc6ddd7)
and the pinned [compatibility README](https://github.com/VerusCoin/verusd-rpc-ts-client/blob/e8ea8c21f8a3d845e20189440dcd820d16f00891/README.md)
explain these source changes:

- ES2015 or newer target. Address UTXOs/deltas can be arrays or objects with
  chain information. Normalize the collection while preserving needed metadata.
- UTXO `isspendable` is boolean; `blocktime` can be absent. Mempool uses
  `timestamp` and `spending`, not confirmed-block fields.
- Currency/blockchain fields are conditional, offers can be `false`, and
  transaction templates can contain `hextx` or `hextxwithoutz`.
- Preserve omitted middle positional arguments; trim trailing omissions only.
  Do not recreate a `filter(x => x != null)` parameter builder.
- Public `signRawTransaction(hex, prevtxs?, sighashtype?, branchid?, privatekeys?)`
  maps keys to the daemon's third wire slot. Omitted keys and an empty list
  have different semantics.
- `fundRawTransaction` accepts hex alone or supported UTXO/change/explicit-fee
  combinations; unsupported combinations fail before transport.
- Nested MMR `signData` inputs use `serializedhex`/`serializedbase64` and
  `mimetype`. Use the actual current interfaces.
- Converter discovery resolves full definitions by unambiguous currency ID
  and preserves original converter records.
- `sendCurrency` normally returns an operation ID; templates are a separate
  mode. Poll terminal operation status and require the resulting transaction
  ID before claiming successful submission; confirmation/readback is separate.

[June fee3d2b2](https://github.com/VerusCoin/verusd-rpc-ts-client/commit/fee3d2b217c2b3b9f63da4527bb852e1cbc5edf2)
adds `getIdentitiesWithAddress`. March changes add API authentication and
transport overrides; `APIAuthData` and `RPCRequestOverride` are exported.
Use [current implementation](https://github.com/VerusCoin/verusd-rpc-ts-client/blob/e8ea8c21f8a3d845e20189440dcd820d16f00891/src/VerusdRpcInterface.ts)
instead of inventing signed-header/body formats. Never record actual auth data.

## Typed offline request preparation

Source-reviewed example; not compiled, signed or wallet-tested here. The
caller supplies synthetic valid Testnet request-ID address data. This builds
an unsigned scaffold; an authentication request must be authorized and signed
before delivery. No RPC is performed by this direct constructor.

```typescript
import { randomBytes } from "crypto";
import { BN } from "bn.js";
import {
  AuthenticationRequestDetails,
  AuthenticationRequestOrdinalVDXFObject,
  CompactIAddressObject,
  GenericRequest,
  ResponseURI,
} from "verus-typescript-primitives";

function prepareLogin(requestIdAddress: string, callback: string,
                      createdAt: number, expiresAt: number): GenericRequest {
  if (new URL(callback).protocol !== "https:") throw new Error("HTTPS required");
  const requestID = CompactIAddressObject.fromAddress(requestIdAddress, "VRSCTEST");
  return new GenericRequest({
    flags: GenericRequest.FLAG_IS_TESTNET,
    requestID,
    createdAt: new BN(createdAt),
    salt: randomBytes(16),
    responseURIs: [ResponseURI.fromUriString(callback, ResponseURI.TYPE_POST)],
    details: [new AuthenticationRequestOrdinalVDXFObject({
      data: new AuthenticationRequestDetails({requestID, expiryTime: new BN(expiresAt)}),
    })],
  });
}
```

Sources: [request](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/request/GenericRequest.ts),
[authentication](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/login/AuthenticationRequestDetails.ts),
[callback type](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/ResponseURI.ts).
Request IDs are compact address objects, not arbitrary UUID JSON. Explicitly
select POST because `ResponseURI.fromUriString` otherwise defaults to redirect.
The HTTPS check is application policy, not enforcement by that constructor.

For separately authorized application signing, use `VerifiableSignatureData`
with explicit `DEFAULT_VERSION`, `isTestnet: true`, and compact `systemID` and
`identityID`; assign it to `request.signature`, then `request.setFlags()`.
Call `client.signGenericRequest(request, authorizedKey, verifiedIdentity,
verifiedHeight)`. Keep key access in the approved signing boundary. A scaffold
can set the signed flag before actual signature bytes exist: emit only after
signing succeeds. This signature does not approve the end user's wallet action.

Encode using `request.toWalletDeeplinkUri()`; parse with
`GenericRequest.fromWalletDeeplinkUri(uri)`. Verify via
`client.verifyGenericRequest(request, verifiedIdentity, expectedChainIAddress,
verifiedSignatureBlockTime)`. Unsigned acceptance defaults false. `createdAt`
is required for the signed-envelope time check. The `createGenericRequest`
convenience method may look up chain ID if it is omitted, even without signing.

Other exact detail constructors:

| Detail | Fields to review in pinned source |
|---|---|
| [IdentityUpdateRequestDetails](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/identity/IdentityUpdateRequestDetails.ts) | `identity: PartialIdentity`, optional `requestID`, `expiryHeight`, `systemID`, `txid`, `signDataMap` |
| [UserDataRequestDetails](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/data/UserDataRequestDetails.ts) | `flags`, `dataType`, `requestType`, hash-buffer `searchDataKey`, optional hash type/signer/requested keys/request ID |
| [DataPacketRequestDetails](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/data/DataPacketRequestDetails.ts) | `flags`, `signableObjects`, optional `statements`, `signature`, `requestID` |
| [VerusPayInvoiceDetails](https://github.com/VerusCoin/verus-typescript-primitives/blob/3ffa9d77a3dd98c23fe4f66cf4368946906de780/src/vdxf/classes/payment/VerusPayInvoiceDetails.ts) | BN `amount`, typed `destination`, `requestedcurrencyid`, other invoice fields; second constructor argument defaults V4 |

Wrap each in its corresponding `...OrdinalVDXFObject({data: detail})`.
User-data type/request constants are scalar values, not bit flags. Mobile
supports only the subset in [the mobile guide](MOBILE_V1.1.0-21.md).
Data-packet signature bit is 8; transmittal bit 16 is rejected by Mobile.
Invoice flags use `detail.setFlags({isTestnet: true})` and, when appropriate,
`isBurnChangePrice: true`; set both intended flags together. Current
`TransferDestination` uses `destinationBytes`, not the older README's
`destination_bytes` example.

Order backup first, authentication next/first, provisioning/app encryption
after authentication, and at most one identity-update-or-invoice terminal
action last. Full detail validation is still required. Encrypted details use
one encrypted descriptor and flag 1024; a flag does not perform encryption.

## Verification work still required by a consuming implementation

Review fixed-byte round trips, fresh parser/failure behavior, falsy ordinals,
multi-detail offsets, signature hashes, MMR vectors, response encryption,
positional omissions and RPC unions. Then, with separate explicit authority,
validate on exact Testnet daemon 1.2.18 and Mobile store build/device.

Local `tests/test_primitives_upstream_contract.py` only checks three source
strings (FQN content maps, remove actions 3/4, optional auth request ID). It
does not establish those binary contracts or daemon compatibility. A skipped
contract lane is not a pass. No knowledge claim upgrades this lane's evidence.
