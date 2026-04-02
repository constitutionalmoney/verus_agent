# Recreating Yuma Consensus & Emission Distribution on Verus

> **Date**: March 2026  
> **Prepared for**: Mark Smith
> **Status**: Detailed Implementation Design  
> **Prerequisite**: [Rebuilding Bittensor on Verus — Architecture Report](BITTENSOR_ON_VERUS_ARCHITECTURE_REPORT.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Bittensor's Yuma Consensus — How It Works](#2-bittensors-yuma-consensus--how-it-works)
3. [Bittensor's Emission Distribution — How It Works](#3-bittensors-emission-distribution--how-it-works)
4. [The Verus Architecture: Three-Layer Design](#4-the-verus-architecture-three-layer-design)
5. [Layer 1 — On-Chain Data Substrate](#5-layer-1--on-chain-data-substrate)
6. [Layer 2 — Off-Chain Consensus Computation](#6-layer-2--off-chain-consensus-computation)
7. [Layer 3 — On-Chain Settlement & Verification](#7-layer-3--on-chain-settlement--verification)
8. [Multi-Party Orchestrator Design](#8-multi-party-orchestrator-design)
9. [Emission Distribution on Verus](#9-emission-distribution-on-verus)
10. [VDXF Schema Specification](#10-vdxf-schema-specification)
11. [Yuma Consensus Algorithm — Full Implementation](#11-yuma-consensus-algorithm--full-implementation)
12. [Epoch Lifecycle — End-to-End Flow](#12-epoch-lifecycle--end-to-end-flow)
13. [Auditing & Dispute Resolution](#13-auditing--dispute-resolution)
14. [Comparison: On-Chain vs Off-Chain Consensus](#14-comparison-on-chain-vs-off-chain-consensus)
15. [Security Analysis](#15-security-analysis)
16. [Implementation Priorities](#16-implementation-priorities)

---

## 1. Executive Summary

Bittensor runs Yuma Consensus **on-chain** inside Substrate pallets — Rust code executing Yuma's matrix algebra directly in block validation. Verus has no smart contract VM, so the same algorithm cannot run natively on-chain. This is not a limitation to work around — it's an opportunity to build something **more transparent, auditable, and upgradeable**.

The design presented here uses a **three-layer architecture**:

| Layer | Location | Purpose |
|-------|----------|---------|
| **Layer 1: Data Substrate** | On-chain ( UAI-Tensor PBaaS) | Store all consensus inputs — weight vectors, stakes, neuron registry — as signed VDXF data in VerusID contentmultimaps |
| **Layer 2: Consensus Computation** | Off-chain (multi-party orchestrators) | Run Yuma Consensus math — deterministic algorithm over on-chain inputs — producing emission vectors |
| **Layer 3: Settlement** | On-chain ( UAI-Tensor PBaaS) | Execute emission payments via multisig `sendcurrency`, publish results for auditability |

The critical insight: because Layer 2 runs a **deterministic algorithm** over **publicly visible Layer 1 inputs**, **anyone can independently verify** the results. This makes the off-chain computation trust-minimized — not trustless, but auditable to a degree that exceeds Bittensor's on-chain approach (where verifying Yuma requires running a full Substrate node and understanding Rust pallet internals).

---

## 2. Bittensor's Yuma Consensus — How It Works

### 2.1 What Yuma Consensus Does

Yuma Consensus is Bittensor's mechanism for converting **subjective validator opinions** (weight vectors) into **objective emission distributions** (who gets paid how much). It runs once per **tempo** (~360 blocks, ~72 minutes on Bittensor's 12-second blocks).

### 2.2 Inputs

| Input | Source | Description |
|-------|--------|-------------|
| **Weight matrix W** | Validators | Each validator `i` submits a weight vector `W[i]` scoring all miners `j` |
| **Stake vector S** | Blockchain state | TAO staked by or delegated to each validator |
| **Bond matrix B_old** | Previous epoch | Exponential moving average of historical bonds |
| **Hyperparameters** | Subnet config | `kappa` (clipping threshold), `bond_penalty` (penalty factor), `liquid_alpha` (EMA rate) |

### 2.3 Algorithm Steps

The Yuma Consensus algorithm executes these steps in order:

**Step 1 — Stake-Weighted Rank**
```
# Normalize stakes to sum to 1
S_norm = S / sum(S)

# Compute stake-weighted rank for each miner
R[j] = Σ_i (S_norm[i] × W[i][j])
```
Each miner's rank `R[j]` is the stake-weighted average of all validator scores for that miner. Validators with more stake have proportionally more influence.

**Step 2 — Consensus Vector**
```
# For each miner j, compute the consensus (median-like) score
# Only count validators who gave positive weight to miner j
C[j] = stake-weighted median of {W[i][j] for all i where W[i][j] > 0}
```
The consensus vector `C` represents what the "majority" of stake-weighted validators agree a miner's performance is.

**Step 3 — Clipping (Penalize Out-of-Consensus Validators)**
```
# For each validator i, for each miner j:
W_clipped[i][j] = min(W[i][j], C[j] × kappa)
```
This is the core anti-gaming mechanism. If a validator's weight for a miner is far above the consensus (suggesting collusion or manipulation), the weight is clipped down to `kappa × consensus`. Validators who consistently set outlier weights receive fewer emissions themselves.

**Step 4 — Bonds**
```
# Compute current bonds from clipped weights
B_current[i][j] = S_norm[i] × W_clipped[i][j]

# EMA (Exponential Moving Average) with previous bonds
B_new[i][j] = alpha × B_current[i][j] + (1 - alpha) × B_old[i][j]
```
Bonds represent a validator's accumulated "investment" in each miner. The EMA smooths bonds over time — bonds grow slowly but decay slowly, preventing validators from rapidly shifting all emissions to a new miner.

**Step 5 — Emission Computation**
```
# Validator dividends (from bonds)
D[i] = Σ_j (B_new[i][j] × R[j])

# Miner incentive
I[j] = R[j] - Σ_i D[i][j]

# Total emission pool for this tempo
E_total = block_reward × tempo_blocks × subnet_emission_share

# Split into validator and miner pools
E_validators = E_total × validator_fraction  # typically 41%
E_miners = E_total × miner_fraction          # typically 41%
E_owner = E_total × owner_fraction            # typically 18%

# Per-miner emission
emission_miner[j] = I[j] / sum(I) × E_miners

# Per-validator emission
emission_validator[i] = D[i] / sum(D) × E_validators
```

### 2.4 Key Design Properties

| Property | Why It Matters |
|----------|---------------|
| **Stake weighting** | Validators with more skin-in-the-game have more influence |
| **Clipping** | Prevents validators from inflating scores for colluding miners |
| **Bond EMA** | Prevents rapid emission shifting — forces long-term commitment |
| **Determinism** | Same inputs always produce same outputs — verifiable |
| **Symmetry** | Both miners and validators earn — incentivizes participation on both sides |

### 2.5 What Clipping Actually Prevents

Without clipping, a validator with 30% of total stake could direct 100% of their influence to a single colluding miner. With clipping (kappa ≈ 0.5):
- If consensus says miner `j` deserves a score of 0.1, the colluding validator's weight is clipped from (say) 0.9 to max 0.05 (0.1 × kappa)
- The validator's own emissions also decrease because their clipped weights produce lower bond returns
- This creates a double punishment: the colluding miner gets fewer emissions AND the colluding validator earns less

---

## 3. Bittensor's Emission Distribution — How It Works

### 3.1 Block-Level Emission

Bittensor emits approximately **1 TAO per block** (12-second blocks), yielding ~7,200 TAO per day. This emission halves approximately every 4 years (10.5M blocks), mirroring Bitcoin's halving schedule. Total max supply: 21,000,000 TAO.

### 3.2 Subnet Emission Share (Dynamic TAO)

Since November 2024, Bittensor uses **Dynamic TAO (dTAO)** to determine each subnet's share of total emissions. Each subnet has an **alpha token** (α) with an automated market maker (AMM) pool connecting it to TAO.

```
emission_share[subnet_k] = f(net_tao_inflow[subnet_k])
```

The key mechanisms:
- **Alpha tokens**: Each subnet mints its own token (e.g., α_1, α_2, ..., α_64)
- **AMM pools**: Each alpha has a TAO ↔ alpha pool determining its price
- **Net inflow**: TAO flowing into a subnet's pool (buying alpha) relative to outflow (selling alpha) determines emission share
- **Market signal**: Subnets producing valuable AI work attract stakers (TAO inflow → higher emission share); bad subnets lose stakers (TAO outflow → lower emission share)

### 3.3 Emission Distribution Per Tempo

Each tempo (72 minutes), the subnet's accumulated emissions are distributed:

```
┌─────────────────────────────────────────────────────────────┐
│               EMISSION DISTRIBUTION PER TEMPO                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Total Subnet Emission (E_total)                            │
│  ├── 18% → Subnet Owner                                    │
│  ├── 41% → Miners (proportional to Yuma incentive scores)   │
│  └── 41% → Validators + Stakers                            │
│       ├── Validator take (configurable, default 18%)        │
│       └── Remaining → Delegated stakers (pro-rata)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Flow-Based vs Fixed Emission

Prior to Dynamic TAO, emission shares were set by **root network validators** voting — a small group of powerful validators decided which subnets got funding. Dynamic TAO replaced this with market-driven emission allocation, where capital flows (staking/unstaking into subnet alpha tokens) determine shares. This is more decentralized and responsive.

### 3.5 Validator-to-Staker Distribution

Validators receive 41% of subnet emissions, but they share most of this with their delegated stakers:
1. Validator keeps a **"take"** (default 18%, configurable per validator)
2. Remaining (82%) is distributed to stakers proportional to their delegated TAO
3. Stakers can switch validators at any time (subject to AMM slippage)

---

## 4. The Verus Architecture: Three-Layer Design

### 4.1 Why Three Layers?

Bittensor collapses everything into one layer — all data storage, consensus computation, and emission payments happen on-chain in Substrate pallets. This is elegant but:
- Expensive (computation consumes block space)
- Opaque (verifying requires running a Substrate node)
- Rigid (upgrading consensus requires a runtime upgrade / hard fork)

The Verus design separates concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  LAYER 1: ON-CHAIN DATA SUBSTRATE                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Validator weight vectors (VDXF contentmultimap)       │ │
│  │ • Stake amounts (UTXO balances on VerusIDs)             │ │
│  │ • Neuron registry (SubIDs under subnet namespace)       │ │
│  │ • Hyperparameters (subnet config in namespace ID)       │ │
│  │ • All data signed by VerusID (non-repudiation)          │ │
│  │ • MMR proofs ensure tamper evidence                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ↕                                   │
│  LAYER 2: OFF-CHAIN CONSENSUS COMPUTATION                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Multiple independently-run orchestrators              │ │
│  │ • Read all Layer 1 inputs from chain                    │ │
│  │ • Execute deterministic Yuma Consensus algorithm        │ │
│  │ • Produce emission vectors (who gets how much)          │ │
│  │ • Compare results across orchestrators (must agree)     │ │
│  │ • Sign results with orchestrator VerusIDs               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ↕                                   │
│  LAYER 3: ON-CHAIN SETTLEMENT & VERIFICATION                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Multisig sendcurrency for emission payments           │ │
│  │ • Published epoch results (VDXF on orchestrator SubID)  │ │
│  │ • Input hash for independent verification               │ │
│  │ • Bond state snapshots                                  │ │
│  │ • Anyone can re-run computation to audit                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Trust Model

| Actor | What They Must Trust | What They Can Verify |
|-------|---------------------|---------------------|
| **Miner** | That orchestrators compute Yuma fairly | Read all inputs, re-run algorithm, compare with published results |
| **Validator** | That their weight submission was included | Verify their SubID update is in the block, check input hash |
| **Staker** | That emissions are distributed correctly | Read epoch results, verify sendcurrency transactions on-chain |
| **Auditor** | Nothing — fully verifiable | Download all inputs, re-run Yuma, compare with all outputs |
| **Orchestrator** | That other orchestrators are honest | Multisig requires agreement; disagreement triggers public audit |

---

## 5. Layer 1 — On-Chain Data Substrate

### 5.1 Weight Vector Submission

Each validator submits their weight vector by updating their SubID's contentmultimap:

```bash
# Validator "alice" in subnet "llm-inference" submits weights for epoch 42
verus -chain= UAI-Tensor updateidentity '{
  "name": "alice.llm-inference",
  "contentmultimap": {
    "vt::weights.vector": [{
      "data": {
        "address": "alice.llm-inference@",
        "label": "epoch-42-weights",
        "createmmr": true,
        "objectdata": {
          "vt::weights.epoch": "42",
          "vt::weights.version": "1.0",
          "vt::weights.data": "[0.15, 0.22, 0.08, 0.31, 0.04, 0.20]",
          "vt::weights.uid_map": "[101, 102, 103, 104, 105, 106]",
          "vt::weights.block_height": "158400"
        }
      }
    }]
  }
}'
```

Key properties:
- **VerusID signed**: The update transaction is signed by Alice's VerusID primary address — no one else can submit weights for Alice
- **MMR proof** (`createmmr: true`): The data is hashed into a Merkle Mountain Range, providing tamper evidence. If anyone modifies the data after the fact, the MMR root changes
- **Block-timestamped**: The transaction is included in a specific block, providing a verifiable timestamp
- **Retrievable**: Anyone can read the weight vector via `getidentitycontent "alice.llm-inference@"`

### 5.2 Stake Visibility

Stake amounts are visible on-chain through standard balance queries:

```bash
# Get VT balance of validator alice
verus -chain= UAI-Tensor getaddressbalance '{"addresses":["alice.llm-inference@"]}'

# Get subnet alpha (LLM) balance
verus -chain= UAI-Tensor getaddressbalance '{"addresses":["alice.llm-inference@"],"currencynames":true}'
```

For delegated stake (stakers who sent alpha tokens to a validator), the orchestrator tracks delegation via:
1. Reading `sendcurrency` transactions to the validator's address
2. Or reading a delegation record from the staker's SubID contentmultimap

```bash
# Staker "bob" records delegation to validator "alice"
verus -chain= UAI-Tensor updateidentity '{
  "name": "bob.llm-inference",
  "contentmultimap": {
    "vt::stake.delegation": [{
      "data": {
        "objectdata": {
          "vt::stake.validator": "alice.llm-inference@",
          "vt::stake.amount": "500",
          "vt::stake.currency": "LLM",
          "vt::stake.block_height": "158200"
        }
      }
    }]
  }
}'
```

### 5.3 Neuron Registry

Every miner and validator is a SubID under the subnet namespace:

```bash
# List all registered neurons in a subnet
verus -chain= UAI-Tensor listidentities '{"launchstate":"active","parent":"llm-inference@"}'
```

Each SubID stores:
- `vt::neuron.type` — "miner" or "validator"
- `vt::neuron.axon` — IP:PORT endpoint (miners only)
- `vt::neuron.uid` — Assigned UID slot number (0–255)
- `vt::neuron.registered_at` — Block height of registration
- `vt::neuron.model_hash` — SHA-256 hash of the ML model being served

### 5.4 Hyperparameters

Subnet hyperparameters are stored on the namespace identity itself:

```bash
verus -chain= UAI-Tensor getidentity "llm-inference@"
# contentmultimap includes:
# vt::subnet.tempo         = "360"      (blocks per epoch)
# vt::subnet.immunity      = "4096"     (blocks before deregistration eligible)
# vt::subnet.max_uids      = "256"      (max miners + validators)
# vt::subnet.validator_slots = "64"     (max validators)
# vt::subnet.miner_slots   = "192"      (max miners)
# vt::subnet.min_stake     = "1000"     (min alpha to validate)
# vt::subnet.kappa         = "0.5"      (clipping threshold)
# vt::subnet.bond_penalty  = "0.65"     (penalty factor for out-of-consensus)
# vt::subnet.alpha         = "0.9"      (bond EMA rate)
# vt::subnet.owner_take    = "0.18"     (owner emission fraction)
# vt::subnet.miner_fraction = "0.41"    (miner emission fraction)
# vt::subnet.validator_fraction = "0.41"(validator emission fraction)
```

### 5.5 Data Integrity Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| **Authenticity** | VerusID signature on every `updateidentity` transaction |
| **Immutability** | Once confirmed in a block, data is permanent (UTXO model) |
| **Timestamping** | Block height and timestamp on every transaction |
| **Tamper evidence** | MMR proofs via `createmmr: true` on data submissions |
| **Non-repudiation** | Only the VerusID owner can update their SubID — proven by signature |
| **Ordered history** | `getidentitycontent` returns data ordered by block height |

---

## 6. Layer 2 — Off-Chain Consensus Computation

### 6.1 The Orchestrator

The consensus orchestrator is a Python service that:
1. Monitors block heights on the  UAI-Tensor chain
2. At each tempo boundary, collects all inputs from Layer 1
3. Runs the deterministic Yuma Consensus algorithm
4. Produces emission vectors
5. Submits results back to Layer 3

### 6.2 Why Off-Chain Is Viable

The Yuma Consensus algorithm is **deterministic** — given the same inputs, it always produces the same outputs. This means:
- If three orchestrators independently read the same on-chain state and run the same algorithm, they **must** get the same results
- If they disagree, at least one has a bug or is malicious — and anyone can determine which by re-running the computation themselves
- The algorithm is pure math (matrix operations), not interactive — it doesn't need to be "live" during execution

### 6.3 Input Collection

```python
async def collect_epoch_inputs(self, epoch_block: int) -> EpochInputs:
    """Collect all inputs for Yuma Consensus from on-chain state."""
    
    # 1. Get all registered validators
    validators = await self.list_subnet_identities(neuron_type="validator")
    
    # 2. Get all registered miners  
    miners = await self.list_subnet_identities(neuron_type="miner")
    
    # 3. For each validator, read their weight vector
    weight_matrix = {}
    for v in validators:
        content = await self.cli.getidentitycontent(
            f"{v.name}.{self.subnet}@",
            heightstart=epoch_block - self.tempo,
            heightend=epoch_block
        )
        weights = self.parse_weight_vector(content)
        if weights and weights.epoch == self.current_epoch:
            weight_matrix[v.uid] = weights
    
    # 4. Get stake for each validator
    stakes = {}
    for v in validators:
        balance = await self.cli.getaddressbalance(
            f"{v.name}.{self.subnet}@",
            currency="LLM"
        )
        delegated = await self.get_delegated_stake(v.name)
        stakes[v.uid] = balance + delegated
    
    # 5. Get previous bond state
    bonds_prev = await self.get_previous_bonds()
    
    # 6. Get hyperparameters
    config = await self.get_subnet_config()
    
    # 7. Compute deterministic hash of all inputs
    input_hash = self.hash_inputs(weight_matrix, stakes, bonds_prev, config)
    
    return EpochInputs(
        epoch=self.current_epoch,
        epoch_block=epoch_block,
        weight_matrix=weight_matrix,
        stakes=stakes,
        bonds_previous=bonds_prev,
        config=config,
        input_hash=input_hash,
        miners=miners,
        validators=validators
    )
```

### 6.4 Computing Input Hash

The **input hash** is the lynchpin of verifiability. It's a deterministic hash over all inputs, using a canonical serialization:

```python
def hash_inputs(self, weights, stakes, bonds, config) -> str:
    """Compute deterministic SHA-256 hash of all Yuma inputs."""
    import hashlib
    import json
    
    # Canonical JSON serialization (sorted keys, no whitespace)
    canonical = json.dumps({
        "weights": {str(k): v for k, v in sorted(weights.items())},
        "stakes": {str(k): float(v) for k, v in sorted(stakes.items())},
        "bonds": {str(k): v for k, v in sorted(bonds.items())},
        "config": {k: str(v) for k, v in sorted(config.items())}
    }, sort_keys=True, separators=(',', ':'))
    
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

If two orchestrators compute different input hashes from the same block range, one of them has a data collection bug. If they compute the same input hash but different emissions, one has an algorithm bug. If both match, the results are correct.

---

## 7. Layer 3 — On-Chain Settlement & Verification

### 7.1 Publishing Results

After computing emissions, the orchestrator publishes the full results on-chain:

```bash
verus -chain= UAI-Tensor updateidentity '{
  "name": "orchestrator.llm-inference",
  "contentmultimap": {
    "vt::epoch.results": [{
      "data": {
        "address": "orchestrator.llm-inference@",
        "label": "epoch-42-results",
        "createmmr": true,
        "objectdata": {
          "vt::epoch.number": "42",
          "vt::epoch.block": "158400",
          "vt::epoch.input_hash": "a3f8c2d1e9b7...sha256...",
          "vt::epoch.emission_total": "180.5",
          "vt::epoch.miner_emissions": "{\"101\":12.5,\"102\":18.3,\"103\":6.1,...}",
          "vt::epoch.validator_emissions": "{\"201\":9.2,\"202\":14.1,...}",
          "vt::epoch.owner_emission": "32.49",
          "vt::epoch.bonds_snapshot": "{...serialized bond matrix...}",
          "vt::epoch.consensus_vector": "[0.15,0.22,0.08,0.31,0.04,0.20]",
          "vt::epoch.rank_vector": "[0.14,0.21,0.09,0.30,0.05,0.21]"
        }
      }
    }]
  }
}'
```

### 7.2 Executing Emission Payments

Payments are executed via `sendcurrency` from the subnet treasury (controlled by multisig):

```bash
# Miner emissions (batch payment)
verus -chain= UAI-Tensor sendcurrency "consensus.llm-inference@" '[
  {"address": "miner101.llm-inference@", "currency": "LLM", "amount": 12.5},
  {"address": "miner102.llm-inference@", "currency": "LLM", "amount": 18.3},
  {"address": "miner103.llm-inference@", "currency": "LLM", "amount": 6.1},
  {"address": "miner104.llm-inference@", "currency": "LLM", "amount": 27.9},
  {"address": "miner105.llm-inference@", "currency": "LLM", "amount": 3.6},
  {"address": "miner106.llm-inference@", "currency": "LLM", "amount": 18.0}
]'

# Validator emissions
verus -chain= UAI-Tensor sendcurrency "consensus.llm-inference@" '[
  {"address": "alice.llm-inference@", "currency": "LLM", "amount": 9.2},
  {"address": "charlie.llm-inference@", "currency": "LLM", "amount": 14.1},
  {"address": "diana.llm-inference@", "currency": "LLM", "amount": 11.8}
]'

# Subnet owner emission
verus -chain= UAI-Tensor sendcurrency "consensus.llm-inference@" '[
  {"address": "llm-inference@", "currency": "LLM", "amount": 32.49}
]'
```

### 7.3 Payment Verification

Every `sendcurrency` transaction is on-chain and verifiable:

```bash
# Anyone can see all payments from the consensus identity
verus -chain= UAI-Tensor getaddresstxids '{"addresses":["consensus.llm-inference@"]}'

# Verify specific payment
verus -chain= UAI-Tensor getrawtransaction "txid" 1
```

### 7.4 Tagged Payments for Epoch Tracking

Using VDXF tags (`vdxftag`), each emission payment can be tagged with the epoch number for tracking:

```bash
verus -chain= UAI-Tensor sendcurrency "consensus.llm-inference@" '[{
  "address": "miner101.llm-inference@",
  "currency": "LLM",
  "amount": 12.5,
  "vdxftag": "xEpoch42TagAddress..."
}]'
```

This allows any participant to query "show me all payments tagged for epoch 42" without parsing every transaction.

---

## 8. Multi-Party Orchestrator Design

### 8.1 Why Multiple Orchestrators?

A single orchestrator is a single point of trust and failure. If Alice runs the only orchestrator, she could:
- Inflate her own emission payments
- Exclude a miner from the calculation
- Use stale or modified weight data

Multiple orchestrators prevent this through **redundancy and agreement**.

### 8.2 Multisig Consensus Identity

The subnet's emission treasury is controlled by a multisig VerusID requiring agreement from multiple orchestrators:

```bash
# Create multisig consensus identity (2-of-3)
verus -chain= UAI-Tensor registeridentity '{
  "name": "consensus.llm-inference",
  "parent": "llm-inference",
  "primaryaddresses": ["AliceRAddr", "BobRAddr", "CarolRAddr"],
  "minimumsignatures": 2
}'
```

This means:
- **Any 2 of 3** orchestrators must sign each emission payment
- A single malicious orchestrator **cannot** steal or misdirect funds
- If all 3 agree, payments execute automatically
- If 2 agree and 1 disagrees, payments still execute (majority rules) — but the disagreement is logged

### 8.3 Orchestrator Agreement Protocol

```
╔══════════════════════════════════════════════════════════════════╗
║                    EPOCH AGREEMENT PROTOCOL                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  T+0: Tempo boundary reached (block height % tempo == 0)        ║
║                                                                  ║
║  T+1: All orchestrators independently:                          ║
║       • Read weight vectors from all validator SubIDs            ║
║       • Read stake balances for all validators                   ║
║       • Read previous bond state                                 ║
║       • Compute input_hash                                       ║
║                                                                  ║
║  T+2: Orchestrators publish their input_hash:                   ║
║       • updateidentity on their own SubID                        ║
║       • "vt::orchestrator.input_hash" = computed hash            ║
║                                                                  ║
║  T+3: Compare input hashes:                                     ║
║       ┌─────────────────────────────────────────────────────┐   ║
║       │ IF all hashes match:                                 │   ║
║       │   → All orchestrators saw the same data             │   ║
║       │   → Proceed to compute emissions                    │   ║
║       │                                                      │   ║
║       │ IF hashes diverge:                                   │   ║
║       │   → At least one orchestrator has stale/wrong data  │   ║
║       │   → Wait additional blocks for chain sync           │   ║
║       │   → Re-collect and compare again                    │   ║
║       │   → If still divergent, flag for manual review      │   ║
║       └─────────────────────────────────────────────────────┘   ║
║                                                                  ║
║  T+4: All orchestrators run Yuma Consensus independently        ║
║       • Same deterministic algorithm over same inputs           ║
║       • Must produce identical emission vectors                  ║
║                                                                  ║
║  T+5: Orchestrators publish emission_hash:                      ║
║       • Hash of the computed emission vector                     ║
║                                                                  ║
║  T+6: Compare emission hashes:                                  ║
║       ┌─────────────────────────────────────────────────────┐   ║
║       │ IF all match:                                        │   ║
║       │   → Sign multisig sendcurrency transaction          │   ║
║       │   → Publish full results on-chain                   │   ║
║       │   → Epoch complete                                  │   ║
║       │                                                      │   ║
║       │ IF mismatch:                                         │   ║
║       │   → Algorithm bug detected in one orchestrator      │   ║
║       │   → Majority (2/3) result wins                      │   ║
║       │   → Disagreeing orchestrator flagged for review     │   ║
║       │   → All inputs + outputs published for audit        │   ║
║       └─────────────────────────────────────────────────────┘   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### 8.4 Orchestrator Incentives

Orchestrators must be incentivized to participate honestly:

| Income | Source | Amount |
|--------|--------|--------|
| Orchestrator fee | Each epoch, a small percentage of emissions | 1-2% of subnet emissions |
| Staking returns | Orchestrators can also be validators/stakers | Normal staking rewards |
| Reputation | Reliable orchestrators attract subnet operator selection | Indirect value |

| Penalty | Trigger | Consequence |
|---------|---------|-------------|
| Disagreement | Producing different results from majority | Flagged on-chain, reputation damage |
| Downtime | Missing an epoch deadline | Replacement orchestrator activated |
| Provable fraud | Publishing results that don't match re-computation | Removed from multisig by subnet owner |

### 8.5 Orchestrator Scaling

| Subnet Size | Recommended Orchestrators | Multisig Threshold |
|-------------|--------------------------|-------------------|
| Small (< 50 neurons) | 3 | 2-of-3 |
| Medium (50-256 neurons) | 5 | 3-of-5 |
| Large (production critical) | 7 | 5-of-7 |

More orchestrators = more redundancy, but also more coordination overhead. The 3-of-5 model provides a good balance for most subnets.

---

## 9. Emission Distribution on Verus

### 9.1 Emission Source:  UAI-Tensor Block Rewards

The  UAI-Tensor PBaaS chain produces block rewards (VT tokens) on its own schedule:

```
 UAI-Tensor chain parameters:
  Block time:     60 seconds
  Block reward:   5 VT (halving every ~2 years / 1,051,200 blocks)
  Max supply:     21,000,000 VT
  Consensus:      Verus Proof of Power (50% PoW via VerusHash 2.2 / 50% PoS)
```

Block rewards are earned by PoW miners and PoS stakers on the  UAI-Tensor chain itself. These are **not** ML miners — they are blockchain miners who secure the chain. The ML incentive layer sits above this.

### 9.2 Subnet Emission Pool

The subnet emission pool is funded by a dedicated allocation from block rewards, managed by the chain's governance:

```
Per block (5 VT total):
  ├── 2.5 VT → PoW/PoS block producers (chain security)
  └── 2.5 VT → Subnet emission pool (ML incentives)
      └── Distributed across subnets proportional to alpha token demand
```

The subnet emission pool can also be funded by:
- **Alpha token minting**: Each subnet has a centralized token (options: 32, `proofprotocol: 2`), allowing the orchestrator to mint alpha tokens as emissions. These are separate from the AMM pool.
- **VT conversion**: VT from the emission pool is converted to each subnet's alpha token via the two-reserve basket AMM pool (LLMPool), then distributed

### 9.3 Dynamic Subnet Emission Shares (Equivalent to Dynamic TAO)

How much of the total subnet pool goes to each subnet? The Verus two-reserve basket AMM provides a natural answer:

```
┌─────────────────────────────────────────────────────────────────┐
│           DYNAMIC SUBNET EMISSION ON VERUS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Each subnet has two currencies:                                 │
│  • LLM  = centralized token (options: 32, proofprotocol: 2)      │
│  • LLMPool = two-reserve basket (options: 33, VT + LLM)          │
│                                                                  │
│  • getcurrencystate "LLMPool" returns:                           │
│    - VT reserves in the AMM pool                                │
│    - LLM reserves in the AMM pool                               │
│    - LLMPool supply outstanding                                  │
│    - Recent conversion volumes                                   │
│                                                                  │
│  • Net inflow = VT added to pool - VT removed from pool        │
│    (tracked over a rolling window of N blocks)                  │
│                                                                  │
│  • emission_share[LLM] = net_inflow[LLM] / Σ net_inflow[all]  │
│                                                                  │
│  Higher VT inflow (people buying LLM alpha via LLMPool)         │
│    → Higher emission share                                       │
│    → Orchestrator mints more LLM tokens as emissions              │
│    → More rewards for miners/validators in that subnet          │
│    → Attracts more talent/compute                                │
│    → Better AI output                                            │
│    → More demand for alpha                                       │
│    → Virtuous cycle                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

The orchestrator monitors this by querying `getcurrencystate` for each subnet's AMM pool and computing relative shares.

### 9.4 Emission Flow — Complete Path

```
Step 0: BLOCK PRODUCED
   UAI-Tensor block mined → 5 VT created
  2.5 VT to block producer, 2.5 VT to emission pool

Step 1: SUBNET SHARE COMPUTATION (per epoch)
  Orchestrator queries getcurrencystate for each subnet's AMM pool
  Computes net VT inflow per subnet over the tempo window
  Determines emission_share per subnet

Step 2: SUBNET EMISSION POOL
  For subnet "LLM" with 30% emission share:
    epoch_emission = 2.5 VT/block × 360 blocks × 0.30 = 270 VT
    OR: orchestrator mints 270 LLM alpha tokens (via proofprotocol: 2)

Step 3: YUMA CONSENSUS SPLITS
  Owner:      270 × 0.18 = 48.6 VT (or LLM equivalent)
  Miners:     270 × 0.41 = 110.7 VT
  Validators: 270 × 0.41 = 110.7 VT

Step 4: MINER DISTRIBUTION (via Yuma incentive scores)
  miner101: 110.7 × 0.113 = 12.5 VT
  miner102: 110.7 × 0.165 = 18.3 VT
  miner103: 110.7 × 0.055 = 6.1 VT
  ... (proportional to normalized incentive vector I)

Step 5: VALIDATOR DISTRIBUTION (via Yuma dividend scores)
  alice:   110.7 × 0.083 = 9.2 VT (her take: 1.66 VT, stakers: 7.54 VT)
  charlie: 110.7 × 0.127 = 14.1 VT (his take: 2.54 VT, stakers: 11.56 VT)
  diana:   110.7 × 0.107 = 11.8 VT (her take: 2.12 VT, stakers: 9.68 VT)
  ...

Step 6: STAKER DISTRIBUTION (from each validator's staker pool)
  alice's stakers:
    bob:  7.54 × (bob_delegation / total_alice_delegation)
    eve:  7.54 × (eve_delegation / total_alice_delegation)
    ...
  All via sendcurrency from the validator's SubID

Step 7: ON-CHAIN RECORD
  Epoch results published to orchestrator SubID
  All sendcurrency transactions verifiable on-chain
  Input hash published for independent verification
```

### 9.5 Verus Advantages in Emission Distribution

| Feature | Bittensor |  UAI-Tensor |
|---------|-----------|-------------|
| **MEV on staking** | AMM transactions vulnerable to sandwich attacks | MEV-free simultaneous settlement in Verus basket AMMs |
| **Payment transparency** | Emissions computed in opaque pallet | All emission payments are standard `sendcurrency` transactions |
| **Staker rewards** | Automatic via on-chain accounting | Explicit `sendcurrency` — every payment visible |
| **Owner take** | Hardcoded in pallet | Configurable via subnet hyperparameters in VDXF |
| **Epoch results** | Only viewable via Substrate storage queries | Published as VDXF data, readable by any client |
| **Emission tracking** | Requires specialized block explorer | Standard `getaddresstxids` queries + vdxftag tracking |

---

## 10. VDXF Schema Specification

### 10.1 Namespace

All keys are under the `vt` ( UAI-Tensor) namespace, registered as a VerusID on the  UAI-Tensor chain. The full qualified name format is `vt::key.name`.

### 10.2 Key Categories

#### Neuron Registry Keys
| VDXF Key | Data Type | Description | Stored On |
|----------|-----------|-------------|-----------|
| `vt::neuron.type` | string | "miner" or "validator" | Neuron SubID |
| `vt::neuron.axon` | string | IP:PORT endpoint | Miner SubID |
| `vt::neuron.uid` | integer | UID slot (0-255) | Neuron SubID |
| `vt::neuron.registered_at` | integer | Block height of registration | Neuron SubID |
| `vt::neuron.model_hash` | string | SHA-256 of served model | Miner SubID |
| `vt::neuron.version` | string | Protocol version | Neuron SubID |

#### Weight Submission Keys
| VDXF Key | Data Type | Description | Stored On |
|----------|-----------|-------------|-----------|
| `vt::weights.vector` | JSON array | Score per miner UID | Validator SubID |
| `vt::weights.uid_map` | JSON array | UID mapping for weight indices | Validator SubID |
| `vt::weights.epoch` | integer | Epoch number for these weights | Validator SubID |
| `vt::weights.version` | string | Weight format version | Validator SubID |
| `vt::weights.block_height` | integer | Block at which weights were set | Validator SubID |

#### Subnet Configuration Keys
| VDXF Key | Data Type | Description | Stored On |
|----------|-----------|-------------|-----------|
| `vt::subnet.tempo` | integer | Blocks per epoch (default: 360) | Subnet namespace ID |
| `vt::subnet.immunity` | integer | Immunity period in blocks | Subnet namespace ID |
| `vt::subnet.max_uids` | integer | Max neurons (default: 256) | Subnet namespace ID |
| `vt::subnet.validator_slots` | integer | Max validators | Subnet namespace ID |
| `vt::subnet.miner_slots` | integer | Max miners | Subnet namespace ID |
| `vt::subnet.min_stake` | float | Min alpha to validate | Subnet namespace ID |
| `vt::subnet.kappa` | float | Clipping threshold (default: 0.5) | Subnet namespace ID |
| `vt::subnet.bond_penalty` | float | Bond penalty factor | Subnet namespace ID |
| `vt::subnet.alpha` | float | Bond EMA rate (default: 0.9) | Subnet namespace ID |
| `vt::subnet.owner_take` | float | Owner fraction (default: 0.18) | Subnet namespace ID |
| `vt::subnet.miner_fraction` | float | Miner fraction (default: 0.41) | Subnet namespace ID |
| `vt::subnet.validator_fraction` | float | Validator fraction (default: 0.41) | Subnet namespace ID |

#### Epoch Results Keys
| VDXF Key | Data Type | Description | Stored On |
|----------|-----------|-------------|-----------|
| `vt::epoch.number` | integer | Epoch sequential number | Orchestrator SubID |
| `vt::epoch.block` | integer | Block height of epoch boundary | Orchestrator SubID |
| `vt::epoch.input_hash` | string | SHA-256 of all inputs (canonical) | Orchestrator SubID |
| `vt::epoch.emission_total` | float | Total emissions for this epoch | Orchestrator SubID |
| `vt::epoch.miner_emissions` | JSON object | `{uid: amount}` per miner | Orchestrator SubID |
| `vt::epoch.validator_emissions` | JSON object | `{uid: amount}` per validator | Orchestrator SubID |
| `vt::epoch.owner_emission` | float | Owner's emission amount | Orchestrator SubID |
| `vt::epoch.bonds_snapshot` | JSON object | Bond matrix after EMA | Orchestrator SubID |
| `vt::epoch.consensus_vector` | JSON array | Computed consensus values | Orchestrator SubID |
| `vt::epoch.rank_vector` | JSON array | Stake-weighted ranks | Orchestrator SubID |

#### Orchestrator Keys
| VDXF Key | Data Type | Description | Stored On |
|----------|-----------|-------------|-----------|
| `vt::orchestrator.input_hash` | string | Hash from this orchestrator's input collection | Orchestrator's own SubID |
| `vt::orchestrator.emission_hash` | string | Hash of computed emission vector | Orchestrator's own SubID |
| `vt::orchestrator.status` | string | "active", "syncing", "disagreement" | Orchestrator's own SubID |
| `vt::orchestrator.version` | string | Software version running | Orchestrator's own SubID |

#### Stake & Delegation Keys
| VDXF Key | Data Type | Description | Stored On |
|----------|-----------|-------------|-----------|
| `vt::stake.delegation` | JSON object | Delegation record | Staker SubID |
| `vt::stake.validator` | string | Validator identity delegated to | Staker SubID |
| `vt::stake.amount` | float | Amount delegated | Staker SubID |
| `vt::stake.currency` | string | Currency (alpha token name) | Staker SubID |

---

## 11. Yuma Consensus Algorithm — Full Implementation

### 11.1 Python Reference Implementation

```python
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
import hashlib
import json


@dataclass
class SubnetConfig:
    """Subnet hyperparameters for Yuma Consensus."""
    tempo: int = 360           # blocks per epoch
    kappa: float = 0.5         # clipping threshold
    bond_penalty: float = 0.65 # penalty for out-of-consensus bonds
    alpha: float = 0.9         # bond EMA rate (liquid_alpha)
    owner_take: float = 0.18   # owner emission fraction
    miner_fraction: float = 0.41
    validator_fraction: float = 0.41
    max_uids: int = 256
    immunity_period: int = 4096


@dataclass
class EpochResult:
    """Output of one Yuma Consensus epoch."""
    epoch: int
    input_hash: str
    emission_total: float
    miner_emissions: Dict[int, float]    # uid -> amount
    validator_emissions: Dict[int, float] # uid -> amount
    owner_emission: float
    bonds_new: np.ndarray                # updated bond matrix
    consensus_vector: np.ndarray
    rank_vector: np.ndarray
    incentive_vector: np.ndarray
    dividend_vector: np.ndarray


class YumaConsensus:
    """
    Deterministic implementation of Bittensor's Yuma Consensus.
    
    This is the core algorithm that converts validator weight vectors
    and stake amounts into emission distributions for miners and validators.
    
    All operations are pure functions over the inputs — no side effects,
    no randomness, fully reproducible.
    """

    def __init__(self, config: SubnetConfig):
        self.config = config

    def run(
        self,
        weight_matrix: Dict[int, List[float]],  # validator_uid -> weights per miner
        stakes: Dict[int, float],                # validator_uid -> stake amount
        bonds_previous: Optional[np.ndarray],    # previous bond matrix
        miner_uids: List[int],                   # ordered list of miner UIDs
        validator_uids: List[int],               # ordered list of validator UIDs
        emission_total: float                     # total emissions for this epoch
    ) -> EpochResult:
        """
        Execute one epoch of Yuma Consensus.

        Args:
            weight_matrix: Mapping from validator UID to their weight vector
                           (scores for each miner)
            stakes: Mapping from validator UID to their total stake
                    (own stake + delegated)
            bonds_previous: Bond matrix from previous epoch (None if first epoch)
            miner_uids: Ordered list of active miner UIDs
            validator_uids: Ordered list of active validator UIDs
            emission_total: Total emission pool for this epoch

        Returns:
            EpochResult with complete emission breakdown
        """
        n_validators = len(validator_uids)
        n_miners = len(miner_uids)

        # --- Build matrices ---
        # W[i][j] = weight validator i gave to miner j
        W = np.zeros((n_validators, n_miners))
        for i, v_uid in enumerate(validator_uids):
            if v_uid in weight_matrix:
                weights = weight_matrix[v_uid]
                for j in range(min(len(weights), n_miners)):
                    W[i][j] = max(0.0, weights[j])  # non-negative

        # Normalize each validator's weights to sum to 1
        for i in range(n_validators):
            row_sum = W[i].sum()
            if row_sum > 0:
                W[i] /= row_sum

        # Stake vector S (normalized)
        S = np.zeros(n_validators)
        for i, v_uid in enumerate(validator_uids):
            S[i] = stakes.get(v_uid, 0.0)
        S_total = S.sum()
        if S_total > 0:
            S_norm = S / S_total
        else:
            S_norm = np.ones(n_validators) / n_validators

        # --- Step 1: Stake-Weighted Rank ---
        # R[j] = Σ_i S_norm[i] * W[i][j]
        R = S_norm @ W  # matrix multiply: (n_validators,) @ (n_validators, n_miners) = (n_miners,)

        # --- Step 2: Consensus Vector ---
        C = self._compute_consensus(W, S_norm, n_miners)

        # --- Step 3: Clipping ---
        W_clipped = self._clip_weights(W, C)

        # --- Step 4: Bonds ---
        B_current = np.outer(S_norm, np.ones(n_miners)) * W_clipped
        # Normalize columns of B_current
        for j in range(n_miners):
            col_sum = B_current[:, j].sum()
            if col_sum > 0:
                B_current[:, j] /= col_sum

        if bonds_previous is not None and bonds_previous.shape == B_current.shape:
            alpha = self.config.alpha
            B_new = alpha * B_current + (1 - alpha) * bonds_previous
        else:
            B_new = B_current

        # Normalize bond columns
        for j in range(n_miners):
            col_sum = B_new[:, j].sum()
            if col_sum > 0:
                B_new[:, j] /= col_sum

        # --- Step 5: Dividends and Incentives ---
        # Dividend vector: D[i] = Σ_j B_new[i][j] * R[j]
        D = B_new @ R  # (n_validators, n_miners) @ (n_miners,) = (n_validators,)

        # Incentive vector: fraction of rank not captured by bonds
        # I[j] = R[j] * (1 - Σ_i B_new[i][j])  -- simplified
        # More accurately, incentive is what's left after dividends
        bond_captured = B_new.sum(axis=0) * R
        I = R - bond_captured
        I = np.maximum(I, 0)  # no negative incentives

        # Normalize
        D_sum = D.sum()
        I_sum = I.sum()
        if D_sum > 0:
            D_norm = D / D_sum
        else:
            D_norm = np.ones(n_validators) / n_validators
        if I_sum > 0:
            I_norm = I / I_sum
        else:
            I_norm = np.ones(n_miners) / n_miners

        # --- Step 6: Emission Distribution ---
        E_owner = emission_total * self.config.owner_take
        E_miners_pool = emission_total * self.config.miner_fraction
        E_validators_pool = emission_total * self.config.validator_fraction

        miner_emissions = {}
        for j, m_uid in enumerate(miner_uids):
            miner_emissions[m_uid] = float(I_norm[j] * E_miners_pool)

        validator_emissions = {}
        for i, v_uid in enumerate(validator_uids):
            validator_emissions[v_uid] = float(D_norm[i] * E_validators_pool)

        # Compute input hash
        input_hash = self._compute_input_hash(
            weight_matrix, stakes, bonds_previous,
            miner_uids, validator_uids, emission_total
        )

        return EpochResult(
            epoch=0,  # set by caller
            input_hash=input_hash,
            emission_total=emission_total,
            miner_emissions=miner_emissions,
            validator_emissions=validator_emissions,
            owner_emission=float(E_owner),
            bonds_new=B_new,
            consensus_vector=C,
            rank_vector=R,
            incentive_vector=I_norm,
            dividend_vector=D_norm
        )

    def _compute_consensus(
        self, W: np.ndarray, S_norm: np.ndarray, n_miners: int
    ) -> np.ndarray:
        """
        Compute stake-weighted median consensus for each miner.
        
        For each miner j, the consensus C[j] is the weighted median of
        {W[i][j]} across all validators i, weighted by S_norm[i].
        """
        C = np.zeros(n_miners)
        for j in range(n_miners):
            weights_for_miner = []
            stake_weights = []
            for i in range(len(S_norm)):
                if W[i][j] > 0:
                    weights_for_miner.append(W[i][j])
                    stake_weights.append(S_norm[i])
            if weights_for_miner:
                C[j] = self._weighted_median(weights_for_miner, stake_weights)
        return C

    @staticmethod
    def _weighted_median(values: List[float], weights: List[float]) -> float:
        """Compute weighted median of values with given weights."""
        if not values:
            return 0.0
        # Sort by value, carry weights
        sorted_pairs = sorted(zip(values, weights))
        cumulative_weight = 0.0
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        for value, weight in sorted_pairs:
            cumulative_weight += weight
            if cumulative_weight >= total_weight / 2:
                return value
        return sorted_pairs[-1][0]

    def _clip_weights(self, W: np.ndarray, C: np.ndarray) -> np.ndarray:
        """
        Clip validator weights to kappa × consensus.
        
        If a validator's weight for a miner exceeds kappa × consensus,
        it's clipped down. This penalizes validators who inflate scores
        for specific miners beyond what the consensus supports.
        """
        kappa = self.config.kappa
        W_clipped = W.copy()
        for i in range(W.shape[0]):
            for j in range(W.shape[1]):
                if C[j] > 0:
                    max_weight = C[j] * (1 + kappa)
                    W_clipped[i][j] = min(W[i][j], max_weight)
                # If C[j] == 0, clip to 0 (no consensus support)
                elif W[i][j] > 0:
                    W_clipped[i][j] = 0.0
        return W_clipped

    @staticmethod
    def _compute_input_hash(
        weight_matrix, stakes, bonds_previous,
        miner_uids, validator_uids, emission_total
    ) -> str:
        """Deterministic hash of all inputs for verification."""
        canonical = json.dumps({
            "weights": {str(k): list(v) for k, v in sorted(weight_matrix.items())},
            "stakes": {str(k): float(v) for k, v in sorted(stakes.items())},
            "bonds_prev": bonds_previous.tolist() if bonds_previous is not None else None,
            "miner_uids": sorted(miner_uids),
            "validator_uids": sorted(validator_uids),
            "emission_total": float(emission_total)
        }, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

### 11.2 Verification Implementation

Anyone can verify an epoch's results:

```python
class EpochAuditor:
    """
    Independent verification of Yuma Consensus epoch results.
    
    This can be run by anyone — miners, stakers, community members —
    to verify that the orchestrator computed emissions correctly.
    """

    def __init__(self, chain=" UAI-Tensor"):
        self.cli = VerusCLI(chain=chain)
        self.yuma = YumaConsensus(SubnetConfig())

    async def audit_epoch(self, subnet: str, epoch: int) -> AuditResult:
        """
        Independently verify an epoch's emission computation.

        Steps:
        1. Read the published epoch results from the orchestrator
        2. Read all input data (weights, stakes) from the chain
        3. Re-run Yuma Consensus
        4. Compare our results with the published results
        """
        # 1. Get published results
        published = await self.get_published_results(subnet, epoch)

        # 2. Collect the same inputs the orchestrator used
        inputs = await self.collect_inputs(subnet, published.epoch_block)

        # 3. Verify input hash matches
        our_input_hash = self.yuma._compute_input_hash(
            inputs.weight_matrix, inputs.stakes,
            inputs.bonds_previous, inputs.miner_uids,
            inputs.validator_uids, published.emission_total
        )

        if our_input_hash != published.input_hash:
            return AuditResult(
                valid=False,
                reason="Input hash mismatch — orchestrator used different inputs",
                our_hash=our_input_hash,
                their_hash=published.input_hash
            )

        # 4. Re-run Yuma Consensus
        our_result = self.yuma.run(
            weight_matrix=inputs.weight_matrix,
            stakes=inputs.stakes,
            bonds_previous=inputs.bonds_previous,
            miner_uids=inputs.miner_uids,
            validator_uids=inputs.validator_uids,
            emission_total=published.emission_total
        )

        # 5. Compare emissions
        emissions_match = self._compare_emissions(
            our_result.miner_emissions, published.miner_emissions,
            our_result.validator_emissions, published.validator_emissions,
            tolerance=1e-8
        )

        if not emissions_match:
            return AuditResult(
                valid=False,
                reason="Emission mismatch — orchestrator computed different emissions from same inputs",
                our_miner_emissions=our_result.miner_emissions,
                their_miner_emissions=published.miner_emissions
            )

        # 6. Verify payments were actually made on-chain
        payments_verified = await self._verify_payments(
            subnet, epoch, published.miner_emissions, published.validator_emissions
        )

        return AuditResult(
            valid=True and payments_verified,
            reason="All checks passed" if payments_verified else "Payments not found on chain",
            input_hash_verified=True,
            emissions_verified=True,
            payments_verified=payments_verified
        )

    @staticmethod
    def _compare_emissions(
        ours_miners, theirs_miners,
        ours_validators, theirs_validators,
        tolerance=1e-8
    ) -> bool:
        """Compare two emission distributions within floating-point tolerance."""
        for uid in set(list(ours_miners.keys()) + list(theirs_miners.keys())):
            if abs(ours_miners.get(uid, 0) - theirs_miners.get(uid, 0)) > tolerance:
                return False
        for uid in set(list(ours_validators.keys()) + list(theirs_validators.keys())):
            if abs(ours_validators.get(uid, 0) - theirs_validators.get(uid, 0)) > tolerance:
                return False
        return True
```

---

## 12. Epoch Lifecycle — End-to-End Flow

### 12.1 Timeline

```
EPOCH 42 LIFECYCLE (tempo = 360 blocks = 360 minutes = 6 hours)

Block 158041 ─────── EPOCH 41 ENDS / EPOCH 42 BEGINS ────────────
│
│  [Blocks 158041 - 158100]  TASK DISTRIBUTION PHASE
│  • Orchestrator (or validators directly) sends ML tasks to miners
│  • Tasks are subnet-specific: LLM prompts, image requests, etc.
│  • Miners receive via their Axon endpoints (read from SubID)
│
│  [Blocks 158100 - 158300]  EVALUATION PHASE
│  • Validators evaluate miner responses
│  • Validators compute scores using incentive mechanism code
│  • Validators may run multiple evaluation rounds
│
│  [Blocks 158300 - 158380]  WEIGHT SUBMISSION PHASE
│  • Validators submit weight vectors via updateidentity
│  • Each submission is VerusID-signed and block-timestamped
│  • Late submissions (after block 158380) may be excluded
│
│  [Blocks 158380 - 158400]  CONSENSUS WINDOW
│  • Orchestrators collect all submitted weights
│  • Orchestrators query stake balances
│  • Orchestrators retrieve previous bond state
│  • Orchestrators compute input hash
│
Block 158401 ─────── EPOCH 42 SETTLEMENT ─────────────────────────
│
│  [Blocks 158401 - 158405]  AGREEMENT PHASE
│  • Orchestrators publish input hashes
│  • Orchestrators compare hashes (must agree)
│  • If agreement: proceed to computation
│
│  [Blocks 158405 - 158410]  COMPUTATION PHASE
│  • All orchestrators run Yuma Consensus independently
│  • Deterministic algorithm produces identical results
│  • Orchestrators publish emission hashes
│
│  [Blocks 158410 - 158420]  SETTLEMENT PHASE
│  • Multisig sendcurrency for miner emissions
│  • Multisig sendcurrency for validator emissions
│  • Multisig sendcurrency for owner emission
│  • Validators distribute to stakers
│  • Full results published to orchestrator SubID
│
│  [Blocks 158420+]  NEXT EPOCH BEGINS
│  • New tasks distributed
│  • Cycle repeats
│
Block 158401 ─────── EPOCH 43 BEGINS ─────────────────────────────
```

### 12.2 Timing Considerations

| Parameter | Bittensor |  UAI-Tensor | Notes |
|-----------|-----------|-------------|-------|
| Block time | 12 seconds | 60 seconds |  UAI-Tensor blocks are 5x slower |
| Tempo | 360 blocks = 72 minutes | 360 blocks = 360 minutes (6 hours) | Same block count, longer wall-clock |
| Weight submission window | ~30 blocks = 6 minutes | ~80 blocks = 80 minutes | Proportionally longer |
| Settlement time | 1 block = 12 seconds | ~20 blocks = 20 minutes | Allow time for multisig agreement |

The longer tempo is actually advantageous for ML workloads:
- More time for miners to process complex tasks (e.g., long LLM sequences, large image batches)
- More time for validators to thoroughly evaluate outputs
- Less on-chain overhead per unit of useful work
- The tempo can be adjusted per subnet via hyperparameters

---

## 13. Auditing & Dispute Resolution

### 13.1 Continuous Auditing

Any party can run a continuous auditor that checks every epoch:

```python
class ContinuousAuditor:
    """
    Runs alongside the network, independently verifying every epoch.
    Can be operated by miners, stakers, community watchdogs, or anyone.
    """

    async def monitor(self, subnet: str):
        """Continuously monitor and audit epoch results."""
        auditor = EpochAuditor()
        last_epoch = 0

        while True:
            current_epoch = await self.get_current_epoch(subnet)
            if current_epoch > last_epoch:
                # New epoch settled — audit it
                result = await auditor.audit_epoch(subnet, current_epoch)
                if not result.valid:
                    await self.raise_alert(subnet, current_epoch, result)
                last_epoch = current_epoch
            await asyncio.sleep(60)  # check every minute

    async def raise_alert(self, subnet, epoch, result):
        """
        Publish audit failure on-chain for community visibility.
        """
        await self.cli.updateidentity({
            "name": f"auditor.{subnet}",
            "contentmultimap": {
                "vt::audit.alert": [{
                    "data": {
                        "objectdata": {
                            "vt::audit.epoch": str(epoch),
                            "vt::audit.reason": result.reason,
                            "vt::audit.our_hash": result.our_hash,
                            "vt::audit.their_hash": result.their_hash
                        }
                    }
                }]
            }
        })
```

### 13.2 Dispute Resolution Process

```
DISPUTE RAISED:
  Auditor publishes alert on-chain with evidence

INVESTIGATION:
  1. Community members download all epoch inputs
  2. Multiple parties independently re-run Yuma Consensus
  3. Results compared with orchestrator's published results

RESOLUTION PATHS:

  Path A — Orchestrator Bug (innocent error):
    • Orchestrator acknowledges error
    • Corrective payment issued from subnet treasury
    • Orchestrator updates software

  Path B — Orchestrator Fraud (intentional manipulation):
    • Evidence chain:
      a. Published input_hash does not match re-computed hash
         → Orchestrator used different inputs (data manipulation)
      b. Input hashes match but emissions differ
         → Orchestrator ran different algorithm (computation fraud)
      c. Emissions match but payments don't match published amounts
         → Orchestrator skimmed emissions (payment fraud)
    • Subnet owner removes fraudulent orchestrator from multisig
    • Remaining orchestrators issue corrective payments
    • Fraudulent orchestrator's reputation permanently damaged on-chain

  Path C — Auditor False Alarm:
    • Multiple independent re-computations confirm orchestrator was correct
    • Alert retracted
    • Auditor may have had stale data (chain sync issue)
```

### 13.3 Evidence Preservation

All evidence is automatically preserved on-chain:
- **Weight vectors**: Stored in validator SubIDs, immutable once confirmed
- **Stake snapshots**: UTXO balances at specific block heights
- **Input hashes**: Published by orchestrators before computation
- **Emission results**: Published after computation
- **Payment transactions**: Standard `sendcurrency` transactions with `vdxftag`
- **Audit alerts**: Published by auditors with evidence

This creates a permanent, verifiable audit trail — far more transparent than Bittensor's on-chain pallet computation, which requires running a full Substrate node to verify.

---

## 14. Comparison: On-Chain vs Off-Chain Consensus

### 14.1 Side-by-Side Analysis

| Dimension | Bittensor (On-Chain) |  UAI-Tensor (Off-Chain + On-Chain Verification) |
|-----------|---------------------|------------------------------------------------|
| **Where computation runs** | Substrate pallet (Rust, WASM) | Python/Node.js on orchestrator servers |
| **Computation cost** | Consumed block space; limits subnet count | Zero on-chain cost; unlimited computation |
| **Verifiability** | Run full Substrate node + understand Rust | Read JSON data from chain + run Python script |
| **Upgradeability** | Substrate runtime upgrade (on-chain governance vote, hard fork) | Update Python orchestrator code (no chain changes) |
| **Algorithm flexibility** | Same algorithm for all subnets (hardcoded) | Each subnet can customize consensus parameters or even use a different algorithm variant |
| **Transparency** | Opaque pallet internals | All inputs/outputs published as readable VDXF data |
| **Trust assumption** | Trust that Substrate executes pallet correctly | Trust that orchestrators run correct algorithm (verifiable) |
| **Failure mode** | Pallet bug affects ALL subnets simultaneously | Orchestrator bug affects ONE subnet; independently detectable |
| **Attack surface** | Substrate VM + pallet code | Orchestrator multisig + deterministic algorithm |
| **Data availability** | Stored in Substrate state trie (specialized queries) | Stored in VDXF contentmultimap (standard identity queries) |
| **Inter-subnet isolation** | Shared pallet code | Independent orchestrators per subnet |
| **Dispute resolution** | Hard — need to debug Substrate internals | Easy — download inputs, run Python, compare |

### 14.2 When On-Chain Is Better

On-chain consensus has one clear advantage: **atomicity**. In Bittensor, weight submission, consensus computation, and emission payment all happen in the same block production pipeline. There's no window where inputs are collected but payments haven't been made. In  UAI-Tensor, there's a settlement delay between input collection and payment execution.

However, this atomicity is less important than it appears:
- Bittensor already has a tempo delay (72 minutes between epochs)
-  UAI-Tensor's settlement adds ~20 minutes to a 6-hour epoch — negligible
- The settlement delay actually provides a verification window before payments

### 14.3 When Off-Chain Is Better

Off-chain consensus is superior in every other dimension:
1. **Cost**: No gas/weight consumed for computation
2. **Flexibility**: Algorithm upgrades don't require chain hard forks
3. **Auditability**: Readable data instead of opaque state tries
4. **Resilience**: Per-subnet isolation prevents cascading failures
5. **Customization**: Each subnet can tune or extend the algorithm
6. **Accessibility**: Python is more accessible than Rust/Substrate for subnet developers

---

## 15. Security Analysis

### 15.1 Threat Model

| Threat | Attack Vector | Mitigation |
|--------|---------------|------------|
| **Orchestrator collusion** | All orchestrators collude to steal emissions | Multisig requires M-of-N agreement; community auditors detect mismatches; subnet owner can replace orchestrators |
| **Weight manipulation** | Validator submits inflated weights for colluding miner | Yuma Consensus clipping penalizes out-of-consensus weights; VerusID signatures ensure authenticity |
| **Stake gaming** | Attacker rapidly moves stake to game emission distribution | Bond EMA smooths over time; rapid stake changes don't immediately affect bonds |
| **Data withholding** | Orchestrator claims weight data was unavailable | All weight submissions are on-chain in SubIDs; anyone can verify data was available |
| **Replay attack** | Re-broadcasting old weights as current | Epoch number in weight submission; orchestrator checks block height range |
| **Front-running** | Validator sees others' weights before submitting own | Encrypt weights until submission deadline (z-address or timelock reveal) |
| **Sybil validators** | One entity runs many pseudo-validators | Minimum stake requirement; each validator needs real capital |
| **Key compromise** | Validator's private key stolen | VerusID revocation + recovery (unlike Bittensor where key loss is permanent) |

### 15.2 Front-Running Prevention (Advanced)

Bittensor has a front-running problem: validators can see others' weight submissions and adjust their own.  UAI-Tensor can solve this with a commit-reveal scheme using Verus z-addresses:

```
Phase 1 — COMMIT (blocks 158300-158380):
  Validators submit hash(weights || salt) to their SubID
  Hash reveals nothing about actual weights

Phase 2 — REVEAL (blocks 158380-158395):
  Validators submit actual weights + salt
  Orchestrator verifies hash matches
  Weights that don't match their commit are rejected

This ensures:
  • No validator can see others' weights before committing their own
  • Changing weights after seeing others' commits is detectable
  • Non-revealing validators are penalized (treated as zero weight)
```

Alternatively, Verus's native z-address (Sapling) encryption can be used: validators encrypt their weight vector to the orchestrator's viewing key, and the orchestrator decrypts all weights simultaneously after the submission window closes.

### 15.3 Orchestrator Accountability Matrix

| Scenario | Detection Method | Recovery |
|----------|-----------------|----------|
| Orchestrator offline | Missing epoch results publication | Remaining orchestrators continue (M-of-N) |
| Incorrect computation | Auditor re-computation mismatch | Majority result prevails; corrective payment |
| Selective exclusion | Input hash mismatch (missing validator weights) | Re-collect from chain; flag orchestrator |
| Payment skimming | On-chain payment amounts don't match published results | Corrective payment from treasury |
| Data delay | Orchestrator uses stale chain state | Input hash comparison across orchestrators catches this |

### 15.4 VerusID Security Advantages

| Feature | How It Helps Yuma Consensus |
|---------|----------------------------|
| **Revocation** | Compromised validator key → immediately revoke and stop malicious weight submissions |
| **Recovery** | Legitimate validator recovers identity → doesn't lose stake or history |
| **Vault** | Large-stake validators enable vault → time delay prevents instant theft |
| **Multisig identity** | Validator operated by a team → no single person can submit malicious weights |
| **Transfer** | Validator identity can be sold → clean ownership transfer without stake migration |

---

## 16. Implementation Priorities

### 16.1 Minimum Viable Product (MVP)

The MVP for Yuma Consensus on Verus requires:

| Component | Priority | Effort | Description |
|-----------|----------|--------|-------------|
| **VDXF key registration** | P0 | 1 week | Register all `vt::` keys on testnet |
| **Weight submission flow** | P0 | 2 weeks | Validator → updateidentity → contentmultimap |
| **Single orchestrator** | P0 | 3 weeks | Python Yuma implementation + input collection + emission payments |
| **Subnet creation script** | P0 | 1 week | Automate namespace ID + alpha token + AMM pool + config |
| **Basic auditor** | P0 | 1 week | Re-run consensus and compare results |
| **Multisig orchestrator** | P1 | 3 weeks | Multi-party agreement protocol |
| **Staker delegation** | P1 | 2 weeks | Track delegation, distribute staker rewards |
| **Commit-reveal weights** | P2 | 2 weeks | Front-running prevention |
| **Continuous auditor** | P2 | 1 week | Always-on verification service |
| **Subnet explorer UI** | P2 | 4 weeks | Web dashboard for emissions, scores, neurons |

### 16.2 Build Order

```
Phase 1: Core (weeks 1-8)
  ├── Register vt:: VDXF keys on  UAI-Tensor testnet
  ├── Build YumaConsensus Python class (the algorithm)
  ├── Build input collection (read weights/stakes from chain)
  ├── Build single orchestrator (collect → compute → pay)
  ├── Create first subnet (namespace + basket + config)
  ├── Test with 3 validators + 5 miners on testnet
  └── Build basic auditor to verify results

Phase 2: Decentralization (weeks 8-14)
  ├── Add multi-orchestrator support
  ├── Implement multisig consensus identity
  ├── Build agreement protocol (input hash → emission hash → sign)
  ├── Add staker delegation tracking
  ├── Implement validator → staker reward distribution
  └── Test with 3 orchestrators on testnet

Phase 3: Hardening (weeks 14-20)
  ├── Implement commit-reveal for weight submissions
  ├── Build continuous auditor service
  ├── Add deregistration mechanism
  ├── Implement immunity period enforcement
  ├── Performance test with 64 validators + 192 miners
  └── Security audit of orchestrator code

Phase 4: Production Readiness (weeks 20-26)
  ├── Subnet explorer web UI
  ├── Miner/Validator SDK (Python package)
  ├── Dynamic emission share computation
  ├── Documentation and tutorials
  └── Mainnet launch preparation
```

### 16.3 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Algorithm | Python + NumPy | Matches Bittensor's research ecosystem; NumPy for efficient matrix ops |
| Orchestrator | Python asyncio | Async RPC calls to  UAI-Tensor daemon |
| Chain interaction | `verus` CLI / JSON-RPC | Direct daemon communication |
| SDK | Python package (` UAI-Tensor`) | Distribute as pip-installable package |
| Auditor | Python | Same algorithm as orchestrator for bit-exact comparison |
| Explorer | TypeScript + React | Web dashboard leveraging verus-typescript-primitives |
| Weight encoding | JSON in VDXF DataDescriptor | Human-readable, parseable, versioned |

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **Alpha token** | Subnet-specific centralized token (options: 32, proofprotocol: 2); minted by orchestrator as emissions |
| **Alpha AMM pool** | Two-reserve basket currency (options: 33, VT + ALPHA); provides price discovery between VT and alpha |
| **Bond** | Validator's accumulated "investment" in each miner; determines dividend share |
| **Bond EMA** | Exponential moving average of bonds across epochs; prevents rapid shifting |
| **Clipping** | Penalty mechanism that reduces outlier validator weights to consensus × kappa |
| **Consensus vector** | Stake-weighted median of all validator scores per miner |
| **Contentmultimap** | VDXF key-value store on VerusIDs; supports multiple values per key |
| **Dividend** | Validator's emission share, derived from their bond positions |
| **Emission** | New tokens created per epoch, distributed to miners, validators, and owner |
| **Epoch** | One tempo period; the interval between Yuma Consensus computations |
| **Incentive** | Miner's emission share, derived from their rank minus bond-captured rank |
| **Input hash** | SHA-256 of all canonical inputs; used to verify orchestrators used same data |
| **Kappa** | Clipping threshold; how far above consensus a weight can be before clipping |
| **Multisig** | VerusID requiring M-of-N primary address signatures to transact |
| **Orchestrator** | Off-chain service that collects inputs, runs Yuma Consensus, executes payments |
| **Rank** | Stake-weighted sum of validator weights per miner; raw performance metric |
| **SubID** | Sub-identity under a namespace; used for neuron registration |
| **Tempo** | Number of blocks per epoch (default 360) |
| **VDXF** | Verus Data eXchange Format; typed, namespaced keys for on-chain data |
| **Weight vector** | A validator's scores for all miners; submitted via updateidentity |

## Appendix B: Key Shell Commands Reference

```bash
# === SUBNET CREATION ===
# Register subnet namespace identity
verus -chain= UAI-Tensor registernamecommitment "llm-inference" "ROwnerAddr"
# (wait 1 block)
verus -chain= UAI-Tensor registeridentity '{"txid":"...","namereservation":{...},"identity":{...}}'

# Define subnet alpha token (centralized, orchestrator-controlled)
verus -chain= UAI-Tensor definecurrency '{
  "name": "LLM",
  "options": 32,
  "proofprotocol": 2
}'

# Define subnet AMM pool (two-reserve basket for VT ↔ LLM price discovery)
verus -chain= UAI-Tensor definecurrency '{
  "name": "LLMPool",
  "options": 33,
  "currencies": [" UAI-Tensor", "LLM"],
  "weights": [0.5, 0.5],
  "initialsupply": 10000,
  "conversions": [1, 1]
}'

# === NEURON REGISTRATION ===
# Register miner SubID
verus -chain= UAI-Tensor registernamecommitment "miner101" "RMinerAddr" "llm-inference"
verus -chain= UAI-Tensor registeridentity '{"name":"miner101","parent":"llm-inference",...}'

# === WEIGHT SUBMISSION ===
verus -chain= UAI-Tensor updateidentity '{"name":"alice.llm-inference","contentmultimap":{"vt::weights.vector":[...]}}'

# === ORCHESTRATOR SETUP ===
# Create multisig consensus identity
verus -chain= UAI-Tensor updateidentity '{
  "name": "consensus.llm-inference",
  "primaryaddresses": ["AliceRAddr", "BobRAddr", "CarolRAddr"],
  "minimumsignatures": 2
}'

# === EMISSION PAYMENTS ===
verus -chain= UAI-Tensor sendcurrency "consensus.llm-inference@" '[
  {"address":"miner101.llm-inference@","currency":"LLM","amount":12.5}
]'

# === STAKING (buy LLM alpha via the AMM pool) ===
verus -chain= UAI-Tensor sendcurrency "*" '[{
  "address":"alice.llm-inference@","currency":" UAI-Tensor","via":"LLMPool","convertto":"LLM","amount":100
}]'

# === AUDITING ===
verus -chain= UAI-Tensor getidentitycontent "orchestrator.llm-inference@" heightstart heightend
verus -chain= UAI-Tensor getidentitycontent "alice.llm-inference@" heightstart heightend
verus -chain= UAI-Tensor getaddressbalance '{"addresses":["consensus.llm-inference@"]}'
```

---

*This report details the design for implementing Bittensor's Yuma Consensus and Emission Distribution mechanisms on the Verus Network using off-chain orchestrators with on-chain data storage and verification. It builds on the [Rebuilding Bittensor on Verus Architecture Report](BITTENSOR_ON_VERUS_ARCHITECTURE_REPORT.md) with a focused deep-dive into the consensus and emission subsystems.*
