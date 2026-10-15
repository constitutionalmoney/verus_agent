# Bootstrap discovery and ID treasury simulation

Public pages checked 2026-10-15. These are reference resources; no bootstrap
was downloaded, simulation executed, daemon launched or chain action performed.

## Browser-selectable PBaaS bootstraps

[bootstrap.verus.expert](https://bootstrap.verus.expert/) now exposes clickable
chain entries, so users can select a PBaaS chain and its snapshot without
manually composing the full archive URL. The index links vARRR, vDEX and CHIPS,
and directs VRSC users to bootstrap.verus.io.

| Landing page | Snapshot timestamp displayed (UTC) |
|---|---|
| [vARRR](https://bootstrap.verus.expert/e9e10955b7d16031e3d6f55d9c908a038e3ae47d-bootstrap) | 2026-10-12 04:59:07 |
| [vDEX](https://bootstrap.verus.expert/53fe39eea8c06bba32f1a4e20db67e5524f0309d-bootstrap) | 2026-10-13 04:55:07 |
| [CHIPS](https://bootstrap.verus.expert/f315367528394674d45277e369629605a1c3ce9f-bootstrap) | 2026-10-14 04:59:46 |

Landing pages list archive downloads, MD5/SHA256/SHA512 files and VerusID
signatures, plus chain folder, height and hash. Availability of those links
does not prove archive integrity, signer trust or synchronization. For a
separately authorized installation, positively verify target network/chain,
snapshot provenance, strong checksum/signature, storage destination and
recovery plan before using any downloaded data. Never overwrite wallet data.
The linked older wiki how-to redirected to a JavaScript wiki root and was not
verified as a current installation procedure.

These listings include production chains. This repository remains Testnet-only;
recording discovery knowledge does not authorize using those snapshots or
running an installer/daemon. A request for this knowledge update is not runtime
or download authorization.

## ID Treasury Model

[idtreasury.buildwithdreams.com](https://idtreasury.buildwithdreams.com/) is a
community Streamlit simulator, inspected in Chrome. Current controls:

| Control | Observed values |
|---|---|
| Mode | `Market Only` or `ID Treasury Growth` |
| Growth steps | 1 to 1,000; default 20 |
| DreamTree SubIDs per step | 0 to 100,000; default 0 |
| Revenue per subID ($) | 0 to 5; default 0.50 |

Select **ID Treasury Growth** to expose the ID revenue inputs. The current
page's help says shocks ramp gradually across steps. The user's explanation
that an iteration can represent a day/week/month is a modeling interpretation,
not a built-in clock. Choose and document the period assumption explicitly.

The About page models approximately $0.50 net per DreamTree subID after
referrals flowing into reserves without minting. This is the simulator
author's methodology, not independently verified chain economics. The supplied
explanation of a $0.75 gross registration fee versus $0.50 average referral-net
inflow is **user-provided and unverified here**; it is not a universal VerusID
fee rule.

Current tabs are **Supply & NAV**, **Compositions**, **Basket Cards**, and
**About**. The supplied instruction to look in “Baskets” appears to refer to
older UI wording; inspect basket composition/cards for modeled reserve changes.
Current default SubIDs per step is zero, so setting positive growth is necessary
to model ID-driven inflow. No outputs were generated or checked in this run.

No source repository, release/data timestamp or independent mathematical
validation was exposed by the page. Claims of live calibration or exact AMM
mechanics remain author claims. Label inputs **ASSUMED** and outputs
**SIMULATED**; do not treat them as a forecast, guarantee, valuation, reserve
attestation or investment instruction.

## Emission Model Planner

[emp.verus.trading](https://emp.verus.trading/) redirects to
[emp.buildwithdreams.com](https://emp.buildwithdreams.com/). The live Verus
PBaaS E.M.P. UI offers era forms/Expert JSON, block time, preallocation,
reward/halving/decay/era-end inputs, charts, tables, CSV exports and shareable
configuration links. No source-repository link was exposed. Its decay
explanation is planner documentation, not conformance testing against daemon
1.2.18. Use for proposed emission schedules, then independently validate exact
daemon parameters under separately approved Testnet work.
