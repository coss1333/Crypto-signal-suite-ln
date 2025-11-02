from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Signal:
    action: str   # BUY / SELL / NEUTRAL
    score: float  # -1..+1
    reasons: list # list of strings

def combine_rules(ctx: Dict[str, Any]) -> Signal:
    reasons = []
    score = 0.0

    rsi_val = ctx["rsi"]
    mfi_val = ctx["mfi"]
    funding = ctx.get("funding", 0.0)
    basis = ctx.get("basis", 0.0)
    basis_z = ctx.get("basis_z", 0.0)
    oi = ctx.get("oi", 0.0)
    obv_slope = ctx.get("obv_slope", 0.0)
    vol_spike = ctx.get("vol_spike", False)

    if rsi_val < ctx["rsi_os"]:
        score += 0.25; reasons.append(f"RSI {rsi_val:.1f} < oversold {ctx['rsi_os']}")
    if rsi_val > ctx["rsi_ob"]:
        score -= 0.25; reasons.append(f"RSI {rsi_val:.1f} > overbought {ctx['rsi_ob']}")
    if mfi_val < ctx["mfi_os"]:
        score += 0.2; reasons.append(f"MFI {mfi_val:.1f} < oversold {ctx['mfi_os']}")
    if mfi_val > ctx["mfi_ob"]:
        score -= 0.2; reasons.append(f"MFI {mfi_val:.1f} > overbought {ctx['mfi_ob']}")

    if obv_slope > 0:
        score += 0.1; reasons.append("OBV rising (accumulation)")
    elif obv_slope < 0:
        score -= 0.1; reasons.append("OBV falling (distribution)")

    if vol_spike:
        if ctx["spot_last"] > ctx["spot_prev"]:
            score += 0.15; reasons.append("Volume spike with up-close")
        else:
            score -= 0.15; reasons.append("Volume spike with down-close")

    if abs(basis_z) >= ctx["basis_enter"]:
        if basis_z > 0 and funding > 0:
            score -= 0.2; reasons.append(f"Positive basis z={basis_z:.2f} & funding {funding:.4f} (froth -> SELL bias)")
        elif basis_z < 0 and funding < 0:
            score += 0.2; reasons.append(f"Negative basis z={basis_z:.2f} & funding {funding:.4f} (stress -> BUY bias)")

    if oi is not None:
        if ctx["spot_last"] > ctx["spot_prev"] and ctx["oi_change"] > 0:
            score += 0.1; reasons.append("Price↑ + OI↑ (long buildup)")
        if ctx["spot_last"] < ctx["spot_prev"] and ctx["oi_change"] > 0:
            score -= 0.1; reasons.append("Price↓ + OI↑ (short buildup)")

    action = "NEUTRAL"
    if score >= 0.25:
        action = "BUY"
    elif score <= -0.25:
        action = "SELL"

    return Signal(action=action, score=max(-1,min(1,score)), reasons=reasons)
