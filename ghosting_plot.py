"""
app/utils/ghosting_plot.py

Plotly figure builder for ghosting scenario visualisations.
Used by 07_ghosting_analysis.py to show source and spread
scenarios side-by-side alongside the criteria text.

Each scenario diagram shows:
  - P1's anchor symptom bar
  - P1's inoculation point (D1 or D2)
  - The ghosted lesion window for P2
  - P2's own symptoms (if any)
  - The exposure window (if recorded)
  - Pass/fail/warn criterion bands shaded behind the timeline
"""

from __future__ import annotations
from datetime import date, timedelta
import plotly.graph_objects as go
from app.utils.clinical import (
    GhostedLesion, Symptom, Exposure, GhostingResult,
    PRIMARY, INCUBATION,
)


# Shared colour palette — matches 08_vca_chart.py
_C = {
    "p1_symptom":   "#378ADD",   # blue  — P1 anchor symptom
    "p1_inoc":      "#1D9E75",   # green — inoculation / D1 / D2
    "ghosted":      "#EF9F27",   # amber — ghosted lesion window
    "p2_symptom":   "#E24B4A",   # red   — P2 symptoms
    "exposure":     "#7F77DD",   # purple — exposure window
    "pass_band":    "rgba(29,158,117,0.08)",
    "fail_band":    "rgba(226,75,74,0.08)",
    "warn_band":    "rgba(239,159,39,0.10)",
    "grid":         "rgba(180,178,169,0.20)",
}

_Y_P1    = 1.0
_Y_P2    = 0.0
_Y_GHOST = 0.0   # ghosted lesion is on P2's row
_BAR_W   = 8
_MARK_S  = 12


def _date_range(items: list) -> tuple[date, date]:
    """Collect all dates from a mixed list and return (min-45d, max+45d)."""
    dates = []
    for item in items:
        if isinstance(item, date):
            dates.append(item)
        elif isinstance(item, (list, tuple)):
            dates.extend(d for d in item if isinstance(d, date))
    if not dates:
        today = date.today()
        return today - timedelta(days=90), today + timedelta(days=30)
    return min(dates) - timedelta(days=45), max(dates) + timedelta(days=45)


def _base_layout(title: str, x_range: tuple, p1_label: str, p2_label: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=13)),
        height=260,
        xaxis=dict(
            type="date",
            range=[x_range[0].isoformat(), x_range[1].isoformat()],
            showgrid=True,
            gridcolor=_C["grid"],
            dtick="M1",
            tickformat="%b %y",
            tickangle=-30,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            tickvals=[_Y_P2, _Y_P1],
            ticktext=[p2_label, p1_label],
            range=[-0.6, 1.6],
            showgrid=False,
            tickfont=dict(size=11),
        ),
        legend=dict(
            orientation="h",
            y=1.18, x=0,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.7)",
            tracegroupgap=0,
        ),
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=60, b=50),
    )


def _grid_lines(fig: go.Figure, x0: date, x1: date):
    for y in [_Y_P1, _Y_P2]:
        fig.add_shape(type="line",
                      x0=x0, y0=y, x1=x1, y1=y,
                      line=dict(color=_C["grid"], width=1, dash="dot"))


def _criterion_band(fig: go.Figure, criterion_status: str,
                    x0: date, x1: date, label: str):
    """Add a translucent band showing pass/fail/warn for a date window."""
    color = {
        "pass": _C["pass_band"],
        "fail": _C["fail_band"],
        "warn": _C["warn_band"],
        "na":   "rgba(0,0,0,0)",
    }.get(criterion_status, "rgba(0,0,0,0)")

    if color == "rgba(0,0,0,0)":
        return

    fig.add_shape(
        type="rect",
        x0=x0, x1=x1,
        y0=-0.5, y1=1.5,
        fillcolor=color,
        line=dict(width=0),
        layer="below",
    )


