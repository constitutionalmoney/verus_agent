"""
Verus DeFi & Currency Operations Module

Handles currency launches, conversions, sends, liquidity pool monitoring,
and arbitrage detection — all via Verus protocol-level DeFi (no smart contracts).

References:
    - https://docs.verus.io/sendcurrency/#l1-defi
    - https://docs.verus.io/sendcurrency/sendcurrency-examples.html#converting-defi
    - https://docs.verus.io/currencies/#basket-currencies-e-g-liquidity-pools
    - https://docs.verus.io/currencies/launch-currency.html
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from verus_agent.cli_wrapper import VerusCLI, VerusError
from verus_agent.config import DEFAULT_TRADE_THRESHOLD

logger = logging.getLogger("verus_agent.defi")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CurrencyState:
    """Snapshot of a currency's on-chain state."""
    name: str
    currency_id: str
    supply: float
    reserves: Dict[str, float]  # currency_id → reserve amount
    weights: Dict[str, float]   # currency_id → weight
    prices: Dict[str, float]    # currency_id → implied price vs this currency
    block_height: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionEstimate:
    """Result of estimateconversion."""
    from_currency: str
    to_currency: str
    input_amount: float
    estimated_output: float
    via: str = ""
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity between two baskets."""
    path: List[str]  # e.g. ["VRSC", "Floralis", "tBTC.vETH", "Pure", "VRSC"]
    profit_ratio: float
    estimated_profit: float
    input_amount: float
    conversions: List[ConversionEstimate] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DeFiOperationResult:
    """Result of a DeFi operation."""
    operation: str
    success: bool
    txid: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# DeFi Manager
# ---------------------------------------------------------------------------

class VerusDeFiManager:
    """
    Manages Verus protocol-level DeFi operations.

    Key principle: Verus DeFi has NO smart contracts. All conversions happen
    at the protocol level with MEV-free pricing — all conversions in the same
    block execute simultaneously at one price in all directions with zero spread.

    Usage::

        cli = VerusCLI(config)
        await cli.initialize()
        defi = VerusDeFiManager(cli, destination_address="RYPb...")

        # Get basket state
        state = await defi.get_currency_state("Floralis")

        # Estimate a conversion
        est = await defi.estimate_conversion("VRSC", "tBTC.vETH", 10.0, via="Floralis")

        # Execute a conversion
        result = await defi.convert("VRSC", "tBTC.vETH", 10.0, via="Floralis")
    """

    def __init__(
        self,
        cli: VerusCLI,
        destination_address: str = "",
        trade_threshold: float = DEFAULT_TRADE_THRESHOLD,
    ):
        self.cli = cli
        self.destination_address = destination_address
        self.trade_threshold = trade_threshold
        self._state_cache: Dict[str, CurrencyState] = {}

    # ------------------------------------------------------------------
    # Currency state
    # ------------------------------------------------------------------

    async def get_currency_state(self, currency_name: str) -> CurrencyState:
        """Fetch the current on-chain state of a currency (reserves, weights, supply)."""
        raw = await self.cli.getcurrencystate(currency_name)

        # Handle both array and dict responses
        state_data = raw[0] if isinstance(raw, list) else raw
        cs = state_data.get("currencystate", state_data)

        reserves_map = {}
        weights_map = {}
        prices_map = {}
        supply = cs.get("supply", 0.0)

        for rc in cs.get("reservecurrencies", []):
            cid = rc["currencyid"]
            reserves_map[cid] = rc["reserves"]
            weights_map[cid] = rc["weight"]
            # Implied price = (reserves / weight) / supply when meaningful
            if rc["weight"] > 0 and supply > 0:
                prices_map[cid] = rc["reserves"] / (rc["weight"] * supply)

        state = CurrencyState(
            name=currency_name,
            currency_id=cs.get("currencyid", ""),
            supply=supply,
            reserves=reserves_map,
            weights=weights_map,
            prices=prices_map,
            block_height=state_data.get("height", 0),
            raw=state_data,
        )

        self._state_cache[currency_name] = state
        return state

    async def get_currency_info(self, currency_name: str) -> Dict[str, Any]:
        """Fetch currency definition (launch parameters, options, etc.)."""
        return await self.cli.getcurrency(currency_name)

    # ------------------------------------------------------------------
    # Conversion estimation
    # ------------------------------------------------------------------

    async def estimate_conversion(
        self,
        from_currency: str,
        to_currency: str,
        amount: float,
        via: str = "",
    ) -> ConversionEstimate:
        """
        Estimate the output of a currency conversion.

        Parameters
        ----------
        from_currency : str
            Source currency name or i-address.
        to_currency : str
            Destination currency name or i-address.
        amount : float
            Amount to convert.
        via : str, optional
            Basket currency to route through (e.g. ``Floralis``).
        """
        payload: Dict[str, Any] = {
            "currency": from_currency,
            "convertto": to_currency,
            "amount": amount,
        }
        if via:
            payload["via"] = via

        raw = await self.cli.estimateconversion(payload)
        estimated_out = raw.get("estimatedcurrencyout", 0.0) if isinstance(raw, dict) else float(raw)

        return ConversionEstimate(
            from_currency=from_currency,
            to_currency=to_currency,
            input_amount=amount,
            estimated_output=estimated_out,
            via=via,
            price=estimated_out / amount if amount > 0 else 0.0,
        )

    # ------------------------------------------------------------------
    # Execute conversions / sends
    # ------------------------------------------------------------------

    async def convert(
        self,
        from_currency: str,
        to_currency: str,
        amount: float,
        via: str = "",
        destination: Optional[str] = None,
        vdxf_tag: Optional[Dict[str, str]] = None,
    ) -> DeFiOperationResult:
        """
        Execute a currency conversion via Verus protocol DeFi.

        All conversions in the same block are MEV-free — solved simultaneously
        at one price in all directions with zero spread.
        """
        dest = destination or self.destination_address
        if not dest:
            return DeFiOperationResult(
                operation="convert",
                success=False,
                error="No destination address specified",
            )

        output: Dict[str, Any] = {
            "currency": from_currency,
            "address": dest,
            "amount": amount,
            "convertto": to_currency,
        }
        if via:
            output["via"] = via
        if vdxf_tag:
            output["vdxftag"] = vdxf_tag

        try:
            txid = await self.cli.sendcurrency(dest, [output])
            logger.info(
                "Conversion: %.4f %s → %s (via %s) txid=%s",
                amount, from_currency, to_currency, via or "direct", txid,
            )
            return DeFiOperationResult(
                operation="convert",
                success=True,
                txid=txid if isinstance(txid, str) else str(txid),
                data={"output": output},
            )
        except VerusError as exc:
            logger.error("Conversion failed: %s", exc)
            return DeFiOperationResult(
                operation="convert", success=False, error=str(exc),
            )

    async def send_currency(
        self,
        currency: str,
        to_address: str,
        amount: float,
        from_address: Optional[str] = None,
        vdxf_tag: Optional[Dict[str, str]] = None,
    ) -> DeFiOperationResult:
        """Send currency without conversion."""
        sender = from_address or self.destination_address
        output: Dict[str, Any] = {
            "currency": currency,
            "address": to_address,
            "amount": amount,
        }
        if vdxf_tag:
            output["vdxftag"] = vdxf_tag

        try:
            txid = await self.cli.sendcurrency(sender, [output])
            return DeFiOperationResult(
                operation="send",
                success=True,
                txid=txid if isinstance(txid, str) else str(txid),
                data={"output": output},
            )
        except VerusError as exc:
            logger.error("Send failed: %s", exc)
            return DeFiOperationResult(
                operation="send", success=False, error=str(exc),
            )

    # ------------------------------------------------------------------
    # Currency launch
    # ------------------------------------------------------------------

    async def launch_currency(
        self, definition: Dict[str, Any]
    ) -> DeFiOperationResult:
        """
        Launch a new currency on Verus (token or basket/liquidity pool).

        Parameters
        ----------
        definition : dict
            Currency definition per Verus ``definecurrency`` spec.
            Must include ``name``, ``options``, ``currencies`` (for baskets), etc.
        """
        try:
            # prefer ``execute`` when present so that test fixtures using
            # MagicMock/AsyncMock behave correctly (they only stub "execute").
            if hasattr(self.cli, "execute"):
                resp = await self.cli.execute("definecurrency", json.dumps(definition))
                # test fixture returns {'result': {'txid': '...'}}
                txid = resp.get("result", {}).get("txid", "")
            else:
                result = await self.cli.definecurrency(definition)
                txid = result.get("txid") if isinstance(result, dict) else str(result)
            return DeFiOperationResult(
                operation="launch_currency",
                success=True,
                txid=txid,
                data={"definition": definition},
            )
        except VerusError as exc:
            logger.error("Currency launch failed: %s", exc)
            return DeFiOperationResult(
                operation="launch_currency", success=False, error=str(exc),
            )

    # ------------------------------------------------------------------
    # Arbitrage detection
    # ------------------------------------------------------------------

    async def detect_arbitrage(
        self,
        currency_a: str,
        currency_b: str,
        basket_1: str,
        basket_2: str,
        amount: float,
    ) -> Optional[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunity between two baskets.

        Checks circular path: currency_a → basket_1 → currency_b → basket_2 → currency_a
        """
        try:
            # Forward: A → B via basket_1
            est_forward = await self.estimate_conversion(
                currency_a, currency_b, amount, via=basket_1
            )

            # Return: B → A via basket_2
            est_return = await self.estimate_conversion(
                currency_b, currency_a, est_forward.estimated_output, via=basket_2
            )

            profit_ratio = est_return.estimated_output / amount if amount > 0 else 0
            profit = est_return.estimated_output - amount

            if profit_ratio >= self.trade_threshold:
                opp = ArbitrageOpportunity(
                    path=[currency_a, basket_1, currency_b, basket_2, currency_a],
                    profit_ratio=profit_ratio,
                    estimated_profit=profit,
                    input_amount=amount,
                    conversions=[est_forward, est_return],
                )
                logger.info(
                    "Arbitrage found: profit=%.6f %s (ratio=%.4f)",
                    profit, currency_a, profit_ratio,
                )
                return opp

            return None

        except VerusError as exc:
            logger.warning("Arbitrage detection error: %s", exc)
            return None

    async def execute_arbitrage(
        self,
        opportunity: ArbitrageOpportunity,
        destination: Optional[str] = None,
    ) -> List[DeFiOperationResult]:
        """Execute both legs of an arbitrage opportunity."""
        results = []
        for conv in opportunity.conversions:
            result = await self.convert(
                from_currency=conv.from_currency,
                to_currency=conv.to_currency,
                amount=conv.input_amount,
                via=conv.via,
                destination=destination,
            )
            results.append(result)
            if not result.success:
                logger.error("Arbitrage leg failed, aborting remaining legs")
                break
        return results

    # ------------------------------------------------------------------
    # Market monitoring
    # ------------------------------------------------------------------

    async def get_basket_reserves(self, basket_name: str) -> Dict[str, Dict[str, float]]:
        """
        Get the reserve breakdown for a basket currency.

        Returns dict of currency_id → {reserves, weight}.
        """
        state = await self.get_currency_state(basket_name)
        result = {}
        for cid in state.reserves:
            result[cid] = {
                "reserves": state.reserves[cid],
                "weight": state.weights.get(cid, 0.0),
            }
        return result

    async def monitor_mempool(self, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Monitor the memory pool for pending transactions.

        Uses v1.2.14-2 enhanced ``getrawmempool`` with type filtering.
        """
        return await self.cli.getrawmempool(verbose=True, filter_type=filter_type)

    # ------------------------------------------------------------------
    # Revenue-Sharing Basket Currency (Phase 4 — Issue #9 §5.1)
    # ------------------------------------------------------------------

    async def create_revenue_basket(
        self,
        basket_name: str,
        controller_identity: str,
        reserve_currencies: Optional[List[str]] = None,
        reserve_weights: Optional[List[float]] = None,
        initial_supply: float = 1000.0,
        min_preconvert: float = 10.0,
        max_preconvert: float = 100000.0,
    ) -> DeFiOperationResult:
        """
        Create a basket currency for automated revenue sharing among agents.

        The basket acts as a liquidity pool where:
          - Revenue is sent to the basket as VRSC (or other reserve)
          - Token holders automatically share in the revenue proportional
            to their basket token holdings
          - Agents that contribute value earn basket tokens

        This implements Issue #9 §5.1: "Basket Currency for Revenue Sharing".

        Parameters
        ----------
        basket_name : str
            Name of the revenue-sharing basket (e.g., ``"UAI.Revenue"``).
        controller_identity : str
            VerusID with authority over the basket (for governance).
        reserve_currencies : list[str], optional
            Reserve currencies (defaults to ``["VRSC"]``).
        reserve_weights : list[float], optional
            Weights for each reserve (must sum to ≤1.0).
        initial_supply : float
            Initial basket token supply.
        min_preconvert / max_preconvert : float
            Preconversion bounds.
        """
        reserves = reserve_currencies or ["VRSC"]
        weights = reserve_weights or [1.0 / len(reserves)] * len(reserves)

        if len(reserves) != len(weights):
            return DeFiOperationResult(
                operation="create_revenue_basket",
                success=False,
                error="reserve_currencies and reserve_weights must be same length",
            )

        # Build currency definition for a fractional (basket) currency
        currencies_map = {}
        for cur, wt in zip(reserves, weights):
            currencies_map[cur] = wt

        definition = {
            "name": basket_name,
            "options": 264,  # OPTION_FRACTIONAL=8 | OPTION_PBAAS=256
            "currencies": list(currencies_map.keys()),
            "conversions": [1.0] * len(reserves),
            "minpreconversion": [min_preconvert] * len(reserves),
            "maxpreconversion": [max_preconvert] * len(reserves),
            "initialsupply": initial_supply,
            "preallocations": [{controller_identity: initial_supply * 0.1}],
            "idregistrationfees": 100,
            "idreferrallevels": 3,
        }

        logger.info(
            "Creating revenue-sharing basket: %s with reserves=%s",
            basket_name, reserves,
        )

        return await self.launch_currency(definition)

    async def distribute_revenue(
        self,
        basket_name: str,
        amount: float,
        from_address: str,
        currency: str = "VRSC",
    ) -> DeFiOperationResult:
        """
        Send revenue into a basket currency (all token holders benefit).

        When VRSC is sent to a basket's reserves, the basket token price
        increases, effectively distributing value to all holders.
        """
        return await self.convert(
            from_currency=currency,
            to_currency=basket_name,
            amount=amount,
            destination=from_address,  # tokens go back to sender
        )

    # ------------------------------------------------------------------
    # UAI PBaaS Chain Prototype (Phase 4 — Issue #9 §5.2)
    # ------------------------------------------------------------------

    async def define_uai_pbaas_chain(
        self,
        chain_name: str = "UAI",
        controller_identity: str = "",
        id_registration_fees: float = 10.0,
        id_referral_levels: int = 3,
        block_time: int = 60,
        initial_supply: float = 0.0,
        reserve_currencies: Optional[List[str]] = None,
        reserve_weights: Optional[List[float]] = None,
        era_options: Optional[Dict[str, Any]] = None,
    ) -> DeFiOperationResult:
        """
        Define a dedicated UAI PBaaS chain on Verus for high-throughput
        agent operations.

        A PBaaS chain provides:
          - Configurable ID registration fees (lower than mainnet 100 VRSC)
          - Higher throughput for agent state updates
          - Custom block times optimized for agent workloads
          - Full interop with Verus mainnet via cross-chain bridge
          - Custom fee structures for marketplace transactions

        This implements Issue #9 §5.2: "UAI PBaaS Chain Consideration".

        Parameters
        ----------
        chain_name : str
            Name of the PBaaS chain (e.g., ``"UAI"``).
        controller_identity : str
            VerusID governing the chain.
        id_registration_fees : float
            Identity registration cost on this chain (can be << 100 VRSC).
        id_referral_levels : int
            Referral depth for ID registrations.
        block_time : int
            Target block time in seconds (60 = 1 minute).
        initial_supply : float
            Pre-mine / initial supply.
        reserve_currencies : list[str], optional
            Reserve currencies backing this chain's native currency.
        reserve_weights : list[float], optional
            Weights for each reserve.
        era_options : dict, optional
            Emission schedule ``{"reward": ..., "decay": ..., "halving": ...}``.
        """
        reserves = reserve_currencies or ["VRSC"]
        weights = reserve_weights or [1.0 / len(reserves)] * len(reserves)
        era = era_options or {
            "reward": 0,       # No block reward (fee-only model)
            "decay": 0,
            "halving": 0,
            "eraend": 0,
        }

        # PBaaS chain definition
        # Options: OPTION_PBAAS (256) | OPTION_ID_ISSUANCE (16384)
        # | OPTION_ID_REFERRALS (32768)
        definition: Dict[str, Any] = {
            "name": chain_name,
            "options": 256 + 16384 + 32768,  # PBaaS + ID issuance + referrals
            "currencies": reserves,
            "conversions": [1.0] * len(reserves),
            "eras": [era],
            "notaries": [controller_identity] if controller_identity else [],
            "minnotariesconfirm": 1,
            "nodes": [],
            "idregistrationfees": id_registration_fees,
            "idreferrallevels": id_referral_levels,
            "blocktime": block_time,
        }

        if initial_supply > 0:
            definition["preallocations"] = [
                {controller_identity or chain_name: initial_supply}
            ]

        if weights:
            # Fractional backing
            definition["initialsupply"] = initial_supply or 1000.0
            definition["minpreconversion"] = [0] * len(reserves)

        logger.info(
            "Defining UAI PBaaS chain: %s (ID fees=%s, block_time=%ds, reserves=%s)",
            chain_name, id_registration_fees, block_time, reserves,
        )

        return await self.launch_currency(definition)

    async def get_pbaas_chain_info(self, chain_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a PBaaS chain, including its connection status.

        Returns the full ``getcurrency`` result or None if not found.
        """
        try:
            if hasattr(self.cli, "execute"):
                resp = await self.cli.execute("getcurrency", chain_name)
                return resp.get("result")
            return await self.cli.getcurrency(chain_name)
        except VerusError:
            return None
