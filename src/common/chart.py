"""Plotly charts for network layout and pressure observation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import plotly.graph_objects as go
import plotly.io as pio

from .context import GasNetworkData


def _looks_like_swiss_coords(x_value: float | None, y_value: float | None) -> bool:
    if x_value is None or y_value is None:
        return False
    return 450000.0 <= float(x_value) <= 900000.0 and 50000.0 <= float(y_value) <= 350000.0


def _lv03_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert Swiss LV03 coordinates to WGS84 latitude/longitude."""

    y = (float(easting) - 600000.0) / 1000000.0
    x = (float(northing) - 200000.0) / 1000000.0

    lat = (
        16.9023892
        + 3.238272 * x
        - 0.270978 * y * y
        - 0.002528 * x * x
        - 0.0447 * y * y * x
        - 0.0140 * x * x * x
    )
    lon = (
        2.6779094
        + 4.728982 * y
        + 0.791484 * y * x
        + 0.1306 * y * x * x
        - 0.0436 * y * y * y
    )
    return lat * 100.0 / 36.0, lon * 100.0 / 36.0


def _node_positions(data: GasNetworkData) -> dict[str, tuple[float, float, bool]]:
    positions: dict[str, tuple[float, float, bool]] = {}

    has_xy = {"x", "y"}.issubset(data.nodes.columns)
    if has_xy and data.nodes["x"].notna().any() and data.nodes["y"].notna().any():
        for row in data.nodes.itertuples(index=False):
            node_id = str(row.uid)
            x_value = getattr(row, "x", None)
            y_value = getattr(row, "y", None)
            if _looks_like_swiss_coords(x_value, y_value):
                lat, lon = _lv03_to_wgs84(float(x_value), float(y_value))
                positions[node_id] = (lon, lat, True)
            else:
                positions[node_id] = (float(x_value or 0.0), float(y_value or 0.0), False)
        return positions

    graph = nx.Graph()
    graph.add_nodes_from(data.nodes["uid"].astype(str))
    graph.add_edges_from((str(row.from_node), str(row.to_node)) for row in data.pipes.itertuples(index=False))
    layout = nx.spring_layout(graph, seed=42)
    for node_id, coords in layout.items():
        positions[str(node_id)] = (float(coords[0]), float(coords[1]), False)
    return positions


def _node_size(node_count: int) -> int:
    if node_count > 500:
        return 6
    if node_count > 100:
        return 7
    if node_count > 20:
        return 8
    return 10


def _line_segments(dataframe, positions: dict[str, tuple[float, float, bool]]) -> tuple[list[float | None], list[float | None]]:
    x_values: list[float | None] = []
    y_values: list[float | None] = []
    for row in dataframe.itertuples(index=False):
        start = positions.get(str(row.from_node))
        end = positions.get(str(row.to_node))
        if start is None or end is None:
            continue
        x_values.extend([start[0], end[0], None])
        y_values.extend([start[1], end[1], None])
    return x_values, y_values


def _map_center(positions: dict[str, tuple[float, float, bool]]) -> dict[str, float]:
    if not positions:
        return {"lat": 46.8, "lon": 8.3}
    return {
        "lat": sum(v[1] for v in positions.values()) / len(positions),
        "lon": sum(v[0] for v in positions.values()) / len(positions),
    }


