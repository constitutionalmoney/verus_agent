# How Subnets Compete for Emissions: Bittensor vs VerusTensor

> **Date**: March 2026  
> **Prepared for**: UAI-e-Gold Project  
> **Purpose**: Plain-language explanation of how VerusTensor models subnet competition for VT emissions, compared side-by-side with Bittensor's dTAO system

---

## Table of Contents

1. [The Big Picture — What Problem Are We Solving?](#1-the-big-picture)
2. [How Bittensor Does It (Summary)](#2-how-bittensor-does-it)
3. [How VerusTensor Does It on Verus](#3-how-verustensor-does-it-on-verus)
4. [The AMM — Same Idea, Different Engine](#4-the-amm--same-idea-different-engine)
5. [Subnet Competition for Emissions — Side by Side](#5-subnet-competition-for-emissions--side-by-side)
6. [Anti-Manipulation — Where Verus Is Structurally Superior](#6-anti-manipulation--where-verus-is-structurally-superior)
7. [Inside a Subnet — Who Gets Paid and How](#7-inside-a-subnet--who-gets-paid-and-how)
8. [Subnet Lifecycle — Birth, Competition, and Death](#8-subnet-lifecycle--birth-competition-and-death)
9. [The Root Network Problem — And Why VerusTensor Doesn't Need One](#9-the-root-network-problem)
10. [Token Supply and Emission Schedule](#10-token-supply-and-emission-schedule)
11. [A Day in the Life — Walkthrough Example](#11-a-day-in-the-life--walkthrough-example)
12. [What's the Same, What's Different — Summary Table](#12-whats-the-same-whats-different)
13. [Why These Differences Matter](#13-why-these-differences-matter)

---

## 1. The Big Picture

Both Bittensor and VerusTensor solve the same fundamental problem:

> **How do you allocate newly minted tokens to the AI subnets that produce the most value — without a central committee deciding?**

The answer in both systems is: **let the market decide**. People "vote with their wallets" by staking tokens into the subnets they believe are most valuable. Subnets that attract more capital get more emissions. Subnets that lose capital get fewer emissions — and eventually get replaced.

The core mechanics are strikingly similar. The differences are in the *engine* underneath — and those engine differences create real advantages for VerusTensor.

---

## 2. How Bittensor Does It

Here's Bittensor's system in plain language:

### 2.1 The Token Layer

```
TAO (native token, 21M max supply)
 └── Each subnet has an "alpha" token (α₁, α₂, α₃, ...)
     └── Each alpha has an AMM pool: TAO ↔ αₖ
         └── Pool uses constant product formula: TAO_reserve × α_reserve = k
```

### 2.2 How Subnets Compete

1. **You "vote" by buying alpha**: When you think a subnet is valuable, you stake TAO into its pool and receive alpha tokens in return
2. **Buying alpha raises its price**: More TAO in the pool = higher alpha price = signal to the network that this subnet matters
3. **Network follows the signal**: Subnets with more TAO flowing in get a bigger share of daily emissions
4. **Bad subnets lose capital**: If people unstake (sell alpha for TAO), the subnet's emission share drops
5. **Worst subnet dies**: When a new subnet wants to launch, the subnet with the lowest emissions gets kicked off the network

### 2.3 The Flow-Based Model (Taoflow)

Since November 2025, emissions aren't just based on pool size — they're based on **net flows** over a rolling window:

- **Net inflow** = TAO staked into subnet minus TAO unstaked from subnet
- Smoothed by a **30-day half-life EMA** (so short-term spikes don't distort long-term allocation)
- If a subnet has sustained negative flow (more people leaving than joining), its emissions can drop to **zero**

### 2.4 Inside a Subnet (Reward Split)

Once a subnet earns its share of TAO, it splits the rewards:
- **41% → Miners** (the AI workers producing actual output)
- **41% → Validators** (the scorers evaluating miner quality)
- **18% → Subnet Owner** (the team maintaining the subnet code)

### 2.5 Bittensor's AMM Details

- **Formula**: Constant product (x × y = k), same as Uniswap V2
- **Transaction ordering**: Random within each block (to prevent front-running)
- **Liquidity injection**: Every block, new TAO + alpha are injected into pools by the protocol
- **Slippage**: A trade representing 10% of pool volume causes ~11% price impact
- **Concentrated liquidity**: Uniswap V3-style being introduced (late 2025+)

---

## 3. How VerusTensor Does It on Verus

### 3.1 The Token Layer

```
VRSC (Verus root chain — provides the security backbone)
 └── VT (VerusTensor PBaaS native coin — equivalent to TAO)
      ├── Each subnet has a centralized token (alpha, proofprotocol: 2)
      │   ├── LLM (text inference subnet alpha)
      │   ├── IMG (image generation subnet alpha)
      │   ├── PRO (protein folding subnet alpha)
      │   └── ... (unlimited — no slot limit)
      └── Each subnet has a two-reserve basket AMM pool
          ├── LLMPool (basket: VT + LLM → price discovery)
          ├── IMGPool (basket: VT + IMG → price discovery)
          ├── PROPool (basket: VT + PRO → price discovery)
          └── ... (one pool per subnet)
```

> **Why two currencies per subnet?** A single-reserve basket with `weights: [1]` (100% reserve ratio) creates a 1:1 peg with VT — the price never changes. To get real price discovery (like Bittensor’s Uniswap V2 AMM), we define a **centralized token** (the alpha, minted by the orchestrator as emissions) and a separate **two-reserve basket** (the AMM pool where VT ↔ alpha trades happen).

### 3.2 How Subnets Compete — Same Market Logic, Different Plumbing

The competitive mechanism is **conceptually identical** to Bittensor:

1. **You "vote" by buying alpha**: Stake VT into a subnet's AMM pool (LLMPool) → receive alpha tokens (LLM)
2. **Buying alpha raises its price**: Verus two-reserve basket AMMs follow constant-product-like pricing
3. **Orchestrator follows the signal**: The emission orchestrator reads AMM pool state and allocates emissions proportionally to net VT inflow
4. **Bad subnets lose capital**: People sell alpha via the pool → VT outflow → emission share drops
5. **No hard slot limit**: Unlike Bittensor's 32-64 slots, VerusTensor allows **unlimited** subnets — but market forces still cause uncompetitive subnets to receive zero emissions

### 3.3 What's Different About the Plumbing

| Aspect | Bittensor | VerusTensor |
|--------|-----------|-------------|
| AMM engine | Custom on-chain Uniswap V2 (constant product) | Verus two-reserve basket currency (protocol-level, simultaneous settlement) |
| MEV protection | Random transaction ordering within blocks | **Simultaneous settlement** — all orders in a block get the same price |
| Emission computation | On-chain in Substrate pallets | Off-chain orchestrators reading on-chain AMM pool state |
| Subnet slots | Fixed (32-64), enforced by deregistration | **Unlimited** — no artificial cap on subnets |
| Liquidity injection | Protocol auto-injects TAO + alpha every block | Orchestrator mints alpha tokens (proofprotocol: 2), seeds AMM pool |
| Pool creation cost | Hundreds of TAO (dynamic burn) | ~200 VT (token) + ~200 VT (basket pool) + ~100 VT (namespace identity) |
| Cross-chain | Polkadot relay (if parachain) | Trustless Ethereum bridge + PBaaS interop |

---

## 4. The AMM — Same Idea, Different Engine

This is the most important technical difference. Both systems use an AMM to determine subnet value, but the underlying engines work differently.

### 4.1 Bittensor's AMM: Uniswap V2 Constant Product

```
How it works:
  Pool holds: 1000 TAO + 10000 αₖ
  Invariant: 1000 × 10000 = 10,000,000 (must stay constant)
  Price: 1000/10000 = 0.10 TAO per alpha

When Alice stakes 100 TAO:
  New TAO reserve: 1000 + 100 = 1100
  New α reserve: 10,000,000 / 1100 = 9090.9
  Alice receives: 10000 - 9090.9 = 909.1 alpha
  New price: 1100/9090.9 = 0.121 TAO per alpha (+21% impact!)

Key properties:
  ✓ Simple, well-understood formula
  ✗ Large trades cause significant slippage
  ✗ Vulnerable to sandwich attacks without random ordering
  ✗ Sequential processing (one trade at a time within a block)
```

### 4.2 Verus's AMM: Two-Reserve Basket Currency with Simultaneous Settlement

```
How it works:
  Basket "LLMPool" holds: 1000 VT + 10000 LLM in reserves
  LLMPool supply outstanding: 10000 tokens
  Reserve weights: [0.5, 0.5] (equal weighting)
  Price: derived from reserve ratio (similar to constant product AMM)

When Alice and Bob both trade in the same block:
  Alice wants to buy: 100 VT → LLM
  Bob wants to sell: 80 LLM → VT

  Step 1: NET the orders
    Net buy pressure: 100 VT in - 80 LLM out (VT equivalent ~8 VT)
    Net demand: only 92 VT of actual buying pressure impacts the pool

  Step 2: SETTLE simultaneously
    Both Alice and Bob get the SAME price
    This price is calculated AFTER netting, not sequentially

  Step 3: RESULT
    Pool absorbs only the net imbalance
    Slippage is dramatically reduced
    Price impact: ~9.2% instead of sequential impact of ~21% + ~8%

Key properties:
  ✓ MEV-free by design — no front-running possible
  ✓ All traders in a block get the same fair price
  ✓ Netting reduces real slippage (opposing trades cancel out)
  ✓ Protocol-level (not a smart contract — can't be exploited via contract bugs)
  ✗ Slightly less familiar to DeFi users accustomed to Uniswap
```

### 4.3 Why This Matters for Subnets

Subnet staking IS AMM trading. Every time someone stakes into or unstakes from a subnet, they're trading on the AMM. The AMM engine determines:

1. **How much alpha they get** for their VT (staking)
2. **How much VT they get back** when they leave (unstaking)
3. **The effective "market cap"** of the subnet (which drives emission share)

If the AMM is vulnerable to manipulation, the entire emission system is compromised. This is why Verus's simultaneous settlement matters so much — it makes the emission signal **honest**.

### 4.4 Practical Comparison

| Scenario | Bittensor AMM | Verus Basket AMM |
|----------|---------------|-------------------|
| **Alice stakes 100 TAO** | Gets her alpha at whatever price she ends up at in the block ordering | Gets alpha at the same fair price as everyone else in that block |
| **Whale dumps 10,000 alpha** | Crashes the price; small stakers in the same block get wrecked | Dump is netted against buys; price impact is the NET effect only |
| **Sandwich attack** | Attacker front-runs large stake, profits from slippage | **Impossible** — all trades in a block settle simultaneously at one price |
| **Bot front-runs staking tx** | Bot sees the mempool, buys alpha first, sells after victim | **Impossible** — there is no "first" or "second" in a Verus block's conversions |
| **10% of pool traded in 1 block** | ~11% price impact | Depends on net direction after offsetting — could be much less |

---

## 5. Subnet Competition for Emissions — Side by Side

### 5.1 The Flow-Based Model — How It Maps

Bittensor's Taoflow model (net inflows determine emissions) maps directly to VerusTensor:

**Bittensor:**
```
emission_share[subnet_k] = EMA(net_TAO_inflow[subnet_k]) / Σ EMA(net_TAO_inflow[all])
```

**VerusTensor:**
```
emission_share[subnet_k] = EMA(net_VT_inflow[subnet_k]) / Σ EMA(net_VT_inflow[all])
```

The math is identical. The data source is different:

| Data Point | Bittensor Source | VerusTensor Source |
|------------|-----------------|-------------------|
| TAO/VT flowing into subnet | Substrate storage, opaque pallet | `getcurrencystate "LLMPool"` — returns full AMM pool state as JSON |
| TAO/VT flowing out of subnet | Substrate storage | Same `getcurrencystate` query — reserve changes are publicly visible |
| Net flow calculation | On-chain pallet code | Off-chain orchestrator reading transparent on-chain data |
| EMA smoothing | On-chain, 30-day half-life | Off-chain orchestrator, configurable half-life |

### 5.2 How the Orchestrator Computes Emission Shares

```python
async def compute_emission_shares(self) -> Dict[str, float]:
    """
    Compute each subnet's share of the total emission pool.
    
    Equivalent to Bittensor's Taoflow, but using on-chain basket
    currency state as the data source.
    """
    subnets = await self.list_all_subnets()
    
    net_flows = {}
    for subnet in subnets:
        # getcurrencystate returns full AMM pool state including reserves
        current_state = await self.cli.getcurrencystate(subnet.pool_currency)
        previous_state = await self.get_state_at_block(
            subnet.pool_currency,
            self.current_block - self.config.flow_window
        )
        
        # Net VT inflow = change in VT reserves over the window
        vt_reserve_now = current_state['currencystate']['reservecurrencies']['VT']
        vt_reserve_then = previous_state['currencystate']['reservecurrencies']['VT']
        net_flow = vt_reserve_now - vt_reserve_then
        
        # Apply EMA smoothing
        net_flows[subnet.name] = self.ema_update(
            subnet.name, net_flow, half_life_blocks=43200  # ~30 days at 60s blocks
        )
    
    # Compute shares (only positive flows get emissions)
    positive_flows = {k: max(0, v) for k, v in net_flows.items()}
    total_positive = sum(positive_flows.values())
    
    if total_positive == 0:
        # No positive flows — distribute equally
        return {k: 1.0/len(subnets) for k in net_flows}
    
    return {k: v/total_positive for k, v in positive_flows.items()}
```

### 5.3 Key Insight: Transparent Price Discovery

In Bittensor, the AMM state lives inside Substrate pallets. You need a Substrate client to query it, and the emission calculation runs in opaque Rust code.

In VerusTensor, the AMM state is a **standard Verus query**:

```bash
# Anyone can see the full state of any subnet's AMM pool:
verus -chain=VerusTensor getcurrencystate "LLMPool"

# Returns:
# {
#   "currencystate": {
#     "reservecurrencies": {
#       "VT": 15000.0,     ← VT reserves in the pool
#       "LLM": 50000.0     ← LLM reserves in the pool
#     },
#     "supply": 10000.0,   ← LLMPool basket tokens outstanding
#     "flags": 33,
#     ...
#   }
# }
```

This transparency means:
- Anyone can verify emission share calculations
- No specialized tooling needed — standard CLI/API
- Historical state visible via block height queries
- No hidden variables or opaque on-chain logic

---

## 6. Anti-Manipulation — Where Verus Is Structurally Superior

### 6.1 The Manipulation Problem

If a wealthy actor can manipulate a subnet's apparent value (by spiking its AMM price), they can steal emissions from honest subnets. Both Bittensor and VerusTensor take this seriously, but they solve it differently.

### 6.2 Bittensor's Anti-Manipulation

| Mechanism | How It Works | Effectiveness |
|-----------|-------------|---------------|
| **Random tx ordering** | Transactions within a block are shuffled randomly | Prevents front-running but not within-block sandwich attacks |
| **30-day EMA** | Flows are smoothed over 30 days — short spikes are damped | Good for long-term but still allows sustained manipulation |
| **Deregistration threat** | Worst subnet gets replaced — low performers are removed | Creates accountability but is blunt (only kills the worst) |
| **No concentrated liquidity initially** | Prevents sophisticated LP strategies from gaming the pool | Being relaxed with V3 introduction — may reopen attack vectors |

### 6.3 VerusTensor's Anti-Manipulation

| Mechanism | How It Works | Effectiveness |
|-----------|-------------|---------------|
| **Simultaneous settlement** | ALL trades in a block get the SAME price — no ordering advantage | **Eliminates** front-running, back-running, and sandwich attacks entirely |
| **Order netting** | Buy and sell orders cancel against each other before affecting price | Reduces effective price impact of manipulation (attacker's buy is offset by natural sellers) |
| **EMA smoothing** | Same 30-day EMA as Bittensor — configurable per subnet | Same effectiveness as Bittensor |
| **No slot limit** | No deregistration — subnets simply get zero emissions if no demand | No artificial pressure that could be gamed by registering spoiler subnets |
| **VerusID-signed staking** | Every stake/unstake is tied to a real VerusID — pseudonymous but accountable | Can build reputation around staking patterns |
| **Public AMM state** | Everyone sees the same reserves — no information asymmetry | Level playing field for all participants |

### 6.4 The MEV Deep Dive

This deserves special attention because it's the single biggest structural advantage Verus has over Bittensor's AMM:

```
BITTENSOR (Sequential Processing with Random Ordering):
  Block contains: [Alice buys 100 TAO → α₁, Bob sells 50 α₁ → TAO, Eve buys 200 TAO → α₁]
  
  Processing: Random order is selected, e.g., Bob → Alice → Eve
    1. Bob sells: price drops from 0.10 to 0.095
    2. Alice buys: price rises from 0.095 to 0.115 (Alice gets slightly better deal from Bob's dip)
    3. Eve buys: price rises from 0.115 to 0.155 (Eve gets worst price)
  
  Issue: The random ordering helps, but different orderings still produce different outcomes
  for each trader. Some get lucky, some don't. Result is fair ON AVERAGE but not fair PER TRADE.

VERUSTENSOR (Simultaneous Settlement):
  Block contains: [Alice buys 100 VT → LLM, Bob sells 50 LLM → VT, Eve buys 200 VT → LLM]
  
  Processing:
    1. NET: Total buy = 300 VT in. Total sell = 50 LLM out (~5 VT equivalent)
       Net pressure = 295 VT of buying
    2. COMPUTE single clearing price from net demand
    3. ALL THREE get the SAME price
  
  Result: Every trader gets the same fair price. No luck, no ordering dependency,
  no possible advantage from seeing the mempool.
```

### 6.5 What About Concentrated Liquidity (Uniswap V3)?

Bittensor is introducing concentrated liquidity, which allows sophisticated players to position liquidity in specific price ranges. While this improves capital efficiency, it also introduces new attack vectors:
- LPs can "just-in-time" provide liquidity to extract value from large trades
- Sophisticated actors with better models can out-earn passive LPs
- Adds complexity that benefits insiders

**VerusTensor doesn't need concentrated liquidity** because Verus's netting mechanism already achieves higher effective liquidity. When opposing orders cancel each other, the pool behaves as if it were much larger. This achieves the capital efficiency benefit without the complexity or attack surface.

---

## 7. Inside a Subnet — Who Gets Paid and How

### 7.1 The Split — Same as Bittensor

Once a subnet earns its share of emissions, the internal distribution is **the same** as Bittensor:

```
Subnet Epoch Emission (e.g., 270 VT or equivalent alpha)
├── 18% → Subnet Owner (48.6 VT)
│   └── Paid to the subnet namespace VerusID (e.g., "llm-inference@")
│
├── 41% → Miners (110.7 VT)
│   └── Distributed proportionally via Yuma Consensus incentive vector
│   └── Better AI work = higher score = more emissions
│
└── 41% → Validators + their Stakers (110.7 VT)
    ├── Validator keeps their "take" (e.g., 18% of their share)
    └── Remaining distributed to stakers who delegated to that validator
```

### 7.2 Where Payment Happens

| Step | Bittensor | VerusTensor |
|------|-----------|-------------|
| Owner payment | Automatic in Substrate runtime | `sendcurrency "consensus.subnet@" to "subnet-owner@"` |
| Miner payment | Automatic in Substrate runtime | `sendcurrency` per miner, proportional to Yuma scores |
| Validator payment | Automatic in Substrate runtime | `sendcurrency` per validator, proportional to dividend scores |
| Staker payment | Automatic via pallet accounting | Validator or orchestrator sends proportional `sendcurrency` to each delegator |

The key difference: **all VerusTensor payments are explicit, visible transactions** on the chain. In Bittensor, payments happen inside the pallet — you see the result but not the calculation. In VerusTensor, you can trace every single emission payment via `getaddresstxids`.

### 7.3 Payment Currencies

There's a design choice on VerusTensor that's worth understanding:

**Option A: Pay in alpha tokens (subnet-specific)**
```bash
# Orchestrator mints alpha tokens and pays miners in the subnet's own currency
verus -chain=VerusTensor sendcurrency "consensus.llm-inference@" '[
  {"address": "miner101.llm-inference@", "currency": "LLM", "amount": 12.5}
]'
```
- Miners receive LLM tokens
- If they want VT, they sell on the basket AMM
- Similar to Bittensor's alpha distribution

**Option B: Pay in VT (native coin)**
```bash
# Orchestrator pays miners directly in VT
verus -chain=VerusTensor sendcurrency "consensus.llm-inference@" '[
  {"address": "miner101.llm-inference@", "currency": "VerusTensor", "amount": 12.5}
]'
```
- Miners receive VT directly
- No AMM interaction needed
- Simpler for miners who just want to earn

**Option C: Hybrid (recommended)**
- Pay **owner** in VT (they maintain infrastructure — need stable value)
- Pay **miners** in alpha (aligns their incentives with subnet success)
- Pay **validators** in alpha (aligns incentives with subnet they validate)
- **Stakers** already hold alpha — pay them in alpha (compounds their position)

---

## 8. Subnet Lifecycle — Birth, Competition, and Death

### 8.1 Birth: Creating a Subnet

**Bittensor:**
```
Cost: Dynamic burn (hundreds of TAO, varies with demand)
Slots: Limited (32-64)
Wait: Rate-limited to 1 per ~4 days
Code: Full Substrate pallet knowledge required
```

**VerusTensor:**
```
Cost: ~200 VT (alpha token) + ~200 VT (AMM pool) + ~100 VT (namespace VerusID) = ~500 VT total
Slots: Unlimited
Wait: No rate limit (permissionless)
Code: No blockchain coding — only off-chain orchestrator (Python)
```

Verus subnet creation:
```bash
# Step 1: Create the subnet namespace identity
verus -chain=VerusTensor registernamecommitment "llm-inference" "ROwnerAddr"
# (wait 1 block)
verus -chain=VerusTensor registeridentity '{
  "txid": "...",
  "namereservation": {...},
  "identity": {
    "name": "llm-inference",
    "primaryaddresses": ["ROwnerAddr"],
    "minimumsignatures": 1
  }
}'

# Step 2: Define the alpha token (centralized, orchestrator-controlled)
verus -chain=VerusTensor definecurrency '{
  "name": "LLM",
  "options": 32,
  "proofprotocol": 2
}'

# Step 2b: Define the AMM pool (two-reserve basket for VT ↔ LLM price discovery)
verus -chain=VerusTensor definecurrency '{
  "name": "LLMPool",
  "options": 33,
  "currencies": ["VerusTensor", "LLM"],
  "weights": [0.5, 0.5],
  "initialsupply": 10000,
  "conversions": [1, 1]
}'

# Step 3: Store subnet configuration in VDXF
verus -chain=VerusTensor updateidentity '{
  "name": "llm-inference",
  "contentmultimap": {
    "vt::subnet.tempo": [{"data": "360"}],
    "vt::subnet.max_uids": [{"data": "256"}],
    "vt::subnet.kappa": [{"data": "0.5"}],
    "vt::subnet.owner_take": [{"data": "0.18"}],
    "vt::subnet.miner_fraction": [{"data": "0.41"}],
    "vt::subnet.validator_fraction": [{"data": "0.41"}]
  }
}'

# Step 4: Deploy off-chain orchestrator (Python service)
# This is where the actual ML tasks, scoring, and consensus run
```

### 8.2 Competition: How Subnets Attract Capital

The flow is identical in both systems:

```
Subnet builds good AI product
  ↓
Users experience value (fast inference, quality images, etc.)
  ↓
Investors stake VT/TAO into subnet (buying alpha)
  ↓
Net VT/TAO inflow increases
  ↓
Emission share increases
  ↓
More rewards attract more/better miners
  ↓
Better AI output → more users → more staking → virtuous cycle
```

And the reverse for failing subnets:

```
Subnet produces poor AI output
  ↓
Users leave, investors unstake (selling alpha)
  ↓
Net VT/TAO outflow
  ↓
Emission share decreases (can reach zero with sustained outflow)
  ↓
Miners leave for better-paying subnets
  ↓
Even worse output → death spiral
```

### 8.3 Death: What Happens to Failing Subnets

**Bittensor:**
- Fixed number of slots (32-64)
- When a new subnet registers, the one with the **lowest emissions** is forcibly **deregistered**
- Deregistered subnet's alpha tokens become worthless
- Hard cutoff — one subnet dies so another can live

**VerusTensor:**
- **Unlimited** subnet slots — no forced deregistration
- Subnets that attract zero VT inflow simply receive **zero emissions**
- The basket currency AMM still exists — people can still trade alpha
- A "dead" subnet can revive if it improves and attracts new capital
- The subnet owner can voluntarily shut down by revoking the namespace identity

This is a meaningful difference:

| Aspect | Bittensor (Slot-Based) | VerusTensor (Market-Based) |
|--------|----------------------|--------------------------|
| **Competition model** | Musical chairs — last place gets eliminated | Open field — everyone competes, worst gets zero rewards |
| **New subnet cost** | Must outperform the weakest existing subnet OR pay the burn cost | Just create one (~300 VT); success depends on attracting stakers |
| **Subnet investment safety** | Your subnet could be deregistered and your alpha becomes worthless | Your subnet might earn zero, but it still exists — can recover |
| **Attack vector** | Register a spoiler subnet to kill a competitor | Not possible — no forced displacement |
| **Innovation** | Risk-averse — losing your slot is catastrophic | Risk-friendly — low cost to experiment |

---

## 9. The Root Network Problem

### 9.1 What Is Bittensor's Root Network?

Bittensor has a **Subnet 0** (Root Network) consisting of the top 64 validators by stake. Before dTAO, these 64 validators **directly controlled** which subnets got emissions by voting on weights.

Even after dTAO shifted power to the market, Root validators still:
- Influence emissions through residual mechanisms
- Act as a "senate" with governance power
- Can bias the system toward subnets they operate or invest in

### 9.2 Why VerusTensor Doesn't Need a Root Network

VerusTensor's emission allocation is **purely market-driven** from day one:

```
Emission share = f(net VT inflow via basket AMM)
```

There is no special committee of validators that votes on emission weights. The AMM state — visible to everyone via `getcurrencystate` — IS the vote. No human override is possible.

**But what about governance?** 

Subnet-level governance (changing tempo, kappa, owner take, etc.) is handled by the subnet owner's VerusID. Network-level governance (total emission rate, emission pool split between chain security and ML incentives) is handled via the VerusTensor PBaaS chain's parameters, which can be governed by a multisig VerusID representing the community.

| Governance Layer | Bittensor | VerusTensor |
|-----------------|-----------|-------------|
| Subnet emission allocation | Root validators + dTAO market | Pure market (basket AMM state) |
| Subnet parameters | Subnet owner (on-chain pallet) | Subnet owner VerusID (VDXF contentmultimap) |
| Network parameters | Substrate runtime upgrade (governance vote) | PBaaS chain parameters + community multisig |
| Emergency actions | Root senate vote | Multisig VerusID governance |

---

## 10. Token Supply and Emission Schedule

### 10.1 Supply Comparison

| Parameter | TAO (Bittensor) | VT (VerusTensor) |
|-----------|-----------------|-------------------|
| Max supply | 21,000,000 | 21,000,000 |
| Block time | 12 seconds | 60 seconds |
| Block reward | ~1 TAO | 5 VT |
| Emission per minute | ~5 TAO (5 blocks × ~1 TAO) | ~5 VT (1 block × 5 VT) |
| Emission per day | ~7,200 TAO | ~7,200 VT |
| Halving schedule | Every ~4 years (~10.5M blocks) | Every ~2 years (~1,051,200 blocks) |
| Consensus | NPoS (Nominated Proof of Stake) | Verus Proof of Power (50% PoW + 50% PoS) |
| Mining hardware | N/A (pure PoS) | CPU mining via VerusHash 2.2 |

### 10.2 How Block Rewards Are Split

**Bittensor:**
```
1 TAO per block
└── 100% goes to the subnet emission pool
    └── Distributed across subnets via dTAO/Taoflow
```

**VerusTensor:**
```
5 VT per block
├── 50% (2.5 VT) → Chain security (PoW miners + PoS stakers)
│   └── This secures the blockchain itself
│
└── 50% (2.5 VT) → Subnet emission pool
    └── Distributed across subnets via flow-based model
```

The chain security portion is a difference. Bittensor relies on Polkadot's relay chain for base-layer security (or its own NPoS). VerusTensor must secure its own chain, which requires dedicating some emissions to PoW/PoS block producers. The trade-off: VerusTensor has independent security (not dependent on any relay chain), but dedicates a portion of emissions to that security.

### 10.3 Emission Allocation in Practice

Assume VerusTensor has 5 active subnets with these net VT inflows:

```
Subnet        | Net VT Inflow (30d EMA) | Emission Share | VT per epoch
─────────────────────────────────────────────────────────────────────────
LLM           | +5,000 VT              | 50%            | 450 VT
IMG           | +2,000 VT              | 20%            | 180 VT
Storage       | +2,000 VT              | 20%            | 180 VT
Protein       | +1,000 VT              | 10%            | 90 VT
FailingSubnet | -500 VT (outflow)      | 0%             | 0 VT
─────────────────────────────────────────────────────────────────────────
Total positive| 10,000 VT              | 100%           | 900 VT/epoch

(Epoch = 360 blocks at 60s = 6 hours; 2.5 VT/block × 360 = 900 VT emission pool)
```

Within the LLM subnet (450 VT per epoch):
```
Owner (18%):      81 VT → llm-inference@
Miners (41%):     184.5 VT → split by Yuma Consensus scores
Validators (41%): 184.5 VT → split by Yuma Consensus dividends
                    → Validators keep their "take" (~18% of their share)
                    → Rest goes to their delegated stakers
```

---

## 11. A Day in the Life — Walkthrough Example

### 11.1 Setting the Scene

Let's follow the VerusTensor network through one epoch (6 hours) to see how everything fits together.

**Network state:**
- 4 active subnets: LLM, IMG, Storage, Code
- LLM is the most popular (highest VT inflow)
- Code is new and growing
- A new "Audio" subnet just launched

### 11.2 Hour-by-Hour

```
HOUR 0: EPOCH BEGINS (Block 158,400)
════════════════════════════════════════

  The orchestrator notes this is an epoch boundary.
  
  Meanwhile, in the LLM subnet:
  • 64 validators are sending LLM prompts to 192 miners
  • Miners run their GPU-powered models and return responses  
  • Validators score responses on quality, speed, coherence

  In the background, investors are staking:
  • Alice stakes 500 VT → LLM pool (buys LLM alpha)
  • Bob stakes 200 VT → Code pool (buys Code alpha)
  • Carol unstakes 100 LLM alpha → VT (she thinks LLM is overvalued)

HOURS 1-4: EVALUATION CONTINUES
════════════════════════════════════════

  • Validators keep querying miners, scoring results
  • More staking/unstaking happens organically
  • The basket AMM processes all these trades with simultaneous settlement
  
  AMM State (visible to everyone):
  │ Subnet  │ VT Reserve │ Alpha Supply │ Price (VT/α) │ Net Flow │
  │ LLM     │ 15,500     │ 50,000       │ 0.31         │ +400     │
  │ IMG     │ 8,200      │ 30,000       │ 0.27         │ +150     │
  │ Storage │ 5,100      │ 20,000       │ 0.25         │ +200     │
  │ Code    │ 2,800      │ 15,000       │ 0.19         │ +180     │
  │ Audio   │ 300        │ 5,000        │ 0.06         │ +50      │

HOUR 5: WEIGHT SUBMISSION (Blocks 158,700 - 158,740)
════════════════════════════════════════

  Validators submit their final weight vectors:

  verus -chain=VerusTensor updateidentity '{
    "name": "alice-validator.llm-inference",
    "contentmultimap": {
      "vt::weights.vector": [{
        "data": {
          "objectdata": {
            "vt::weights.data": "[0.15, 0.22, 0.08, 0.31, 0.04, 0.20]",
            "vt::weights.epoch": "42"
          }
        }
      }]
    }
  }'

  Every validator does this. Each submission is:
  ✓ Signed by their VerusID (unforgeable)
  ✓ Timestamped at a specific block height
  ✓ Publicly readable by anyone

HOUR 6: CONSENSUS + SETTLEMENT (Blocks 158,760 - 158,780)
════════════════════════════════════════

  Step 1: EMISSION SHARE COMPUTATION
  ─────────────────────────────────────
  Orchestrators query getcurrencystate for each subnet.
  
  Flow-based emission shares (30-day EMA):
    LLM:     40.8% → 367.2 VT
    IMG:     15.3% → 137.7 VT
    Storage: 20.4% → 183.6 VT
    Code:    18.4% → 165.6 VT
    Audio:    5.1% → 45.9 VT
    ──────────────────────────
    Total:  100.0% → 900 VT (this epoch's subnet pool)

  Step 2: YUMA CONSENSUS (per subnet)
  ─────────────────────────────────────
  For LLM subnet (367.2 VT):
    Read 64 validator weight vectors from chain
    Read stake balances for all validators
    Run Yuma Consensus algorithm (deterministic math)
    
    Output:
      Owner:      66.1 VT → llm-inference@
      Miner pool: 150.6 VT
        miner_001: 25.1 VT  (best performer)
        miner_002: 19.3 VT
        ... (192 miners)
        miner_192:  0.2 VT  (worst performer)
      Validator pool: 150.6 VT
        alice-validator: 12.4 VT → keeps 2.2 VT, stakers get 10.2 VT
        bob-validator:   8.7 VT → keeps 1.6 VT, stakers get 7.1 VT
        ... (64 validators)

  Step 3: MULTI-ORCHESTRATOR AGREEMENT
  ─────────────────────────────────────
  Orchestrator A publishes: input_hash = "a3f8c2..."  emission_hash = "7b2d1e..."
  Orchestrator B publishes: input_hash = "a3f8c2..."  emission_hash = "7b2d1e..."
  Orchestrator C publishes: input_hash = "a3f8c2..."  emission_hash = "7b2d1e..."
  
  All agree! → Sign multisig transaction

  Step 4: ON-CHAIN PAYMENTS
  ─────────────────────────────────────
  verus -chain=VerusTensor sendcurrency "consensus.llm-inference@" '[
    {"address":"miner_001.llm-inference@", "currency":"LLM", "amount":25.1},
    {"address":"miner_002.llm-inference@", "currency":"LLM", "amount":19.3},
    ...
  ]'

  Every payment is a visible on-chain transaction.
  Anyone can verify by checking getaddresstxids.

  Step 5: PUBLISH RESULTS
  ─────────────────────────────────────
  Full epoch results stored on-chain:
    • input_hash (so anyone can verify inputs)
    • emission breakdown per participant
    • bond matrix snapshot
    • consensus vector
  
  → Epoch 42 complete. Epoch 43 begins.
```

---

## 12. What's the Same, What's Different — Summary Table

### 12.1 What's Essentially the Same

| Feature | Bittensor | VerusTensor | Verdict |
|---------|-----------|-------------|---------|
| Alpha tokens per subnet | ✅ | ✅ (centralized tokens + AMM basket pools) | **Same concept** |
| AMM for price discovery | ✅ (Uniswap V2) | ✅ (two-reserve basket AMM) | **Same concept, different engine** |
| Staking = buying alpha | ✅ | ✅ (sendcurrency via LLMPool + convertto) | **Same mechanism** |
| Flow-based emission share | ✅ (Taoflow) | ✅ (orchestrator reads AMM state) | **Same formula** |
| EMA smoothing of flows | ✅ (30-day half-life) | ✅ (configurable half-life) | **Same math** |
| 18/41/41 split | ✅ | ✅ | **Same split** |
| Yuma Consensus | ✅ (on-chain) | ✅ (off-chain, same algorithm) | **Same math** |
| Max supply 21M | ✅ | ✅ | **Same cap** |
| No slashing | ✅ | ✅ | **Same policy** |
| Market-driven allocation | ✅ (dTAO) | ✅ (pure market) | **Same philosophy** |

### 12.2 What's Different

| Feature | Bittensor | VerusTensor | Why It Matters |
|---------|-----------|-------------|----------------|
| **AMM fairness** | Random tx ordering | Simultaneous settlement + netting | Verus eliminates MEV entirely |
| **Subnet slots** | Fixed (32-64), deregistration kills worst | Unlimited, zero-emission market pressure | Verus is more innovation-friendly |
| **Root network** | Top 64 validators influence emissions | None — pure market pricing | Verus has no privileged gatekeepers |
| **Consensus location** | On-chain (Substrate pallet) | Off-chain (multi-party orchestrator) | Verus is more transparent and upgradeable |
| **Block reward destination** | 100% to subnet pool | 50% chain security, 50% subnet pool | Verus secures its own chain |
| **Identity recovery** | Lose coldkey = lose everything | VerusID revoke/recover/vault | Verus protects long-term participants |
| **Subnet creation cost** | Hundreds of TAO + Rust knowledge | ~500 VT + Python knowledge | Verus has 100x lower barrier |
| **Payment visibility** | Opaque pallet accounting | Explicit sendcurrency transactions | Verus is fully transparent |
| **Privacy** | None | Sapling z-addresses available | Verus enables private ML work |
| **Cross-chain** | Polkadot (if parachain) | Trustless Ethereum bridge | Verus has native cross-chain |
| **Block time** | 12 seconds | 60 seconds | Verus is 5x slower per block (same throughput per minute) |
| **Concentrated liquidity** | Uniswap V3 being added | Not needed (netting achieves similar efficiency) | Verus is simpler with same benefit |
| **Chain security** | NPoS (Nominated Proof of Stake) | Proof of Power (50% CPU PoW + 50% PoS) | Verus is provably more attack-resistant |

---

## 13. Why These Differences Matter

### 13.1 For Stakers (Investors)

**You want**: Fair pricing when staking/unstaking, protection from MEV, ability to recover if your keys are compromised.

- **Verus wins on MEV**: When you stake 1000 VT into the LLM subnet, you get the same price as everyone else in that block. No bot can front-run you. On Bittensor, random ordering helps but you could still get an unfavorable random position.
- **Verus wins on safety**: VerusID vault lets you timelock your staked position. If your keys are compromised, the attacker has to wait (giving you time to recover). On Bittensor, stolen coldkey = stolen everything, no recourse.
- **Verus wins on transparency**: You can verify exactly how your emission share was calculated by reading on-chain data + re-running simple Python math.

### 13.2 For Subnet Owners (Entrepreneurs)

**You want**: Low cost to launch, no risk of being killed, control over your subnet parameters.

- **Verus wins on cost**: ~300 VT vs hundreds of TAO. Lower barrier means more experimentation.
- **Verus wins on survival**: Your subnet won't be forcibly deregistered. If you build slowly, you can still exist with zero emissions while you improve, and attract stakers when you're ready.
- **Verus wins on flexibility**: Change your subnet parameters (tempo, splits, kappa) by updating a VDXF key — no governance vote or chain upgrade needed.

### 13.3 For Miners (GPU Operators)

**You want**: Predictable, fair payment for your compute work.

- **Same in both**: Payments are proportional to Yuma Consensus scores. Better work = more money.
- **Verus wins on transparency**: You can independently verify that the Yuma Consensus was computed correctly over the inputs. On Bittensor, you trust that the pallet code is correct.
- **Verus wins on identity**: If your mining rig's keys are compromised, you can recover your identity and emission history. On Bittensor, you'd need to re-register from scratch.

### 13.4 For Validators (Quality Evaluators)

**You want**: Your scoring work to be fairly rewarded, your delegated stakers to be protected.

- **Same in both**: Validators earn dividends based on their bonds (accumulated weights aligned with consensus).
- **Verus wins on verifiability**: Your weight submission is a signed, timestamped, on-chain record. If the orchestrator claims you submitted different weights, the chain proves otherwise.

### 13.5 For the Network (System Health)

**You want**: Honest price discovery, no manipulation, sustainable growth.

- **Verus wins on anti-manipulation**: Simultaneous settlement + netting makes it structurally harder to game emission allocation.
- **Bittensor has advantage in maturity**: Battle-tested since 2021, larger ecosystem, more subnets live.
- **Verus wins on scalability**: No artificial subnet cap. If 1000 different AI tasks need funding, they can all exist simultaneously.
- **Verus wins on independence**: Not reliant on Polkadot. The VerusTensor PBaaS chain has its own security via Proof of Power, inheritable from Verus root chain via merge-mining.

---

## Appendix A: Quick Visual Comparison

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BITTENSOR (TAO)                              │
│                                                                      │
│  TAO Block Reward (~1/block)                                        │
│  └─→ 100% → Subnet Emission Pool                                   │
│      └─→ Distributed via Taoflow (net inflow EMA)                  │
│          ├─→ Subnet 0 (Root): special governance role               │
│          ├─→ Subnet 1: TAO→α₁ AMM (Uniswap V2, random ordering)   │
│          ├─→ Subnet 2: TAO→α₂ AMM                                  │
│          ├─→ ...                                                     │
│          └─→ Subnet 64: TAO→α₆₄ AMM (MAX 64 slots)               │
│              └─→ Within each subnet:                                │
│                  ├─→ 18% Owner                                      │
│                  ├─→ 41% Miners (Yuma Consensus)                    │
│                  └─→ 41% Validators + Stakers (Yuma Consensus)      │
│                                                                      │
│  Anti-MEV: Random transaction ordering                              │
│  Subnet death: Lowest emissions gets deregistered                   │
│  Identity: SS58 keypairs (no recovery)                              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       VERUSTENSOR (VT)                               │
│                                                                      │
│  VT Block Reward (5/block)                                          │
│  ├─→ 50% → Chain Security (PoW miners + PoS stakers)               │
│  └─→ 50% → Subnet Emission Pool                                    │
│      └─→ Distributed via Flow Model (net inflow EMA)               │
│          ├─→ LLM: VT↔LLM via LLMPool (sim. settlement, MEV-free) │
│          ├─→ IMG: VT↔IMG via IMGPool                               │
│          ├─→ Storage: VT↔STR via STRPool                            │
│          ├─→ Code: VT↔CODE via CODEPool                             │
│          ├─→ ...                                                     │
│          └─→ (UNLIMITED subnets — no slot cap)                      │
│              └─→ Within each subnet:                                │
│                  ├─→ 18% Owner                                      │
│                  ├─→ 41% Miners (Yuma Consensus, off-chain)         │
│                  └─→ 41% Validators + Stakers (Yuma Consensus)      │
│                                                                      │
│  Anti-MEV: Simultaneous settlement + order netting                  │
│  Subnet death: Market-driven (zero emissions, but subnet survives) │
│  Identity: VerusID (revoke/recover/vault)                           │
│  Root network: NONE (pure market pricing)                           │
│  Governance: Community multisig VerusID                             │
└─────────────────────────────────────────────────────────────────────┘
```

## Appendix B: Key CLI Commands for Subnet Tokenomics

```bash
# === STAKING INTO A SUBNET (Buying Alpha) ===
# Stake 100 VT into LLM subnet (get LLM alpha tokens)
verus -chain=VerusTensor sendcurrency "*" '[{
  "address": "mystaker@",
  "currency": "VerusTensor",
  "convertto": "LLM",
  "amount": 100
}]'

# === UNSTAKING FROM A SUBNET (Selling Alpha) ===
# Convert 50 LLM alpha back to VT
verus -chain=VerusTensor sendcurrency "*" '[{
  "address": "mystaker@",
  "currency": "LLM",
  "convertto": "VerusTensor",
  "amount": 50
}]'

# === CHECK SUBNET AMM STATE ===
# See reserves, supply, price — this IS the emission signal
verus -chain=VerusTensor getcurrencystate "LLM"

# === ESTIMATE STAKING PRICE ===
verus -chain=VerusTensor estimateconversion '{
  "currency": "VerusTensor",
  "convertto": "LLM",
  "amount": 100
}'

# === LIST ALL SUBNETS ===
verus -chain=VerusTensor listcurrencies '{"systemtype":"pbaas","launchstate":"launched"}'

# === CHECK EMISSION RESULTS ===
verus -chain=VerusTensor getidentitycontent "orchestrator.llm-inference@" 158400 158800
```

---

*This report explains how VerusTensor models subnet competition for VT emissions compared to Bittensor's dTAO system. The core economic model is the same (market-driven alpha token staking determines emission share), but Verus's protocol-level AMM with simultaneous settlement provides structural MEV resistance that Bittensor's Uniswap V2-based system cannot match. Additional advantages include unlimited subnet slots, no root network gatekeepers, identity recovery, and full transparency of all emission calculations.*
