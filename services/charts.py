"""
Chart generation service using matplotlib.

Renders branded charts based on structured specifications from Claude API.
Supports: horizontal_bar, vertical_bar, line, table.
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)


def generate_chart(chart_spec: Dict, config: Dict, output_name: str) -> str:
    """
    Generate a chart image from a chart specification.

    Args:
        chart_spec: Chart specification dict with type, title, data, etc.
        config: Configuration dict (for brand settings)
        output_name: Base name for output file (without extension)

    Returns:
        Path to generated chart image file
    """
    logger.info(f"Generating {chart_spec['type']} chart: {chart_spec.get('title', 'Untitled')}")

    # Extract brand settings
    brand = config.get("brand", {})
    colours = brand.get("colours", {})

    # Set up matplotlib with brand settings
    plt.style.use('default')

    # Try to set Roboto font, fall back to system default if not available
    try:
        plt.rcParams['font.family'] = brand.get('font', 'Roboto')
    except:
        logger.warning("Roboto font not available, using default")

    # Create chart based on type
    chart_type = chart_spec.get("type", "horizontal_bar")

    if chart_type == "horizontal_bar":
        fig = _create_horizontal_bar(chart_spec, colours)
    elif chart_type == "vertical_bar":
        fig = _create_vertical_bar(chart_spec, colours)
    elif chart_type == "line":
        fig = _create_line_chart(chart_spec, colours)
    elif chart_type == "table":
        fig = _create_table(chart_spec, colours)
    else:
        logger.warning(f"Unknown chart type '{chart_type}', defaulting to horizontal_bar")
        fig = _create_horizontal_bar(chart_spec, colours)

    # Save the chart
    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{output_name}.png"

    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    logger.info(f"Chart saved to {output_path}")
    return str(output_path)


def _create_horizontal_bar(spec: Dict, colours: Dict) -> plt.Figure:
    """Create a horizontal bar chart."""
    data = spec.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    highlight_index = spec.get("highlight_index")

    # Determine figure size
    size = spec.get("size", [1200, 1200])
    figsize = (size[0] / 150, size[1] / 150)  # Convert pixels to inches at 150 DPI

    fig, ax = plt.subplots(figsize=figsize)

    # Determine bar colours
    bar_colours = []
    for i in range(len(labels)):
        if highlight_index is not None and i == highlight_index:
            bar_colours.append(colours.get("primary_gold", "#E8C07D"))
        else:
            bar_colours.append(colours.get("primary_dark_brown", "#47403F"))

    # Create horizontal bars
    y_pos = range(len(labels))
    ax.barh(y_pos, values, color=bar_colours)

    # Set labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # Highest value at top

    # Title
    title = spec.get("title", "")
    ax.set_title(title, fontsize=14, fontweight='bold',
                 color=colours.get("primary_dark_brown", "#47403F"),
                 pad=20, loc='left')

    # Source
    source = spec.get("source", "")
    fig.text(0.95, 0.02, f"Source: {source}", ha='right', va='bottom',
             fontsize=8, color='#666666')

    # Styling
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    ax.grid(axis='x', alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)

    return fig


def _create_vertical_bar(spec: Dict, colours: Dict) -> plt.Figure:
    """Create a vertical bar chart."""
    data = spec.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    highlight_index = spec.get("highlight_index")

    # Determine figure size
    size = spec.get("size", [1200, 675])
    figsize = (size[0] / 150, size[1] / 150)

    fig, ax = plt.subplots(figsize=figsize)

    # Determine bar colours
    bar_colours = []
    for i in range(len(labels)):
        if highlight_index is not None and i == highlight_index:
            bar_colours.append(colours.get("primary_gold", "#E8C07D"))
        else:
            bar_colours.append(colours.get("primary_dark_brown", "#47403F"))

    # Create vertical bars
    x_pos = range(len(labels))
    ax.bar(x_pos, values, color=bar_colours)

    # Set labels
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=45, ha='right')

    # Title
    title = spec.get("title", "")
    ax.set_title(title, fontsize=14, fontweight='bold',
                 color=colours.get("primary_dark_brown", "#47403F"),
                 pad=20, loc='left')

    # Source
    source = spec.get("source", "")
    fig.text(0.95, 0.02, f"Source: {source}", ha='right', va='bottom',
             fontsize=8, color='#666666')

    # Styling
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    ax.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)

    return fig


def _create_line_chart(spec: Dict, colours: Dict) -> plt.Figure:
    """Create a line chart."""
    data = spec.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])

    # Determine figure size
    size = spec.get("size", [1200, 675])
    figsize = (size[0] / 150, size[1] / 150)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot main line
    ax.plot(labels, values, color=colours.get("primary_gold", "#E8C07D"),
            linewidth=2.5, marker='o', markersize=6)

    # Plot comparison line if present
    if "comparison_values" in data:
        comparison = data["comparison_values"]
        ax.plot(labels, comparison, color=colours.get("secondary_light_blue", "#CADAE8"),
                linewidth=2.5, marker='o', markersize=6, linestyle='--')

        # Add legend
        series_name = data.get("series_name", "Series 1")
        comparison_name = data.get("comparison_series_name", "Series 2")
        ax.legend([series_name, comparison_name])

    # Title
    title = spec.get("title", "")
    ax.set_title(title, fontsize=14, fontweight='bold',
                 color=colours.get("primary_dark_brown", "#47403F"),
                 pad=20, loc='left')

    # Source
    source = spec.get("source", "")
    fig.text(0.95, 0.02, f"Source: {source}", ha='right', va='bottom',
             fontsize=8, color='#666666')

    # Styling
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    ax.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)

    return fig


def _create_table(spec: Dict, colours: Dict) -> plt.Figure:
    """Create a table image."""
    data = spec.get("data", {})
    columns = data.get("columns", [])
    rows = data.get("rows", [])
    highlight_index = spec.get("highlight_index")

    # Determine figure size
    size = spec.get("size", [1200, 1200])
    figsize = (size[0] / 150, size[1] / 150)

    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('tight')
    ax.axis('off')

    # Create table
    table_data = [columns] + rows

    # Determine row colours
    row_colours = []
    # Header row
    row_colours.append([colours.get("primary_dark_brown", "#47403F")] * len(columns))

    # Data rows
    for i in range(len(rows)):
        if highlight_index is not None and i == highlight_index:
            row_colours.append([colours.get("primary_gold", "#E8C07D")] * len(columns))
        elif i % 2 == 0:
            row_colours.append([colours.get("white", "#FFFFFF")] * len(columns))
        else:
            row_colours.append([colours.get("secondary_linen", "#F7EFE4")] * len(columns))

    table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                     cellColours=row_colours)

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style header row text (white)
    for i in range(len(columns)):
        cell = table[(0, i)]
        cell.set_text_props(weight='bold', color='white')

    # Title
    title = spec.get("title", "")
    fig.text(0.5, 0.95, title, ha='center', fontsize=14, fontweight='bold',
             color=colours.get("primary_dark_brown", "#47403F"))

    # Source
    source = spec.get("source", "")
    fig.text(0.95, 0.02, f"Source: {source}", ha='right', va='bottom',
             fontsize=8, color='#666666')

    return fig
