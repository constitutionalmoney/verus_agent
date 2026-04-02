# Verus Blockchain — Comprehensive Development Report

> **Date**: January 2026 (Revised March 2026)
> **Prepared for**: UAI-e-Gold Project — Agent Swarm Integration
> **Version**: Verus Protocol v1.2.14-2 (Latest CRITICAL/MANDATORY Upgrade)
> **Report Version**: 3.1 — Updated with Wiki Update findings + verus-connect analysis (webhook/redirect VDXF keys, web wallet extension API, drop-in login SDK)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Protocol Architecture](#2-protocol-architecture)
3. [VerusID — Self-Sovereign Identity](#3-verusid--self-sovereign-identity)
4. [VDXF — Verus Data eXchange Format](#4-vdxf--verus-data-exchange-format)
5. [VDXF Data Pipeline — DefinedKey, DataDescriptor, VdxfUniValue](#5-vdxf-data-pipeline--definedkey-datadescriptor-vdxfunivalue)
6. [DeFi — Currencies, Baskets & Liquidity Pools](#6-defi--currencies-baskets--liquidity-pools)
7. [On-Chain File Storage (Multipart Data)](#7-on-chain-file-storage-multipart-data)
8. [Privacy & Shielded Transactions](#8-privacy--shielded-transactions)
9. [Cross-Chain & Ethereum Bridge](#9-cross-chain--ethereum-bridge)
10. [PBaaS — Public Blockchains as a Service](#10-pbaas--public-blockchains-as-a-service)
11. [On-Chain Marketplace (Atomic Swaps)](#11-on-chain-marketplace-atomic-swaps)
12. [Mining & Staking](#12-mining--staking)
13. [VerusLogin SDK & QR Authentication](#13-veruslogin-sdk--qr-authentication)
14. [Attestations & Credentials](#14-attestations--credentials)
15. [Decentralized Reputation System](#15-decentralized-reputation-system)
16. [Encrypted Messaging Between Agents](#16-encrypted-messaging-between-agents)
17. [Agent Economy & Commerce Patterns](#17-agent-economy--commerce-patterns)
18. [Agent Identity & Profile Schema](#18-agent-identity--profile-schema)
19. [Agent Bootstrap — From Zero to Operational](#19-agent-bootstrap--from-zero-to-operational)
20. [CLI/RPC Command Reference](#20-clirpc-command-reference)
21. [Reference Code & Libraries](#21-reference-code--libraries)
22. [Development Environment & Testnet](#22-development-environment--testnet)
23. [Hidden & Undocumented Features](#23-hidden--undocumented-features)
24. [v1.2.14-2 Critical Release Update](#24-v1214-2-critical-release-update)
25. [Verus Mobile Wallet Architecture](#25-verus-mobile-wallet-architecture)
26. [Mobile Wallet Modification Guide (UAI-e-Gold Fork)](#26-mobile-wallet-modification-guide-uai-e-gold-fork)
27. [verus_agent — UAI Neural Swarm Specialist](#27-verus_agent--uai-neural-swarm-specialist)
28. [Key Resources & Links](#28-key-resources--links)
29. [Wiki Update Findings (March 2026)](#29-wiki-update-findings-march-2026)
30. [verus-connect — Drop-in Login SDK (March 2026)](#30-verus-connect--drop-in-login-sdk-march-2026)

---

## 1. Executive Summary

Verus is a **UTXO-based, PoW/PoS hybrid** blockchain protocol that provides:
- **Self-sovereign identity** (VerusID) with revoke/recover/vault capabilities
- **MEV-resistant DeFi** via simultaneous transaction settlement (not sequential)
- **Unlimited scalability** through PBaaS (Public Blockchains as a Service)
- **VDXF** (Verus Data eXchange Format) for typed, decentralized data schemas
- **Cross-chain interoperability** with a trustless Ethereum bridge
- **On-chain file storage** — proven at 18.6MB (19 chunks), fully automated chunking
- **Decentralized marketplace** via atomic swap offers (makeoffer/takeoffer)
- **Privacy** via Sapling zero-knowledge proofs (z-addresses)
- **Decentralized reputation** via wallet-level trust ratings (setidentitytrust)
- **Encrypted messaging** via z-address encryption + VerusID signatures
- **Smart Transactions** (protocol-level primitives) instead of smart contracts
- **No ICO, no premine, no developer fee** — fully community-driven

The protocol is designed so that **all currencies, identities, and DeFi operations are validated at the consensus layer** by miners and stakers, unlike VM-based blockchains where only the native currency is consensus-secured.

**Lead Developer**: Mike Toutonghi (former VP at Microsoft)
**Consensus**: Verus Proof of Power — 50% PoW (VerusHash 2.2, CPU-friendly) + 50% PoS (no minimum stake)
**Block Time**: ~60 seconds (1440 blocks/day)
**Max Supply**: 83,540,184 VRSC
**Current Reward**: 3 VRSC/block (+ fee pool release)
**API Servers**: Mainnet `https://api.verus.services` | Testnet `https://api.verustest.net`

### What People Think Verus Is
- A CPU-mineable cryptocurrency
- A blockchain with on-chain identities (VerusID)
- A system for launching tokens

### What Verus Actually Is
- A **decentralized file storage protocol** (18.6MB proven, unlimited via multi-block)
- A **private data vault** (Sapling z-address encryption per object)
- A **cross-chain data reference system** (UTXO/identity/URL references)
- A **decentralized reputation system** (wallet-level trust ratings)
- A **namespace-scoped schema system** (DefinedKey → DataDescriptor → VdxfUniValue)
- An **on-chain marketplace** (atomic swaps for currencies, identities, tokens)
- **Multi-currency DeFi primitives** at the consensus layer (MEV-free AMM)
- A **complete identity recovery system** (revoke/recover/vault across chains)

---

## 2. Protocol Architecture

### 2.1 Consensus — Verus Proof of Power (VerusPoP)
- **Hybrid 50/50**: Half blocks mined (PoW), half staked (PoS)
- **VerusHash 2.2**: CPU-optimized algorithm that disincentivizes ASICs/FPGAs — mobile phones and ARM devices (Orange Pi 5) can profitably mine
- **Provable 51% attack resistance** via the hybrid design
- **No minimum stake** — anyone running a node can stake with any amount of VRSC
- **No slashing** — Verus solved the "nothing-at-stake" problem differently
- **Merge-mining**: Miners can simultaneously mine up to 22 PBaaS chains without sacrificing hash power

### 2.2 Smart Transactions vs. Smart Contracts
Verus uses **Smart Transactions** — protocol-level primitives — instead of VM-based smart contracts:
- All currencies, IDs, liquidity pools, conversions, and cross-chain operations are **validated by consensus**
- No Solidity, no EVM — dApps communicate via the **same RPC/CLI API** as the daemon
- **Result**: No smart contract bugs/hacks, no MEV, no gas fee spikes
- Extension points planned via PBaaS chains with optional VM/ZKVM capabilities

### 2.3 UTXO Model
Verus is UTXO-based (like Bitcoin), not account-based (like Ethereum):
- Each identity update spends the previous identity output
- Identity updates **cannot be parallelized** — each must wait for the previous to confirm (~60s)
- UTXO selection matters for staking — staking rewards go to the UTXO that stakes
- Transaction construction uses `@bitgo/utxo-lib` (with Verus network support) in mobile wallets

### 2.4 Fee Pool
Protocol fees are collected into a **Fee Pool**; each new block releases 1% of the pool on top of the coinbase reward. This prevents fee-sniping attacks and stabilizes the network.

**Protocol fees**:
| Operation | Fee |
|---|---|
| PBaaS chain launch | 10,000 VRSC |
| Currency/token launch | 200 VRSC |
| VerusID registration (root) | 100 VRSC (80 with referral) |
| SubID registration | 0.02 VRSC |
| DeFi conversion (basket↔reserve) | 0.025% |
| DeFi conversion (reserve↔reserve) | 0.05% |
| Transaction fee | 0.0001 VRSC |

### 2.5 Referral System Economics
- Root ID registration: 100 VRSC total
- With referral: registrant pays 80 VRSC, referral chain receives 20 VRSC
- The 20 VRSC discount goes to the referral chain, NOT back to the registrant
- Free IDs available via Valu app; SubIDs and PBaaS chain IDs cost pennies

---

## 3. VerusID — Self-Sovereign Identity

VerusID is a **first-class protocol primitive** — not a smart contract. Every identity:
- Has a **friendly name** (e.g., `myname@`) and a derived **i-address** (e.g., `i5v3h9FWVdRFbNHU7DfcpGykQjRaHtMqu7`)
- Supports **multisig** (multiple primary addresses with minimum signature threshold)
- Has **revocation** and **recovery** authorities (separate identity addresses)
- Supports **timelocking** (vault mode) with configurable unlock delays
- Can store arbitrary data in **contentmap** (1:1 key→value) and **contentmultimap** (1:many key→values)
- Is **transferable** — can be sold or gifted on-chain
- Can **launch currencies/blockchains** under its namespace
- Works **cross-chain** — can be exported to PBaaS chains and Ethereum

### 3.1 Name Qualification (Critical)
Understanding name formats is essential — using the wrong form returns "Identity not found":

| Format | Meaning | Example |
|---|---|---|
| `name@` | Top-level identity on current chain | `ari@` |
| `name.PARENT@` | SubID under a parent namespace | `alice.agentplatform@` |
| `name.VRSCTEST@` | Fully qualified with chain suffix | `ari.VRSCTEST@` |

**⚠️ `alice@` ≠ `alice.agentplatform@`** — The first looks for a top-level identity "alice" (which may not exist). Always use the fully qualified name when working with SubIDs.

### 3.2 SubID Creation (5-Step Process)
SubIDs require a parent namespace identity with a TOKEN currency:

1. **Register namespace identity** with a TOKEN currency (`definecurrency` with `options: 32, proofprotocol: 2`)
2. **Mint tokens** (required before SubIDs can be registered)
3. **Register VDXF keys** — get i-addresses via `getvdxfid`
4. **Store DefinedKeys** on the namespace identity under key `iD3yzD6KnrSG75d8RzirMD6SyvrAS2HxjH`
5. **Register SubIDs** per entity (e.g., `alice.agentplatform@`)

### 3.3 Identity Flags
| Flag | Value | Meaning |
|---|---|---|
| `ACTIVECURRENCY` | 1 | Has associated currency |
| `TOKENIZED_CONTROL` | 2 | Tokenized governance |
| `LOCKED` | 4 | Timelock active (vault mode) |
| `REVOKED` | 8 | Identity is revoked |
| `NFT_TOKEN` | 0x20 | NFT token identity |

### 3.4 Vault Protection
- **Lock**: `setidentitytimelock "myname@" '{"setunlockdelay":1440}'` (1440 blocks ≈ 24 hours)
- **Unlock**: Begin delay period, then spend after delay completes
- Funds are safe while locked — can receive but not send
- Works across PBaaS chains

### 3.5 Key CLI Commands
```bash
# Register (2-step to prevent front-running)
verus registernamecommitment "myname" "Raddr"
# Wait 1 confirmation (~60s)
verus registeridentity '{"txid":"...","namereservation":{...},"identity":{...}}'

# Read / Update / Revoke / Recover
verus getidentity "myname@"
verus updateidentity '{"name":"myname","contentmultimap":{...}}'
verus revokeidentity "myname@"
verus recoveridentity '{"name":"myname","primaryaddresses":["newRaddr"]}'

# Vault
verus setidentitytimelock "myname@" '{"setunlockdelay":1440}'

# List / Content
verus listidentities
verus getidentitycontent "myname@" heightstart heightend txproofs
```

---

## 4. VDXF — Verus Data eXchange Format

VDXF provides **typed, namespaced keys** (i-addresses) for structuring on-chain data. Keys are derived via the `getvdxfid` RPC command.

### 4.1 How VDXF Keys Work
```bash
# Generate a VDXF key
verus getvdxfid "myapp.vrsc::user.profile.name"
# Returns: {"vdxfid": "iXXXX...", "hash160result": "...", "qualifiedname": {...}}
```

Keys are **namespace-scoped** — the same string under different namespaces produces different i-addresses. This means `ari::agent.v1.name` and `agentplatform::agent.v1.name` are completely different keys.

### 4.2 Critical System VDXF Keys
| Key Name | vdxfid | Purpose |
|---|---|---|
| `vrsc::data.type.string` | `iK7a5JNJnbeuYWVHCDRpJosj3irGJ5Qa8c` | String data type |
| `vrsc::data.type.object.datadescriptor` | `i4GC1YGEVD21afWudGoFJVdnfjJ5XWnCQv` | Universal typed data envelope |
| `vrsc::data.mmrdescriptor` | `i9dVDb4LgfMYrZD1JBNP2uaso4bNAkT4Jr` | MMR root + hashes |
| `vrsc::data.signaturedata` | `i7PcVF9wwPtQ6p6jDtCVpohX65pTZuP2ah` | Signature information |
| `vrsc::identity.multimapkey` | `i3mbggp3NBR77C5JeFQJTpAxmgMidayLLE` | Multimap key marker |
| `vrsc::identity.multimapremove` | `i5Zkx5Z7tEfh42xtKfwbJ5LgEWE9rEgpFY` | Remove multimap entry |
| `vrsc::data.type.url` | `iJ3WDnpueJTqSCMN8dUWmfPuKbjFhZqQdM` | URL data type |
| `vrsc::identity.profile.media` | `iF4oGJU53g4ZpeSJ4CxV6EFjPBPgBCznzR` | Profile media |

### 4.3 ContentMap vs ContentMultiMap
- **contentmap**: Simple 1:1 mapping — `{vdxfid: DataDescriptor}`
- **contentmultimap**: 1:many mapping — `{vdxfid: [DataDescriptor1, DataDescriptor2, ...]}`
- **contentmultimap** also supports complex nested structures with MMRDescriptor + SignatureData
- **⚠️ `updateidentity` replaces the ENTIRE contentmultimap** — always include all existing entries plus new ones

### 4.4 ContentMultiMap Operations
| Operation | Effect |
|---|---|
| `ACTION_CLEAR_MAP` | Clear all entries |
| `ACTION_REMOVE_ALL_KEY` | Remove all values for a specific VDXF key |
| `ACTION_REMOVE_ONE_KEYVALUE` | Remove one specific value (by hash) |
| `ACTION_REMOVE_ALL_KEYVALUE` | Remove all matching values (by hash) |

### 4.5 VDXF Tags (vdxftag) & x-Addresses — Tagged Transaction Payment Tracking

VDXF tags allow **any `sendcurrency` transaction** (payment, conversion, cross-chain) to be tagged
with a VDXF-derived **x-address** for tracking purposes. This replaces the need for unique deposit
addresses per customer/invoice.

#### How It Works
```bash
# 1. Generate an x-address for a specific invoice
verus getvdxfid "mike.vrsc::invoiceid" '{"indexid":1002}'
# Returns:
# {
#   "vdxfid": "iNppQCRzekJK5FqAN6xYGffLc5PDNRMQfi",
#   "indexid": "xTevrzs5W4WyhRiCDnchF4BsdjQEF2dPRH",   <-- USE THIS
#   "hash160result": "27a5a9f6c1c76884ac24d35b83c087187bdf40d4",
#   "qualifiedname": {
#     "namespace": "i4NpJp1vqrXgDvSNBXkNYvTR1VF2HMkeDA",
#     "name": "mike.vrsc::invoiceid"
#   }
# }

# 2. Send a tagged payment using the x-address (indexid, not vdxfid)
verus sendcurrency "mike@" '[{"address":"mike@","amount":100,"vdxftag":"xTevrzs5W4WyhRiCDnchF4BsdjQEF2dPRH"}]'
```

#### Key Facts
| Property | Details |
|---|---|
| **Requires VerusID?** | **No** — any address can tag transactions |
| **Where supported** | `sendcurrency`, currency conversions, VerusPay QR codes |
| **x-address source** | `indexid` field from `getvdxfid` (NOT `vdxfid`) |
| **Namespace scoping** | Tags are namespace-scoped — `mike::invoiceid` ≠ `alice::invoiceid` |
| **Bound data** | `indexid` parameter binds arbitrary data (invoice #, hash, etc.) to the key |
| **Privacy caveat** | Tagging **links** transactions — use separate addresses for greater privacy |
| **VerusPay** | vdxftag support coming in next Verus Mobile VerusPay release |

#### Use Cases
- **Invoice tracking** — tag payments with invoice numbers without unique deposit addresses
- **Order management** — link transactions to order IDs for e-commerce
- **Agent economy** — tag service payments with job/task identifiers
- **Game payments** — tag in-game purchases with player/item IDs

---

## 5. VDXF Data Pipeline — DefinedKey, DataDescriptor, VdxfUniValue

Three complementary systems form a complete structured data layer:

| Component | Problem It Solves | Layer |
|---|---|---|
| **VdxfUniValue** | How to **serialize** typed data into bytes | Encoding |
| **DataDescriptor** | How to **annotate** data with metadata | Container |
| **DefinedKey** | How to **label** keys so wallets can read them | Discovery |

### 5.1 Pipeline Flow
```
Application Layer → "Store agent profile with name, type, version"
        ↓
DefinedKey (Labels) → Register human-readable names for keys
        ↓
DataDescriptor (Container) → Wrap data with label, MIME, encryption
        ↓
VdxfUniValue (Serializer) → Encode typed values into binary bytes
        ↓
contentmultimap (Storage) → { "iABC...": ["hex_bytes"] } on VerusID
```

### 5.2 DataDescriptor Structure
```json
{
  "version": 1,
  "flags": 0,
  "label": "myapp.vrsc::attestation.id",
  "mimetype": "text/plain",
  "objectdata": "actual-data-here",
  "salt": "hex-salt-for-privacy",
  "epk": "encryption-public-key",
  "ivk": "incoming-viewing-key",
  "ssk": "secret-spending-key"
}
```
- **Flags**: Control encryption (`0x01`), salting (`0x02`), EPK inclusion (`0x04`)
- **~4KB limit** per contentmap entry
- **contentmultimap** allows multiple values per key

### 5.3 DefinedKey — Human-Readable Labels
DefinedKeys are published on a namespace identity so wallets can automatically decode what each contentmultimap key means — without any external registry:

```typescript
import { DefinedKey } from 'verus-typescript-primitives';

const dk = new DefinedKey({
  version: DefinedKey.DEFINEDKEY_VERSION_CURRENT,
  flags: DefinedKey.DEFINEDKEY_DEFAULT_FLAGS,
  vdxfuri: 'agentplatform::agent.v1.name',
});
const hex = dk.toBuffer().toString('hex');
// Publish on agentplatform@ under key iD3yzD6KnrSG75d8RzirMD6SyvrAS2HxjH (DATA_TYPE_DEFINEDKEY)
```

### 5.4 Decision Guide
```
Do you need encryption?
  YES → Use DataDescriptor (encryption fields)
  NO  ↓
Is it simple key-value data?
  YES → Plain hex in contentmultimap + DefinedKey for labels
  NO  ↓
Does the data need a MIME type or label?
  YES → Use DataDescriptor (label + mimeType)
  NO  ↓
Is it a complex nested structure?
  YES → Use VdxfUniValue typed keys
  NO  → Plain hex encoding is fine
```

### 5.5 Hash Types Supported
| Type | Name | Use |
|---|---|---|
| `sha256` | SHA-256 | Default for single objects |
| `sha256D` | Double SHA-256 | Bitcoin-style |
| `blake2b` | BLAKE2b | Default for MMR trees (fast) |
| `keccak256` | Keccak-256 | Ethereum-compatible |

---

## 6. DeFi — Currencies, Baskets & Liquidity Pools

### 6.1 Currency Types
1. **Simple tokens**: Fixed or mintable supply, pegged or floating — `options: 32`
2. **Basket currencies** (fractional reserve): Multi-reserve liquidity pools — `options: 33` (FRACTIONAL+TOKEN)
3. **PBaaS chain native coins**: Full independent blockchain currencies — `options: 264`
4. **Mapped ERC-20s**: Ethereum tokens bridged 1:1 to Verus

### 6.2 Currency Options Bitfield
| Bit | Value | Name | Meaning |
|---|---|---|---|
| 5 | 32 | TOKEN | Simple token |
| 0+5 | 33 | FRACTIONAL+TOKEN | Basket/AMM currency |
| 3+8 | 264 | PBAAS+TOKEN | Independent blockchain |
| Various | — | ID_ISSUANCE | Can issue SubIDs |
| Various | — | ID_REFERRALS | Referral system active |

### 6.3 MEV Resistance (Solved at Protocol Level)
Unlike Ethereum where transactions are processed **sequentially** (enabling front-running, back-running, sandwich attacks), Verus processes DeFi conversions **simultaneously**:
- All conversions within 1–10 blocks get the **same fair price**
- Orders are **offset** against each other (buy 100, sell 80 → only 20 impacts price)
- **Enhanced liquidity** through netting — pool behaves as if more liquid
- Conversion fees: basket↔reserve 0.025%, reserve↔reserve 0.05%

### 6.4 Basket Currency Parameters
- `currencies`: Array of reserve currencies (up to 10, e.g., `["VRSC","Bridge.vETH"]`)
- `weights`: Relative weights in the basket
- `conversions`: Pre-launch conversion ratios
- `minpreconversion` / `maxpreconversion`: Bounds for pre-launch contributions
- `initialsupply`: Supply after pre-conversion
- `prelaunchdiscount`: Discount percentage at launch
- `prelaunchcarveout`: Percentage to launching ID
- `preallocations`: Pre-allocated amounts to specific IDs
- `proofprotocol`: 1 = Verus MMR proof, 2 = centralized control (can mint/burn)

### 6.5 Key DeFi Commands
```bash
# Estimate a conversion
verus estimateconversion '{"currency":"VRSC","convertto":"Bridge.vETH","amount":100}'

# Send with conversion (returns opid — poll z_getoperationstatus for txid)
verus sendcurrency "*" '[{"currency":"VRSC","amount":100,"convertto":"Bridge.vETH","address":"myaddr@"}]'

# Track send operation — sendcurrency returns an OPID, NOT a txid
verus z_getoperationstatus '["opid-value-here"]'
# When status is "success", the result object contains the actual txid

# Send with conversion + vdxftag (tagged transaction tracking)
verus sendcurrency "*" '[{"currency":"VRSC","amount":100,"convertto":"Bridge.vETH","address":"myaddr@","vdxftag":"xTevrzs5W4WyhRiCDnchF4BsdjQEF2dPRH"}]'

# Cross-pair conversion via basket
verus sendcurrency "*" '[{"currency":"VRSC","amount":100,"convertto":"DAI.vETH","via":"Bridge.vETH","address":"myaddr@"}]'

# Get currency info / state / converters
verus getcurrency "Bridge.vETH"
verus getcurrencystate "Bridge.vETH"
verus getcurrencyconverters "VRSC" "Bridge.vETH"

# Define a new currency (token)
verus definecurrency '{"name":"MyCoin","options":32,"currencies":["VRSC"],"weights":[1],...}'

# Define a basket (AMM pool)
verus definecurrency '{"name":"MyPool","options":33,"currencies":["VRSC","vETH"],"weights":[0.5,0.5],...}'
```

---

## 7. On-Chain File Storage (Multipart Data)

Verus has a complete decentralized file storage system built into its identity layer. **Proven at 18.6MB** (19 chunks across 19 transactions, byte-perfect SHA-256 verification on vrsctest).

### 7.1 Three-Layer Architecture

| Layer | What It Does | Key Component |
|---|---|---|
| **Data Creation** | Build structured data with MMR integrity | `signdata` RPC |
| **Storage** | Store in identity contentmultimap, auto-chunk if too large | `updateidentity` + `BreakApart()` |
| **Retrieval** | Aggregate data across blocks, reassemble chunks | `getidentitycontent` + `Reassemble()` |

### 7.2 Three Proven Storage Methods

#### Method 1: `updateidentity` + Data Wrapper ⭐ RECOMMENDED
Place a `"data"` object inside `contentmultimap` — triggers auto `signdata`, auto-chunking via `BreakApart()`, auto-encryption.

**Cost**: ~6–7 VRSCTEST per 999KB chunk

```bash
# CRITICAL: "data" MUST be inside contentmultimap, NOT at top level
# ❌ WRONG: {"name": "id", "data": {"filename": "/path/to/file"}}
# ✅ CORRECT:
cat > /tmp/upload-chunk.json << 'EOF'
{
  "jsonrpc": "1.0",
  "method": "updateidentity",
  "params": [{
    "parent": "<currency_i-address>",
    "name": "trial1",
    "primaryaddresses": ["<R-address>"],
    "minimumsignatures": 1,
    "contentmultimap": {
      "<vdxf-key>": [{
        "data": {
          "address": "trial1.filestorage@",
          "filename": "/tmp/chunks/chunk_aa",
          "createmmr": true,
          "label": "chunk-0",
          "mimetype": "application/octet-stream"
        }
      }]
    }
  }]
}
EOF
curl --user "$RPCUSER:$RPCPASS" --data-binary @/tmp/upload-chunk.json \
  -H 'content-type: text/plain;' http://127.0.0.1:$RPCPORT/
```

#### Method 2: `sendcurrency` to z-address
Send file data to a shielded address. Built-in encryption, private access control.

**Cost**: ~10.3 VRSCTEST per 999KB chunk

#### Method 3: Raw `contentmultimap` (Small Data Only)
Direct hex-encode and store. Essentially free (~0.0001 tx fee). **Limit: ~5KB max** — above this data is silently truncated.

### 7.3 Method Comparison

| | updateidentity + data ⭐ | sendcurrency | Raw contentmultimap |
|---|---|---|---|
| **Cost per 999KB** | ~6–7 VRSCTEST | ~10.3 VRSCTEST | ~0.0001 (tx fee) |
| **Max per call** | 1,000,000 bytes | 1,000,000 bytes | ~5KB |
| **Auto-chunking** | ✅ Yes | ✅ Yes | ❌ No |
| **Encryption** | ✅ Auto (ivk published) | ✅ To z-address | ❌ None |
| **Linked to identity** | ✅ Yes | ❌ Manual tracking | ✅ Yes |
| **Operation** | Synchronous | Async (opid) | Synchronous |

### 7.4 Size Limits
| What | Limit | Notes |
|---|---|---|
| Single script element | ~6,000 bytes | `MAX_SCRIPT_ELEMENT_SIZE_PBAAS` |
| Data wrapper input | 1,000,000 bytes | Hard limit in `signdata` |
| Single transaction | 2,000,000 bytes (2MB) | Can fill an entire block |
| Single block | 2,000,000 bytes (2MB) | `MAX_BLOCK_SIZE` |
| Multiple blocks | **Unlimited** | Via sequential `updateidentity` txs |

### 7.5 Cost Breakdown
| File Size | Chunks Needed | Time (~60s/block + processing) | Est. Cost |
|---|---|---|---|
| 5 KB | 1 | ~1 minute | ~0.0001 (raw) or ~6 VRSCTEST |
| 100 KB | 1 | ~4 minutes | ~6 VRSCTEST |
| 1 MB | 1 | ~4 minutes | ~6–7 VRSCTEST |
| 5 MB | 6 | ~30 minutes | ~40 VRSCTEST |
| 18.6 MB | 19 | ~2 hours | ~125 VRSCTEST |

### 7.6 Retrieval
```bash
# Step 1: Get encrypted descriptors
verus getidentitycontent "trial1.filestorage@"

# Step 2: Decrypt each chunk (requires txid + ivk from identity output)
verus decryptdata '{
  "datadescriptor": {
    "version": 1, "flags": 13,
    "objectdata": "<objectdata_hex>",
    "epk": "<epk>", "ivk": "<ivk>"
  },
  "ivk": "<same_ivk>",
  "txid": "<txid_of_the_updateidentity_call>",
  "retrieve": true
}'
```

### 7.7 Key Protocol Functions
| Function | Location | Purpose |
|---|---|---|
| `BreakApart()` | `src/primitives/block.cpp:820` | Split oversized data into chunks |
| `Reassemble()` | `src/primitives/block.cpp:851` | Validate + concatenate chunks |
| `signdata` | `src/wallet/rpcwallet.cpp:1231` | Build MMR, hash, sign, encrypt |
| `getidentitycontent` | `src/rpc/pbaasrpc.cpp:17215` | Retrieve aggregated multimap data |

### 7.8 Cross-Chain Data References
Data stored on-chain can be referenced from anywhere via `CCrossChainDataRef`:

| Reference Type | What It References |
|---|---|
| **UTXO Reference** (`CPBaaSEvidenceRef`) | Data in a specific transaction output on any PBaaS chain |
| **Identity Multimap Reference** (`CIdentityMultimapRef`) | Data under identity + VDXF key + block height range |
| **URL Reference** (`CURLRef`) | External data at a URL, with optional hash verification |

### 7.9 Schema Design: Namespace Pattern
For organized file storage, use a namespace identity with schema:
```
filestorage@  (namespace identity — TOKEN currency, schema registry)
│
├── DefinedKeys (25 keys):
│     chunk.0 .. chunk.18, manifest, filename, mimetype,
│     filesize, hash, chunkcount
│
└── trial1.filestorage@  (sub-ID — one per stored file)
      └── contentmultimap:
            ├── filestorage::chunk.0  → encrypted data (999KB)
            ├── filestorage::chunk.1  → encrypted data (999KB)
            ├── ...
            ├── filestorage::filename → "document.pdf"
            ├── filestorage::mimetype → "application/pdf"
            ├── filestorage::filesize → "18586159"
            ├── filestorage::hash     → "<sha256>"
            └── filestorage::chunkcount → "19"
```

### 7.10 Key Gotchas
1. **Sequential updates only** — each `updateidentity` spends the previous identity output; cannot parallelize
2. **Silent truncation** — raw hex >~5KB is silently truncated with no error
3. **Track your txids** — system does NOT store upload txids; needed for `decryptdata`
4. **CPU-intensive** — each 999KB chunk takes 3–5 minutes to process
5. **`definecurrency` requires manual broadcast** — returns tx object but does NOT auto-send
6. **Two entries per chunk** — `getidentitycontent` returns `[0]` = data, `[1]` = signature proof

---

## 8. Privacy & Shielded Transactions

### 8.1 Sapling Zero-Knowledge Proofs
- Z-addresses (`zs...`) for fully shielded transactions
- Only sender and recipient know the transaction details
- 512-byte encrypted memo field per shielded output

### 8.2 Key Operations
```bash
# Create z-address
verus z_getnewaddress

# Get viewing keys
verus z_getencryptionaddress '{"address":"zs1..."}'
# Returns: extendedviewingkey, incomingviewingkey, address

# Send shielded
verus z_sendmany "fromaddr" '[{"address":"zs1...","amount":1}]'

# Check z-balance
verus z_getbalance "zs1..."

# List z-addresses
verus z_listaddresses
```

### 8.3 Privacy Use Cases
- **Private payments** — only sender/recipient know details
- **Encrypted data delivery** — store encrypted keys via z-address memo
- **Selective disclosure** — share viewing key to grant read access
- **Agent-to-agent secure communication** — encrypt messages to z-address

---

## 9. Cross-Chain & Ethereum Bridge

### 9.1 Trustless Ethereum Bridge
- **Non-custodial**: No central authority — bridge operated by miners/stakers via consensus
- **Bidirectional**: VRSC ↔ ETH, ERC-20s ↔ Verus currencies
- **Bridge currency**: `Bridge.vETH` — fractional basket representing bridge reserves
- **Mapped currencies**: Any Verus currency can be exported as ERC-20
- **Transfer time**: ~30–60 minutes
- **Supported assets**: ETH, DAI, MKR (plus any mapped currencies)

### 9.1.1 Ethereum Bridge Contract Addresses (Updated March 2026)
| Contract | Address |
|---|---|
| Delegator | `0xBc2738BA63882891094C99E59a02141Ca1A1C36a` |
| Verus Bridge | `0xE6052Dcc60573561ECef2D9A4C0FEA6d3aC5B9A2` |

> **WARNING**: Previous addresses (`0x1Af5b8015C64d39Ab44C60EAd8317f9F5a9B6C4C` and `0x0200EbbD26467B866120D84A0d37c82CdE0acAEB`) are **DEPRECATED**. Using old addresses will send funds to defunct contracts.

### 9.2 Key Currency IDs
| Currency | i-address |
|---|---|
| VRSC | `i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV` |
| Bridge.vETH | (basket currency for ETH bridge) |
| vETH (mainnet) | `i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X` |
| vETH (testnet) | `iCtawpxUiCc2sEupt7Z4u8SDAncGZpgSKm` |

### 9.3 Cross-Chain Operations
```bash
# Export to Ethereum
verus sendcurrency "*" '[{"address":"0xEthAddr","amount":10,"currency":"VRSC","exportto":"vETH"}]'

# Check export/import status
verus getexports "vETH"
verus getimports "vETH"
verus getlastimportfrom "vETH"
```

---

## 10. PBaaS — Public Blockchains as a Service

PBaaS allows **anyone to launch a fully independent blockchain** on the Verus network:
- **No coding required** — launch via CLI/API commands
- **Inherits all Verus features**: VerusID, VDXF, DeFi, cross-chain
- **75–800 TPS** per chain depending on configuration
- **Merge-minable**: Up to 22 chains simultaneously
- **Launch cost**: 10,000 VRSC
- **Unlimited scalability**: No upper limit on PBaaS chains

### 10.1 PBaaS Chain Launch
```bash
verus definecurrency '{
  "name": "MyChain",
  "options": 264,
  "currencies": ["VRSC"],
  "conversions": [1],
  "eras": [{"reward": 1200000000, "decay": 0, "halving": 0, "eraend": 0}],
  "notaries": ["notary1@", "notary2@", "notary3@"],
  "minnotariesconfirm": 2,
  "idregistrationfees": 100,
  "idreferrallevels": 3,
  "notarizationreward": 0.001,
  "proofprotocol": 1
}'
```

### 10.2 PBaaS Notary Parameters (Wiki Update March 2026)

| Parameter | Type | Description |
|---|---|---|
| `notaries` | array | List of notary identity names for PBaaS chain validation (e.g. `["notary1@", "notary2@", "notary3@"]`) |
| `minnotariesconfirm` | number | Minimum unique notary signatures required for confirmation |

Notaries validate cross-chain transfers and state proofs between PBaaS chains and the Verus root chain. Setting `minnotariesconfirm` ensures that no single notary can unilaterally confirm a cross-chain operation.

---

## 11. On-Chain Marketplace (Atomic Swaps)

The `makeoffer`/`takeoffer` system implements a native decentralized marketplace:

### 11.1 Supported Trades
- Currency ↔ Currency
- Currency ↔ Identity
- Identity ↔ Identity

### 11.2 Commands
```bash
# Make an offer — first param is fromaddress, second is offer JSON
verus makeoffer "youragent@" '{"changeaddress":"youragent@","offer":{"currency":"VRSCTEST","amount":10},"for":{"currency":"OtherCurrency","amount":50}}'

# List open offers
verus getoffers "VRSCTEST" true
verus listopenoffers "VRSCTEST"

# Accept an offer — first param is fromaddress, txid goes INSIDE the JSON
verus takeoffer "youragent@" '{"txid":"OFFER_TXID","changeaddress":"youragent@","deliver":{"currency":"VRSCTEST","amount":10},"accept":{"currency":"OtherCurrency","amount":50}}'

# Close an offer
verus closeoffers '["OFFER_TXID"]'
```

> **Note**: `makeoffer` and `takeoffer` both take `fromaddress` as their first parameter.
> For `takeoffer`, the offer txid is a field **inside** the JSON (not a separate parameter).
> Examples use VRSCTEST for safety — change to VRSC for mainnet.

### 11.3 Agent Use Cases
- List services as offers (e.g., "research hours" tokens for VRSC)
- Find other agents' service offers programmatically
- Automated atomic swaps for arbitrage

---

## 12. Mining & Staking

### 12.1 VerusHash 2.2
- **CPU-optimized** — disincentivizes ASICs/FPGAs
- Mobile phones and ARM devices can mine profitably
- No special hardware advantage

### 12.2 Staking
- **No minimum stake** — any amount of VRSC
- **No slashing** — different "nothing-at-stake" solution
- **No lockup** — funds remain fully liquid
- Staking rewards go to the UTXO that stakes

### 12.3 Rewards
- **Current block reward**: 3 VRSC/block (was 6, halving schedule)
- **Max supply**: 83,540,184 VRSC
- **Block time**: ~60 seconds
- **Fee pool**: Each block releases 1% of accumulated fees

### 12.4 Mining Commands
```bash
# Start mining
verus setgenerate true <threads>

# Mining info
verus getmininginfo

# Merged mining (up to 22 PBaaS chains)
verus setminingdistribution '{"chain1":0.5,"chain2":0.5}'
```

---

## 13. VerusLogin SDK & QR Authentication

### 13.1 Overview
VerusLogin enables **passwordless authentication** using VerusID. No emails, no passwords — scan a QR code with Verus Mobile wallet.

### 13.2 ⚠️ CRITICAL API CHANGE: GenericRequest replaces LoginConsent

**All `LoginConsent*` classes and methods are now `@deprecated` in `verusid-ts-client`.**

The new API uses **`GenericRequest` / `GenericResponse`** extending `GenericEnvelope` with an
ordered `details[]` array of `OrdinalVDXFObject` items. The old `LoginConsentRequest` /
`LoginConsentResponse` classes still function but should NOT be used for new code.

| Old (Deprecated)                  | New (Current)                              |
|-----------------------------------|--------------------------------------------|
| `LoginConsentChallenge`           | `AuthenticationRequestDetails` in details  |
| `LoginConsentRequest`             | `GenericRequest`                           |
| `LoginConsentResponse`            | `GenericResponse`                          |
| `LoginConsentDecision`            | `AuthenticationResponseDetails` in details |
| `VerusIDSignature`                | `VerifiableSignatureData`                  |
| `createLoginConsentRequest()`     | `createGenericRequest()`                   |
| `verifyLoginConsentResponse()`    | `verifyGenericResponse()`                  |

### 13.3 BitGo UTXO Library (Offline Signing)
**The VerusID login operation needs to use the BitGo UTXO library for offline QR code generation.**

Library: `@bitgo/utxo-lib`
NPM: https://www.npmjs.com/package/@bitgo/utxo-lib

Key imports used by VerusIdInterface:
```typescript
import {
  IdentitySignature,  // Offline sign/verify VerusID signatures
  ECPair,             // ECPair.fromWIF(wif, networks.verus)
  networks,           // networks.verus for chain parameters
  address,            // fromBase58Check / toBase58Check
  smarttxs,           // createUnfundedIdentityUpdate, validateFundedCurrencyTransfer, completeFundedIdentityUpdate
  Transaction,        // SIGHASH_ALL, fromHex, toHex
} from "@bitgo/utxo-lib";
```

```bash
npm install @bitgo/utxo-lib
```

### 13.4 Installation & Initialization
```bash
yarn add https://github.com/VerusCoin/verusid-ts-client.git
```

```typescript
import { VerusIdInterface } from 'verusid-ts-client';

const verusId = new VerusIdInterface(
  "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV",  // VRSC system ID
  "https://api.verus.services",
  { auth: { username: '', password: '' } }
);
```

### 13.5 NEW Login Flow — GenericRequest API

#### 13.5.1 Data Model

```
GenericEnvelope (base)
├── version: number
├── flags: number
├── signature: VerifiableSignatureData
│   ├── version, flags, signatureVersion, hashType
│   ├── systemID: CompactIAddressObject (e.g. VRSC)
│   ├── identityID: CompactIAddressObject (signing identity)
│   ├── vdxfKeys?, vdxfKeyNames?, boundHashes?, statements?
│   └── signatureAsVch: Buffer
├── requestID: string (VDXF key)
├── createdAt: number (seconds since epoch)
├── salt: Buffer (32 bytes)
├── appOrDelegatedID: string (i-address)
└── details: Array<OrdinalVDXFObject>

GenericRequest extends GenericEnvelope
├── responseURIs: Array<ResponseURI>
│   ├── uri: string
│   └── type: TYPE_POST (1) | TYPE_REDIRECT (2)
└── encryptResponseToAddress?: SaplingPaymentAddress (z-address)

GenericResponse extends GenericEnvelope
└── (inherits everything; signature is from the responding wallet)
```

#### 13.5.2 OrdinalVDXFObject Detail Types

The `details[]` array holds typed objects. **Ordering is enforced** by
`isValidGenericRequestDetails()`:

| Ordinal VDXFObject Type                        | Position Rule                    |
|------------------------------------------------|----------------------------------|
| `AuthenticationRequestOrdinalVDXFObject`       | MUST be at index 0               |
| `AppEncryptionRequestOrdinalVDXFObject`        | Must come after auth (index > 0) |
| `ProvisionIdentityDetailsOrdinalVDXFObject`    | Must come after auth (index > 0) |
| `VerusPayInvoiceDetailsOrdinalVDXFObject`      | MUST be last                     |
| `IdentityUpdateRequestOrdinalVDXFObject`       | MUST be last                     |

#### 13.5.3 AuthenticationRequestDetails

```typescript
import { AuthenticationRequestDetails, RecipientConstraint } from 'verus-typescript-primitives';

const authDetails = new AuthenticationRequestDetails({
  flags: 0,
  requestID: LOGIN_CONSENT_REQUEST_VDXF_KEY.vdxfid,
  recipientConstraints: [
    new RecipientConstraint({
      type: RecipientConstraint.REQUIRED_ID,       // 1 = specific identity
      // or: RecipientConstraint.REQUIRED_SYSTEM,   // 2 = any ID on a system
      // or: RecipientConstraint.REQUIRED_PARENT,   // 3 = any ID under parent
      identity: { address: "iExampleIdentity..." }
    }),
  ],
  expiryTime: Math.floor(Date.now() / 1000) + 3600,  // 1 hour from now
});
```

#### 13.5.4 Complete New Login Flow

```
Server                          User (Mobile/Desktop)
  |                                     |
  |-- 1. Create GenericRequest -------->|
  |    (with AuthenticationRequest      |
  |     at details[0])                  |
  |-- 2. Generate QR / Deep Link ------>|
  |    (uses @bitgo/utxo-lib for        |
  |     offline QR code generation)     |
  |                                     |-- 3. Scan QR / Click Link
  |                                     |-- 4. Sign GenericResponse with VerusID
  |<-- 5. Signed GenericResponse -------|
  |    (via ResponseURI POST/REDIRECT)  |
  |-- 6. verifyGenericResponse() ------>|
  |-- 7. Authenticate User ------------>|
```

**Step 1-2: Server creates GenericRequest**
```typescript
import * as primitives from 'verus-typescript-primitives';

const request = await verusId.createGenericRequest(
  {
    signingId: "MyApp@",
    details: [
      new primitives.AuthenticationRequestOrdinalVDXFObject({
        data: new primitives.AuthenticationRequestDetails({
          flags: 0,
          requestID: primitives.LOGIN_CONSENT_REQUEST_VDXF_KEY.vdxfid,
          recipientConstraints: [],
          expiryTime: Math.floor(Date.now() / 1000) + 3600,
        })
      }),
    ],
    responseURIs: [
      new primitives.ResponseURI({
        uri: "https://myserver.com/api/verus/login",
        type: primitives.ResponseURI.TYPE_POST,  // 1
      }),
    ],
  },
  primaryAddrWif  // WIF for signing (optional if signing externally)
);

const qrData = request.toWalletDeeplinkUri(); // → verus://...
```

**Steps 5-6: Server verifies GenericResponse**
```typescript
const response = new primitives.GenericResponse(incomingData);
const isValid = await verusId.verifyGenericResponse(response);
// Extract signing identity from response.signature.identityID
```

### 13.6 Legacy Login Flow (DEPRECATED)

> ⚠️ **The following API is deprecated.** Use GenericRequest (Section 13.5) for all new code.

```typescript
// DEPRECATED — do not use for new implementations
const challenge = new primitives.LoginConsentChallenge({
  challenge_id: "unique-session-id",
  requested_access: [new primitives.RequestedPermission(
    primitives.IDENTITY_VIEW.vdxfid
  )],
  redirect_uris: [new primitives.RedirectUri(
    "https://myserver.com/api/verus/login",
    primitives.LOGIN_CONSENT_WEBHOOK_VDXF_KEY.vdxfid
  )],
});

const request = await verusId.createLoginConsentRequest(
  "MyApp@",
  challenge,
  primaryAddrWif
);
const qrData = request.toWalletDeeplinkUri();
```

### 13.7 Additional GenericRequest Capabilities

The `details[]` array can include multiple detail types in a single request:

| Detail Type                        | Purpose                                              |
|------------------------------------|------------------------------------------------------|
| `AuthenticationRequestDetails`     | Login/authentication with recipient constraints      |
| `AppEncryptionRequestDetails`      | Request encrypted derived seed from user master seed |
| `ProvisionIdentityDetails`         | Provision/create a new VerusID (systemID, parentID)  |
| `IdentityUpdateRequestDetails`     | Request identity update with optional signDataMap    |
| `VerusPayInvoiceDetails`           | Request payment (amount, currency, destination)      |

### 13.8 Mobile Wallet UI Routing

The Verus Mobile wallet **does NOT have a generic catch-all page** for QR/deep link data.
Each VDXF detail type in the GenericRequest `details[]` array triggers a **specific UI page**:

| Detail VDXF Key                        | Wallet UI Page        | Status            |
|:---------------------------------------|:----------------------|:------------------|
| `AUTHENTICATION_REQUEST_VDXF_KEY`      | Login / Auth page     | ✅ Fully supported |
| `IDENTITY_UPDATE_REQUEST_VDXF_KEY`     | ID Update confirm     | ✅ Fully supported |
| `VERUSPAY_INVOICE_DETAILS_VDXF_KEY`    | Payment / Invoice     | ✅ Fully supported |
| `APP_ENCRYPTION_REQUEST_VDXF_KEY`      | App Encryption seed   | ⚠️ Partially known |
| `DATA_PACKET_REQUEST_VDXF_KEY`         | Data Packet           | ❓ Not yet documented |
| `USER_DATA_REQUEST_VDXF_KEY`           | User Data             | ❓ Not yet documented |

**Key takeaway**: Login, updateidentity, and invoices each render completely different UI screens
in the wallet. Developers must use the correct VDXF key type to trigger the intended UI workflow.

### 13.9 Login Template
```bash
git clone https://github.com/monkins1010/verusid-login-template.git
# Vite + React client + Node + Express server
```

### 13.10 Webhook vs Redirect VDXF Key (CRITICAL)

When constructing a login challenge `redirect_uri`, the VDXF key determines how the wallet returns the signed response:

| Key | Constant | Behavior |
|-----|----------|----------|
| **Webhook** | `LOGIN_CONSENT_WEBHOOK_VDXF_KEY` | Wallet POSTs signed response directly to server (server-to-server) |
| **Redirect** | `LOGIN_CONSENT_REDIRECT_VDXF_KEY` | Wallet redirects user's browser to callback URL |

> **⚠️ Always use the Webhook key.**  It works with Verus Mobile **and** the Verus Web Wallet extension. The Redirect key only works with Verus Mobile — the web wallet extension rejects the challenge with “No webhook URI found in challenge.”

```typescript
// ✅ Correct — works with ALL wallets (extension + mobile + desktop)
new RedirectUri(callbackUrl, LOGIN_CONSENT_WEBHOOK_VDXF_KEY.vdxfid)

// ❌ Will NOT work with the web wallet extension
new RedirectUri(callbackUrl, LOGIN_CONSENT_REDIRECT_VDXF_KEY.vdxfid)
```

verus-connect (Section 30) uses the Webhook key automatically, so this only matters when constructing challenges manually.

### 13.11 Verus Web Wallet Extension Provider API

The Verus Web Wallet browser extension injects `window.verus` and dispatches a `verus#initialized` event:

```typescript
interface VerusProvider {
  isVerusWallet: true;
  version: string;
  requestLogin(uri: string): Promise<unknown>;     // Opens approval popup
  sendDeeplink(uri: string): Promise<unknown>;      // Processes deep link
  sendTransaction(params: {
    to: string;
    amount: number;
    currency?: string;
  }): Promise<{ txid: string }>;                    // Direct send
}
```

**Detection**:
1. Check `window.verus?.isVerusWallet` immediately
2. If not present, listen for `verus#initialized` event (give ~500ms for content script injection)
3. If still not present, fall back to QR code (desktop) or deep link (mobile)

**Login flow with extension**: Fire-and-forget — `window.verus.requestLogin(uri)` opens the approval popup, but the actual result comes back via the server webhook + polling (same as QR/deep link flows).

**Send flow with extension**: Direct — `window.verus.sendTransaction({to, amount, currency})` returns `{txid}` on approval.

### 13.12 Three Wallet Environments

The verus-connect SDK auto-detects the user’s wallet environment:

| Environment | Detection | Login Method | Send Method |
|-------------|-----------|-------------|-------------|
| **extension** | `window.verus?.isVerusWallet` | Challenge sent directly to extension popup | `sendTransaction()` returns txid |
| **mobile** | User-agent regex (`/Android\|iPhone/i`) | Deep link (`verus://verusid-login/...`) opens Verus Mobile | VerusPay deep link |
| **desktop** | Default fallback | QR code modal — scan with Verus Mobile | Not yet supported |

**Deep link security**: Only these URI schemes are allowed: `verus:`, `vrsc:`, `i5jtwbp6zymeay9llnraglgjqgdrffsau4:`. Others (e.g., `javascript:`, `data:`) are blocked.

---

## 14. Attestations & Credentials

### 14.1 Creating Attestations
Attestations use `signdata` RPC to create signed, MMR-backed proofs:

```javascript
const attestationData = {
  "address": "signingID@",
  "createmmr": true,
  "mmrdata": [
    {
      "vdxfdata": {
        [DataDescriptorKey().vdxfid]: {
          "version": 1, "flags": 0,
          "label": "myapp.vrsc::attestation.id",
          "mimetype": "text/plain",
          "objectdata": "document-id-12345"
        }
      }
    }
  ]
};
const reply = await verusdCall('signdata', [attestationData]);
```

### 14.2 Storing in Identity
```javascript
await verusdCall('updateidentity', [{
  name: "targetidentity",
  contentmultimap: {
    [zookeepersVdxfid]: {
      [MMRDescriptorKey().vdxfid]: reply.mmrdescriptor,
      [SignatureDataKey().vdxfid]: reply.signaturedata
    }
  }
}]);
```

---

## 15. Decentralized Reputation System

### 15.1 Protocol-Level Trust Ratings
Hidden in the wallet layer are `setidentitytrust` and `setcurrencytrust`:

| Mode | Behavior |
|---|---|
| **Mode 0** | Open — sync everything |
| **Mode 1** | Allow-list — only sync from approved identities |
| **Mode 2** | Block-list — sync everything except blocked identities |

### 15.2 Agent Reputation via Attestations
Store job completion records in contentmultimap:
- Job count and ratings (verifiable on-chain)
- Payment transactions matching job IDs
- Signed completion messages from buyers
- Identity age (block height of creation)

Other agents verify reputation by:
1. Reading contentmultimap attestation data
2. Verifying VerusID signatures on attestations
3. Checking staking weight (on-chain balance)
4. Computing confidence scores with diversity bonuses

---

## 16. Encrypted Messaging Between Agents

### 16.1 Architecture
```
Sender (VerusID)  ──sign + encrypt──▶  Encrypted blob  ──deliver──▶  Recipient (z-addr)
                                                                         │
                                                                   decrypt with ivk
                                                                         │
                                                                   verify signature
```

### 16.2 Setup
Each agent needs a z-address for receiving encrypted messages:
```bash
# Create shielded address
verus z_getnewaddress
# Returns: "zs1..."

# Get viewing keys (needed for decryption)
verus z_getencryptionaddress '{"address":"zs1YOUR_ADDRESS"}'
# Returns: { "extendedviewingkey": "...", "incomingviewingkey": "...", "address": "zs1..." }
```

### 16.3 Sending
```bash
# Sign and encrypt message to recipient's z-address
verus signdata '{
  "address": "sender.VRSCTEST@",
  "message": "{\"type\":\"message\",\"from\":\"sender@\",\"body\":\"Hello\"}",
  "encrypttoaddress": "zs1RECIPIENT_Z_ADDRESS"
}'
```

### 16.4 Receiving
```bash
# Decrypt with incoming viewing key
verus decryptdata '{
  "datadescriptor": {
    "version": 1, "flags": 5,
    "objectdata": "encrypted_hex_blob...",
    "epk": "ephemeral_public_key..."
  },
  "ivk": "your_incoming_viewing_key"
}'
```

### 16.5 Message Types
| Type | Purpose |
|---|---|
| `message` | Standard text message |
| `job_request` | Service request with pricing |
| `system` | Key rotation, status updates |

### 16.6 Security Properties
- **Confidentiality**: z-address encryption (only recipient can decrypt)
- **Authenticity**: VerusID signature (proves sender)
- **Integrity**: SHA256 hash in signature (tamper detection)
- **Non-repudiation**: Signature tied to block height (timestamped)
- **Selective disclosure**: Per-message SSK keys for arbitration

---

## 17. Agent Economy & Commerce Patterns

### 17.1 Receiving Payments
```bash
# Anyone can send VRSC to your identity name
verus sendcurrency "*" '[{"address":"youragent@","currency":"VRSC","amount":5}]'

# Generate fresh address per transaction (better tracking)
verus getnewaddress "payments"
```

### 17.2 Sending Payments
```bash
# Send with memo for job tracking (NOTE: memo only works with z-addresses!)
verus sendcurrency "youragent@" '[{"address":"zs1recipientzaddr...","currency":"VRSC","amount":5,"memo":"job_20260207_001"}]'
# Returns opid — poll z_getoperationstatus for actual txid
verus z_getoperationstatus '["opid-value"]'
```

> **Memo limitation**: The `memo` field is **only supported when sending to z-addresses** (`zs...`). Transparent addresses (`R...`) silently ignore memo data.

### 17.3 Job Flow (Agent-to-Agent Commerce)
```
1. Seller: List services in contentmultimap
2. Buyer: Look up agent's services via getidentity
3. Buyer: Create and sign job request
4. Seller: Verify buyer's signature, accept job
5. Seller: Do the work, deliver results (signed)
6. Buyer: Pay (prepay or postpay per terms)
7. Buyer: Verify and acknowledge completion
```

### 17.4 Currency Conversions
```bash
# Estimate conversion
verus estimateconversion '{"currency":"VRSC","convertto":"OTHERCURRENCY","amount":10}'

# Execute conversion
verus sendcurrency "youragent@" '[{"address":"youragent@","currency":"VRSC","convertto":"OTHERCURRENCY","amount":10}]'
```

### 17.5 Transaction Monitoring
```python
def monitor_payments(callback, poll_interval=15):
    seen = set()
    while True:
        txs = rpc("listtransactions", ["*", 50])
        for tx in txs:
            if tx["txid"] not in seen and tx["category"] == "receive":
                seen.add(tx["txid"])
                callback(tx)
        time.sleep(poll_interval)
```

### 17.6 Advanced Economy Patterns
- **Agent tokens**: Launch a TOKEN currency under agent's namespace
- **Revenue baskets**: Create FRACTIONAL basket for automated revenue sharing
- **Agent collectives**: Multi-agent baskets with proportional token distribution
- **Insurance pools**: Reserve-backed baskets for service guarantees
- **Staking income**: Stake VRSC holdings for passive income (no lockup)

---

## 18. Agent Identity & Profile Schema

### 18.1 `ari::agent.v1.*` Namespace (Testnet)
| Field | VDXF Key | i-address |
|---|---|---|
| version | `ari::agent.v1.version` | `i6HXzMMD3TTDDPvGB5UbHZVKxk8UhnKiE3` |
| type | `ari::agent.v1.type` | `iB5K4HoKTBzJErGscJaQkWrdg6c3tMsU6R` |
| name | `ari::agent.v1.name` | `iDdkfGg9wCLk6im1BrKTwh9rhSiUEcrE9d` |
| description | `ari::agent.v1.description` | `iKdG3eo2DLm19NJWDHiem2WobtYzbmqW6U` |
| capabilities | `ari::agent.v1.capabilities` | `iRu8CaKpMEkqYiednh7Ff1BT32TNgDXasZ` |
| endpoints | `ari::agent.v1.endpoints` | `i9kWQsJkfSATuWdSJs9QG6SA9MfbhbpPKt` |
| protocols | `ari::agent.v1.protocols` | `i8BMBVcsX9GDm3yrRNaMeTe1TQ2m1ng1qC` |
| owner | `ari::agent.v1.owner` | `iC6oQAC5rufBtks35ctW1YtugXc9QyxF2a` |
| status | `ari::agent.v1.status` | `iCwKbumFMBTmBFFQAGzsH4Nz2xpT2yvsyf` |
| services | `ari::agent.v1.services` | `iPpTtEbDj79FMMScKyfjSyhjJbSyaeXLHe` |

### 18.2 `agentplatform::agent.v1.*` Namespace
| Field | VDXF Key | i-address |
|---|---|---|
| version | `agentplatform::agent.v1.version` | `iBShCc1dESnTq25WkxzrKGjHvHwZFSoq6b` |
| type | `agentplatform::agent.v1.type` | `i9YN6ovGcotCnFdNyUtNh72Nw11WcBuD8y` |
| name | `agentplatform::agent.v1.name` | `i3oa8uNjgZjmC1RS8rg1od8czBP8bsh5A8` |
| description | `agentplatform::agent.v1.description` | `i9Ww2jR4sFt7nzdc5vRy5MHUCjTWULXCqH` |
| status | `agentplatform::agent.v1.status` | `iNCvffXEYWNBt1K5izxKFSFKBR5LPAAfxW` |
| capabilities | `agentplatform::agent.v1.capabilities` | `i7Aumh6Akeq7SC8VJBzpmJrqKNCvREAWMA` |
| protocols | `agentplatform::agent.v1.protocols` | `iFQzXU4V6am1M9q6LGBfR4uyNAtjhJiW2d` |
| owner | `agentplatform::agent.v1.owner` | `i5uUotnF2LzPci3mkz9QaozBtFjeFtAw45` |
| services | `agentplatform::agent.v1.services` | `iGVUNBQSNeGzdwjA4km5z6R9h7T2jao9Lz` |

### 18.3 Service Schema (`agentplatform::svc.v1.*`)
| Field | i-address |
|---|---|
| `agentplatform::svc.v1.name` | `iNTrSV1bqDAoaGRcpR51BeoS5wQvQ4P9Qj` |
| `agentplatform::svc.v1.description` | `i7ZUWAqwLu9b4E8oXZq4uX6X5W6BJnkuHz` |
| `agentplatform::svc.v1.price` | `iLjLxTk1bkEd7SAAWT27VQ7ECFuLtTnuKv` |
| `agentplatform::svc.v1.currency` | `iANfkUFM797eunQt4nFV3j7SvK8pUkfsJe` |
| `agentplatform::svc.v1.category` | `iGiUqVQcdLC3UAj8mHtSyWNsAKdEVXUFVC` |
| `agentplatform::svc.v1.turnaround` | `iNGq3xh28oV2U3VmMtQ3gjMX8jrH1ohKfp` |
| `agentplatform::svc.v1.status` | `iNbPugdyVSCv54zsZs68vAfvifcf14btX2` |

### 18.4 Register as an Agent
```bash
# Encode fields to hex
VERSION_HEX=$(echo -n '"1"' | xxd -p | tr -d '\n')
TYPE_HEX=$(echo -n '"autonomous"' | xxd -p | tr -d '\n')
NAME_HEX=$(echo -n '"MyAgent"' | xxd -p | tr -d '\n')
STATUS_HEX=$(echo -n '"active"' | xxd -p | tr -d '\n')

# Update identity with agent profile
verus updateidentity '{
  "name": "agentname",
  "parent": "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq",
  "contentmultimap": {
    "i6HXzMMD3TTDDPvGB5UbHZVKxk8UhnKiE3": ["'"$VERSION_HEX"'"],
    "iB5K4HoKTBzJErGscJaQkWrdg6c3tMsU6R": ["'"$TYPE_HEX"'"],
    "iDdkfGg9wCLk6im1BrKTwh9rhSiUEcrE9d": ["'"$NAME_HEX"'"],
    "iCwKbumFMBTmBFFQAGzsH4Nz2xpT2yvsyf": ["'"$STATUS_HEX"'"]
  }
}'
```

---

## 19. Agent Bootstrap — From Zero to Operational

### 19.1 Step-by-Step

| Step | Command | Autonomous? |
|---|---|---|
| Download CLI | `wget`/`curl` from GitHub releases | ✅ |
| Install | `tar -xzf` | ✅ |
| Start daemon | `verusd -testnet -bootstrap` | ✅ |
| Sync chain | Wait (<3 hours with bootstrap) | ✅ |
| Create address | `getnewaddress` | ✅ |
| Get funds | Faucet / human sponsor | ❌ Requires help |
| Register identity | `registeridentity` | ✅ (once funded) |

**Bottleneck**: Getting initial VRSC. Everything else is fully automatable.

### 19.2 Complete Bootstrap Script
```bash
#!/bin/bash
set -e
NETWORK="${1:-testnet}"
INSTALL_DIR="$HOME/verus-cli"

# Download latest
URL=$(curl -s https://api.github.com/repos/VerusCoin/VerusCoin/releases/latest \
  | grep "browser_download_url.*Linux.*x86_64" | head -1 | cut -d '"' -f 4)
mkdir -p "$INSTALL_DIR"
wget -q -O /tmp/verus-cli.tgz "$URL"
tar -xzf /tmp/verus-cli.tgz -C "$INSTALL_DIR" --strip-components=1

# ZK params (~1.7GB)
[ ! -f "$HOME/.zcash-params/sprout-proving.key" ] && cd "$INSTALL_DIR" && ./fetch-params

# Start with bootstrap (auto-creates dirs + random RPC credentials)
if [ "$NETWORK" = "testnet" ]; then
  DARGS="-testnet"; PORT=18843
else
  DARGS=""; PORT=27486
fi

"$INSTALL_DIR/verusd" $DARGS -bootstrap -daemon
sleep 10

# Read auto-generated credentials
CONF_DIR="$HOME/.komodo/$([ "$NETWORK" = "testnet" ] && echo "VRSCTEST" || echo "VRSC")"
RPC_USER=$(grep rpcuser "$CONF_DIR"/*.conf | cut -d= -f2)
RPC_PASS=$(grep rpcpassword "$CONF_DIR"/*.conf | cut -d= -f2)

ADDR=$("$INSTALL_DIR/verus" $DARGS getnewaddress "agent-wallet")
echo "Address: $ADDR"
echo "RPC: http://127.0.0.1:$PORT (user: $RPC_USER)"
echo "⚠️  Send VRSC to $ADDR, then register your identity."
```

### 19.3 Requirements
- ~2GB RAM, ~25GB disk (mainnet) or ~10GB (testnet)
- `-bootstrap` flag for fast first sync (<3 hours)

### 19.4 Daemon Management
```bash
# systemd
sudo tee /etc/systemd/system/verusd.service << EOF
[Unit]
Description=Verus Daemon
After=network.target
[Service]
User=$USER
ExecStart=$HOME/verus-cli/verusd -testnet -fastload
ExecStop=$HOME/verus-cli/verus -testnet stop
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now verusd

# Or tmux
tmux new -d -s verusd "~/verus-cli/verusd -testnet"
```

---

## 20. CLI/RPC Command Reference

### 20.1 Command Categories (201+ Commands, 14 Categories)

| Category | Key Commands |
|---|---|
| **Identity** | `registeridentity`, `getidentity`, `updateidentity`, `revokeidentity`, `recoveridentity`, `listidentities`, `getidentitycontent`, `getidentityhistory`, `signdata`, `signmessage`, `verifydata`, `verifymessage`, `verifysignature`, `setidentitytimelock` |
| **Multichain** | `definecurrency`, `getcurrency`, `listcurrencies`, `getcurrencystate`, `getcurrencyconverters`, `sendcurrency`, `estimateconversion`, `getexports`, `getimports`, `getnotarizationdata` |
| **Marketplace** | `makeoffer`, `takeoffer`, `getoffers`, `listopenoffers`, `closeoffers` |
| **VDXF** | `getvdxfid` |
| **Wallet** | `getwalletinfo`, `getcurrencybalance`, `sendtoaddress`, `z_sendmany`, `z_getbalance`, `z_getnewaddress`, `z_listaddresses`, `decryptdata`, `fundrawtransaction` |
| **Blockchain** | `getblock`, `getblockcount`, `getblockchaininfo`, `getrawmempool`, `getmempoolinfo` |
| **Mining** | `setgenerate`, `getmininginfo`, `setminingdistribution` |
| **Network** | `getpeerinfo`, `getnetworkinfo`, `addnode` |
| **Privacy** | `z_getnewaddress`, `z_sendmany`, `z_getbalance`, `z_getencryptionaddress`, `z_exportviewingkey` |
| **Hidden** | `hashdata`, `invalidateblock`, `reconsiderblock`, `setmocktime`, `resendwallettransactions` |

### 20.2 `signmessage` vs `signdata`

| | `signmessage` | `signdata` |
|---|---|---|
| **Use case** | Simple text signing | Encryption, MMR proofs, files |
| **Input** | `["identity@", "message"]` | `[{"address":"id@", "message":"text", ...}]` |
| **Output** | **JSON**: `{"hash": "hexhash", "signature": "base64sig"}` | Hash + signature + optional encrypted data |
| **Verify with** | `verifymessage` | `verifysignature` (pass `datahash`) |
| **Rule of thumb** | 90% of cases | When you need encryption/MMR |

> **CRITICAL**: `signmessage` returns a **JSON object** `{"hash": "...", "signature": "..."}`,
> NOT a plain base64 string. Code that parses the result as a raw string will break.

### 20.3 JSON-RPC Access
```bash
# Direct CLI
verus <command> [args...]

# HTTP JSON-RPC
curl --user rpcuser:rpcpassword \
  --data-binary '{"jsonrpc":"1.0","id":"1","method":"getinfo","params":[]}' \
  -H 'content-type:text/plain;' http://127.0.0.1:27486/

# HTTP API (no auth needed)
curl https://api.verus.services/api/getinfo
```

### 20.4 Common Error Codes
| Error Code | Message | Likely Cause |
|---|---|---|
| -5 | `Identity not found` | Wrong name qualification |
| -8 | `Invalid identity or not in wallet` | Don't control this identity |
| -6 | `Insufficient funds` | Not enough balance + fees |
| -1 | Various | Invalid parameters |

### 20.5 `getinfo` — Extended Response Fields (Wiki Update March 2026)

The `getinfo` RPC returns 13+ additional fields not previously documented:

| Field | Type | Description |
|---|---|---|
| `tiptime` | number | Timestamp of the chain tip (epoch seconds) |
| `nextblocktime` | number | Expected next block timestamp |
| `CCid` | number | Consensus branch ID |
| `p2pport` | number | P2P network port |
| `rpcport` | number | RPC server port |
| `magic` | string | Network magic bytes (hex) |
| `premine` | number | Premine amount |
| `eras` | number | Number of reward eras |
| `reward` | number | Current block reward (satoshis) |
| `halving` | number | Halving interval (blocks) |
| `decay` | number | Decay parameter |
| `endsubsidy` | number | Block height where subsidy ends |
| `veruspos` | number | VerusPoS configuration value |

> **Sync check**: The `synced` field does NOT exist in `getinfo`. Instead compare `blocks == longestchain` to determine if the node is fully synchronized.

### 20.6 `sendcurrency` — Returns opid, NOT txid (Wiki Update March 2026)

`sendcurrency` returns an **operation ID** (opid), not a transaction ID. To track completion:

```bash
# 1. Send currency (returns opid)
OPID=$(verus sendcurrency "*" '[{"address":"recipient@","currency":"VRSCTEST","amount":5}]')

# 2. Poll operation status
verus z_getoperationstatus '["$OPID"]'

# 3. When status is "success", result contains the actual txid:
# {"id":"opid-...", "status":"success", "result":{"txid":"abc123..."}, ...}
```

### 20.7 Memo Limitation

**Memos only work when sending to z-addresses** (`zs...`). Transparent addresses (`R...`) silently ignore the `memo` field. To attach memos for job tracking, use z-addresses as destinations.

---

## 21. Reference Code & Libraries

### 21.1 TypeScript/JavaScript Libraries
| Library | Purpose |
|---|---|
| **`verusid-ts-client`** | VerusID authentication SDK — signing, verification, login, identity updates ([GitHub](https://github.com/VerusCoin/verusid-ts-client)) |
| **`verus-typescript-primitives`** | Core data types: GenericRequest/Response, VDXF, Identity, PBaaS, Offers ([GitHub](https://github.com/AuraSoldique/verus-typescript-primitives)) |
| **`verusd-rpc-ts-client`** | TypeScript RPC client wrapping 20+ daemon methods ([GitHub](https://github.com/VerusCoin/verusd-rpc-ts-client)) |
| **`verus-connect`** | Drop-in VerusID login (server middleware + frontend SDK, ~10 lines) ([GitHub](https://github.com/Fried333/verus-connect)) |
| **`@bitgo/utxo-lib`** | UTXO transaction construction, signing, offline QR code generation ([NPM](https://www.npmjs.com/package/@bitgo/utxo-lib)) |
| `react-native-verus-light-client` | Zcash-based shielded transaction support |
| `verus-zkedid-utils` | ZK proof utilities for identity claims |

### 21.2 verusid-ts-client — `VerusIdInterface` Methods

```typescript
// Constructor
new VerusIdInterface(chainId: string, baseURL: string, axiosConfig?: AxiosRequestConfig)

// --- NEW GenericRequest/Response API ---
createGenericRequest(params, wif?, identity?, height?, chainIAddr?)
createGenericResponse(params, wif?, identity?, height?, chainIAddr?)
signGenericRequest(request, wif, identity?, height?)
signGenericResponse(response, wif, identity?, height?)
verifyGenericRequest(request, identity?, chainIAddr?, sigBlockTime?)
verifyGenericResponse(response, identity?, chainIAddr?, sigBlockTime?)

// --- Signatures ---
signMessage(iAddrOrIdentity, message, wif, ...)
verifyMessage(iAddrOrIdentity, base64Sig, message, ...)
signHash(iAddrOrIdentity, hash, wif, ...)
verifyHash(iAddrOrIdentity, base64Sig, hash, ...)
getSignatureInfo(iAddrOrIdentity, base64Sig, chainIAddr?)

// --- Identity Transactions (client-side) ---
createUpdateIdentityTransaction(identity, changeAddr, rawTx, height, utxos?, ...)
signUpdateIdentityTransaction(hex, inputs, keys)
createRevokeIdentityTransaction(identity, changeAddr, rawTx, height, utxos?, ...)
createRecoverIdentityTransaction(identity, changeAddr, rawTx, height, utxos?, ...)

// --- VerusPay ---
createVerusPayInvoice(details, signingId?, wif?, ...)
signVerusPayInvoice(invoice, signingId, systemId, wif, ...)
verifySignedVerusPayInvoice(invoice, identity?, chainIAddr?)

// --- Provisioning ---
signVerusIdProvisioningResponse(response, wif, identity?, height?)
createVerusIdProvisioningResponse(signingId, decision, wif?, ...)
verifyVerusIdProvisioningResponse(response, identity?, chainIAddr?)
static createVerusIdProvisioningRequest(signingAddr, challenge, wif?)
static verifyVerusIdProvisioningRequest(request, address)

// --- DEPRECATED (use GenericRequest/Response instead) ---
createLoginConsentRequest(...)
verifyLoginConsentRequest(...)
createLoginConsentResponse(...)
verifyLoginConsentResponse(...)
```

### 21.3 verusd-rpc-ts-client — `VerusdRpcInterface` (Full Reference)

> **Package**: `verusd-rpc-ts-client` v0.1.0 | **Author**: Michael Filip Toutonghi
> **GitHub**: https://github.com/VerusCoin/verusd-rpc-ts-client
> **License**: MIT | **Dependencies**: axios 1.11.0, verus-typescript-primitives (git)
>
> **⚠️ VerusID Login MUST reference this client**: `VerusIdInterface` (verusid-ts-client)
> wraps `VerusdRpcInterface` internally — all RPC calls during login verification go through it.

```typescript
// Constructor — 4th param enables custom transport (React Native bridges, IPC, mock testing)
new VerusdRpcInterface(
  chain: string,           // Chain i-address (VRSC: "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV")
  baseURL: string,         // RPC endpoint (e.g. "http://127.0.0.1:27486")
  config?: AxiosRequestConfig,  // { auth: { username, password } }
  rpcRequestOverride?: <D>(req: RpcRequestBody<number>) => Promise<RpcRequestResult<D>>
)

// ============ 24 RPC Methods ============

// Identity (used during login verification)
getIdentity(nameOrAddress, height?, includeTxid?, includeHistory?)
  → { identity: IdentityDefinition, status, canspendfor, cansignfor, blockheight, txid, vout }
getIdentityContent(nameOrAddress, fromHeight?, toHeight?)
  → same as getIdentity return
updateIdentity(identityJSON) → txid string

// Blockchain
getInfo() → { version, blocks, longestchain, connections, testnet, tiptime, ... }
getBlock(hashOrHeight, verbosity?) → string | BlockInfo
getBlockCount() → number
getRawTransaction(txid, verbose?) → string | RawTransaction

// Addresses
getAddressBalance(addresses) → { balance, received, currencybalance, currencyreceived }
getAddressDeltas(addresses, start?, end?, fromHeight?) → Array<{ satoshis, txid, ... }>
getAddressMempool(addresses) → Array<{ satoshis, txid, ... }>
getAddressUtxos(addresses) → Array<{ address, txid, outputIndex, script, satoshis, height }>

// Currency/DeFi
getCurrency(name) → CurrencyDefinition
getCurrencyConverters(currencies) → Array<{ [key]: CurrencyDefinition }>
listCurrencies(query?) → Array<{ currencydefinition, bestheight?, ... }>
estimateConversion(amount, convertTo, via?, preConvert?, sendTo?)
  → { estimatedcurrencyout, inputcurrencyid, outputcurrencyid, ... }
sendCurrency(fromAddr, outputs) → txid string | { outputtotals, feeamount, hextx }

// Transactions
sendRawTransaction(hex) → txid
fundRawTransaction(hex, changeAddr?) → { hex, changepos, fee }
signRawTransaction(hex) → { hex, complete, errors? }

// Marketplace
makeOffer(offer) → { txid?, hex? }
getOffers(currencyOrId, isCurrency?, withTx?) → OfferList

// Signatures & VDXF
signData(sigParams) → { signature?, signaturedata?, mmrdescriptor?, hash?, ... }
getVdxfId(vdxfuri) → { vdxfid, indexid?, hash160result, qualifiedname, bounddata? }

// Misc
zGetOperationStatus(opids?) → z_operation[]

// ============ Composite Helper Methods ============

// Complex DeFi path discovery with 4-cache system (currency, converters, listcurrencies, info)
getCurrencyConversionPaths(src, dest?, includeVia?, ignoreCurrencies?, via?, root?)
  → Convertables  // { [key: string]: Array<{ via?, destination, exportto?, price, gateway }> }
  // Recursively discovers all conversion paths between currencies
  // Handles gateway, fractional, PBaaS routing; auto-clears caches after completion

// Unwrap RPC result — throws Error(res.error.message) if response has error
static extractRpcResult<D>(res: RpcRequestResult<D>) → D

// ============ Currency Option Flags (from utils/flags.ts) ============
IS_TOKEN_FLAG           = 0x20   // 32
IS_FRACTIONAL_FLAG      = 0x01   // 1
IS_PBAAS_FLAG           = 0x100  // 256
IS_GATEWAY_FLAG         = 0x80   // 128
IS_GATEWAY_CONVERTER_FLAG = 0x200 // 512
checkFlag(integer, flag) → boolean

// ============ Constants (from utils/constants) ============
VERUS_I_ADDRESS      = "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV"  // Mainnet
VERUSTEST_I_ADDRESS  = "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq"  // Testnet
```

**Re-exports**: The package re-exports the entire `verus-typescript-primitives` module as `Primitives`:
```typescript
import VerusdRpcInterface, { Primitives } from 'verusd-rpc-ts-client';
// Primitives contains ALL types from verus-typescript-primitives
```

**Key architecture detail**: The `rpcRequestOverride` constructor parameter allows completely
replacing Axios with any custom transport. This is how React Native bridges and IPC channels
work — VerusdRpcInterface handles JSON-RPC framing, the override handles network I/O.

### 21.4 verus-typescript-primitives — Key Classes

**New Login API:**
```typescript
// Envelope infrastructure
import { GenericRequest, GenericResponse, GenericEnvelope } from './api/classes/GenericRequest'
import { OrdinalVDXFObject } from './api/classes/OrdinalVDXFObject'
import { ResponseURI, RequestURI } from './api/classes/ResponseURI'

// Authentication
import { AuthenticationRequestDetails,
         AuthenticationResponseDetails } from './api/classes/AuthenticationRequestDetails'
import { RecipientConstraint } from './api/classes/RecipientConstraint'
// RecipientConstraint.REQUIRED_ID = 1, REQUIRED_SYSTEM = 2, REQUIRED_PARENT = 3

// Signature (replaces VerusIDSignature)
import { VerifiableSignatureData } from './api/classes/VerifiableSignatureData'
// { version, flags, signatureVersion, hashType, systemID, identityID,
//   vdxfKeys?, vdxfKeyNames?, boundHashes?, statements?, signatureAsVch }

// Payment
import { VerusPayInvoiceDetails } from './api/classes/VerusPayInvoiceDetails'

// Provisioning
import { ProvisionIdentityDetails } from './api/classes/ProvisionIdentityDetails'

// App Encryption
import { AppEncryptionRequestDetails } from './api/classes/AppEncryptionRequestDetails'

// Identity Update
import { IdentityUpdateRequestDetails } from './api/classes/IdentityUpdateRequestDetails'
```

**PBaaS Primitives:**
```typescript
import { Identity, PartialIdentity } from './pbaas/Identity'
import { ContentMultiMap } from './pbaas/ContentMultiMap'
import { DataDescriptor } from './pbaas/DataDescriptor'
import { SignatureData } from './pbaas/SignatureData'
import { VdxfUniValue } from './pbaas/VdxfUniValue'
import { TransferDestination } from './pbaas/TransferDestination'
import { SaltedData } from './pbaas/SaltedData'
```

**VDXF Keys (from keys.ts — 50+):**
```typescript
// Generic Envelope
GENERIC_ENVELOPE_DEEPLINK_VDXF_KEY   // iHybTbGDvBQsxGKzBkjCBqS2RmEYQWMqaW
GENERIC_REQUEST_DEEPLINK_VDXF_KEY    // iML2i1HBEPb5CfMXjpz5A14LGWMQC4pKdp
GENERIC_RESPONSE_DEEPLINK_VDXF_KEY   // iL5aWfjGFPJEpYgPmSEvLfUzFi8sR41c5E

// Identity Update
IDENTITY_UPDATE_REQUEST_VDXF_KEY     // i9YLAS79BjndxK98qYL6WFiJjXiMbvuHAX
IDENTITY_UPDATE_RESPONSE_VDXF_KEY    // iU7kDLEyPSTpMK1raQh8sib8hNSCp96JvK
IDENTITY_AUTH_SIG_VDXF_KEY           // i6qAAxsGMiasFj84c3GrUCKnAQFbMxRvBx

// Login Consent (deprecated flow)
LOGIN_CONSENT_REQUEST_VDXF_KEY       // iKNufnRrJiQXnBMDHbvHBFjBRKMLKSEsvk
LOGIN_CONSENT_RESPONSE_VDXF_KEY      // iRQZGW36EPMBJhJFhf6fQHTzRCJtni4cYU
LOGIN_CONSENT_CHALLENGE_VDXF_KEY     // iKJ465xQKaEz3PFYcLEEMqjqPB4kCpNquf
LOGIN_CONSENT_DECISION_VDXF_KEY      // i5SYcDuXZVWqfeaYZPQYHami6LS36ZWEET
LOGIN_CONSENT_REDIRECT_VDXF_KEY      // i4VoSEihPNEGbqW8tcrmDs5BF5oLPFRCNp
LOGIN_CONSENT_WEBHOOK_VDXF_KEY       // i61GGEtjHTjFKJkz5ykLNATUBsjVi8XVvN
LOGIN_CONSENT_CONTEXT_VDXF_KEY       // i92PaETCi27UVEPcSibkXdaMPANdRaZhAy

// Provisioning
IDENTITY_PROVISIONING_REQUEST_VDXF_KEY   // i8kWr3VKy4EBiYUm1sG5kXmFKcXKHQHqin
IDENTITY_PROVISIONING_RESPONSE_VDXF_KEY  // iLSa6CZCyKkQFGCi3BxVnnGsHb4q8Mr7bp
IDENTITY_PROVISIONING_RESULT_VDXF_KEY    // iCBqZEPsfBxJRH2jkNuFsNvEvMfJBtiJe6

// Permission Scopes (from scopes.ts)
IDENTITY_VIEW                        // iLUrDR3gfNVicoM5nsT78RDjdqWtUahFXQ
IDENTITY_AGREEMENT                   // iRmBDkNsBPiCmfQDxS5kTFoJmhEH7JqPmb
ATTESTATION_READ_REQUEST             // iQXF1LS389JUBm1xPfg7PDqTa1MmJHE9Xz
PROFILE_DATA_READ_REQUEST            // iDJUWYmj2FLJbBZboTjpjR7554E1nSYhEi
```

**Legacy Login (deprecated — for reference only):**
```typescript
import {
  LoginConsentChallenge, LoginConsentRequest,
  LoginConsentResponse, LoginConsentDecision,
  RequestedPermission, RedirectUri,
} from 'verus-typescript-primitives';
```

### 21.5 @bitgo/utxo-lib — Key Imports
```typescript
import {
  IdentitySignature,  // Offline sign/verify VerusID signatures
  ECPair,             // ECPair.fromWIF(wif, networks.verus)
  networks,           // networks.verus chain parameters
  address,            // fromBase58Check / toBase58Check
  smarttxs,           // { createUnfundedIdentityUpdate,
                      //   validateFundedCurrencyTransfer,
                      //   completeFundedIdentityUpdate,
                      //   getFundedTxBuilder }
  Transaction,        // Transaction.SIGHASH_ALL, fromHex, toHex
} from "@bitgo/utxo-lib";
```

### 21.6 Reference Implementations
- **verusidx-tauri** (Rust/Tauri Desktop): Full RPC client, 40+ Tauri command handlers, OS keychain
- **verusid-login-template** (Node/Express + Vite/React): Complete VerusID login boilerplate
- **Verus Mobile** (React Native): Full wallet with all channels
- **Python Arbitrage Bot**: Monitors basket reserves, executes cross-pair arbitrage

---

## 22. Development Environment & Testnet

### 22.1 Private Testnet (Docker)
```bash
git clone https://github.com/monkins1010/chainify.git
cd chainify && yarn install
docker-compose -f test/integration/environment/verus/docker-compose.yaml up -d \
  --force-recreate --renew-anon-volumes
```

### 22.2 Daemon Configuration
Config file locations:
- **Linux**: `~/.komodo/VRSC/VRSC.conf` (mainnet) / `~/.komodo/VRSCTEST/VRSCTEST.conf` (testnet)
- **macOS**: `~/Library/Application Support/Komodo/VRSC/VRSC.conf`
- **Windows**: `%AppData%\Roaming\Komodo\VRSC\VRSC.conf`

Auto-generated on first daemon start with random RPC credentials.

### 22.3 RPC Ports
- **Mainnet**: 27486
- **Testnet**: 18843

---

## 23. Hidden & Undocumented Features

Discovered via C++ source code audit (not in `help` output):

| Command | What It Does |
|---|---|
| `hashdata` | Hash arbitrary data with configurable algorithm + personal string |
| `invalidateblock` | Force-reject a block and descendants (fork recovery) |
| `reconsiderblock` | Reverse a previous `invalidateblock` |
| `setmocktime` | Set fake internal clock (testing) |
| `resendwallettransactions` | Force re-broadcast unconfirmed wallet transactions |

**Deliberately disabled**:
| Command | Reason |
|---|---|
| `signhash` | Signs arbitrary hash without knowing content — disabled to prevent tricking users into signing malicious data |

---

## 24. v1.2.14-2 Critical Release Update

### 24.1 Release Classification
- **Type**: CRITICAL / MANDATORY soft-fork
- **Deadline**: All nodes must upgrade by January 7, 2026
- **Min daemon version**: `1021400` / `"1.2.14-2"`

### 24.2 Changes
- **Bridge event fix**: Corrects bridge event processing for Verus-Ethereum bridge
- **`-currencyindex` performance fix**: Fixes degradation with `-currencyindex` flag
- **Bridgekeeper improvements**: More accurate fee calculation, enhanced reliability
- **`fundrawtransaction` improvements**: Better mobile wallet support (preparation for Verus Mobile and Valu wallet releases)

### 24.3 Impact on UAI-e-Gold
The `fundrawtransaction` improvements directly affect mobile wallet development:
1. Verus Mobile calls `fundrawtransaction` via VrpcProvider
2. All conversion/cross-chain preflights use `fundRawTransaction`
3. API servers automatically upgraded — mobile VRPC calls benefit automatically

---

## 25. Verus Mobile Wallet Architecture

> **Repository**: [VerusCoin/Verus-Mobile](https://github.com/VerusCoin/Verus-Mobile)
> **Stack**: React Native + Redux + Redux-Saga + React Navigation v6

### 25.1 API Channel Architecture

| Channel | Purpose | Key Operations |
|---|---|---|
| **VRPC** | Verus daemon RPC | Send, convert, cross-chain, fund raw tx |
| **Electrum** | SPV for BTC/KMD | UTXO management |
| **ETH** | Ethereum via ethers.js | ETH send/receive |
| **ERC20** | ERC-20 tokens | Token transfers, bridge |
| **DLIGHT** | Zcash light client | Shielded (z-address) transactions |
| **VERUSID** | Identity management | getIdentity, updateIdentity |

### 25.2 Key Dependencies
| Package | Purpose |
|---|---|
| `verusid-ts-client` | VerusID authentication |
| `verus-typescript-primitives` | Core data types, VDXF keys |
| `verusd-rpc-ts-client` | RPC interface |
| **`@bitgo/utxo-lib`** | **UTXO construction, signing, QR generation** |
| `ethers` (v6) | Ethereum/ERC-20 |
| `react-native-verus-light-client` | Shielded transactions |

### 25.3 VRPC Send Pipeline
```
createUnfundedCurrencyTransfer (@bitgo/utxo-lib/smarttxs)
    → fundRawTransaction (daemon)
    → sign (utxo-lib)
    → sendRawTransaction (daemon)
```

---

## 26. Mobile Wallet Modification Guide (UAI-e-Gold Fork)

### 26.1 Priority Tier 1 — Branding & Identity
| File/Area | What to Modify |
|---|---|
| `env/index.js` | Feature flags, network defaults |
| `App.js` | Theme colors, fonts |
| `src/globals/colors.js` | All color constants |
| `app.json` | App name, display name |
| Android/iOS | Package name, bundle ID |

### 26.2 Priority Tier 2 — Coin Configuration
| File/Area | What to Modify |
|---|---|
| `src/utils/CoinData/CoinsList.js` | `START_COINS` array, channels |
| `src/utils/CoinData/CoinDirectory.js` | Default currencies, PBaaS discovery |
| `src/utils/defaultSubWallets.js` | Sub-wallet mappings |

### 26.3 Priority Tier 3 — Core API Layer
| File/Area | Research Needed |
|---|---|
| `src/utils/vrpc/vrpcInterface.js` | VrpcProvider endpoints |
| `src/utils/api/channels/vrpc/requests/preflight.js` | vETH bridge addresses, conversion logic |
| `src/utils/api/channels/vrpc/requests/send.js` | `networks.verus` from @bitgo/utxo-lib |

---

## 27. verus_agent — UAI Neural Swarm Specialist

### 27.1 Architecture Overview
The `verus_agent` package (v0.4.0) is the **Verus Blockchain Specialist Agent** for the UAI Neural Swarm cluster. It integrates 10 sub-modules under a single orchestrator:

```
VerusBlockchainAgent (agent.py — 1316 lines)
├── VerusCLI (cli_wrapper.py)          — 2 backends: local subprocess / HTTP JSON-RPC
├── VerusIDManager (verusid.py)        — CRUD + vault + revoke/recover + signatures
├── VerusDeFiManager (defi.py)         — conversions, arbitrage, baskets, PBaaS
├── VerusLoginManager (login.py)       — passwordless challenge/response auth
├── VerusStorageManager (storage.py)   — on-chain (<4KB) + gateway (large files)
├── VerusSwarmSecurity (swarm_security.py) — optional identity/permission enforcement
├── VerusAgentMarketplace (marketplace.py) — product/license/invoice/discovery
├── VerusIPProtection (ip_protection.py)   — model hash, encryption, watermarks, Sapling
├── VerusReputationSystem (reputation.py)  — attestations, scoring, leaderboard
└── VerusMobileHelper (mobile.py)          — VerusPay URIs, LoginConsent, deep links
```

### 27.2 Agent States (13)
`INITIALIZING`, `IDLE`, `PROCESSING_TASK`, `EXECUTING_CLI`, `MANAGING_IDENTITY`, `EXECUTING_DEFI`, `AUTHENTICATING`, `STORING_DATA`, `MONITORING_MARKET`, `COLLABORATING`, `LEARNING`, `ERROR`, `SHUTDOWN`

### 27.3 Specializations (7)
`IDENTITY_MANAGER`, `DEFI_OPERATOR`, `MARKET_MONITOR`, `STORAGE_MANAGER`, `AUTH_PROVIDER`, `BRIDGE_OPERATOR`, `FULL_STACK`

### 27.4 Capability Dispatch (45+ handlers)
- **14 core**: identity CRUD/vault, currency launch/convert/send, storage, login, bridge, market, CLI
- **7 marketplace**: register_product, issue_license, verify_license, list_offers, create_invoice, discover, search
- **6 IP protection**: register_model, verify_integrity, encrypt/decrypt_model, full_protect
- **4 security**: register/verify/revoke agent, security_status
- **4 reputation**: attest, query, leaderboard, verify
- **3 DeFi extension**: create_revenue_basket, distribute_revenue, define_pbaas_chain
- **3 mobile**: payment_uri, login_consent, purchase_link
- **2 watermark**: generate, verify
- **1 cross-chain**: license verification

### 27.5 Learning & Adaptation
- **Decision weights**: Dirichlet-random initialized, reinforced on success
- **Autonomous params**: curiosity=0.3, cooperation=0.8, innovation=0.5
- **Experience history**: Last 1000 entries
- **Adaptive behavior**: Adjusts weights + learning rate based on success rate

### 27.6 Key Configuration (config.py)
| Constant | Value |
|---|---|
| `AGENT_ID` | `"verus_blockchain_agent"` |
| `AGENT_ROLE` | `"SPECIALIST"` |
| `MIN_DAEMON_VERSION` | `1021400` (v1.2.14) |
| `DEFAULT_TRADE_THRESHOLD` | `1.0003` (0.03% profit) |
| `DEFAULT_SLEEP_SECONDS` | `80` |
| `AGENT_CAPABILITIES` | 45 capability strings |
| `VDXF_NAMESPACE` | ~40 `vrsc::uai.*` key mappings |

### 27.7 Dependencies
| Required | Optional |
|---|---|
| `aiohttp`, `numpy` | `cryptography` (AES-256-GCM), `torch` + `safetensors` (LoRA watermark) |

### 27.8 IP Protection (7 Security Layers)
1. **Provenance Proof** — VerusID signature over model hash
2. **Integrity Check** — SHA-256 verification
3. **Access Control** — Sapling z-address encrypted key delivery
4. **License Gating** — License SubID required to decrypt
5. **Revocation** — Revoke model identity or license
6. **Vault Protection** — Timelock on master model identity
7. **Watermarking** — Per-buyer LoRA delta tracking

### 27.9 Gaps Identified for Update
Based on Verus Agent Wiki analysis, the following capabilities should be added:

1. **On-chain file storage** — `storage.py` currently limited to 4KB direct + gateway; should implement the 3 proven methods (updateidentity+data wrapper, sendcurrency, raw contentmultimap) with auto-chunking
2. **Encrypted messaging** — No module exists for z-address encrypted agent-to-agent messaging
3. **Marketplace atomic swaps** — `marketplace.py` has `create_offer()` but should incorporate full `makeoffer`/`takeoffer`/`listopenoffers` patterns
4. **Agent profile schema** — Should support both `ari::agent.v1.*` and `agentplatform::agent.v1.*` VDXF namespaces
5. **VDXF Data Pipeline** — Should support DefinedKey publishing and DataDescriptor creation
6. **Trust/reputation** — Should implement `setidentitytrust`/`setcurrencytrust` commands
7. **BitGo UTXO library** — `login.py` and `mobile.py` should reference `@bitgo/utxo-lib` for offline QR code generation
8. **Mining/staking management** — No mining/staking module exists

---

## 28. Key Resources & Links

### 28.1 Official Documentation
- **Docs**: https://docs.verus.io
- **Wiki CLI**: https://wiki.verus.io/#!faq-cli/clifaq-02_verus_commands.md
- **Developer Docs**: https://monkins1010.github.io/

### 28.2 Developer Docs (monkins1010.github.io)
- [VerusLogin Getting Started](https://monkins1010.github.io/veruslogin/getting-started/)
- [VerusLogin Server Login](https://monkins1010.github.io/veruslogin/server-login/)
- [VerusLogin Process Login](https://monkins1010.github.io/veruslogin/process-login/)
- [VerusLogin Validate Login](https://monkins1010.github.io/veruslogin/validate-login/)
- [VDXF Keys Reference](https://monkins1010.github.io/verusvdxf/getting-started-copy/)
- [Identity Storage](https://monkins1010.github.io/verusstorage/getting-started/)
- [File Storage](https://monkins1010.github.io/verusstorage/storing-files/)
- [Attestations](https://monkins1010.github.io/attestations/getting-started/)

### 28.3 GitHub Repositories
- [VerusCoin/VerusCoin](https://github.com/VerusCoin/VerusCoin) — Core daemon
- [VerusCoin/verusid-ts-client](https://github.com/VerusCoin/verusid-ts-client) — TS Login SDK
- [Fried333/verus-connect](https://github.com/Fried333/verus-connect) — Drop-in VerusID login (server + frontend)
- [monkins1010/verusid-login-template](https://github.com/monkins1010/verusid-login-template) — Login boilerplate
- [monkins1010/chainify](https://github.com/monkins1010/chainify) — Docker testnet
- [devdudeio/verus-gateway](https://github.com/devdudeio/verus-gateway) — File hosting gateway

### 28.4 NPM Packages
- **@bitgo/utxo-lib**: https://www.npmjs.com/package/@bitgo/utxo-lib — UTXO transaction construction, signing, offline QR code generation for VerusID login

### 28.5 API Endpoints
| Service | URL |
|---|---|
| Mainnet API | `https://api.verus.services` |
| Testnet API | `https://api.verustest.net` |
| Market Tracker | `https://markets.verus.trading` |
| Dashboard | `https://cryptodashboard.faldt.net` |
| Verus Gateway | `https://beamup.devdude.io/` |

### 28.6 Key Articles
- [How Verus Solved MEV](https://medium.com/veruscoin/how-verus-solved-mev-maximal-extractable-value-in-defi-c9ca31f1c153)
- [Scalability — What Trilemma?](https://medium.com/veruscoin/scalability-decentralization-security-what-trilemma-8d2d6869924d)
- [Smart Transactions vs. Smart Contracts](https://medium.com/veruscoin/verus-smart-transactions-vs-smart-contracts-f98079c00ed0)

---

## 29. Wiki Update Findings (March 2026)

This section documents all corrections and additions discovered during the Verus Agent Wiki Update comparison (original vs updated wiki, March 2026). Full details in `VERUS_WIKI_UPDATE_FINDINGS_REPORT.md`.

### 29.1 Critical API Corrections Applied

| Finding | Old Value | Corrected Value | Affected Code |
|---|---|---|---|
| `signmessage` return format | Plain base64 string | JSON: `{"hash":"hexhash","signature":"base64sig"}` | `cli_wrapper.py`, Section 20.2 |
| `sendcurrency` return value | txid | **opid** — must poll `z_getoperationstatus` | `cli_wrapper.py`, `defi.py`, Section 6.5, 17.2, 20.6 |
| `makeoffer` params | `(offer_json)` | `(fromaddress, offer_json)` | `cli_wrapper.py`, `marketplace.py`, Section 11.2 |
| `takeoffer` params | `(offer_txid, identity_json)` | `(fromaddress, offer_json)` — txid inside JSON | `cli_wrapper.py`, Section 11.2 |
| Memo limitation | Not documented | Only works with z-addresses (`zs...`) | `storage.py`, `defi.py`, Section 17.2, 20.7 |

### 29.2 Protocol Fact Corrections

| Fact | Old Value | Corrected Value | Section |
|---|---|---|---|
| VerusHash version | Already correct (2.2) | 2.2 confirmed | 1, 2.1 |
| Block time | Already correct (~60s) | ~60s confirmed (not ~62s) | 1, 2.1, 7.5 |
| Blocks per day | Already correct (1440) | 1440 confirmed | 1 |

### 29.3 New Content Added

| Content | Source | Applied To |
|---|---|---|
| Ethereum bridge contract addresses | Wiki Update §5 | `config.py` (ETH_BRIDGE_CONTRACTS), Section 9.1.1 |
| 13 new `getinfo` response fields | Wiki Update §6.1 | `config.py` (GETINFO_EXTRA_FIELDS), Section 20.5 |
| `definecurrency` notary params | Wiki Update §6.2 | `config.py` (DEFINECURRENCY_PBAAS_PARAMS), Section 10.2 |
| Protocol facts & statistics | Wiki Update §1.1 | `config.py` (PROTOCOL_FACTS) |
| `sendcurrency` opid tracking | Wiki Update §4.2 | `cli_wrapper.py`, `defi.py`, Section 20.6 |
| Opid polling helper | New implementation | `defi.py` (`await_opid()`) |

### 29.4 New Wiki Documentation (5 New Files, 1,032 Lines)

| File | Lines | Key Content |
|---|---|---|
| **Verus Facts and Statistics** | 424 | Protocol overview, VerusID facts, DeFi facts, comparison table (vs ETH/SOL/BTC), mining facts, privacy facts, PBaaS facts |
| **FAQ: General** | 166 | What is Verus, vs Ethereum, Zcash fork history, creator, decentralization, VRSC usage |
| **FAQ: Identity** | 148 | VerusID cost/recovery/SubIDs, multisig, data storage, login/auth |
| **FAQ: DeFi** | 127 | Protocol-level DeFi, basket currencies, MEV resistance, swaps, token launch, ETH bridge |
| **FAQ: Mining & Staking** | 167 | Mining commands, VerusHash, staking requirements, rewards, hardware, hybrid consensus |

### 29.5 Safety: VRSCTEST Convention

All agent-facing examples in the Wiki Update use **VRSCTEST** instead of VRSC. This prevents accidental mainnet transactions when following examples. Section 11.2 and `config.py` examples updated accordingly.

### 29.6 Structural Changes in Wiki Update

- **New directories**: `FAQ/` (4 files), `Introduction/` (2 relocated files)
- **Removed**: `.obsidian/` (editor config), `Welcome.md` (replaced by enhanced landing page), empty `basket-currencies-defi.md`
- **Relocated**: `Key Concepts` and `The Hidden Power of Verus` moved into `Introduction/`
- **Navigation**: All cross-links updated for new directory structure

---

## 30. verus-connect — Drop-in Login SDK (March 2026)

Source: Analysis of [Fried333/verus-connect](https://github.com/Fried333/verus-connect) (cloned March 2026).

### 30.1 Overview

`verus-connect` packages the entire VerusID login flow into a single npm package with **server middleware** (Express) and a **frontend SDK** (vanilla JS, works with React/Vue/etc). It replaces the manual multi-hundred-line setup from the Developer Guide with ~10 lines of code.

```bash
npm install verus-connect express
npm install git+https://github.com/VerusCoin/verusid-ts-client.git
```

### 30.2 Server Setup (~5 lines)

```javascript
const { verusAuth } = require('verus-connect/server');
app.use('/auth/verus', verusAuth({
  iAddress: process.env.VERUS_ID,
  privateKey: process.env.VERUS_WIF,
  callbackUrl: 'https://mysite.com/auth/verus/verusidlogin',
  async onLogin({ iAddress, friendlyName }) {
    return { token: jwt.sign({ iAddress }, SECRET) };
  },
}));
```

Creates five routes:

| Route | Method | Purpose |
|-------|--------|---------|---
| `/login` | POST | Create signed login challenge |
| `/verusidlogin` | POST | Receives signed response from wallet |
| `/result/:id` | GET | Frontend polls for result |
| `/pay-deeplink` | POST | Generate VerusPay invoice deep link |
| `/health` | GET | Health check |

### 30.3 Frontend Setup (~5 lines)

```javascript
import { VerusConnect } from 'verus-connect';
const vc = new VerusConnect({ appName: 'My App', serverUrl: '/auth/verus' });

const result = await vc.login();
console.log(result.iAddress);     // "iABC123..."
console.log(result.friendlyName); // "alice@"
console.log(result.method);       // "extension", "qr", or "deeplink"
```

Auto-detects wallet environment: extension → sends challenge directly; mobile → deep link; desktop → QR code modal.

### 30.4 Key Technical Details

**Challenge IDs**: Generated as random i-addresses (version byte 102, bs58check encoded), not hex strings.

**Identity display**: Middleware prefers `friendlyname` over `fullyqualifiedname` — chain suffix (`.VRSC@`) is implied and stripped for display.

**Graceful RPC failure**: If RPC verification is unavailable (e.g., PBaaS identities not resolvable on mainnet), the middleware trusts the signed callback rather than blocking login.

**VerusPay invoice deep links**:
```javascript
// POST /auth/verus/pay-deeplink
// Body: { address: "RYour...", amount: 1.5, currency_id?: "i5w5..." }
// Returns: { deep_link: "i5jtwbp6zymeay9llnraglgjqgdrffsau4://x-callback-url/..." }
```
Uses VerusPayInvoice V3 format with `DEST_PKH` TransferDestination for broad Verus Mobile compatibility.

**Send via extension**:
```javascript
const result = await vc.send({ to: 'RAddress...', amount: 1.5, currency: 'VRSC' });
console.log(result.txid); // Transaction ID
```
Currently extension-only. Mobile send via deep link not yet supported.

### 30.5 Events

```javascript
vc.on('login:start', () => {});
vc.on('login:success', (result) => {});
vc.on('login:error', (err) => {});
vc.on('login:cancel', () => {});
vc.on('provider:detected', (env) => {}); // 'extension' | 'mobile' | 'desktop'
vc.on('modal:open', () => {});
vc.on('modal:close', () => {});
```

### 30.6 Theming

```javascript
new VerusConnect({
  theme: {
    primaryColor: '#3165D4',
    backgroundColor: '#1a1a2e',
    textColor: '#e0e0e0',
    overlayColor: 'rgba(0,0,0,0.6)',
    borderRadius: '16px',
    fontFamily: 'system-ui, sans-serif',
  },
});
```

---

## Appendix A: signdata — The MMR Builder

`signdata` supports these input types:
- **Files**: `"filename": "/path/to/file"`
- **Text messages**: `"message": "hello world"`
- **Hex data**: `"serializedhex": "deadbeef"`
- **Base64 data**: `"serializedbase64": "..."`
- **Pre-computed hashes**: `"datahash": "256bithex"`
- **VDXF data**: `"vdxfdata": {...}`

Returns `CMMRDescriptor` containing MMR root hash (signed by identity), all leaf hashes, and all data descriptors.

## Appendix B: Source Code Reference Table

| Component | File | Line |
|---|---|---|
| `CMultiPartDescriptor` | `src/primitives/block.h` | 1153 |
| `CEvidenceData` | `src/primitives/block.h` | 1170 |
| `CIdentityMultimapRef` | `src/primitives/block.h` | 2504 |
| `CCrossChainDataRef` | `src/primitives/block.h` | 2669 |
| `BreakApart()` | `src/primitives/block.cpp` | 820 |
| `Reassemble constructor` | `src/primitives/block.cpp` | 851 |
| `CMMRDescriptor` | `src/pbaas/vdxf.h` | 1391 |
| `CDataDescriptor` | `src/pbaas/vdxf.h` / `vdxf.cpp` | 697+ |
| `GetAggregatedIdentityMultimap` | `src/pbaas/identity.cpp` | 454 |
| `signdata` | `src/wallet/rpcwallet.cpp` | 1231 |
| `updateidentity` (chunking) | `src/rpc/pbaasrpc.cpp` | 16186 |
| `getidentitycontent` | `src/rpc/pbaasrpc.cpp` | 17215 |
| `hashdata` (hidden) | `src/rpc/misc.cpp` | 746 |
| `MAX_SCRIPT_ELEMENT_SIZE_PBAAS` | `src/script/script.h` | 36 |
| `MAX_BLOCK_SIZE` | `src/consensus/consensus.h` | 22 |

---

*Report generated from deep analysis of the Verus Agent Wiki (80+ markdown files), VerusCoin C++ source code audit, verus_agent Python codebase review, and testnet verification. Every claim cross-referenced against source code and official documentation.*

*Wiki research by Ari — verus_agent analysis by UAI Cluster Intelligence — Report compiled June 2026*
