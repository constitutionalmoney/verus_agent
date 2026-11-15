# Verus Mobile v1.1.1

Checked 2026-11-15. **Latest GitHub release: v1.1.1**, a call for testers
focused on the VerusID lifecycle. The release does not replace the separately
observed public-store baseline.

| Channel | Evidence |
|---|---|
| Android GitHub APK | [v1.1.1 release](https://github.com/VerusCoin/Verus-Mobile/releases/tag/v1.1.1), published 2026-11-15 at 08:43:48 UTC, lists `VerusWallet-1.1.1.apk`. The [tagged source](https://github.com/VerusCoin/Verus-Mobile/tree/d82d0e8ea457979778a857c9812b7aa29ebd0410) is the implementation baseline. [Android Gradle](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/android/app/build.gradle) specifies `com.verusmobile` and `1.1.1`; the APK was not downloaded, inspected or installed. |
| iOS TestFlight | v1.1.1 is announced in the supplied release announcement. Availability to a particular account and the installed build were not independently verified. |
| Public stores | Live [Google Play](https://play.google.com/store/apps/details?hl=en&id=org.autonomoussoftwarefoundation.verusmobile.android) metadata still exposes `1.1.0-21` for the store package. [Apple lookup](https://itunes.apple.com/lookup?id=6447361908&country=us) still exposes marketing version `1.1.0`, released October 12, while the [October announcement](https://t.me/TruthAndPrivacyForAll/422) identifies build `-21`. See the [October store guide](MOBILE_V1.1.0-21.md). |

The tag is commit `d82d0e8ea457979778a857c9812b7aa29ebd0410`. Source inspection
does not establish binary equivalence, store rollout, Android/iOS parity or
daemon interoperability. The [SDK companion](SDK_AND_PRIMITIVES.md) records
the three refreshed pins. Use the exact release channel and package/build
when comparing behavior.

## Register a VerusID: commitment, confirmation, registration

**Source facts.** The wallet's Identity registrations screen uses
[registration orchestration](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityRegistration/registration.js),
[review screens](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/containers/Services/ServiceComponents/VerusIdService/IdentityRegistration/RegistrationScreens.js),
and [profile-scoped storage](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/actions/actions/services/dispatchers/verusid/registration.js).

1. Bind the flow to the active profile and selected system. Resolve the
   name and parent namespace with the pinned SDK. A bare leaf uses the
   selected native system; a qualified sub-name uses its namespace's
   registration terms. Verify the parent/currency, namespace authorization,
   the selected referrer's eligibility and fee currency. For display,
   [referral pricing](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityRegistration/referrals.js)
   derives the registrant's discount from full minus referred registration
   cost, separately from the referral reward. Do not hardcode prices.
2. Resolve controllers, recovery and revocation authorities, and the selected
   wallet funding source. The setup includes the wallet's private receiving
   address when present on the selected system. Review registration amount,
   both transaction fees and the actual signing policy; verify exact amounts
   rather than converting them through floating point.
3. Create the first stage with `createNameReservationTransaction` and a
   fresh locally generated salt. Bind the approval to the reviewed job and
   transaction, verify funding with `verifyIdentityRegistrationFunding`, and
   let the wallet call `signIdentityRegistrationTransaction` and submit only
   after the user confirms. Persist the
   recoverable reservation, receipts and stage data privately in the profile;
   never place a commitment preimage, signed bytes or funding details in
   analytics, logs, or shared agent state. A draft is not a commitment.
4. Require active-chain confirmation and the exact commitment output still
   unspent before building the reveal. `createIdentityRegistrationTransaction`
   consumes the saved reservation and verified commitment outpoint; keep
   the same preimage across a rebuild. Review and approve this distinct
   transaction, then confirm and read back the identity on the expected
   system. Linking is a separate step. Reconcile expiry, reorg, conflicting
   spend, unknown broadcast and stale approvals before any retry; do not
   generate a new commitment merely because a response was lost.

**Integration boundary.** This is a native wallet flow. An application must
not treat it as a general-purpose registration deeplink or an agent write API.
The older Provision Identity request is a separate protocol path and does not
establish equivalence to this native ceremony.

## Modify, transfer, revoke or recover an identity

Use the tagged [identity definition builder](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityManagement/identityDefinition.js),
[prepare/send pipeline](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityManagement/updateIdentity.js),
and [review screens](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/containers/Services/ServiceComponents/VerusIdService/IdentityManagement/IdentityManagementScreens.js).

- **Modify:** decode the actual current identity transaction output, clone
  the typed identity and apply only enabled fields: primary addresses,
  minimum signatures, recovery/revocation authorities and private receiving
  address. JSON snapshots can omit opaque content and additional private
  addresses. Validate distinct supported controllers, a feasible threshold,
  required signer authority and private-address format. Show explicitly
  removed values and possible loss of control. Setting the first private
  address preserves the rest when editing; an explicit clear is different.
  Configuring a threshold does not mean this tagged wallet can complete an
  update that already requires multiple signers; the native management flow
  checks whether its signing address can complete the update.
- **Transfer:** require a same-system transparent receiver or an eligible
  VerusID and resolve it again before signing. An identity recipient supplies
  its primary addresses, minimum signatures and first private address. A
  transparent recipient gives one controller and clears the old private
  address. The updated identity's recovery and revocation authorities become
  itself; they are not inherited from the recipient. Tokenized control is
  rejected by this wallet flow. Verify the expected post-transfer authority
  and warn when the sending profile will lose control.
- **Funds:** explicitly review whether funds stay at the same identity
  address under the new ownership or are returned to the wallet as part of
  the update. The [funds reader](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityManagement/identityFunds.js)
  rejects pending activity and verifies indexed outpoints against decoded
  output bytes; index totals alone do not prove spendability or amounts.
  Reject unsupported output types, stale snapshots and changed fees instead
  of signing. Review exact input/output/fee/expiry; recheck the identity and
  funding immediately before approval, verify the funded and signed bytes,
  reconcile ambiguous submission, then confirm and read back ownership and
  funds independently on-chain. Do not reuse an invoice or payment QR as
  a transfer approval; recipient QR scanning only fills the form.
- **Revoke/recover:** use the separate [native transaction builders](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/api/channels/verusid/requests/updateIdentity.js)
  and the appropriate current revocation or recovery authority. Bind each
  review to subject, system, resulting authority, fee and transaction; treat
  revoke and recover as separate operations with independent confirmation.

## Discover and link identities without writing to the chain

[Discovery and linking](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityLinking/identityLinking.js)
verifies the system and height, uses `getIdentitiesWithAddress` with
`unspent: true` for current wallet addresses, and deduplicates by identity ID
without merging authority records. Resolve PBaaS parent names on that same
system; retain the canonical qualified name separately from its display label.
Filter out ineligible or already-linked records; availability depends on
current spend authority, distinct controlled keys, status and lock checks.
Present a searchable list and save only the user's selection in the active
wallet profile. Track partial local saves independently from refresh and
retry only unfinished work. A local link, an address-index result and an
application proof of identity control are different evidence.

## Experimental Identity Update: review and local uploads

Use typed `IdentityUpdateRequestDetails` inside a signed GenericRequest. The
[handler](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/handlers/identityUpdateRequestDetailsHandler.js)
checks the subject, request signer namespace and supported changes against
current data. Keep both the wallet's experimental-deeplink setting and a
separate project flag. Follow the [staged review](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/containers/DeepLink/IdentityUpdateRequestInfo/IdentityUpdateRequestInfo.js):
show requester, subject and network; then post-update controls and lockout
risks, separately labelled additions/removals and public/private data, then
the final fee and verified funded transaction. Show high-risk full content
removal distinctly. History/aggregate removals are not retroactive erasure;
preserve intended current state independently of historical reads.

The [local upload adapter](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityUpdate/localUploadCrypto.js)
supplies wallet-native randomness, descriptor encryption and authenticated
verification to the pinned SDK, scoped to one build. In the
[prepare/pay step](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/containers/DeepLink/IdentityUpdateRequestInfo/steps/ConfirmPayStep.js),
pass the adapter to `createUpdateIdentityTransaction` and process uploads
locally before funding/signing; never send plaintext or
derivation material to a remote RPC. A disposable public recipient with a
published viewing key is publicly readable even though the encoding uses
encryption. Private uploads keep verification material operation-local,
authenticate the intended recipient and ciphertext, and dispose on completion,
failure, or context change. Credentials retain a separate reviewed flow;
credential encryption through `signDataMap` and embedded upload signatures are
unsupported. Validate multipart/MMR boundaries through the SDK rather than
using UI size limits as protocol limits. [Verified submission](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/identityUpdate/verifiedSubmission.js)
rechecks current context and exact funding/signed bytes before sending. A
wallet response or txid still needs independent confirmation and readback.

## Experimental App Encryption: authentication and scope

[Envelope validation](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/validator/envelopeValidator.js)
now validates details before the shared signed-request authorization path.
App Encryption requires a signed envelope; by default the signer identifies
the app scope. The [`appOrDelegatorID` authorization path](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/validator/appEncryptionAuthorization.js)
is not third-party delegation: the active profile must meet the signer's
current threshold and possess all signing authorities at the verified
signature height for explicit scope, even when that scope equals the signer.
Do not fall back to today's keys or substitute height zero for a historical
read. At approval, recheck the exact request bytes, active profile/network,
and selected response identity's current signing threshold. A linked label
or watch-only record does not prove control. If an authentication detail
supplies [recipient constraints](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/validator/appEncryptionIdentityConstraints.js),
alternatives within an ID/system/immediate-parent group are ORed; all present
groups must match. A request cannot carry multiple such authentication details.

Use the [typed validator](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/validator/appEncryptionRequestValidator.js)
and [wallet processing flow](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/handlers/appEncryptionRequestHandler.js).
Require a valid Sapling response-encryption address even for viewing-only
material. Validate primary/secondary derivation indices before narrowing to
signed 32-bit values. Derive the app-scoped channel inside the wallet before
any nested derivation. Return channel material only in the encrypted typed
data response; never export intermediate keys, solicit a spending-key
response for ordinary app use, or log plaintext. Correlate and verify the
signed response on the relying-app side. This release does not activate
App Encryption in the agent or prove revocable access to prior ciphertext.

## Transport, performance and lifecycle checks

- **Deeplinks and replies:** keep `toWalletDeeplinkUri()` for
  `verus://1/<Base64URL(binary)>` and use `toQrString()` for a payload-only
  QR. The [tagged handler](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/sagas/deeplink.js)
  rejects URLs of 2046 characters or more. Use the
  [DREAM request lifecycle](DREAM_APPS.md): HTTPS binary POST, fresh readers,
  verify expected network/signer, bind `request.getRawDataSha256()` and all
  expected IDs/details, enforce scope/expiry and consume the session once.
  See the [October guide](MOBILE_V1.1.0-21.md) for the older build's gift cards,
  VerusPay V4, User Data, Data Packet and wire examples; qualify these routes
  independently on the exact target build. Identity Update, App Encryption,
  User Data and Data Packet are all still subject to the
  [wallet experimental setting](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/deeplink/experimentalDeeplinks.js).
  Do not treat Data Packet signatures
  as spend authorization or use an arbitrary JSON payload as a GenericRequest.
- **RPC reads:** [refresh planning](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/vrpc/vrpcRefresh.js)
  deduplicates identical reads by system, method and arguments. Bundle
  independent per-address `getaddressbalance` calls in one transport batch;
  do not union addresses into one balance call, which produces combined
  totals. [Request planning](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/vrpc/vrpcRequestMany.js)
  can combine compatible deltas/mempool address lists, then split results
  back by address, caller order and method semantics. The
  [batcher](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/vrpc/vrpcRequestBatcher.js)
  limits and paces read batches per endpoint (tag defaults: 20 items per
  batch, 80 items/sec); it tracks endpoint batch rejection and falls back to
  paced individual reads where appropriate. The wallet's VRPC proxy preserves
  response order and omits JSON-RPC IDs; do not assume this ordering for an
  arbitrary JSON-RPC server. Keep per-item errors and distinguish
  unsupported batch transports from throttling or timeouts. Do not batch or
  retry mutations this way or assume a batch is an atomic chain snapshot.
- **UI and profile lifecycle:** the release reports clearer revoke/recover
  and control labels, a spinner only for user-initiated refresh, profile
  switching fixes, clearer login failures, profile-scoped notification
  clearing and corrected PBaaS identity resolution. For an implementation,
  invalidate pending results on profile/system switches, keep manual loading
  distinct from background updates, resolve identities on the requested
  system, show actionable errors without leaking internals, and scope both
  persisted and displayed notifications. See upstream tests for
  [profile switching](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/__tests__/unit/homeSessionTransitions.unit.test.js),
  [login feedback](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/__tests__/unit/loginFailureFeedback.unit.test.js)
  and [notification clearing](https://github.com/VerusCoin/Verus-Mobile/blob/d82d0e8ea457979778a857c9812b7aa29ebd0410/src/utils/__tests__/unit/notificationProfileClear.unit.test.js).

**Operator policy.** Use offline synthetic fixtures first: stale approval,
commitment replacement/reorg, opaque-field preservation, transfer with/without
funds, partial links, upload tampering, historical authority, missing keys,
wrong system, decline and profile switch. Separately authorize local `verus-cli`
VRSCTEST reads with reviewed operator configuration and positive version,
network and sync checks. Qualify the exact installed Android emulator/APK and
iOS TestFlight device/build separately, starting with no-spend review/cancel
paths. A mock, emulator launch, callback or txid alone does not satisfy a chain
mutation check. This update did not run a wallet, daemon or live interoperability
test. It adds no registration, transfer, revoke/recover, App Encryption, RPC
batching, arbitrary signing, or broadcasting capability to `verus_agent`.
