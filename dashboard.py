from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="PortPulse AI",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# APPLICATION CONSTANTS
# =========================================================

DATABASE_URL = (
    "postgresql://containerpulse:containerpulse"
    "@localhost:5432/containerpulse"
)

LOCATION_TO_REGION: Dict[str, str] = {
    "CNSHA": "Asia",
    "CNNGB": "Asia",
    "VNSGN": "Asia",
    "INMUN": "Asia",
    "SGSIN": "Asia",
    "USLAX": "North America",
    "USLGB": "North America",
    "USSEA": "North America",
    "USNYC": "North America",
    "USSAV": "North America",
    "USCHI": "North America",
    "USPHX": "North America",
    "USDFW": "North America",
    "USCLT": "North America",
    "USATL": "North America",
}

BLUE = "#1268C4"
DARK_BLUE = "#123A73"
LIGHT_BLUE = "#EAF3FF"
GRID_COLOR = "#E5EAF1"
TEXT_COLOR = "#1F2937"


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>
        /* Main page */
        .stApp {
            background-color: #ffffff;
        }

        .block-container {
            max-width: 1580px;
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* Hide Streamlit chrome */
        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Typography */
        .app-title {
            font-size: 2.15rem;
            font-weight: 800;
            color: #123A73;
            line-height: 1.1;
            margin-bottom: 0.2rem;
        }

        .app-subtitle {
            color: #334155;
            font-size: 1rem;
            font-weight: 600;
            margin-top: 0.2rem;
        }

        .app-description {
            color: #64748B;
            font-size: 0.92rem;
            line-height: 1.55;
            margin-top: 0.55rem;
            max-width: 950px;
        }

        .source-pill {
            display: inline-block;
            background: #EAF3FF;
            color: #1268C4;
            border: 1px solid #CFE3FF;
            border-radius: 8px;
            padding: 6px 11px;
            font-size: 0.79rem;
            font-weight: 700;
        }

        .last-refresh {
            color: #64748B;
            font-size: 0.78rem;
            margin-top: 8px;
        }

        /* Filter wrapper */
        .filter-heading {
            font-size: 1.05rem;
            font-weight: 750;
            color: #123A73;
            margin-bottom: 0.25rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #E1E7EF !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        /* Inputs */
        div[data-baseweb="select"] > div {
            border-color: #D7DFEA !important;
            border-radius: 8px !important;
            min-height: 41px;
            background-color: #ffffff !important;
        }

        div[data-baseweb="select"] > div:focus-within {
            border-color: #1268C4 !important;
            box-shadow: 0 0 0 1px #1268C4 !important;
        }

        /* Blue multiselect tags */
        span[data-baseweb="tag"] {
            background-color: #1268C4 !important;
            border-radius: 5px !important;
            color: white !important;
        }

        span[data-baseweb="tag"] span {
            color: white !important;
        }

        span[data-baseweb="tag"] svg {
            fill: white !important;
        }

        /* Blue buttons */
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            border: 1px solid #1268C4;
            background-color: #1268C4;
            color: white;
            font-weight: 700;
            min-height: 40px;
        }

        div.stButton > button:hover {
            background-color: #0D56A6;
            border-color: #0D56A6;
            color: white;
        }

        /* KPI cards */
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #E1E7EF;
            border-radius: 12px;
            padding: 15px 17px;
            min-height: 112px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        div[data-testid="stMetricLabel"] {
            color: #475569;
            font-size: 0.86rem;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            color: #0F274B;
            font-size: 1.75rem;
            font-weight: 800;
        }

        div[data-testid="stMetricDelta"] {
            font-size: 0.78rem;
        }

        /* Section titles */
        .section-title {
            font-size: 1.03rem;
            font-weight: 750;
            color: #123A73;
            margin-bottom: 0.45rem;
        }

        /* Dataframes */
        div[data-testid="stDataFrame"] {
            border: 1px solid #E1E7EF;
            border-radius: 9px;
            overflow: hidden;
        }

        /* Divider */
        hr {
            border: none;
            border-top: 1px solid #E7ECF2;
            margin: 1rem 0;
        }

        /* Reduce gaps */
        div[data-testid="stVerticalBlock"] {
            gap: 0.8rem;
        }

        /* Date input */
        div[data-testid="stDateInput"] input {
            border-radius: 8px;
        }

        /* Captions */
        .footer-text {
            text-align: center;
            color: #94A3B8;
            font-size: 0.78rem;
            margin-top: 1.3rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATABASE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


@st.cache_data(ttl=15)
def load_data() -> pd.DataFrame:
    query = """
        SELECT
            container_number,
            carrier,
            latest_milestone,
            latest_location,
            origin,
            port_of_discharge,
            destination,
            planned_timestamp,
            event_timestamp,
            is_delayed,
            delay_hours
        FROM latest_container_status
    """

    data = pd.read_sql(query, engine)

    data["planned_timestamp"] = pd.to_datetime(
        data["planned_timestamp"],
        errors="coerce",
        utc=True,
    )

    data["event_timestamp"] = pd.to_datetime(
        data["event_timestamp"],
        errors="coerce",
        utc=True,
    )

    data["delay_hours"] = pd.to_numeric(
        data["delay_hours"],
        errors="coerce",
    ).fillna(0)

    data["is_delayed"] = (
        data["is_delayed"]
        .fillna(False)
        .astype(bool)
    )

    return data


# =========================================================
# HELPERS
# =========================================================

def map_region(location_code: str) -> str:
    return LOCATION_TO_REGION.get(location_code, "Other")


def format_column_name(column_name: str) -> str:
    special_names = {
        "container_number": "Container Number",
        "port_of_discharge": "Port of Discharge",
        "latest_milestone": "Latest Milestone",
        "latest_location": "Latest Location",
        "planned_timestamp": "Planned Timestamp",
        "event_timestamp": "Event Timestamp",
        "is_delayed": "Is Delayed",
        "delay_hours": "Delay Hours",
        "average_delay_hours": "Average Delay Hours",
        "total_containers": "Total Containers",
        "delayed_containers": "Delayed Containers",
    }

    return special_names.get(
        column_name,
        column_name.replace("_", " ").title(),
    )


def format_table(data: pd.DataFrame) -> pd.DataFrame:
    output = data.copy()

    for column in [
        "planned_timestamp",
        "event_timestamp",
    ]:
        if column in output.columns:
            output[column] = output[column].dt.strftime(
                "%Y-%m-%d %H:%M UTC"
            )

    output.columns = [
        format_column_name(column)
        for column in output.columns
    ]

    return output


def normalize_date_filter(
    selected_dates,
) -> Tuple[object, object]:
    if isinstance(selected_dates, tuple):
        if len(selected_dates) == 2:
            return selected_dates[0], selected_dates[1]

        if len(selected_dates) == 1:
            return selected_dates[0], selected_dates[0]

    if isinstance(selected_dates, list):
        if len(selected_dates) == 2:
            return selected_dates[0], selected_dates[1]

        if len(selected_dates) == 1:
            return selected_dates[0], selected_dates[0]

    return selected_dates, selected_dates


def create_panel_title(icon: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="section-title">
            {icon} {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_chart_layout(
    figure,
    height: int,
    show_legend: bool = False,
):
    figure.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(
            family="Arial",
            color=TEXT_COLOR,
            size=12,
        ),
        margin=dict(
            l=25,
            r=25,
            t=25,
            b=25,
        ),
        showlegend=show_legend,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
        ),
    )

    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=GRID_COLOR,
    )

    figure.update_yaxes(
        gridcolor=GRID_COLOR,
        zeroline=False,
        linecolor=GRID_COLOR,
    )

    return figure


# =========================================================
# LOAD DATA
# =========================================================

try:
    df = load_data()
except Exception as error:
    st.error(
        "Unable to connect to PostgreSQL. Confirm that the "
        "containerpulse-postgres Docker container is running."
    )
    st.code(str(error))
    st.stop()


if df.empty:
    st.warning(
        "No container data is available. Start the consumer and "
        "run producer.py to generate tracking events."
    )
    st.stop()


df["region"] = df["origin"].apply(map_region)


# =========================================================
# HEADER
# =========================================================

header_left, header_right = st.columns(
    [4.8, 1.2],
    vertical_alignment="top",
)

with header_left:
    st.markdown(
        """
        <div class="app-title">🚢 PortPulse AI</div>
        <div class="app-subtitle">
            Real-time Tracking of Container Movements
        </div>
        <div class="app-description">
            PortPulse AI provides operational visibility into global
            container journeys. Track milestones, monitor delays,
            compare carrier and port performance, and identify risks
            that may affect final delivery.
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_right:
    st.markdown(
        f"""
        <div style="text-align:right; padding-top:4px;">
            <span class="source-pill">
                Source: Project44-inspired synthetic data
            </span>
            <div class="last-refresh">
                ↻ Last refreshed:
                {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# FILTER PANEL — TOP OF PAGE
# =========================================================

region_options: List[str] = sorted(
    df["region"].dropna().unique().tolist()
)

origin_options: List[str] = sorted(
    df["origin"].dropna().unique().tolist()
)

destination_options: List[str] = sorted(
    df["destination"].dropna().unique().tolist()
)

port_options: List[str] = sorted(
    df["port_of_discharge"].dropna().unique().tolist()
)

milestone_options: List[str] = sorted(
    df["latest_milestone"].dropna().unique().tolist()
)

carrier_options: List[str] = sorted(
    df["carrier"].dropna().unique().tolist()
)

minimum_date = df["event_timestamp"].min().date()
maximum_date = df["event_timestamp"].max().date()


with st.container(border=True):
    filter_heading_col, filter_action_col = st.columns(
        [5, 1]
    )

    with filter_heading_col:
        st.markdown(
            """
            <div class="filter-heading">
                🔎 Filters
            </div>
            """,
            unsafe_allow_html=True,
        )

    with filter_action_col:
        if st.button(
            "Clear Filters",
            use_container_width=True,
        ):
            st.session_state.clear()
            st.rerun()

    filter_row_one = st.columns(4)

    with filter_row_one[0]:
        selected_regions = st.multiselect(
            "Region",
            options=region_options,
            default=region_options,
            key="region_filter",
        )

    with filter_row_one[1]:
        selected_origins = st.multiselect(
            "Origin",
            options=origin_options,
            default=origin_options,
            key="origin_filter",
        )

    with filter_row_one[2]:
        selected_destinations = st.multiselect(
            "Destination",
            options=destination_options,
            default=destination_options,
            key="destination_filter",
        )

    with filter_row_one[3]:
        selected_ports = st.multiselect(
            "Port of Discharge",
            options=port_options,
            default=port_options,
            key="port_filter",
        )

    filter_row_two = st.columns(
        [1.25, 1.25, 1.2, 1.3, 0.8]
    )

    with filter_row_two[0]:
        selected_milestones = st.multiselect(
            "Latest Milestone",
            options=milestone_options,
            default=milestone_options,
            key="milestone_filter",
        )

    with filter_row_two[1]:
        selected_carriers = st.multiselect(
            "Carrier",
            options=carrier_options,
            default=carrier_options,
            key="carrier_filter",
        )

    with filter_row_two[2]:
        selected_delay_status = st.selectbox(
            "Delay Status",
            options=[
                "All Containers",
                "Delayed Only",
                "On-Time Only",
            ],
            key="delay_status_filter",
        )

    with filter_row_two[3]:
        selected_dates = st.date_input(
            "Event Timestamp",
            value=(minimum_date, maximum_date),
            min_value=minimum_date,
            max_value=maximum_date,
            key="event_date_filter",
        )

    with filter_row_two[4]:
        st.write("")
        st.write("")

        if st.button(
            "Refresh Data",
            use_container_width=True,
        ):
            st.cache_data.clear()
            st.rerun()


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_df = df.copy()

if selected_regions:
    filtered_df = filtered_df[
        filtered_df["region"].isin(selected_regions)
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_origins:
    filtered_df = filtered_df[
        filtered_df["origin"].isin(selected_origins)
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_destinations:
    filtered_df = filtered_df[
        filtered_df["destination"].isin(
            selected_destinations
        )
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_ports:
    filtered_df = filtered_df[
        filtered_df["port_of_discharge"].isin(
            selected_ports
        )
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_milestones:
    filtered_df = filtered_df[
        filtered_df["latest_milestone"].isin(
            selected_milestones
        )
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_carriers:
    filtered_df = filtered_df[
        filtered_df["carrier"].isin(selected_carriers)
    ]
else:
    filtered_df = filtered_df.iloc[0:0]


start_date, end_date = normalize_date_filter(
    selected_dates
)

filtered_df = filtered_df[
    (
        filtered_df["event_timestamp"].dt.date
        >= start_date
    )
    & (
        filtered_df["event_timestamp"].dt.date
        <= end_date
    )
]


if selected_delay_status == "Delayed Only":
    filtered_df = filtered_df[
        filtered_df["is_delayed"]
    ]

elif selected_delay_status == "On-Time Only":
    filtered_df = filtered_df[
        ~filtered_df["is_delayed"]
    ]


if filtered_df.empty:
    st.warning(
        "No containers match the selected filters. "
        "Use Clear Filters or adjust your selections."
    )
    st.stop()


# =========================================================
# KPI CALCULATIONS
# =========================================================

total_containers = filtered_df[
    "container_number"
].nunique()

delayed_containers = filtered_df.loc[
    filtered_df["is_delayed"],
    "container_number",
].nunique()

on_time_containers = (
    total_containers - delayed_containers
)

active_ports = filtered_df[
    "port_of_discharge"
].nunique()

average_delay = filtered_df.loc[
    filtered_df["is_delayed"],
    "delay_hours",
].mean()

if pd.isna(average_delay):
    average_delay = 0.0

delayed_percentage = (
    delayed_containers / total_containers * 100
    if total_containers
    else 0
)

on_time_percentage = (
    on_time_containers / total_containers * 100
    if total_containers
    else 0
)


# =========================================================
# KPI CARDS
# =========================================================

kpi_columns = st.columns(5)

with kpi_columns[0]:
    st.metric(
        label="Total Containers",
        value=f"{total_containers:,}",
        help="Unique containers matching the selected filters.",
    )

with kpi_columns[1]:
    st.metric(
        label="Delayed Containers",
        value=f"{delayed_containers:,}",
        delta=f"{delayed_percentage:.1f}% of total",
        delta_color="inverse",
    )

with kpi_columns[2]:
    st.metric(
        label="Active Ports",
        value=f"{active_ports:,}",
        help="Unique ports of discharge.",
    )

with kpi_columns[3]:
    st.metric(
        label="Average Delay",
        value=f"{average_delay:.1f} hrs",
        help="Average delay among delayed containers.",
    )

with kpi_columns[4]:
    st.metric(
        label="On-Time Containers",
        value=f"{on_time_containers:,}",
        delta=f"{on_time_percentage:.1f}% of total",
        delta_color="normal",
    )


st.markdown("<hr>", unsafe_allow_html=True)


# =========================================================
# PORT SUMMARY
# =========================================================

port_summary = (
    filtered_df.groupby(
        "port_of_discharge",
        as_index=False,
    )
    .agg(
        total_containers=(
            "container_number",
            "nunique",
        ),
        delayed_containers=(
            "is_delayed",
            lambda values: int(values.sum()),
        ),
        average_delay_hours=(
            "delay_hours",
            lambda values: round(
                values[values > 0].mean()
                if (values > 0).any()
                else 0,
                1,
            ),
        ),
    )
    .sort_values(
        by=[
            "delayed_containers",
            "total_containers",
        ],
        ascending=[False, False],
    )
)


# =========================================================
# FIRST ANALYTICS ROW
# =========================================================

summary_col, donut_col, distribution_col = st.columns(
    [1.45, 1, 1.15]
)

with summary_col:
    with st.container(border=True):
        create_panel_title(
            "📊",
            "Port Delay Summary",
        )

        st.dataframe(
            format_table(port_summary),
            use_container_width=True,
            hide_index=True,
            height=310,
            column_config={
                "Port of Discharge": st.column_config.TextColumn(
                    width="medium"
                ),
                "Average Delay Hours": st.column_config.NumberColumn(
                    format="%.1f"
                ),
            },
        )


with donut_col:
    with st.container(border=True):
        create_panel_title(
            "⏱",
            "Delayed vs On-Time Containers",
        )

        donut_figure = go.Figure(
            data=[
                go.Pie(
                    labels=[
                        "On-Time",
                        "Delayed",
                    ],
                    values=[
                        on_time_containers,
                        delayed_containers,
                    ],
                    hole=0.63,
                    marker=dict(
                        colors=[
                            BLUE,
                            "#73B9F4",
                        ],
                    ),
                    textinfo="label+percent",
                    textposition="inside",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Containers: %{value}<br>"
                        "Share: %{percent}"
                        "<extra></extra>"
                    ),
                )
            ]
        )

        donut_figure.update_layout(
            height=310,
            margin=dict(
                l=10,
                r=10,
                t=5,
                b=25,
            ),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(
                color=TEXT_COLOR,
                size=11,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.12,
                xanchor="center",
                x=0.5,
            ),
            annotations=[
                dict(
                    text=(
                        f"<b>{total_containers}</b>"
                        "<br>Total"
                    ),
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(
                        size=16,
                        color="#64748B",
                    ),
                )
            ],
        )

        st.plotly_chart(
            donut_figure,
            use_container_width=True,
            config={
                "displayModeBar": False,
            },
        )


with distribution_col:
    with st.container(border=True):
        create_panel_title(
            "📈",
            "Delay Distribution",
        )

        delayed_only = filtered_df[
            filtered_df["is_delayed"]
        ].copy()

        delay_bins = [
            -1,
            12,
            24,
            36,
            48,
            60,
            float("inf"),
        ]

        delay_labels = [
            "0–12",
            "13–24",
            "25–36",
            "37–48",
            "49–60",
            "60+",
        ]

        delayed_only["delay_bucket"] = pd.cut(
            delayed_only["delay_hours"],
            bins=delay_bins,
            labels=delay_labels,
        )

        delay_distribution = (
            delayed_only.groupby(
                "delay_bucket",
                observed=False,
            )
            .size()
            .reset_index(
                name="containers"
            )
        )

        delay_figure = px.bar(
            delay_distribution,
            x="delay_bucket",
            y="containers",
            text="containers",
            labels={
                "delay_bucket": "Delay Hours",
                "containers": "Containers",
            },
        )

        delay_figure.update_traces(
            marker_color=BLUE,
            textposition="outside",
            hovertemplate=(
                "Delay: %{x} hours<br>"
                "Containers: %{y}"
                "<extra></extra>"
            ),
        )

        apply_chart_layout(
            delay_figure,
            height=310,
        )

        delay_figure.update_yaxes(
            rangemode="tozero",
            dtick=1,
        )

        st.plotly_chart(
            delay_figure,
            use_container_width=True,
            config={
                "displayModeBar": False,
            },
        )


# =========================================================
# SECOND ANALYTICS ROW
# =========================================================

delayed_col, carrier_col = st.columns(
    [2.05, 1]
)

with delayed_col:
    with st.container(border=True):
        create_panel_title(
            "⚠️",
            "Delayed Containers",
        )

        delayed_table = (
            filtered_df[
                filtered_df["is_delayed"]
            ][
                [
                    "container_number",
                    "carrier",
                    "latest_milestone",
                    "latest_location",
                    "origin",
                    "port_of_discharge",
                    "destination",
                    "delay_hours",
                    "event_timestamp",
                ]
            ]
            .sort_values(
                by=[
                    "delay_hours",
                    "event_timestamp",
                ],
                ascending=[
                    False,
                    False,
                ],
            )
        )

        st.dataframe(
            format_table(delayed_table),
            use_container_width=True,
            hide_index=True,
            height=340,
            column_config={
                "Delay Hours": st.column_config.NumberColumn(
                    format="%d"
                ),
            },
        )


with carrier_col:
    with st.container(border=True):
        create_panel_title(
            "🚚",
            "Top Carriers by Containers",
        )

        carrier_summary = (
            filtered_df.groupby(
                "carrier",
                as_index=False,
            )
            .agg(
                containers=(
                    "container_number",
                    "nunique",
                )
            )
            .sort_values(
                "containers",
                ascending=True,
            )
        )

        carrier_figure = px.bar(
            carrier_summary,
            x="containers",
            y="carrier",
            orientation="h",
            text="containers",
            labels={
                "containers": "Containers",
                "carrier": "Carrier",
            },
        )

        carrier_figure.update_traces(
            marker_color=BLUE,
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Containers: %{x}"
                "<extra></extra>"
            ),
        )

        apply_chart_layout(
            carrier_figure,
            height=340,
        )

        carrier_figure.update_xaxes(
            rangemode="tozero",
            dtick=1,
        )

        st.plotly_chart(
            carrier_figure,
            use_container_width=True,
            config={
                "displayModeBar": False,
            },
        )


# =========================================================
# LATEST STATUS TABLE
# =========================================================

with st.container(border=True):
    create_panel_title(
        "📦",
        "Latest Container Status",
    )

    latest_status_columns = [
        "container_number",
        "carrier",
        "latest_milestone",
        "latest_location",
        "region",
        "origin",
        "port_of_discharge",
        "destination",
        "planned_timestamp",
        "event_timestamp",
        "is_delayed",
        "delay_hours",
    ]

    latest_status_table = (
        filtered_df[
            latest_status_columns
        ]
        .sort_values(
            "event_timestamp",
            ascending=False,
        )
    )

    st.dataframe(
        format_table(latest_status_table),
        use_container_width=True,
        hide_index=True,
        height=440,
        column_config={
            "Is Delayed": st.column_config.CheckboxColumn(
                width="small"
            ),
            "Delay Hours": st.column_config.NumberColumn(
                format="%d"
            ),
        },
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer-text">
        PortPulse AI · Kafka → PostgreSQL → SQL Analytics
        Views → Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)