def _build_network_figure(data: GasNetworkData, solution: dict[str, Any], positions: dict[str, tuple[float, float, bool]]) -> go.Figure:
    pressure_lookup = {item["uid"]: item["pressure_kpa"] for item in solution["pressures"]}
    use_geo = any(item[2] for item in positions.values())
    fig = go.Figure()

    node_lons = [positions[str(row.uid)][0] for row in data.nodes.itertuples(index=False)]
    node_lats = [positions[str(row.uid)][1] for row in data.nodes.itertuples(index=False)]
    node_customdata = [
        [
            str(row.uid),
            float(pressure_lookup.get(str(row.uid), 0.0)),
            float(getattr(row, "q_demand_tcmh", 0.0) or 0.0),
        ]
        for row in data.nodes.itertuples(index=False)
    ]

    pipe_x, pipe_y = _line_segments(data.pipes, positions)
    valve_x, valve_y = _line_segments(data.valves, positions)

    if use_geo:
        if pipe_x:
            fig.add_trace(
                go.Scattermapbox(
                    lon=pipe_x,
                    lat=pipe_y,
                    mode="lines",
                    line=dict(width=1.5, color="#22c55e"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
        if valve_x:
            fig.add_trace(
                go.Scattermapbox(
                    lon=valve_x,
                    lat=valve_y,
                    mode="lines",
                    line=dict(width=1.5, color="#ef4444"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scattermapbox(
                lon=node_lons,
                lat=node_lats,
                mode="markers",
                marker=dict(size=_node_size(len(data.nodes)), color="#1f77b4"),
                customdata=node_customdata,
                hovertemplate="Node %{customdata[0]}<br>Pressure %{customdata[1]:.2f} kPa<br>Demand %{customdata[2]:.2f}<extra></extra>",
                showlegend=False,
            )
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(center=_map_center(positions), zoom=8),
            margin=dict(l=0, r=0, t=20, b=0),
        )
    else:
        if pipe_x:
            fig.add_trace(
                go.Scattergl(
                    x=pipe_x,
                    y=pipe_y,
                    mode="lines",
                    line=dict(width=1.5, color="#22c55e"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
        if valve_x:
            fig.add_trace(
                go.Scattergl(
                    x=valve_x,
                    y=valve_y,
                    mode="lines",
                    line=dict(width=1.5, color="#ef4444"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scattergl(
                x=node_lons,
                y=node_lats,
                mode="markers",
                marker=dict(size=_node_size(len(data.nodes)), color="#1f77b4"),
                customdata=node_customdata,
                hovertemplate="Node %{customdata[0]}<br>Pressure %{customdata[1]:.2f} kPa<br>Demand %{customdata[2]:.2f}<extra></extra>",
                showlegend=False,
            )
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=20, r=20, t=20, b=20),
        )

    return fig


def _build_pressure_figure(data: GasNetworkData, solution: dict[str, Any], positions: dict[str, tuple[float, float, bool]]) -> go.Figure:
    pressure_lookup = {item["uid"]: item["pressure_kpa"] for item in solution["pressures"]}
    use_geo = any(item[2] for item in positions.values())
    fig = go.Figure()

    node_lons = [positions[str(row.uid)][0] for row in data.nodes.itertuples(index=False)]
    node_lats = [positions[str(row.uid)][1] for row in data.nodes.itertuples(index=False)]
    node_pressures = [pressure_lookup.get(str(row.uid), 0.0) for row in data.nodes.itertuples(index=False)]
    node_customdata = [
        [str(row.uid), float(pressure_lookup.get(str(row.uid), 0.0))]
        for row in data.nodes.itertuples(index=False)
    ]

    pipe_x, pipe_y = _line_segments(data.pipes, positions)
    valve_x, valve_y = _line_segments(data.valves, positions)

    if use_geo:
        if pipe_x:
            fig.add_trace(
                go.Scattermapbox(
                    lon=pipe_x,
                    lat=pipe_y,
                    mode="lines",
                    line=dict(width=1.0, color="#22c55e"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
        if valve_x:
            fig.add_trace(
                go.Scattermapbox(
                    lon=valve_x,
                    lat=valve_y,
                    mode="lines",
                    line=dict(width=1.2, color="#ef4444"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scattermapbox(
                lon=node_lons,
                lat=node_lats,
                mode="markers",
                marker=dict(
                    size=_node_size(len(data.nodes)),
                    color=node_pressures,
                    colorscale="Viridis",
                    colorbar=dict(title="Pressure (kPa)"),
                ),
                customdata=node_customdata,
                hovertemplate="Node %{customdata[0]}<br>Pressure %{customdata[1]:.2f} kPa<extra></extra>",
                showlegend=False,
            )
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(center=_map_center(positions), zoom=8),
            margin=dict(l=0, r=0, t=20, b=0),
        )
    else:
        if pipe_x:
            fig.add_trace(
                go.Scattergl(
                    x=pipe_x,
                    y=pipe_y,
                    mode="lines",
                    line=dict(width=1.0, color="#22c55e"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
        if valve_x:
            fig.add_trace(
                go.Scattergl(
                    x=valve_x,
                    y=valve_y,
                    mode="lines",
                    line=dict(width=1.2, color="#ef4444"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scattergl(
                x=node_lons,
                y=node_lats,
                mode="markers",
                marker=dict(
                    size=_node_size(len(data.nodes)),
                    color=node_pressures,
                    colorscale="Viridis",
                    colorbar=dict(title="Pressure (kPa)"),
                ),
                customdata=node_customdata,
                hovertemplate="Node %{customdata[0]}<br>Pressure %{customdata[1]:.2f} kPa<extra></extra>",
                showlegend=False,
            )
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=20, r=20, t=20, b=20),
        )

    return fig


def build_charts(data: GasNetworkData, solution: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Write the network and pressure charts."""

    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    network_path = charts_dir / "network.html"
    pressure_path = charts_dir / "pressure_heatmap.html"

    positions = _node_positions(data)

    pio.write_html(_build_network_figure(data, solution, positions), file=str(network_path), include_plotlyjs="cdn", auto_open=False)
    pio.write_html(_build_pressure_figure(data, solution, positions), file=str(pressure_path), include_plotlyjs="cdn", auto_open=False)

    return {"network": network_path, "pressure_heatmap": pressure_path}
