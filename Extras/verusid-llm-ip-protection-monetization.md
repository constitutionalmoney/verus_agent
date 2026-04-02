# VerusID as LLM/SLM Container, Security Layer & Monetization Engine for UAI Cluster Intelligence

> **Extends:** #5 (Verus Blockchain Specialist Agent), #8 (Verus Mobile Wallet Integration & v1.2.14-2)  
> **Priority:** High — Strategic Architecture  
> **Type:** Research + Architecture + Feature  

---

## Executive Summary

This issue evaluates the feasibility and architecture for using **VerusID** and its **VDXF contentmultimap** system as:

1. A container to store and sell access to LLM/SLM models and their artifacts  
2. A security layer for UAI Swarm Intelligence agent authentication and authorization  
3. A monetization mechanism for selling specialized agents to the public  
4. An IP protection framework for LLM/SLM intellectual property  

**Key Finding:** Full LLM/SLM model weights are too large to store directly on-chain in VerusID contentmultimap. However, VerusID is **exceptionally well-suited** as a **control plane, licensing registry, access-gating mechanism, and IP verification layer** — storing encrypted metadata, access keys, LoRA adapters (small ones), agent configurations, licensing terms, and provenance proofs that *reference* off-chain model storage.

---

## 1. VerusID Contentmultimap — Data Storage Analysis

### 1.1 On-Chain Storage Constraints

From source code analysis of `VerusCoin/VerusCoin`:

