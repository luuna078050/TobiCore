"""Shared wall-dynamics analytics for TobyCore/TobyCorp.

This is the reusable microstructure rule derived from the BMT/USDT test:
inspect a three-minute sequence of order-book snapshots instead of treating
one book as a static picture. The result can be fed into TobyCore scoring.
"""
from __future__ import annotations
from typing import Sequence


def _pct(a: float, b: float) -> float:
    return ((b / a) - 1.0) * 100.0 if a else 0.0


def analyze_wall_dynamics(snapshots: Sequence[dict], price: float, window_seconds: int = 180) -> dict:
    rows = [x for x in snapshots if float(x.get("ts", 0)) >= float(snapshots[-1].get("ts", 0)) - window_seconds] if snapshots else []
    if not rows or price <= 0:
        return {"direction":"neutral","score":0.0,"support_shift_3m_pct":0.0,"resistance_shift_3m_pct":0.0,
                "ask_wall_absorption":0.0,"breakout_confirmed":False,"retest_confirmed":False}
    first, last = rows[0], rows[-1]
    support_shift = _pct(float(first.get("bid_wall_price", 0)), float(last.get("bid_wall_price", 0)))
    resistance_shift = _pct(float(first.get("ask_wall_price", 0)), float(last.get("ask_wall_price", 0)))
    prev_ask = max((float(x.get("ask_wall_quote", 0)) for x in rows[:-1]), default=float(last.get("ask_wall_quote", 0)))
    ask_absorption = max(0.0, min(1.0, 1.0 - float(last.get("ask_wall_quote", 0)) / prev_ask)) if prev_ask else 0.0
    breakout = False; level = None
    for a, b in zip(rows, rows[1:]):
        if float(a.get("mid", 0)) <= float(a.get("ask_wall_price", 0)) and float(b.get("mid", 0)) > float(a.get("ask_wall_price", 0)):
            breakout = True; level = float(a.get("ask_wall_price", 0))
    retest = bool(breakout and level and price >= level and abs(price / level - 1) <= 0.0015)
    score = max(-1.0, min(1.0, 0.35 * max(-1,min(1,support_shift/.5)) + 0.35 * max(-1,min(1,ask_absorption*2-1)) + 0.20*(1 if breakout else 0) + 0.10*(1 if retest else 0)))
    direction = "bullish" if score > .18 else "bearish" if score < -.18 else "neutral"
    return {"direction":direction,"score":round(score,4),"support_shift_3m_pct":round(support_shift,5),
            "resistance_shift_3m_pct":round(resistance_shift,5),"ask_wall_absorption":round(ask_absorption,4),
            "breakout_confirmed":breakout,"retest_confirmed":retest}
