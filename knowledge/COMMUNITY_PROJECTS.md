# Verus community project catalog

Checked 2026-10-15 through the authenticated Chrome Discord UI and linked
public resources. Numbers preserve the user's list. Activity dates describe
visible discussion history, not verified launches. Community statements,
source implementation and deployed behavior are separate evidence.

Only project-level summaries and public resource links are retained. No raw
Discord export, account/session information, wallet/identity inventories,
balances, private messages, signed attachment URLs or infrastructure records
are included. Images, screencasts and audio were not transcribed or audited;
their presence/metadata is not implementation evidence. Broken/unknown Discord
cross-links cannot establish the contents of the referenced discussion.

## Requested discussions

| # | Discussion | Observed activity and reusable context |
|---|---|---|
| 1 | [VerusID to OpenID Connect / Discourse](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1515772105424240684) | Jun 14-Jul 6, 2026: wallet authentication translated to OIDC for forum SSO; agent posting still API-key based at last update. |
| 2 | [Verus Storage: blow your mind](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1507456523045961930) | May 22-Jun 14, 2026: generated educational podcast, selective disclosure/MMR/chunking and web SSO discussion. |
| 3 | [VerusID CMM Decrypt](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1513262192005353564) | Jun 7, 2026: Node/WASM flags:13 descriptor decryption using raw transactions rather than decryptdata RPC. |
| 4 | [vtimestamp](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1465111050352332802) | Jan 25-Jun 6, 2026: alpha timestamping evolved through wallet-update support, encrypted descriptor format, MCP and client-side decrypt-library migration. |
| 5 | [Verus Notes - Encrypted notes](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1512065529521897472) | Jun 4-5, 2026: Testnet alpha desktop vault using App Encryption, local notes/backups and optional ciphertext sync. |
| 6 | [DreamTree Testnet alpha](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1510713295261143141) | May 31, 2026: early link-in-bio/subID provisioning with payment placeholder; treasury model is proposed usage economics. |
| 7 | [Markets.Verus.Trading](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1410721552030367875) | Aug 28, 2025-Jul 10, 2026: basket pair/spread tables, pending conversions, later market-view refreshes and stale-node reports. |
| 8 | [Make Protocol - Verus Loans, Options, Futures](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1502998771376590858) | May 10-Jul 14, 2026: loan/swap protocol and GUI, collateral/approval UX, automation still evolving; title is broader than proven GUI scope. |
| 9 | [Verus EMP](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1466054143666950165) | Jan 28-Jul 20, 2026: emission planning, CSV/shared configuration; permanent domain migration announced. |
| 10 | [verus-rpc](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1529825184654168174) | Jul 23, 2026: lossless raw JSON parsing and bigint amount handling in a community RPC transport. |
| 11 | [verus-sapling](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1529864310799601835) | Jul 23, 2026: local WASM shielded signing; witnesses/notes/lightwalletd and browser-worker examples. |
| 12 | [Junction41 - Infrastructure for the agent economy](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1492168692728070244) | Apr 10-Jul 31, 2026: Testnet agent-marketplace stack; dispatcher/SDK/MCP/sandbox releases and explicitly untested integration paths. |
| 13 | [verus-sdk](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1529844179356745798) | Jul 23-Aug 13, 2026: offline transaction builders; fee-UTXO/wallet-bloat discussion and sponsored-identity-update MVP blockers. |
| 14 | [Mempool Visualizer](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1540137906813796372) | Aug 20-21, 2026: Testnet transaction-orbit visualization with PBaaS context. |
| 15 | [verus-docker](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1531342699997827143) | Jul 27, 2026 project discussion; Aug 26 off-topic replies: container/bootstrap references, not an authorized deployment. |
| 16 | [Verus.CX - Explorer and Demos](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1491704445111898282) | Apr 9-Oct 7, 2026: explorer/indexer/market features, reorg and display fixes; Mobile callback and cross-network ID lookup issues still reported. |
| 17 | [Verus Creator](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1539184592181928007) | Aug 18-Oct 7, 2026: Electron VDXF explorer/uploader; text packing, Testnet assets, metadata asset references/templates. |
| 18 | [Conversions Viewer App](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1427691387444531341) | Oct 14-Dec 5, 2025: chain/friendly-basket routes, linked source and later layout experiments. |
| 19 | [Verus NFT Marketplace - A Verus-Native](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1454202990897664045) | Dec 26, 2025-Jan 14, 2026: Testnet reference marketplace, naming/collections debate and makeoffer/takeoffer demos. |
| 20 | [Verus Development Workbench](https://discord.com/channels/1180350488256987177/1398718326615572541/threads/1399002431479873587) | Jul 27, 2025-Feb 18, 2026: RPC exploration/requirements tool, later screenshot updates; no source repository established. |

## Reuse notes and linked-resource review

### 1-2: SSO and storage education

[discourse.verus.trading](https://discourse.verus.trading/) is accessible and
now identifies its canonical site as [SyncProof Community](https://community.syncproof.net/).
The thread describes wallet -> identity service -> OIDC provider -> Discourse;
it does not expose a verified reusable implementation repository. July's agent
posting was API-key based; VerusID agent posting was future work.
The linked [VRSCTEST category description](https://discourse.verus.trading/t/about-the-vrsctest-category/10)
contains development/testing context. The linked
[example agent post](https://discourse.verus.trading/t/world-cup-2026-july-6/11)
is a sports brief, not Verus protocol evidence.

The [generated storage podcast](https://drive.google.com/file/d/1SwKgBc41-5i4V8wLRmrlIDmBneiAnDgZ/view?usp=sharing)
is publicly viewable as `verus_storage_blow_your_mind.mp3`, 21:56; only metadata
was inspected. Its described spending/viewing/selective-key tiers, MMR and
chunking are educational leads, not authoritative API/size claims. The
[Imprivata OIDC link](https://docs.imprivata.com/mda/content/topics/mda_oidc.html)
returned 404. Web SSO discussion is not proof of workstation/badge integration.

### 3-4: Descriptors and timestamp provenance

[verusid-cmm-decrypt](https://github.com/vdappdev2/verusid-cmm-decrypt), head
`b5e6755c5018187a6930cd6682afd1dff38197e9` (Jun 6 UTC), is Node >=20 ESM with
bundled WASM and old primitives pin `27e6c07`. Its API
`decryptDescriptor({ivk, epk, objectdata}, originatingTxid, getRawTx)` returns
bytes using an injected raw-transaction lookup. It supports flags:13,
single-chunk, self-reference CCDRs; not flags 5/37 or arbitrary multichunk
formats. Source has Rust regression tests, but none were run here. Reconcile
its older pins with the official SDK snapshot before integration.

[vtimestamp](https://vtimestamp.com/), [Testnet site](https://test.vtimestamp.com/),
[developer guide](https://vtimestamp.com/developers), and
[source](https://github.com/vdappdev2/vtimestamp) are readable. Source head
`631c9b20f385ae687c88fb1972e47b11ecc717ad` (Jun 7 UTC), version 0.7.0,
contains migration commit `377e5f1aa330f8312b639d09b6f71f7580fbefee`.
`SAPLING_DECRYPT_MODE` defaults `rpc-only`; `side-by-side` returns RPC data;
`lib-only` tries the library with RPC fallback. No deployed mode was verified.
Public inline viewing material in flags:13 descriptors means public readability,
not confidentiality. Do not copy plaintext-hex divergence logging into private apps.

The latest update metadata from `getidentitycontent` does not establish an
individual timestamp's original inclusion. Resolve its historical entry and
containing block. The old [production alias](https://vtimestamp.vercel.app/)
redirects to vtimestamp.com; the old [Testnet alias](https://vtimestamp-test.vercel.app/)
redirects to test.vtimestamp.com; all returned HTTP 200. No login or upload occurred.
Linked [vtimestamp-mcp](https://www.npmjs.com/package/vtimestamp-mcp) and
[vtimestamp-mcp-write](https://www.npmjs.com/package/vtimestamp-mcp-write)
registry metadata reports 1.2.0 (May 9), Node >=18; npm pages returned 403.
Their documented Mainnet defaults and write behavior prohibit casually running
them here. Thread-reported successful tests are author evidence only.

### 5-6: DREAM application examples

[Verus Notes source](https://github.com/Meyse/verus-notes-testnet), head
`ae329cca632568773dd5c94caf6166d360f27de5` (Jun 4), is Svelte/Tauri/Rust with
optional Convex ciphertext sync and local-only mode. Its wallet protocol checks
request hashes and rejects plaintext app-encryption responses. Normal unlock
does not request `FLAG_RETURN_ESK`. This is a Testnet alpha, not an audit or
production qualification. The [alpha release](https://github.com/Meyse/verus-notes-testnet/releases/tag/v0.1.0-testnet-alpha.1)
lists Windows NSIS, macOS DMG, Linux AppImage and SHA256SUMS. Those three linked
binary assets were identified through release metadata; none were downloaded
or executed. Cloud test data may be removed; local recovery remains important.

[DreamTree Testnet](https://vrsctest.dreamtree.bio/) is reachable. Its signup
page explicitly shows a **payment placeholder** before the address handoff;
no signup was submitted. Its linked [GitHub destination](https://github.com/dreamtree)
returned 404. Landing-page security, storage, API and paid-plan claims are not
verified backend behavior. Use [the DREAM proposal](DREAM_APPS.md) and
[treasury simulation notes](BOOTSTRAP_AND_TREASURY.md) for separate design context.

### 7-9: Markets, contract research and emission planning

[markets.verus.trading](https://markets.verus.trading/) was described as pair
prices across baskets, spread/midprice differences and pending-conversion
events. The thread mentions a FastAPI data backend and minute refreshes;
November's pivot stopped development of an in-page arbitrage engine in favor of a data stream
and agent examples. Later RVT/Baskets changes are presentation updates, not
authorization for automated trading. July's stalled-node report remains dated
community evidence. Availability responses differed by reader; no current
market freshness or execution behavior was established. The linked
[roadmap](https://github.com/orgs/verustrading/projects/1) is project planning,
not an implementation checkout. The ancillary
[logrotate guide](https://github.com/VerusCoin/VerusServicesSetup/blob/master/S-NOMP.md#enable-logrotate)
is old mining-pool setup material, not current deployment instructions.
Its [public-roadmap source](https://github.com/verustrading/public-roadmap)
contains planning issues. The board marks VerusID login Done (explicitly
completed but not deployed), slippage/SSO work In Progress, basket tracking
Planned, and in-page arbitrage Not Doing. These dated board labels are not
independent live validation. One Make discussion message could not be loaded;
the visible history and source review cannot recover that missing content.

[Make Protocol](https://github.com/Fried333/make-protocol), head
`42f620b891b6a36c12e8a183b30c73acbe98c584` (Jul 14), and
[Make GUI](https://github.com/Fried333/make-gui), head
`83b7d4f1856202769f9f65c0e2ac7272a26722ca` (Jul 15), are community MIT sources.
Review SPEC/SCHEMA/recipes for origination, private repayment and time-locked
default transaction templates. Use stable VDXF keys and internal payload
versions; options/escrow/swap schemas are less mature. The GUI is a local Python
HTTP/RPC proxy and JS interface with wallet/key/write methods. Auto-fund and
auto-accept can sign/broadcast with an unlocked wallet; it is not read-only.
Lender claim-collateral UI, rescue and z-memo workflows are documented gaps.
The author's Mainnet validation claims were not reproduced. Thread discussion
explicitly rejects treating swap primitives as proof of arbitrary off-chain
bounty completion by an unknown counterparty. No loans, orders or broadcasts
were authorized or performed.

[EMP old URL](https://emp.verus.trading/) redirects to
[emp.buildwithdreams.com](https://emp.buildwithdreams.com/). It is an emission
planner with shareable era configuration, charts/tables and CSV exports. No
source-repository link was exposed; modeled emission mechanics require daemon
validation. See [resource details](BOOTSTRAP_AND_TREASURY.md).

### 10-11 and 13: Community transport, signing and light-wallet stack

These packages are separate from the official VerusCoin clients. npm release
versions and later GitHub heads must not be assumed identical.

| Source | Source head / date UTC | Published package evidence |
|---|---|---|
| [chainvue/verus-rpc](https://github.com/chainvue/verus-rpc) | `35112881e3c8a0ad4db8f7d9b250a67738413c8c`, Sep 29 | [npm](https://www.npmjs.com/package/@chainvue/verus-rpc) 0.7.1, Aug 15; Node >=22 |
| [chainvue/verus-sapling](https://github.com/chainvue/verus-sapling) | `ec49007941f1afa97d1a69abf44502d7a84860e3`, Sep 29 | [npm](https://www.npmjs.com/package/@chainvue/verus-sapling) 0.1.1, Jul 27; Node >=18 |
| [chainvue/verus-sdk](https://github.com/chainvue/verus-sdk) | `03d4fb2b2ec429a7d0d1c83002caa4de478a5f25`, Sep 29 | [npm](https://www.npmjs.com/package/@chainvue/verus-sdk) 0.17.0, Sep 10; Node >=18 |
| [VerusCoin/lightwalletd](https://github.com/VerusCoin/lightwalletd) | `3c7c0fa105b712d9ffbcd6345aafe6efb43222d9`, Aug 24 | Current Go manifest requires 1.22.2; inherited README guidance is older |

npm pages returned 403 to extraction; public registry metadata was readable.
RPC uses lossless raw JSON parsing and bigint satoshis in typed methods; raw
`call` preserves exact decimal strings by default. `numbers: "js"` opts into
potential precision loss. `parseAmount`, `formatAmount`, `amountParam` and
operation-wait helpers are relevant APIs. Its README targets daemon 1.2.17,
not a verified 1.2.18 contract. Wait helpers returning a transaction ID still
need independent confirmation.

The SDK constructs/signs transfers, identities, currencies and offers offline
from supplied UTXOs. `parseSats`/`toSatoshis` accept decimal strings; avoid float
conversion. Supply `expiryHeight`. Current source documents separate-funder
`buildMultisigIdentityUpdate` then `addIdentitySignature`, and decoded
`currencyValues: Map<string,bigint>`. Its primitives pin `4243cd075b4f68df1ce72fd2fd9c9b18ac36767e`
differs from the official client snapshot. Protocol transfer fees are distinct
from returned miner fee. July's fee-UTXO/bloat discussion and August's sponsored
update blockers were not proven resolved by later source changes.

Sapling offers `initSapling`, `shieldT2z`, `spendShielded`, `detectNotes`, and
`buildShieldedSpend`; Node lightwalletd and browser gRPC-web/worker adapters are
separate subpaths. Shielded spends require notes, anchors and witnesses.
“No local full node” does not mean no backend. Verify canonical proving-parameter
hashes and fee/value bounds. Local signing still depends on a trusted client
and dependencies; WASM memory is not zeroized, and keys can remain until module/worker teardown. Upstream Testnet
acceptance claims were not reproduced. lightwalletd supplies compact-block,
tree-state, mempool and broadcast APIs; it does not hold the user's signing key.
Do not copy inherited Zcash deployment examples as verified Verus instructions.

### 12: Junction41

[Junction41](https://junction41.io/), [documentation](https://docs.junction41.io/)
and the public repositories below describe agent discovery/dispatch, compute,
data/model markets, MCP tools and sandbox/security components. Initial April
discussion was VRSCTEST-only and buggy; Mobile only authenticated at that time.
April's release announcement explicitly said several executor integrations had
only code-path review. Billing-usage VDXF entries were proposed. In May Mainnet
was still withheld/pending and private-payment confirmation was deferred.
Later repository activity is not evidence that those historical blockers or
all advertised web flows have been resolved.

| Public repository | Inspected head | Head date UTC / manifest version |
|---|---|---|
| [Dashboard](https://github.com/autobb888/junction41-dashboard) | `e5dd86b3217c780bcf8f4b71200ba51fa628a180` | Sep 14 / 0.0.0 |
| [Dispatcher](https://github.com/autobb888/j41-sovagent-dispatcher) | `08905d33023413a11c3908a7b744dbb10f222166` | Oct 4 / 2.37.5 |
| [SDK](https://github.com/autobb888/j41-sovagent-sdk) | `55989e42c96431600863e32fc6ec63c9abaed82b` | Aug 22 / 2.16.1 |
| [MCP server](https://github.com/autobb888/j41-sovagent-mcp-server) | `97c68418cb5088e11ae79656c09590928458d872` | Aug 5 / 2.2.3 |
| [Jailbox](https://github.com/autobb888/j41-jailbox) | `c9c33cdd9957bca8e49d460033d2eabda3753457` | Aug 27 / 2.1.3 |
| [SovGuard](https://github.com/autobb888/sovguard) | `c3965356152299489ccb22984824293497e72c27` | Sep 25 / 1.0.1 |
| [Secure setup](https://github.com/autobb888/j41-secure-setup) | `7b6a93696779b9754dc054806a24cc0e76860dea` | Aug 27 / 0.3.5 |
| [Docs source](https://github.com/autobb888/j41-docs) | `af36a9fcb6ae57d234d53aaad67bdc761507d74b` | Sep 1 / 1.0.0 |

Current docs distinguish website capabilities: Sovagent confirm-hire creates a
job without payment; Sovcompute is a GPU-rental job rather than standing metered
token prepay; Sovdata hiring requires a priced dataset; Sovmodel metered access
does not create a job and its website does not complete signed hire/payment/
delivery. Accepted reviews become on-chain only after a seller writes them.
Tool counts differ by release/page (April announcement 126, docs homepage 121),
so do not hardcode a global count. Read the current capability-specific source
before proposing an integration. No components were installed or executed.

Later dispatcher [source decision](https://github.com/autobb888/j41-sovagent-dispatcher/blob/08905d33023413a11c3908a7b744dbb10f222166/JAILBOX_PARKED.md)
parks Jailbox by default in favor of deliver-and-review; current config sets
`jailbox.enabled: false`. Do not infer default sandbox activation from the
architecture overview. SDK/dispatcher still pin primitives
`27e6c076def4416c20a568e31e4c406b10612807`; MCP pins an older SDK than the
dispatcher. Reconcile them before reuse. SDK exports `J41Agent`, `J41Client`,
chat/workspace, webhook and payment/identity helpers. SovGuard offers scanning,
redaction/canaries/action guards with probabilistic and model-availability
limits; optional external classification can disclose submitted text.
Secure-setup can change the host/install isolation tools. Neither security
claims nor project allowlists authorize this agent's wallet/host operations.

[sovguard.io](https://sovguard.io/) returned 530 to web retrieval. The linked
[Gitlawb token](https://community.gitlawb.com/token) and
[governance](https://community.gitlawb.com/governance) pages now redirect toward
[Twigpine](https://community.twigpine.com/); readers differed on accessibility.
They are non-Verus comparisons, not Junction41 dependencies or a verified
governance specification. An ancillary reaction GIF has no technical content.

### 14-17: Observability, containers and authoring

[Mempool VRSCTEST](https://mempool.chainvue.io/vrsctest) renders an orbit view,
LIVE/DEMO controls, transaction categories and recent PoW/PoS cards. A populated
view does not prove independent chain freshness; no source repo was linked.
The demo screencast was not transcribed. This update did not generate traffic.

[chainvue/verus-docker](https://github.com/chainvue/verus-docker), head
`6581c1c669111d1e9d9135b7b7f8018db8b3a8d5` (Sep 18), and
[imylomylo/verusd](https://github.com/imylomylo/verusd), head
`9780cc403e1b93f93a2a1044627f4eaccf0aa4cd` (Sep 15), are container references.
Both inspected Dockerfiles default to 1.2.17-6, not 1.2.18. Read the linked
[quickstart](https://github.com/chainvue/verus-docker/blob/main/docs/quickstart.md)
as community guidance; no image provenance, build, bootstrap or deployment was
validated here. The thread's automatic parameter/bootstrap-fetch statements
are historical reports, not new authorized runtime commands. Browser bootstrap
selection is covered in [resources](BOOTSTRAP_AND_TREASURY.md).

[scan.verus.cx](https://scan.verus.cx/) exposes explorer/market/identity surfaces
and [provider documentation](https://scan.verus.cx/developers). No project source
repository was established; its footer points to the VerusCoin organization.
The [oracle history page](https://scan.verus.cx/oracle/history) explicitly showed
**stale** snapshots when inspected. Rate limits conflict within provider docs;
recheck them before use. Provider-specific extensions and write whitelists are
not universal daemon behavior or authorization. Dated issue reports include
reorg/indexing, fee-currency display, name/network resolution and Mobile callback
handling. Do not claim them fixed from a live landing page alone.
The original [Verus.CX landing page](https://verus.cx/) and
[demo page](https://verus.cx/dev/demos/) timed out to retrieval. The supplied
[old API docs](https://scan.verus.cx/api/docs#/) returned 404; current
[API docs](https://scan.verus.cx/api/) are readable but have different limits
from `/developers`. Recheck the exact provider route; no API/RPC was called.
June's thread report said a Testnet explorer was not yet available, and October's
Mobile callback/network-display reports have no later resolution in this thread.
Additional thread links for `/conversions`, `/rewards`, `/oracle`, bridge/
transaction examples and identity detail pages returned HTTP 200; example
account data is deliberately omitted. The linked social-demo page timed out.
An Etherscan contract link was inspected as explorer metadata only, not a trust
or protocol attestation. The supporting
[Oink70/Verus-CLI-tools](https://github.com/Oink70/Verus-CLI-tools), head
`b3a9acdbc1f931fe2f45b3c86aabfb5de5e2ff4d` (Sep 21), mixes Linux statistics/
monitoring with upgrade, consolidation, identity/chain and firewall scripts.
Review individual scripts; none were executed or authorized here.

Verus Creator's thread describes Electron viewing through a node and upload
through a local wallet node. September reports Testnet .md/.svg/.png experiments;
October proposes an `Assets` metadata map and `{{v:asset:id:type:version}}`
references normalized during authoring. This is a community application format,
not a universal VDXF/HTML standard. No public source/download link was exposed
in the observed messages; screenshots were not used as proof of executable code.

### 18-20: Conversion charts, NFTs and RPC workbench

[hellcatz/verusrpc-ui](https://github.com/hellcatz/verusrpc-ui), head
`adefb017195e6dc6f76ebf05826126cfc2fb61e2` (Nov 2, 2024), version 0.0.2,
is the linked conversions source. Express/Liquid/Chartly renders basket data;
wallet send/convert/export paths exist behind `config.nowallet`, so do not
assume it is intrinsically read-only. Arbitrary `/rpc` registrations are
commented out. There is no evidence the deployed service uses that head/config.

All 25 linked conversions URLs were attempted: base; `/pbaas/varrr`,
`/pbaas/vdex`, `/pbaas/chips`; corresponding chain subdomain roots;
`/bridge.veth`, `/bridge.varrr`, `/bridge.vdex`, `/bridge.chips`; `/pure`,
`/nati.owl`, `/nati`, `/supervrsc`, `/superbasket`, `/floralis`, `/kaiju`,
`/vyield`, `/trillium`, `/switch`, `/highroller.chips`, `/bankroll.chips`,
`/stack.chips`, and `/floralis/transfers`, under
[conversions.verus.trading](https://conversions.verus.trading/). Redirects resolve
friendly names to chain/view or transfers routes, but all final fetches returned
502 from this environment. No chart/transfer/freshness validation was possible;
that is not proof of global service outage. Avoid copying currency/address
inventories into this public catalog.

The NFT marketplace thread describes a React/Node Testnet reference using
wallet login, subID assets, VDXF metadata, IPFS-linked media and native atomic
offers. Claims about security and decentralization are author statements,
not a completed audit. Despite the initial no-database/noncustodial language,
its stack includes SQLite caching/indexing and followups describe a
semi-custodial hybrid: a threshold of one with user and server primary addresses
allows the server to sign without a user popup. Do not adopt that as a
noncustodial design or per-mutation human approval. Later collection demos and naming discussions do not
establish generic nested-subID support or a complete production marketplace.
No publicly verified implementation repo was established from this discussion.

The Workbench thread links a [YouTube channel](https://www.youtube.com/channel/UC2U1YiFr2zun_GWknSShOwA)
with [Avatar](https://www.youtube.com/watch?v=LPuTiWnSrfE),
[Marketplace](https://www.youtube.com/watch?v=wXFyO8mZ3Ls) and
[Social Currency](https://www.youtube.com/watch?v=vRiDSWgBpTY) demo metadata.
No source repository was exposed, and videos were not transcribed. The
Workbench is a lead for RPC exploration and requirements discovery; screenshots
and a planned roadmap do not prove complete RPC coverage.

## Implementation and evidence limits

Use these resources to locate examples, not to activate external services.
The local agent does not gain these projects' runtime capabilities merely by
reading the catalog. Pin and review source/dependencies, synthetic fixtures,
network/amount/serialization contracts, client privacy and callback validation
before a separately authorized implementation. No tests of community code,
wallet actions, direct daemon queries, signatures, installations, trades,
production deployments or Mainnet operations were performed.