| Constant | Value | Source |
|----------|-------|--------|
| `MAX_SCRIPT_ELEMENT_SIZE_IDENTITY` | **3,073 bytes** | [script.h#L34](https://github.com/VerusCoin/VerusCoin/blob/main/src/script/script.h#L34) |
| `MAX_SCRIPT_ELEMENT_SIZE_PBAAS` | **6,000 bytes** | script.h — for PBaaS fulfillments |
| `MAX_SCRIPT_ELEMENT_SIZE` (runtime) | Dynamic, set by consensus | CScript class static member |
| `MAX_NATIVE_IDENTITY_SIZE` | **512 bytes** | crosschainrpc.h — base identity overhead |
| Max identity export size | `MAX_SCRIPT_ELEMENT_SIZE - 128` bytes | identity.cpp PrecheckIdentityPrimary |
| `MAX_NAME_LEN` | **64 bytes** | crosschainrpc.h |
| Evidence chunk size | `MAX_SCRIPT_ELEMENT_SIZE - 256` | BreakApart() — for multipart data |

**The contentmultimap** is a `std::multimap<uint160, std::vector<unsigned char>>` — meaning each entry is keyed by a 20-byte VDXF key and holds an arbitrary byte vector. Multiple entries per key are supported. However, the entire identity (including all contentmultimap data) must fit within a single transaction output script, bounded by `MAX_SCRIPT_ELEMENT_SIZE_IDENTITY`.

**Effective usable data per identity update:** ~2-5 KB of contentmultimap data per `updateidentity` transaction (after overhead for primary addresses, revocation/recovery authorities, system fields, etc.).

**Aggregate over multiple updates:** The `GetAggregatedIdentityMultimap` function aggregates contentmultimap entries across the *entire history* of identity updates. This means data can be accumulated across many transactions, with each update adding new key-value entries. The `ContentMultiMapRemove` mechanism allows selective deletion of entries.

### 1.2 LLM/SLM Model Size Comparison

| Model Artifact | Typical Size | Fits in Single VerusID Update? | Fits via Aggregated Updates? |
|---------------|-------------|-------------------------------|------------------------------|
| **GPT-2 Small (124M)** | 250 MB (FP16) | **NO** (125,000x too large) | **NO** — impractical |
| **TinyLlama (1.1B)** | 2.2 GB (FP16) | **NO** | **NO** |
| **Phi-2 (2.7B)** | 5.5 GB | **NO** | **NO** |
| **Mistral 7B** | 14.5 GB | **NO** | **NO** |
| **LLaMA 2 7B Q4_K_M** | 4.08 GB | **NO** | **NO** |
| LoRA Adapter (Rank 8) | 5-20 MB | **NO** directly | Theoretically (~2K-5K updates) — **impractical** |
| LoRA Adapter (Rank 16) | 20-100 MB | **NO** | **NO** — impractical |
| `config.json` | 1-5 KB | **YES** ✅ | N/A |
| `tokenizer_config.json` | 1-10 KB | **YES** (multi-update) ✅ | **YES** ✅ |
| System prompt | 500 B - 10 KB | **YES** ✅ | **YES** ✅ |
| Agent instruction set | 10-100 KB | Multi-update possible ✅ | **YES** ✅ |
| Model hash/fingerprint | 32-64 bytes | **YES** ✅ | N/A |
| License terms (JSON) | 500 B - 5 KB | **YES** ✅ | N/A |
| Encryption keys (wrapped) | 32-256 bytes | **YES** ✅ | N/A |
| Embedding (single, 768-dim) | 3,072 bytes | **YES** ✅ | N/A |

### 1.3 Verdict: Can VerusID Store an LLM/SLM?

**Direct storage of full model weights: NO.** Even the smallest quantized SLM (TinyLlama Q2_K at ~600MB) is ~200,000x larger than what a single contentmultimap update can hold. Even with aggregated updates, storing 600MB would require ~120,000-300,000 identity updates at ~2-5KB each — this is economically and technically infeasible.

**However, VerusID is ideal as the model's *identity, license, and access-control container*:**

- ✅ Store model metadata (config, architecture description, version)
- ✅ Store encrypted decryption keys for off-chain model storage
- ✅ Store content hashes (SHA-256/Blake2b) to verify model integrity
- ✅ Store licensing terms and pricing in structured VDXF format
- ✅ Store agent system prompts and instructions (~10-100KB via multiple updates)
- ✅ Store small LoRA adapter configs (adapter_config.json at 1-3 KB)
- ✅ Store `CrossChainDataRef` / `CURLRef` pointers to off-chain storage (IPFS, Arweave, S3)
- ✅ Store digital signatures proving model provenance and authenticity
- ✅ Store access credentials (encrypted with Sapling z-address encryption)

---

## 2. VerusID as Security Layer for UAI Swarm Intelligence

### 2.1 Architecture: Identity-Based Agent Authentication

Each UAI swarm agent gets assigned a VerusID, creating a **cryptographically verifiable identity** for every agent in the swarm:

```
UAI Swarm Architecture with VerusID:

┌──────────────────────────────────────────────────────────────────┐
│                    UAI Cluster Intelligence                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Agent Alpha  │  │ Agent Beta  │  │ Agent Gamma │   ...        │
│  │ VerusID:     │  │ VerusID:    │  │ VerusID:    │              │
│  │ UAIAlpha@    │  │ UAIBeta@    │  │ UAIGamma@   │              │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │              │
│  │ │ contentmultimap          │ │  │ │ contentmultimap          │ │
│  │ │ - role     │ │  │ │ - role     │ │  │ │ - role     │ │     │
│  │ │ - perms    │ │  │ │ - perms    │ │  │ │ - perms    │ │     │
│  │ │ - config   │ │  │ │ - config   │ │  │ │ - config   │ │     │
│  │ │ - pubkeys  │ │  │ │ - pubkeys  │ │  │ │ - pubkeys  │ │     │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │               Swarm Controller VerusID                    │    │
│  │               UAISwarmController@                         │    │
│  │  - Revocation authority over all agent IDs                │    │
│  │  - Recovery authority for disaster recovery               │    │
│  │  - Multisig: requires 2/3 admin signatures                │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Security Features Leveraged

| Verus Feature | UAI Application |
|--------------|-----------------|
| **VerusID Revocation** | Instantly revoke compromised agent access — agent cannot sign or spend |
| **VerusID Recovery** | Recover agent identity to new keys if private keys are compromised |
| **Verus Vault (Timelock)** | Lock agent funds with delay-unlock — gives time to detect/respond to breaches |
| **Multisig** | Require multiple admin VerusIDs to authorize critical agent operations |
| **VerusID Signatures** | Agents sign their outputs/decisions — creates unforgeable audit trail |
| **VDXF Credentials** | `vrsc::identity.credential` — store encrypted API keys, access tokens, capabilities |
| **z-address Privacy** | Agent-to-agent private communication channel via shielded transactions |
| **LoginConsentRequest** | SSID-style authentication for external services accessing UAI agents |
| **Encrypted contentmultimap** | `CDataDescriptor.WrapEncrypted()` using Sapling addresses — only authorized parties can decrypt agent configs |

### 2.3 Agent Authentication Flow

```
External User                    UAI Gateway                   Agent VerusID
     │                               │                              │
     │── LoginConsentRequest ──────> │                              │
     │                               │── getidentity ─────────────>│
     │                               │<── identity + contentmap ───│
     │                               │                              │
     │                               │── Verify user VerusID ──────│
     │                               │   Check permissions in      │
     │                               │   VDXF contentmultimap      │
     │                               │                              │
     │                               │── signLoginConsentResponse ─│
     │<── Authenticated Session ─────│                              │
     │                               │                              │
     │── Agent Request ──────────────│                              │
     │                               │── Verify agent VerusID ─────│
     │                               │   Check agent is active     │
     │                               │   (not revoked/locked)      │
     │                               │                              │
     │<── Signed Agent Response ─────│                              │
```

### 2.4 VDXF Keys for Agent Security

Define custom VDXF keys for the UAI namespace:

```
vrsc::uai.agent.role              → Agent role (researcher, coder, analyst, etc.)
vrsc::uai.agent.permissions       → Capability bitmask or permission set
vrsc::uai.agent.version           → Agent software version
vrsc::uai.agent.model.hash        → SHA-256 of the model weights this agent uses
vrsc::uai.agent.config.encrypted  → Encrypted agent configuration (Sapling-encrypted)
vrsc::uai.agent.endpoint          → API endpoint URL for this agent
vrsc::uai.agent.health.lastseen   → Timestamp of last health check
vrsc::uai.swarm.membership        → Reference to swarm controller VerusID
vrsc::uai.license.tier            → License tier (free/pro/enterprise)
vrsc::uai.license.expiry          → License expiration block height or timestamp
```

---

## 3. Monetizing Specialized Agents via VerusID

### 3.1 Monetization Architecture

VerusID enables a **decentralized, trustless marketplace** for selling access to specialized UAI agents:

```
┌─────────────────────────────────────────────────────────────┐
│                UAI Agent Marketplace (On-Chain)               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Agent Product VerusID: "UAICodeAgent@"                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ contentmultimap:                                      │    │
│  │   vrsc::uai.product.name = "Code Assistant Pro"       │    │
│  │   vrsc::uai.product.description = "..."               │    │
│  │   vrsc::uai.product.tier = "enterprise"               │    │
│  │   vrsc::uai.product.price.vrsc = 50                   │    │
│  │   vrsc::uai.product.price.monthly = 200               │    │
│  │   vrsc::uai.product.model.hash = 0xABCD...           │    │
│  │   vrsc::uai.product.capabilities = [...]              │    │
│  │   vrsc::uai.product.sla.uptime = 99.9                │    │
│  │   vrsc::uai.product.api.docs.ref = CURLRef(...)      │    │
│  │   vrsc::uai.product.access.key.encrypted = EncData   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  Buyer Workflow:                                              │
│  1. Browse agent products via getidentitycontent              │
│  2. Purchase via VerusID Marketplace (makeoffer/takeoffer)    │
│  3. Receive license VerusID (subID of product)                │
│  4. License VerusID contentmultimap contains encrypted        │
│     access credentials (decryptable only by buyer)            │
│  5. Access agent API using VerusID SSID login                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Pricing Models via VerusID

| Model | Implementation |
|-------|---------------|
| **One-time Purchase** | `makeoffer` / `takeoffer` — buyer receives a license VerusID (subID) with encrypted access keys. Transfer of VerusID = transfer of license |
| **Subscription** | License VerusID has `vrsc::uai.license.expiry` set to a future block height. Agent checks expiry before granting access. Renewal = `updateidentity` to extend expiry |
| **Pay-per-Use** | Agent verifies incoming payment (VRSC or basket currency) before each invocation. `VerusPayInvoice` for programmatic billing |
| **Tiered Access** | `vrsc::uai.license.tier` in buyer's license VerusID determines rate limits, model quality, features. Upgrade = updateidentity |
| **Revenue Sharing** | Use Verus basket currencies — create a fractional currency backed by VRSC where agent operators hold reserves. Agent revenue flows to basket, holders earn proportionally |
| **Staking Access** | User stakes VRSC on a specific VerusID; staking weight determines access tier. Verus Vault locks ensure commitment |

### 3.3 Marketplace Flow (Technical)

```python
# Seller: Register an agent product
updateidentity '{
    "name": "UAICodeAgent",
    "contentmultimap": {
        "vrsc::uai.product.name": "Code Assistant Pro v2",
        "vrsc::uai.product.price.vrsc": "50",
        "vrsc::uai.product.model.hash": "<sha256_of_model_weights>",
        "vrsc::uai.product.capabilities": ["code_gen", "debug", "review", "refactor"],
        "vrsc::uai.product.access.encrypted": "<sapling_encrypted_api_key>"
    }
}'

# Buyer: Make offer for a license subID
makeoffer '{
    "changeaddress": "<buyer_verusid>",
    "offer": { "currency": "VRSC", "amount": 50 },
    "for": { "name": "buyer_license.UAICodeAgent", "parent": "<UAICodeAgent_id>" }
}'

# Seller: Accept and create license subID for buyer
# License subID contentmultimap contains:
#   - Encrypted access credentials (only buyer can decrypt)
#   - License tier, expiry, rate limits
#   - Reference to agent endpoint

# Buyer: Authenticate to agent
# Use VerusID SSID LoginConsentRequest
# Agent verifies buyer's license subID is valid and not expired
# Agent checks license tier for rate limiting
# Access granted
```

### 3.4 Agent Catalog Discovery

```python
# Anyone can discover available agents:
getidentitycontent '{"name": "UAICodeAgent@", "key": "vrsc::uai.product.name"}'
getidentitycontent '{"name": "UAICodeAgent@", "key": "vrsc::uai.product.price.vrsc"}'
getidentitycontent '{"name": "UAICodeAgent@", "key": "vrsc::uai.product.capabilities"}'

# Or browse all UAI products via multimap key index:
# All identities with vrsc::uai.product.* keys are discoverable
```

---

## 4. LLM/SLM IP Protection via Verus Technology

### 4.1 The Hybrid Storage Architecture

Since full model weights cannot fit on-chain, the solution is a **hybrid architecture** where VerusID acts as the **trust anchor** and off-chain systems store the bulk data:

```
┌─────────────────────────────────────────────────────────┐
│                 On-Chain (VerusID)                        │
│                                                          │
│  ┌─ Model Identity VerusID ──────────────────────────┐  │
│  │                                                    │  │
│  │  contentmultimap:                                  │  │
│  │    vrsc::uai.model.name     = "UAI-Code-7B"       │  │
│  │    vrsc::uai.model.version  = "2.1.0"             │  │
│  │    vrsc::uai.model.hash     = SHA256(weights)     │  │
│  │    vrsc::uai.model.arch     = "llama-7b-lora"     │  │
│  │    vrsc::uai.model.license  = "commercial"        │  │
│  │    vrsc::uai.model.owner    = VerusID_of_creator  │  │
│  │    vrsc::uai.model.sig      = [VerusID Signature] │  │
│  │    vrsc::uai.model.created  = block_height        │  │
│  │                                                    │  │
│  │  Encrypted Storage Keys (CDataDescriptor):         │  │
│  │    vrsc::uai.model.storage.key.encrypted           │  │
│  │      → Sapling-encrypted AES-256 key               │  │
│  │      → Only owner's z-address can decrypt           │  │
│  │                                                    │  │
│  │  Off-Chain References (CrossChainDataRef/CURLRef): │  │
│  │    vrsc::uai.model.storage.primary                 │  │
│  │      → CURLRef("ipfs://Qm...")                     │  │
│  │    vrsc::uai.model.storage.backup                  │  │
│  │      → CURLRef("arweave://tx/...")                  │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Provenance Chain:                                       │
│    Block 1000: Model created, initial hash registered    │
│    Block 1500: LoRA fine-tune v2, new hash, signed       │
│    Block 2000: License granted to Buyer1 (subID)         │
│    Block 2500: Model updated v2.1, old hash invalidated  │
│    (All immutably recorded on Verus blockchain)          │
│                                                          │
└─────────────────────────────────────────────────────────┘
            │                    │
            │ CrossChainDataRef  │ Encrypted download key
            │ (URL pointer)      │ (Sapling-encrypted)
            ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                Off-Chain Storage Layer                    │
│                                                          │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐  │
│  │    IPFS      │ │   Arweave    │ │  Private S3/R2  │  │
│  │              │ │              │ │                  │  │
│  │  Encrypted   │ │  Permanent   │ │  Hot storage     │  │
│  │  model       │ │  encrypted   │ │  for active      │  │
│  │  weights     │ │  backup      │ │  serving         │  │
│  │  (AES-256)   │ │  (AES-256)   │ │  (AES-256)       │  │
│  └─────────────┘ └──────────────┘ └─────────────────┘  │
│                                                          │
│  Model files AES-256 encrypted at rest                   │
│  Decryption key ONLY available via VerusID               │
│  (Sapling z-address encryption in contentmultimap)       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.2 IP Protection Mechanisms

| Protection Layer | Verus Technology | How It Works |
|-----------------|-----------------|--------------|
| **Provenance Proof** | VerusID Signatures + contentmultimap history | Model creator signs the model hash with their VerusID. Immutably recorded on blockchain with timestamp. Proves who created what and when |
| **Integrity Verification** | SHA-256/Blake2b hash in contentmultimap | Anyone can verify a model file matches the hash registered on-chain. Tampered models are detectable |
| **Access Control** | Encrypted decryption keys via `CDataDescriptor.WrapEncrypted()` | Model files are AES-256 encrypted. The decryption key is stored on-chain, Sapling-encrypted to the license holder's z-address. Only the authorized buyer can decrypt |
| **License Enforcement** | VerusID subIDs + expiry fields | License VerusID can be revoked by the seller (revocation authority). Expired licenses are verifiable on-chain. Agents check license validity before serving |
| **Transfer Tracking** | VerusID Marketplace (makeoffer/takeoffer) | All license transfers are on-chain, creating an auditable chain of custody |
| **Revocation** | VerusID revocation authority | Seller retains revocation authority over license subIDs. Can revoke if terms violated. Revocation is instant and verifiable |
| **Anti-Piracy Watermarking** | VerusID per-buyer unique LoRA delta | Each buyer gets a unique micro-LoRA with buyer's VerusID embedded. If model leaks, watermark traces back to the leaker |
| **Vault Protection** | Verus Vault timelock | Lock model's master VerusID with a delay. Even if master keys are stolen, attacker must wait for unlock period — giving time to revoke and recover |
| **Cross-Chain Proof** | PBaaS cross-chain verification | Model provenance proofs verifiable across all PBaaS chains, not locked to a single chain |

### 4.3 Encryption Details (From Source Code)

The Verus codebase provides multiple encryption mechanisms suitable for IP protection:

**1. `CDataDescriptor.WrapEncrypted()` (vdxf.h)**
- Uses `libzcash::SaplingPaymentAddress` for encryption
- Data is wrapped in a `CVDXF_Data` tagged structure, then encrypted
- Supports Sapling viewing keys (IVK), ephemeral public keys (EPK), and symmetric shared keys (SSK)
- Flags: `FLAG_ENCRYPTED_DATA`, `FLAG_SALT_PRESENT`, `FLAG_ENCRYPTION_PUBLIC_KEY_PRESENT`

**2. `CVDXFEncryptor` (vdxf.h)**
- Dedicated encryption class using **ChaCha20-Poly1305** (`ENCRYPTION_CHACHA20POLY1305`)
- 16-byte cipher overhead (`CHACHA20POLY1305_CIPHEROVERHEAD`)
- Stores encryption type, key data (EPK), and cipher data
- Suitable for encrypting small-to-medium data chunks

**3. Sapling z-address based key exchange**
- Private z-addresses on VerusID enable encrypted peer-to-peer key exchange
- Seller encrypts model decryption key to buyer's z-address
- Only buyer's spending key can decrypt
- Forward secrecy via ephemeral keys

### 4.4 Security Rating

| Threat | Protection Level | Mechanism |
|--------|-----------------|-----------|
| Model theft during storage | **Very High** | AES-256 encryption + keys only in Sapling-encrypted contentmultimap |
| Unauthorized access | **Very High** | VerusID LoginConsent + license verification + revocation |
| Model tampering | **Very High** | On-chain hash verification, VerusID signatures |
| License forgery | **Very High** | VerusID subIDs are blockchain-native, cannot be counterfeited |
| Key compromise | **High** | Verus Vault timelocks + revocation/recovery authorities |
| Provenance disputes | **Very High** | Immutable blockchain timestamps + VerusID signatures |
| Piracy/redistribution | **Medium-High** | Per-buyer watermarking + license tracking, revocation |
| Model extraction from inference | **Medium** | Server-side inference only, no model download (standard industry practice) |

---

## 5. Verus Network Capabilities for UAI Integration

### 5.1 Comprehensive Capability Matrix

| Verus Capability | UAI Application | Integration Priority |
|-----------------|-----------------|---------------------|
| **VerusID** | Agent identity, authentication, authorization | **Critical** |
| **VDXF contentmultimap** | Agent config, model metadata, license terms, access keys | **Critical** |
| **Encrypted contentmultimap** | IP protection, encrypted access credentials | **Critical** |
| **VerusID Signatures** | Agent output verification, model provenance | **High** |
| **VerusID Marketplace** | Agent license sale/transfer (makeoffer/takeoffer) | **High** |
| **VRPC** | Programmatic blockchain interaction from agents | **Critical** |
| **LoginConsentRequest** | User authentication to UAI services | **High** |
| **VerusPay** | Payment processing for agent usage | **High** |
| **Basket Currencies** | Revenue sharing, fractional ownership of agent pools | **Medium** |
| **PBaaS** | Launch dedicated UAI chain for high-throughput agent operations | **Medium** |
| **Verus Vault** | Protect master keys with timelocks | **High** |
| **Revocation/Recovery** | Emergency agent shutdown, key compromise response | **Critical** |
| **z-addresses** | Private agent communication, encrypted key exchange | **High** |
| **Cross-Chain Bridge** | UAI services accessible from Ethereum and other PBaaS chains | **Medium** |
| **CURLRef in contentmultimap** | Reference off-chain model storage (IPFS, Arweave) | **High** |
| **CrossChainDataRef** | Reference data across Verus PBaaS chains | **Medium** |
| **SubIDs** | Per-customer license identities under product VerusID | **High** |
| **Currency Launches** | Create UAI utility token as PBaaS currency | **Medium** |
| **Referral System** | Incentivize agent marketplace growth (20 VRSC per referral) | **Medium** |

### 5.2 UAI-Specific PBaaS Chain Consideration

For high-frequency agent operations, launching a **dedicated UAI PBaaS chain** provides:

- Lower identity costs (configurable, not fixed at 100 VRSC)
- Higher throughput for agent state updates
- Custom consensus parameters optimized for agent workloads
- Still fully interoperable with Verus mainnet (provably connected)
- Agents on UAI chain can interact with Verus DeFi via cross-chain bridge
- Custom fee structures for agent marketplace transactions

---

## 6. Implementation Architecture

### 6.1 Recommended Hybrid System

```
┌────────────────────────────────────────────────────────────────┐
│                    UAI Cluster Intelligence                      │
│                                                                  │
│  ┌───────────────── Verus Layer (On-Chain) ──────────────────┐  │
│  │                                                            │  │
│  │  VerusID Registry:                                         │  │
│  │    UAICluster@          → Master swarm controller          │  │
│  │    UAIMarketplace@      → Agent marketplace root           │  │
│  │    CodeAgent.UAI@       → Product listing (subID)          │  │
│  │    ResearchAgent.UAI@   → Product listing (subID)          │  │
│  │    buyer1.CodeAgent.UAI@ → License (sub-subID)             │  │
│  │                                                            │  │
│  │  On-Chain Data:                                            │  │
│  │    Model hashes, signatures, license terms, encrypted      │  │
│  │    access keys, agent configs, pricing, SLA terms,         │  │
│  │    provenance proofs, capability declarations              │  │
│  │                                                            │  │
│  │  DeFi Integration:                                         │  │
│  │    Payment processing, basket currency revenue sharing,    │  │
│  │    staking-based access tiers                              │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                    VRPC Interface                                  │
│                              │                                    │
│  ┌───────────────── Application Layer ───────────────────────┐  │
│  │                                                            │  │
│  │  UAI Agent Runtime:                                        │  │
│  │    - Verifies caller license via VerusID                   │  │
│  │    - Loads model from encrypted off-chain storage          │  │
│  │    - Decrypts using key from VerusID contentmultimap       │  │
│  │    - Serves inference requests                             │  │
│  │    - Signs outputs with agent VerusID                      │  │
│  │    - Logs usage for billing                                │  │
│  │                                                            │  │
│  │  Model Storage Manager:                                    │  │
│  │    - Encrypts models (AES-256-GCM)                         │  │
│  │    - Uploads to IPFS / Arweave / S3                        │  │
│  │    - Registers hashes on VerusID                           │  │
│  │    - Manages per-buyer watermarked variants                │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 Implementation Tasks

#### Phase 1: VerusID Agent Identity System (Weeks 1-3)
- [ ] Define VDXF key namespace for UAI (`vrsc::uai.*`)
- [ ] Create master swarm controller VerusID
- [ ] Implement agent VerusID registration on swarm join
- [ ] Build VerusID-based agent authentication module
- [ ] Implement revocation monitoring (detect revoked agents)
- [ ] Add Verus Vault protection for master controller keys

#### Phase 2: IP Protection Infrastructure (Weeks 4-6)
- [ ] Build model encryption pipeline (AES-256-GCM)
- [ ] Implement model hash registration on VerusID
- [ ] Build Sapling-encrypted key storage in contentmultimap
- [ ] Implement model integrity verification against on-chain hash
- [ ] Create provenance signing workflow (VerusID signatures)
- [ ] Build off-chain storage integration (IPFS + CURLRef registration)

#### Phase 3: Agent Marketplace (Weeks 7-10)
- [ ] Create product VerusID registration system
- [ ] Implement subID-based licensing (license as VerusID)
- [ ] Build VerusID Marketplace integration (makeoffer/takeoffer)
- [ ] Implement encrypted credential delivery via Sapling z-addresses
- [ ] Build license verification module (expiry, tier, revocation checks)
- [ ] Implement VerusPay integration for pay-per-use billing
- [ ] Create agent discovery API (browse products via contentmultimap queries)

#### Phase 4: Advanced Features (Weeks 11-14)
- [ ] Implement per-buyer LoRA watermarking
- [ ] Build basket currency for revenue sharing
- [ ] Evaluate and prototype UAI PBaaS chain
- [ ] Implement cross-chain license verification
- [ ] Build mobile wallet integration for marketplace (extends #8)
- [ ] Create agent reputation system via VerusID attestations

---

## 7. Acceptance Criteria

- [ ] Agent VerusID registration and authentication working end-to-end
- [ ] Model hash registration and verification against VerusID contentmultimap
- [ ] Encrypted access key storage/retrieval via Sapling z-address encryption
- [ ] License VerusID (subID) creation and verification flow
- [ ] VerusID Marketplace buy/sell flow for agent access
- [ ] Model provenance signatures verifiable via VerusID
- [ ] Agent revocation immediately blocks access
- [ ] Verus Vault timelock protection on master controller
- [ ] VRPC-based programmatic integration with Verus daemon ≥ v1.2.14-2
- [ ] Off-chain model storage with CURLRef/CrossChainDataRef pointers
- [ ] Pay-per-use and subscription billing via VerusPay
- [ ] Documentation and API reference for marketplace integration

---

## 8. Key Technical Findings Summary

### Q: Can VerusID contentmultimap store an LLM/SLM?
**A: No for full weights. Yes for everything else.** The `MAX_SCRIPT_ELEMENT_SIZE_IDENTITY` of 3,073 bytes per transaction output, and even aggregated across multiple updates, makes storing multi-GB model weights on-chain infeasible. However, VerusID is the *perfect* control plane: metadata, hashes, encrypted keys, license terms, small configs, and off-chain storage references all fit comfortably.

### Q: How secure is Verus for LLM IP protection?
**A: Very high.** The combination of Sapling z-address encryption (ChaCha20-Poly1305), immutable blockchain provenance, VerusID signatures, revocation/recovery, and Verus Vault timelocks creates a multi-layered security system. The weakest link is standard industry risk (model extraction from inference), not the Verus layer.

### Q: Can VerusID monetize agents?
**A: Exceptionally well.** The existing VerusID Marketplace (makeoffer/takeoffer), subID licensing, encrypted credential delivery, VerusPay invoicing, and basket currency revenue sharing provide a complete monetization stack — all decentralized, peer-to-peer, with no middlemen.

### Q: What about LoRA adapters specifically?
**A: Small LoRA adapters (5-20 MB, Rank 8) theoretically could be stored via thousands of identity updates, but this is impractical and expensive.** The recommended approach is the same hybrid model: store the LoRA on IPFS/Arweave encrypted, register the hash and encrypted decryption key on VerusID.

---

## 9. References

- **Issue #5:** [Verus Blockchain Specialist Agent](https://github.com/Pikkati/UAI_Cluster_Intelligence/issues/5)
- **Issue #8:** [Verus Mobile Wallet Integration & v1.2.14-2](https://github.com/Pikkati/UAI_Cluster_Intelligence/issues/8)
- **VerusID Documentation:** https://docs.verus.io/verusid/
- **VDXF Specification:** https://docs.verus.io/vdxf/
- **VerusID Marketplace:** https://docs.verus.io/verusid/#marketplace
- **Verus Source (identity.h):** https://github.com/VerusCoin/VerusCoin/blob/main/src/pbaas/identity.h
- **Verus Source (vdxf.h):** https://github.com/VerusCoin/VerusCoin/blob/main/src/pbaas/vdxf.h
- **CDataDescriptor Encryption:** https://github.com/VerusCoin/VerusCoin/blob/main/src/pbaas/vdxf.h#L997-L1072
- **CVDXFEncryptor (ChaCha20):** https://github.com/VerusCoin/VerusCoin/blob/main/src/pbaas/vdxf.h#L864-L927
- **MAX_SCRIPT_ELEMENT_SIZE_IDENTITY:** https://github.com/VerusCoin/VerusCoin/blob/main/src/script/script.h#L34

---

**Labels:** `agent-integration`, `blockchain`, `verus`, `security`, `monetization`, `llm-ip-protection`, `architecture`
