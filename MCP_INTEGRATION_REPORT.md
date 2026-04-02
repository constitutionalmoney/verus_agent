# VerusIDX MCP Integration Report

## Executive Summary

The [verusidx-mcp](https://github.com/vdappdev2/verusidx-mcp) project provides **7 MCP servers with 49 tools** that give AI agents direct, local access to the Verus blockchain via the Model Context Protocol. The Verus Agent currently uses a custom `VerusCLI` wrapper that makes JSON-RPC calls to `verusd` either via subprocess (local binary) or HTTP (remote API). Integrating the MCP servers provides **safety guardrails** (spending limits, audit logging, read-only mode), **new capabilities** the agent lacks, and a **standardized protocol** that any MCP-compatible AI client can leverage.

---

## MCP Server Inventory

| Package | Tools | Domain |
|---|---|---|
| `@verusidx/chain-mcp` | 11 | Foundation — chain discovery, daemon management, health, currency lookup, raw tx |
| `@verusidx/identity-mcp` | 11 | VerusID lifecycle — create, update, revoke, recover, timelock, history |
| `@verusidx/send-mcp` | 8 | Currency sends, conversions, cross-chain transfers, balances |
| `@verusidx/data-mcp` | 7 | On-chain data retrieval, decryption, signing, verification, viewing keys |
| `@verusidx/address-mcp` | 6 | Address generation, validation, listing (transparent + shielded) |
| `@verusidx/marketplace-mcp` | 5 | Atomic swap offers and trades |
| `@verusidx/definecurrency-mcp` | 1 | Currency definition and launch |

---

## Conditions When MCP Should Be Used

### 1. Safety-Critical Write Operations (ALWAYS route to MCP)

The MCP servers enforce **spending limits**, **audit logging**, and optional **read-only mode** — none of which the agent's `VerusCLI` wrapper provides. Any operation that spends funds or modifies on-chain state should route through MCP when available:

| Agent Capability | MCP Server | MCP Tool | Safety Benefit |
|---|---|---|---|
| `verus.currency.send` | send-mcp | `sendcurrency` | Per-currency spending caps enforced before RPC |
| `verus.currency.convert` | send-mcp | `sendcurrency` | Spending limits on conversion amounts |
| `verus.bridge.cross` | send-mcp | `sendcurrency` | Bridge transfers capped per spending-limits.json |
| `verus.marketplace.make_offer` | marketplace-mcp | `makeoffer` | Audit log of every offer created |
| `verus.marketplace.take_offer` | marketplace-mcp | `takeoffer` | Audit log + spending limit on acceptance |
| `verus.marketplace.close_offers` | marketplace-mcp | `closeoffers` | Audit trail |
| `verus.identity.create` | identity-mcp | `registernamecommitment` + `registeridentity` | Audit log |
| `verus.identity.update` | identity-mcp | `updateidentity` | Audit log |
| `verus.identity.vault` | identity-mcp | `setidentitytimelock` | Audit log |
| `verus.currency.launch` | definecurrency-mcp | `definecurrency` | Audit log |

### 2. New Capabilities Not in the Agent (route exclusively to MCP)

These operations have no current handler in the Verus Agent and are only available through MCP:

| MCP Tool | MCP Server | New Capability Added |
|---|---|---|
| `getwalletinfo` | chain-mcp | Wallet balances, keypoolsize, unconfirmed balance |
| `help` | chain-mcp | On-demand RPC documentation for any daemon command |
| `signrawtransaction` | chain-mcp | Sign raw transaction inputs (offline signing) |
| `sendrawtransaction` | chain-mcp | Broadcast pre-signed transactions |
| `refresh_chains` | chain-mcp | Auto-discover running Verus daemons on the machine |
| `status` | chain-mcp | Registry freshness + daemon reachability check |
| `verusd` / `stop` | chain-mcp | Start/stop daemon instances |
| `getidentityhistory` | identity-mcp | Full revision history of any VerusID |
| `listidentities` | identity-mcp | List all wallet VerusIDs (spendable/signable/watch) |
| `revokeidentity` | identity-mcp | Direct identity revocation (vs. agent's swarm_security) |
| `recoveridentity` | identity-mcp | Direct identity recovery |
| `getcurrencybalance` | send-mcp | Multi-currency balances for any address |
| `getcurrencyconverters` | send-mcp | Find fractional baskets for conversion paths |
| `listcurrencies` | send-mcp | Search and filter all currencies |
| `gettransaction` | send-mcp | Transaction details by txid |
| `listtransactions` | send-mcp | Recent wallet transactions with pagination |
| `z_listreceivedbyaddress` | data-mcp | List all data/txs received at a z-address |
| `z_exportviewingkey` | data-mcp | Export viewing key for selective access sharing |
| `z_viewtransaction` | data-mcp | Detailed shielded transaction inspection |
| `z_importviewingkey` | data-mcp | Import viewing key for decryption access |
| `verifysignature` | data-mcp | Verify data signatures (more general than verifymessage) |
| `validateaddress` | address-mcp | Validate and inspect any address |
| `z_validateaddress` | address-mcp | Validate shielded addresses |
| `getaddressesbyaccount` | address-mcp | List transparent addresses by account |
| `getnewaddress` | address-mcp | Generate new transparent R-address |
| `z_getnewaddress` | address-mcp | Generate new Sapling zs-address |
| `listopenoffers` | marketplace-mcp | List wallet's own open offers |

### 3. When Agent Lacks Direct CLI Access (FALLBACK to MCP)

If `VERUS_CLI_PATH` is not set and the remote API is unreachable, the MCP servers can serve as an alternative backend since they discover and connect to local daemons independently via filesystem credential reading.

### 4. When Audit Compliance Is Required

Any deployment requiring a tamper-evident audit trail of blockchain interactions should route ALL write operations through MCP. The MCP servers produce date-stamped, append-only JSONL audit files with restrictive file permissions.

### 5. Multi-Chain Operations

When the agent needs to interact with multiple Verus chains simultaneously (mainnet + testnet, or PBaaS sidechains), the MCP `chain-mcp` registry provides automatic discovery and the `chain` parameter on every tool enables explicit chain targeting — more robust than the agent's single `config.network` approach.

### 6. Read-Only Investigative Mode

When the agent is tasked with data retrieval, balance checking, identity lookup, or market analysis without any writes, the MCP servers can be run with `VERUSIDX_READ_ONLY=true` which completely removes write tools from the tool list, providing an additional safety layer.

---

## Capability Overlap Matrix

| Agent Capability | Direct CLI | MCP Equivalent | Preferred Path |
|---|---|---|---|
| `verus.identity.create` | `registernamecommitment` + `registeridentity` | identity-mcp: same | **MCP** (audit) |
| `verus.identity.update` | `updateidentity` | identity-mcp: `updateidentity` | **MCP** (audit) |
| `verus.identity.vault` | `updateidentity` (flags) | identity-mcp: `setidentitytimelock` | **MCP** (audit) |
| `verus.currency.launch` | `definecurrency` | definecurrency-mcp: `definecurrency` | **MCP** (audit) |
| `verus.currency.convert` | `sendcurrency` | send-mcp: `sendcurrency` | **MCP** (spending limit) |
| `verus.currency.send` | `sendcurrency` | send-mcp: `sendcurrency` | **MCP** (spending limit) |
| `verus.currency.estimate` | `estimateconversion` | send-mcp: `estimateconversion` | Either (read-only) |
| `verus.storage.store` | `updateidentity` | identity-mcp: `updateidentity` | **MCP** (audit) |
| `verus.storage.retrieve` | `getidentitycontent` | identity-mcp: `getidentitycontent` | Either (read-only) |
| `verus.login.authenticate` | `signmessage` | data-mcp: `signdata` | Either |
| `verus.login.validate` | `verifymessage` | data-mcp: `verifysignature` | Either |
| `verus.bridge.cross` | `sendcurrency` (exportto) | send-mcp: `sendcurrency` | **MCP** (spending limit) |
| `verus.market.monitor` | `getcurrencystate` | chain-mcp: `getcurrency` | Either (read-only) |
| `verus.messaging.send_encrypted` | `signdata` | data-mcp: `signdata` | Either |
| `verus.messaging.receive_decrypt` | `decryptdata` | data-mcp: `decryptdata` | Either |
| `verus.marketplace.make_offer` | `makeoffer` | marketplace-mcp: `makeoffer` | **MCP** (audit + limit) |
| `verus.marketplace.take_offer` | `takeoffer` | marketplace-mcp: `takeoffer` | **MCP** (audit + limit) |
| `verus.marketplace.list_open_offers` | `getoffers` | marketplace-mcp: `getoffers` | Either (read-only) |
| `verus.marketplace.close_offers` | `closeoffers` | marketplace-mcp: `closeoffers` | **MCP** (audit) |
| `verus.mining.start` | `setgenerate` | — | Direct CLI only |
| `verus.mining.info` | `getmininginfo` | — | Direct CLI only |
| `verus.cli.execute` | any RPC | chain-mcp: `help` | MCP for docs, CLI for exec |

---

## Routing Decision Logic

```
For each incoming capability request:
  1. Is MCP available? (servers discovered and healthy)
     NO  → route to Direct CLI (fallback)
     YES → continue
  2. Is this a WRITE operation (sends funds, modifies state)?
     YES → route to MCP (safety: spending limits + audit)
  3. Is this a new capability only MCP provides?
     YES → route to MCP (only option)
  4. Is VERUSIDX_READ_ONLY=true?
     YES → route to MCP (enforced read-only)
  5. Otherwise → route to MCP (prefer MCP for consistency)
     Fallback to Direct CLI if MCP call fails
```

---

## Architecture After Integration

```
                    ┌─────────────────────────────┐
                    │   VerusBlockchainAgent       │
                    │   (agent.py)                 │
                    │                              │
                    │  ┌─────────────────────────┐ │
                    │  │   MCP Router             │ │
                    │  │   (mcp_client.py)        │ │
                    │  │                          │ │
                    │  │  ┌─────┐  ┌──────────┐  │ │
                    │  │  │ MCP │  │ Direct   │  │ │
                    │  │  │ Path│  │ CLI Path │  │ │
                    │  │  └──┬──┘  └────┬─────┘  │ │
                    │  └─────┼──────────┼────────┘ │
                    └────────┼──────────┼──────────┘
                             │          │
              ┌──────────────┘          └──────┐
              ▼                                ▼
    ┌──────────────────┐            ┌─────────────────┐
    │ verusidx MCP     │            │ VerusCLI        │
    │ servers (stdio)  │            │ (subprocess/API)│
    │ 7 servers,49 tools│           └────────┬────────┘
    └────────┬─────────┘                     │
             │                               │
             └───────────┬───────────────────┘
                         ▼
                  ┌─────────────┐
                  │   verusd     │
                  │ (local node) │
                  └─────────────┘
```
