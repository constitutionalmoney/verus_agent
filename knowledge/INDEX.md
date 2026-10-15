# Verus developer knowledge

Evidence checked 2026-10-15. This is a curated reference snapshot, not a
training claim, live discovery service, or authorization to operate a wallet.

| Topic | Reference | Purpose |
|---|---|---|
| `mobile` | [Mobile v1.1.0-21](MOBILE_V1.1.0-21.md) | Store release, typed deeplinks, review, encryption, gift cards, supported subsets |
| `sdk` | [SDK and primitives](SDK_AND_PRIMITIVES.md) | Commit pins, daemon 1.2.18 compatibility work, migration and validation gaps |
| `dream` | [DREAM apps](DREAM_APPS.md) | Request lifecycle and a proposed application structure |
| `resources` | [Bootstrap and treasury](BOOTSTRAP_AND_TREASURY.md) | Browser bootstrap discovery and explicitly simulated economics |
| `community` | [Community projects](COMMUNITY_PROJECTS.md) | The 20 requested discussions, linked resources, activity, reusable examples and limits |

Read without initialization or network access:

```python
from verus_agent.knowledge import get_knowledge

mobile_reference = get_knowledge("mobile")
```

The agent task capability `verus.knowledge.get` accepts `topic` and returns
this same content. It is a read-only capability; the ordinary agent startup
still requires its Testnet initialization checks. Use the Python accessor for
fully offline retrieval. Knowledge files ship in the wheel.

Evidence labels used throughout:

- **Source fact:** observed in a release, pinned source, or live public page.
- **Community report:** author statements or demonstrations; not independently
  reproduced by this change.
- **Operator policy:** this repository's Testnet, privacy, and human approval rules.
- **Proposal/inference:** a suggested integration design, not an upstream guarantee.
- **Unverified/unavailable:** an explicit gap, not proof of absence.

The recorded latest store release is **v1.1.0-21**. Android's live store
metadata confirms `1.1.0-21`; Apple exposes marketing version `1.1.0`. The
available GitHub source tag is `v1.1.0-20`; no claim equates that source tree
with the `-21` store binary.

Keep all current activation and per-mutation approval controls. Examples use
synthetic values. Nothing here activates App Encryption, funds or claims a
gift card, writes an identity, signs data, downloads a bootstrap, deploys an
app, or uses Mainnet. Recheck pinned sources and exact device/build behavior
before a separately authorized implementation or external test.