def build_scenario_figure(
    result: GhostingResult,
    scenario: str,           # "source" or "spread"
    p1_name: str,
    p2_name: str,
    p1_symptom: Symptom,
    p2_symptoms: list[Symptom],
    p2_exposure: Exposure | None,
    criteria: dict,
) -> go.Figure:
    """
    Build a Plotly timeline figure for one ghosting scenario.

    scenario = "source" → show ghosted_source lesion
    scenario = "spread" → show ghosted_spread lesion
    """
    lesion: GhostedLesion = (
        result.ghosted_source if scenario == "source" else result.ghosted_spread
    )

    title = (
        f"Source scenario — if {p2_name} infected {p1_name}"
        if scenario == "source"
        else f"Spread scenario — if {p1_name} infected {p2_name}"
    )

    # --- Collect dates for range ---
    collected_dates = [
        p1_symptom.onset,
        lesion.onset, lesion.end,
    ]
    if p2_exposure:
        collected_dates += [p2_exposure.first, p2_exposure.last]
    for s in p2_symptoms:
        collected_dates.append(s.onset)
    x0, x1 = _date_range(collected_dates)

    fig = go.Figure()
    fig.update_layout(_base_layout(title, (x0, x1), p1_name, p2_name))
    _grid_lines(fig, x0, x1)

    # --- Criterion bands ---
    # Shade the ghosted lesion window with exposure pass/fail colour
    exp_status = criteria.get("exposure", {}).get("status", "na")
    _criterion_band(fig, exp_status, lesion.onset, lesion.end, "exposure")

    # Shade latency window with latency pass/fail colour
    # (between ghosted lesion end and next secondary onset of P2)
    secondary = [s for s in p2_symptoms if s.type == "Secondary Rash/Lesions"]
    if secondary:
        earliest_sec = min(s.onset for s in secondary)
        lat_status = criteria.get("latency", {}).get("status", "na")
        _criterion_band(fig, lat_status, lesion.end, earliest_sec, "latency")

    # --- P2 exposure window ---
    if p2_exposure and p2_exposure.first and p2_exposure.last:
        fig.add_trace(go.Scatter(
            x=[p2_exposure.first, p2_exposure.last],
            y=[_Y_P2, _Y_P2],
            mode="lines",
            line=dict(color=_C["exposure"], width=5, dash="dash"),
            name="Exposure window",
            hovertemplate=(
                f"Exposure: {p2_exposure.first} → {p2_exposure.last}"
                f"<br>Sex types: {', '.join(p2_exposure.sex_types) or '—'}"
                "<extra></extra>"
            ),
        ))

    # --- Ghosted lesion bar ---
    fig.add_trace(go.Scatter(
        x=[lesion.onset, lesion.end],
        y=[_Y_GHOST, _Y_GHOST],
        mode="lines",
        line=dict(color=_C["ghosted"], width=_BAR_W, dash="solid"),
        name=f"Ghosted {'source' if scenario == 'source' else 'spread'} lesion",
        hovertemplate=(
            f"Ghosted lesion<br>{lesion.onset} → {lesion.end}<extra></extra>"
        ),
    ))
    # Diamond markers at onset and end
    fig.add_trace(go.Scatter(
        x=[lesion.onset, lesion.end],
        y=[_Y_GHOST, _Y_GHOST],
        mode="markers",
        marker=dict(color=_C["ghosted"], symbol="diamond-open", size=10),
        showlegend=False,
        hoverinfo="skip",
    ))

    # --- P1 anchor symptom bar ---
    p1_dur = p1_symptom.duration_days if p1_symptom.duration_days > 0 else PRIMARY["avg"]
    p1_end = p1_symptom.onset + timedelta(days=p1_dur)
    fig.add_trace(go.Scatter(
        x=[p1_symptom.onset, p1_end],
        y=[_Y_P1, _Y_P1],
        mode="lines",
        line=dict(color=_C["p1_symptom"], width=_BAR_W, dash="solid"),
        name=f"P1 {p1_symptom.type}",
        hovertemplate=(
            f"{p1_name}<br>{p1_symptom.type}<br>"
            f"{p1_symptom.onset} → {p1_end}<extra></extra>"
        ),
    ))
    # Onset marker
    fig.add_trace(go.Scatter(
        x=[p1_symptom.onset], y=[_Y_P1],
        mode="markers",
        marker=dict(color=_C["p1_symptom"], symbol="triangle-up", size=_MARK_S),
        showlegend=False,
        hoverinfo="skip",
    ))

    # --- D1 / D2 inoculation marker ---
    from app.utils.clinical import avg_inoculation_date, calc_d2
    try:
        if scenario == "source":
            d_point = avg_inoculation_date(p1_symptom)
            d_label = "D1 (avg inoculation)"
        else:
            d_point = calc_d2(p1_symptom)
            d_label = "D2 (primary midpoint)"

        fig.add_trace(go.Scatter(
            x=[d_point], y=[_Y_P1],
            mode="markers",
            marker=dict(color=_C["p1_inoc"], symbol="diamond", size=_MARK_S),
            name=d_label,
            hovertemplate=f"{d_label}: {d_point}<extra></extra>",
        ))
        # Vertical reference line at D point
        fig.add_shape(
            type="line",
            x0=d_point, x1=d_point,
            y0=-0.5, y1=1.5,
            line=dict(color=_C["p1_inoc"], width=1.5, dash="dot"),
        )
    except Exception:
        pass

    # --- P2 secondary symptoms ---
    for s in p2_symptoms:
        s_dur = s.duration_days if s.duration_days > 0 else 28
        s_end = s.onset + timedelta(days=s_dur)
        fig.add_trace(go.Scatter(
            x=[s.onset, s_end], y=[_Y_P2, _Y_P2],
            mode="lines",
            line=dict(color=_C["p2_symptom"], width=5, dash="solid"),
            name=f"P2 {s.type}",
            hovertemplate=(
                f"{p2_name}<br>{s.type}<br>"
                f"{s.onset} → {s_end}<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=[s.onset], y=[_Y_P2],
            mode="markers",
            marker=dict(color=_C["p2_symptom"], symbol="triangle-up", size=_MARK_S),
            showlegend=False,
            hoverinfo="skip",
        ))

    return fig
