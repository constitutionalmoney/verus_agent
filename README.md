# Verus Blockchain Specialist Agent

> _Originally built as a worker for the UAI Cluster Intelligence “neural‑swarm”,  
> this agent can also run as a **stand‑alone container** to assist in developing  
> and operating Verus‑blockchain projects._

The `verus_agent` package wraps the Verus CLI and on‑chain services into a  
self‑contained Python agent. When deployed inside a UAI swarm it registers with  
the swarm coordinator and answers capability‑requests from other agents.  
Outside UAI it exposes the same functionality via an asyncio API and is ideal  
for containerised automation, CI pipelines, or interactive scripts.

---

## 🚀 Key Features

- **Verus CLI integration** with automatic JSON‑RPC and daemon‑version checks.
- **VerusID management**: create, update, vault, revoke, trust, and query.
- **DeFi operations**: launch currencies, convert/send/estimate, bridge, PBaaS.
- **On‑chain storage**: encrypt & chunk data, upload to z‑addresses, retrieve.
- **Authentication**: VerusID‑based login/validation for web/mobile flows.
- **Market monitoring**: basket reserves, pricing alerts.
- **Generic CLI execution** for ad‑hoc commands.

### Optional extensions (toggle via config / env vars)

| Extension | Env variable | Capability examples |
|-----------|--------------|---------------------|
| Swarm security | `VERUS_SECURITY_LEVEL` (`verify_only`, `enforced`, `vault_protected`) | register/verify agents, revoke credentials |
| Marketplace | `VERUS_MARKETPLACE_ENABLED=true` | list offers, create invoices, license models |
| IP protection | `VERUS_IP_PROTECTION_ENABLED=true` | register/verify models, encrypt/decrypt weights |
| Reputation | built‑in; enable via marketplace? | attest, query leaderboard |
| Mobile helper | no toggle; used for payment/login URIs |

(See config.py for the full list of environment overrides.)

### Complete capability list (as of v1.0)

```
verus.identity.create       verus.identity.update        verus.identity.vault
verus.currency.launch       verus.currency.convert       verus.currency.send
verus.currency.estimate     verus.storage.store          verus.storage.retrieve
verus.storage.store_data_wrapper
verus.storage.store_sendcurrency
verus.storage.retrieve_data_wrapper
verus.login.authenticate    verus.login.validate
verus.bridge.cross          verus.market.monitor
verus.cli.execute
verus.messaging.send_encrypted
verus.messaging.receive_decrypt
verus.mining.start
verus.mining.info
verus.staking.status
verus.trust.set_identity_trust
verus.trust.set_currency_trust
verus.trust.get_ratings
verus.marketplace.make_offer
verus.marketplace.take_offer
... (and many more including IP, reputation, PBaaS, mobile, etc.)
```

---

## 🛠 Installation

```bash
# clone repo if not already done
git clone https://github.com/constitutionalmoney/verus_agent.git
cd verus_agent

# create virtualenv and install
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt  # you may need to create this with deps below

# or simply `pip install .` for local development
```

> **Dependencies** (implicit from tests & imports):  
> `aiohttp`, `numpy`, `pytest` (dev), plus whatever the Verus CLI needs.

A `Dockerfile` isn’t included, but building a container is straightforward:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install .
ENV VERUS_API_URL=https://api.verustest.net
ENTRYPOINT ["python","-m","verus_agent.cli"]  # example entrypoint
```

---

## ⚙ Configuration

Most options are controlled via `VerusConfig` or environment variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `VERUS_NETWORK` | `testnet` or `mainnet` | `testnet` |
| `VERUS_API_URL` | Override RPC endpoint | auto‑derived |
| `VERUS_CLI_PATH` | Path to `verus` binary | (auto) |
| `VERUS_DESTINATION_ADDRESS` | Default address for DeFi ops | `""` |
| `UAI_CORE_URL` / `UAI_SWARM_WS_URL` | Swarm URLs | `http://uai-core:8001` / `ws://…` |
| `VERUS_SECURITY_LEVEL` | see above | `disabled` |
| `VERUS_MARKETPLACE_ENABLED` | `true`/`false` | `false` |
| `VERUS_IP_PROTECTION_ENABLED` | `true`/`false` | `false` |
| …and others as defined in config.py.|

Instantiate in code:

```python
from verus_agent import VerusConfig, VerusBlockchainAgent

cfg = VerusConfig()  # picks up ENV vars too
agent = VerusBlockchainAgent(cfg)
await agent.initialize()
await agent.start()   # registers with UAI swarm, if reachable
```

You can also use the modules individually:

```python
from verus_agent.cli_wrapper import VerusCLI
from verus_agent.defi import VerusDeFiManager

cli = VerusCLI(cfg)
await cli.initialize()
defi = VerusDeFiManager(cli)
await defi.send_currency("iAddr...", 10.0)
```

---

## 🌐 UAI Integration

When run inside a UAI cluster the agent:

1. Connects to the **Neural Swarm Coordinator** via `uai_core_url`.
2. Registers itself with an **agent‑type/role/domain** (`SPECIALIST`, `blockchain_verus`).
3. Listens on a websocket (`swarm_ws_url`) for tasks and inter‑agent messages.
4. Uses VerusID VDXF metadata to secure and monetise operations (marketplace, IP, security).

The same codebase can run stand‑alone; simply omit UAI‑specific env vars and call  
methods directly. A headless container can therefore serve as a Verus‑aware helper  
in any environment.

---

## ✅ Testing

```bash
pip install -e .
pytest tests/          # unit tests use mocks, no daemon required
```

Coverage exceeds 90 % for core and extension modules.

---

## 📦 Packaging & Usage

- Published wheels / PyPI not yet available.
- The `verus_agent` package exposes the following top‑level symbols:

```python
from verus_agent import (
    VerusBlockchainAgent,
    VerusConfig,
    VerusCLI,
    VerusIDManager,
    VerusDeFiManager,
    VerusLoginManager,
    VerusStorageManager,
    VerusIPProtection,
    VerusAgentMarketplace,
    VerusSwarmSecurity,
    VerusReputationSystem,
    VerusMobileHelper,
    # …plus enums, dataclasses, helpers
)
```

---

## 📝 License & Contribution

This repository is maintained by **constitutionalmoney**.  
Contributions, bug reports and feature requests are welcome via GitHub Issues/PRs.

---

> **Note:** Although originally designed for the UAI neural‑swarm,  
> the agent makes a fully‑functional, container‑friendly toolkit for  
> anyone building on the Verus blockchain.
