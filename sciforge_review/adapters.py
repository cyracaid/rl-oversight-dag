"""Instrument adapter contract (shape C).

Read-only, deliberately small.  An adapter exposes capabilities; a run records
what was asked, what happened, and a failure code.  Phase 0 ships a simulated
adapter only: no device, no credentials, no physical side effect.

The contract is the point.  AutoDNA wraps 20+ instrument classes as composable
atomic services, Shusheng·Duanzhi unifies the physical layer, and Xiaolai
standardizes an instruction set.  SciForge does not need to own hardware; it
needs a vocabulary in which an instrument run can be cited as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class InstrumentCapability:
    capability_id: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    failure_codes: tuple[str, ...]


@dataclass(frozen=True)
class InstrumentRun:
    run_id: str
    capability_id: str
    params: dict
    status: str  # "succeeded" | "failed" | "rejected"
    result: dict = field(default_factory=dict)
    failure_code: str | None = None
    started_at: str = field(default_factory=_now)
    finished_at: str = field(default_factory=_now)


class InstrumentAdapter(Protocol):
    def capabilities(self) -> tuple[InstrumentCapability, ...]: ...

    def run(self, capability_id: str, params: dict) -> InstrumentRun: ...


class SimulatedAdapter:
    """Deterministic stand-in used by the demo and the tests."""

    def __init__(self) -> None:
        self._caps = (
            InstrumentCapability(
                capability_id="plate.read_absorbance",
                inputs=("plate_id", "wavelength_nm"),
                outputs=("absorbance", "well_count"),
                failure_codes=("bubble", "saturated", "plate_missing"),
            ),
        )

    def capabilities(self) -> tuple[InstrumentCapability, ...]:
        return self._caps

    def run(self, capability_id: str, params: dict) -> InstrumentRun:
        cap = next((c for c in self._caps if c.capability_id == capability_id), None)
        if cap is None:
            return InstrumentRun(
                run_id="sim-unknown",
                capability_id=capability_id,
                params=params,
                status="rejected",
                failure_code="unknown_capability",
            )
        if params.get("simulate") == "bubble":
            return InstrumentRun(
                run_id=f"sim-{capability_id}",
                capability_id=capability_id,
                params=params,
                status="failed",
                failure_code="bubble",
            )
        return InstrumentRun(
            run_id=f"sim-{capability_id}",
            capability_id=capability_id,
            params=params,
            status="succeeded",
            result={"absorbance": [0.12, 0.18], "well_count": 2},
        )
