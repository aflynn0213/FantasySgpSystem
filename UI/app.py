"""
Fantasy SGP – Pro Sports Dashboard
Revamped UI with global filters, position intelligence, and config status header.
"""
from __future__ import annotations

import re
from io import BytesIO

import pandas as pd
import streamlit as st
from google.cloud import storage

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUCKET = "fantasysgpsystem-outputs"

GCS_FOLDERS = [
    "results/",
    "auction_calculator_exports/",
    "stats/",
    "ros/",
]

# Columns that identify a player internally – hidden in the UI
_INTERNAL_COLS = {"PlayerId", "playerid", "player_id", "fg_id"}

# Columns whose display should be accented (gold background)
_ACCENT_COLS = {"Total_SGP", "VAR", "ADP", "Dollars", "points_total"}

# Hitter SGP stat columns
_HITTER_SGP_COLS = {
    "SGP_R", "SGP_HR", "SGP_RBI", "SGP_SB", "SGP_OBP", "SGP_SLG",
    "Total_SGP_wSB",
}

# Pitcher SGP stat columns
_PITCHER_SGP_COLS = {
    "SGP_SO", "SGP_QS", "SGP_SV_HLD", "SGP_ERA", "SGP_WHIP", "SGP_K/BB",
}

# ---------------------------------------------------------------------------
# Page config – must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Fantasy SGP Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Pro-Sports Dark Mode CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ── Root & background ─────────────────────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }

    /* ── Sidebar header ─────────────────────────────────────────────────── */
    .sidebar-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f0b429 !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    /* ── Config header cards ────────────────────────────────────────────── */
    .config-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    .config-card .label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8b949e;
        margin-bottom: 4px;
    }
    .config-card .value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f0b429;
    }
    .config-card .sub {
        font-size: 0.78rem;
        color: #58a6ff;
        margin-top: 2px;
    }

    /* ── Section divider ────────────────────────────────────────────────── */
    .sgp-divider {
        border: none;
        border-top: 1px solid #30363d;
        margin: 1rem 0;
    }

    /* ── Metric overrides ────────────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
    }

    /* ── Dataframe header ───────────────────────────────────────────────── */
    [data-testid="stDataFrame"] thead th {
        background-color: #1c2128 !important;
        color: #f0b429 !important;
        font-weight: 600;
    }

    /* ── Buttons ────────────────────────────────────────────────────────── */
    .stDownloadButton > button {
        background-color: #238636 !important;
        color: #ffffff !important;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    .stDownloadButton > button:hover { background-color: #2ea043 !important; }

    /* ── View toggle (radio) ────────────────────────────────────────────── */
    [data-testid="stRadio"] label { font-weight: 600; }

    /* ── Info/warning boxes ─────────────────────────────────────────────── */
    [data-testid="stAlert"] { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Cached helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def list_files(prefix: str = "") -> list[str]:
    """Return sorted list of CSV/XLSX blobs under *prefix* in the GCS bucket."""
    client = storage.Client()
    blobs = client.list_blobs(BUCKET, prefix=prefix)
    return sorted([b.name for b in blobs if b.name.lower().endswith((".csv", ".xlsx"))])


@st.cache_data(ttl=300)
def load_blob_to_df(blob_name: str, sheet_name: str | int = 0) -> pd.DataFrame:
    """Download a GCS blob and parse it into a DataFrame."""
    client = storage.Client()
    raw = client.bucket(BUCKET).blob(blob_name).download_as_bytes()
    if blob_name.lower().endswith(".csv"):
        return pd.read_csv(BytesIO(raw))
    return pd.read_excel(BytesIO(raw), sheet_name=sheet_name, engine="openpyxl")


@st.cache_data(ttl=300)
def get_excel_sheet_names(blob_name: str) -> list[str]:
    """Return sheet names for an XLSX blob (empty list for CSVs)."""
    if blob_name.lower().endswith(".csv"):
        return []
    client = storage.Client()
    raw = client.bucket(BUCKET).blob(blob_name).download_as_bytes()
    xl = pd.ExcelFile(BytesIO(raw), engine="openpyxl")
    return xl.sheet_names


# ---------------------------------------------------------------------------
# Context detection
# ---------------------------------------------------------------------------

def detect_context(blob_name: str) -> dict:
    """
    Infer player_type, projection sources, and ip_adj from a blob path/name.

    Expected result-file pattern (multi-sheet):
        results/SGP_Results_{hitter_proj}_{pitcher_proj}[_sb_included].xlsx

    Expected inseason single-sheet pattern:
        results/SGP_Results_{hitter_proj}_{pitcher_proj}_{player_type}[_sb_included].xlsx
    """
    ctx: dict = {
        "player_type": None,   # "hitting" | "pitching" | "combined" | None
        "hitter_proj": None,
        "pitcher_proj": None,
        "ip_adj": None,
        "sb_included": False,
        "is_auc_calc": False,
        "is_stats": False,
    }

    base = blob_name.split("/")[-1].lower()
    path = blob_name.lower()

    ctx["sb_included"] = "_sb_included" in base

    # Folder-level hints
    if "auction_calculator" in path:
        ctx["is_auc_calc"] = True
    if path.startswith("stats/") or "/stats/" in path:
        ctx["is_stats"] = True

    # Player type from file name
    for ptype in ("hitting", "pitching", "combined"):
        if ptype in base:
            ctx["player_type"] = ptype
            break

    # Player type from folder name when not in file name
    if ctx["player_type"] is None:
        if "hitter" in path:
            ctx["player_type"] = "hitting"
        elif "pitcher" in path:
            ctx["player_type"] = "pitching"

    # Projection sources – try 3-token pattern first (includes ip_adj)
    #   SGP_Results_{h}_{p}_{adj}_{player_type} -> groups (h, p, adj)
    m3 = re.search(
        r"sgp_results_([a-z0-9]+)_([a-z0-9]+)_([a-z0-9]+)_(?:hitting|pitching|combined)",
        base,
    )
    if m3:
        ctx["hitter_proj"] = m3.group(1).upper()
        ctx["pitcher_proj"] = m3.group(2).upper()
        ctx["ip_adj"] = m3.group(3).upper()
    else:
        # 2-token: SGP_Results_{h}_{p}[_player_type]
        m2 = re.search(r"sgp_results_([a-z0-9]+)_([a-z0-9]+)", base)
        if m2:
            ctx["hitter_proj"] = m2.group(1).upper()
            ctx["pitcher_proj"] = m2.group(2).upper()

    # auc_calc files: auc_calc_{player_type}_{proj}.xlsx
    if ctx["is_auc_calc"]:
        m_auc = re.search(r"auc_calc_(hitting|pitching)_([a-z0-9]+)", base)
        if m_auc:
            if ctx["player_type"] is None:
                ctx["player_type"] = m_auc.group(1)
            proj = m_auc.group(2).upper()
            if ctx["hitter_proj"] is None and ctx["player_type"] == "hitting":
                ctx["hitter_proj"] = proj
            if ctx["pitcher_proj"] is None and ctx["player_type"] == "pitching":
                ctx["pitcher_proj"] = proj

    return ctx


# ---------------------------------------------------------------------------
# Data enrichment helpers
# ---------------------------------------------------------------------------

def find_pos_column(df: pd.DataFrame) -> str | None:
    """Return the name of the position column, case-insensitively."""
    for col in df.columns:
        if col.lower() in ("pos", "elig", "position", "eligibility"):
            return col
    return None


def enrich_pitcher_role(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'Role' column (SP / RP) to a pitcher DataFrame.

    Priority:
      1. Use an existing POS / pos column that contains SP/RP values.
      2. Derive from GS: GS > 5 → SP, else RP.
      3. Derive from auc_calc column if present.
    """
    df = df.copy()
    pos_col = find_pos_column(df)
    if pos_col and df[pos_col].astype(str).str.contains("SP|RP", na=False).any():
        df["Role"] = df[pos_col].map(
            lambda v: "SP" if isinstance(v, str) and "SP" in v.upper() else "RP"
        )
    elif "GS" in df.columns:
        df["Role"] = df["GS"].apply(lambda gs: "SP" if (pd.notna(gs) and gs > 5) else "RP")
    else:
        df["Role"] = "Unknown"
    return df


def is_pitcher_data(df: pd.DataFrame, ctx: dict) -> bool:
    """Heuristic: does this DataFrame look like pitcher data?"""
    if ctx["player_type"] == "pitching":
        return True
    pitcher_signals = {"IP", "GS", "SGP_ERA", "SGP_WHIP", "SGP_SO", "Starter"} & set(df.columns)
    hitter_signals = {"PA", "SGP_R", "SGP_HR", "SGP_OBP", "SGP_SLG"} & set(df.columns)
    return len(pitcher_signals) > len(hitter_signals)


def is_hitter_data(df: pd.DataFrame, ctx: dict) -> bool:
    """Heuristic: does this DataFrame look like hitter data?"""
    if ctx["player_type"] == "hitting":
        return True
    hitter_signals = {"PA", "SGP_R", "SGP_HR", "SGP_OBP", "SGP_SLG", "POS", "ELIG"} & set(df.columns)
    return len(hitter_signals) >= 2


# ---------------------------------------------------------------------------
# Column configuration builder
# ---------------------------------------------------------------------------

def build_column_config(df: pd.DataFrame) -> dict:
    """
    Build a st.column_config mapping for the given DataFrame:
    - Hide internal ID columns.
    - Apply number formatting to SGP/stats columns.
    - Highlight accent columns (Total_SGP, VAR, ADP, points_total).
    """
    cfg: dict = {}

    for col in df.columns:
        # Hide internal ID columns
        if col in _INTERNAL_COLS or col.lower() in {c.lower() for c in _INTERNAL_COLS}:
            cfg[col] = None  # None hides the column
            continue

        col_lower = col.lower()

        # points_total — highlight if present
        if col_lower == "points_total":
            cfg[col] = st.column_config.NumberColumn(
                label="⭐ Points",
                format="%.2f",
                help="Total fantasy points (from backend points engine)",
            )
            continue

        # Total_SGP variants
        if col in ("Total_SGP", "Total_SGP_wSB"):
            cfg[col] = st.column_config.NumberColumn(
                label=col.replace("_", " "),
                format="%.3f",
            )
            continue

        # VAR
        if col == "VAR":
            cfg[col] = st.column_config.NumberColumn(
                label="VAR",
                format="%.3f",
                help="Value above replacement",
            )
            continue

        # ADP
        if col_lower == "adp":
            cfg[col] = st.column_config.NumberColumn(
                label="ADP",
                format="%.1f",
                help="Average Draft Position",
            )
            continue

        # Dollars
        if col_lower in ("dollars", "$"):
            cfg[col] = st.column_config.NumberColumn(
                label="$",
                format="$%.1f",
            )
            continue

        # SGP component columns
        if col.startswith("SGP_"):
            cfg[col] = st.column_config.NumberColumn(
                label=col.replace("SGP_", ""),
                format="%.3f",
            )
            continue

        # Float-like numeric catch-all
        if pd.api.types.is_float_dtype(df[col]):
            cfg[col] = st.column_config.NumberColumn(format="%.2f")

    return cfg


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<p class="sidebar-title">⚾ SGP Dashboard</p>', unsafe_allow_html=True)
    st.markdown("---")

    # -- Folder selector
    folder = st.selectbox(
        "GCS Folder",
        GCS_FOLDERS,
        index=0,
        help="Choose which bucket folder to browse",
    )

    # -- File selector
    files = list_files(prefix=folder)
    if not files:
        st.warning("No CSV/XLSX files found in this folder.")
        st.stop()

    pick = st.selectbox(
        "Select file",
        files,
        index=len(files) - 1,
        help="The most recent file is selected by default",
    )
    st.caption(f"gs://{BUCKET}/{pick}")

    # -- Sheet picker (for multi-sheet XLSX)
    sheet_names = get_excel_sheet_names(pick)
    active_sheet: str | int = 0
    if len(sheet_names) > 1:
        active_sheet = st.selectbox("Sheet", sheet_names)

    st.markdown("---")
    st.markdown("**Filters**")

    # Placeholders – filled after df is loaded
    pos_filter_placeholder = st.empty()
    role_filter_placeholder = st.empty()
    search_placeholder = st.empty()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

df_raw = load_blob_to_df(pick, sheet_name=active_sheet)
ctx = detect_context(pick)

# If the active sheet name hints at player type, override ctx
if isinstance(active_sheet, str):
    sheet_lower = active_sheet.lower()
    if "hitter" in sheet_lower or "hitting" in sheet_lower:
        ctx["player_type"] = "hitting"
    elif "pitcher" in sheet_lower or "pitching" in sheet_lower:
        ctx["player_type"] = "pitching"
    elif "combined" in sheet_lower:
        ctx["player_type"] = "combined"

# Enrich pitcher dataframes with a Role column
_is_pitcher = is_pitcher_data(df_raw, ctx)
_is_hitter = is_hitter_data(df_raw, ctx)

if _is_pitcher and not _is_hitter:
    df_raw = enrich_pitcher_role(df_raw)

# ---------------------------------------------------------------------------
# Configuration Status Header
# ---------------------------------------------------------------------------

hitter_proj_label = ctx["hitter_proj"] or "—"
pitcher_proj_label = ctx["pitcher_proj"] or "—"
ip_adj_label = ctx["ip_adj"] or "None"

# Attempt to infer from active sheet name when projection parsing failed
if hitter_proj_label == "—" and isinstance(active_sheet, str):
    hitter_proj_label = active_sheet

player_type_label = (ctx.get("player_type") or "Auto").title()

col_h, col_p, col_ip, col_type = st.columns(4)

with col_h:
    st.markdown(
        f"""<div class="config-card">
            <div class="label">Hitter Projections</div>
            <div class="value">{hitter_proj_label}</div>
            <div class="sub">Hitting</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col_p:
    st.markdown(
        f"""<div class="config-card">
            <div class="label">Pitcher Projections</div>
            <div class="value">{pitcher_proj_label}</div>
            <div class="sub">Pitching</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col_ip:
    ip_color = "#f0b429" if ip_adj_label != "None" else "#8b949e"
    st.markdown(
        f"""<div class="config-card">
            <div class="label">IP Adjustment</div>
            <div class="value" style="color:{ip_color};">{ip_adj_label}</div>
            <div class="sub">Playing Time</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col_type:
    sb_badge = "✔ SB" if ctx["sb_included"] else "— SB"
    st.markdown(
        f"""<div class="config-card">
            <div class="label">View</div>
            <div class="value">{player_type_label}</div>
            <div class="sub">{sb_badge}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown('<hr class="sgp-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Combined-view toggle
# ---------------------------------------------------------------------------

df_display = df_raw.copy()

if ctx["player_type"] == "combined" or (len(sheet_names) > 1 and active_sheet == 0):
    view_toggle = st.radio(
        "View",
        ["Combined", "Hitters only", "Pitchers only"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if view_toggle == "Hitters only":
        # Keep rows that look like hitters (have PA or POS)
        hitter_mask = pd.Series([True] * len(df_display), index=df_display.index)
        if "PA" in df_display.columns:
            hitter_mask = df_display["PA"].notna() & (df_display["PA"] > 0)
        elif "IP" in df_display.columns:
            hitter_mask = df_display["IP"].isna() | (df_display["IP"] == 0)
        df_display = df_display[hitter_mask]
    elif view_toggle == "Pitchers only":
        pitcher_mask = pd.Series([True] * len(df_display), index=df_display.index)
        if "IP" in df_display.columns:
            pitcher_mask = df_display["IP"].notna() & (df_display["IP"] > 0)
        elif "PA" in df_display.columns:
            pitcher_mask = df_display["PA"].isna() | (df_display["PA"] == 0)
        df_display = df_display[pitcher_mask]

# ---------------------------------------------------------------------------
# Sidebar filters (rendered into placeholders now that df is loaded)
# ---------------------------------------------------------------------------

pos_col = find_pos_column(df_display)

with pos_filter_placeholder:
    if pos_col and _is_hitter and not _is_pitcher:
        # Hitter position filter
        all_positions: list[str] = sorted(
            {
                p.strip()
                for cell in df_display[pos_col].dropna().astype(str)
                for p in re.split(r"[/,;|]", cell)
                if p.strip()
            }
        )
        if all_positions:
            pos_filter = st.multiselect(
                "Position (pos)",
                options=all_positions,
                default=[],
                placeholder="All positions",
            )
        else:
            pos_filter = []
    else:
        pos_filter = []

with role_filter_placeholder:
    if _is_pitcher and "Role" in df_display.columns:
        role_opts = sorted(df_display["Role"].dropna().unique().tolist())
        role_filter = st.multiselect(
            "Role (auc_calc)",
            options=role_opts,
            default=[],
            placeholder="SP & RP",
        )
    else:
        role_filter = []

with search_placeholder:
    name_col = next(
        (c for c in df_display.columns if c.lower() in ("name", "player", "playername")),
        None,
    )
    search_query = st.text_input(
        "🔍 Player search",
        value="",
        placeholder="Type a name…",
    )

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------

# Position filter (hitters)
if pos_filter and pos_col:
    mask = df_display[pos_col].astype(str).apply(
        lambda v: any(p in re.split(r"[/,;|]", v) for p in pos_filter)
    )
    df_display = df_display[mask]

# Role filter (pitchers)
if role_filter and "Role" in df_display.columns:
    df_display = df_display[df_display["Role"].isin(role_filter)]

# Name search
if search_query and name_col:
    df_display = df_display[
        df_display[name_col].astype(str).str.contains(search_query, case=False, na=False)
    ]

# ---------------------------------------------------------------------------
# Main data display
# ---------------------------------------------------------------------------

row_count = len(df_display)
col_count = len(df_display.columns)

col_info, col_dl = st.columns([3, 1])

with col_info:
    points_note = " · **points_total** ready" if "points_total" in df_display.columns else ""
    adp_note = " · ADP ✔" if any(c.lower() == "adp" for c in df_display.columns) else ""
    st.markdown(
        f"Showing **{row_count:,}** players · {col_count} columns{adp_note}{points_note}"
    )

with col_dl:
    out_name = pick.split("/")[-1].rsplit(".", 1)[0] + ".csv"
    st.download_button(
        "⬇ Download CSV",
        df_display.to_csv(index=False).encode("utf-8"),
        file_name=out_name,
        mime="text/csv",
        use_container_width=True,
    )

# Sort by VAR or Total_SGP descending by default if present
default_sort = next(
    (c for c in ("VAR", "Total_SGP", "points_total") if c in df_display.columns),
    None,
)
if default_sort:
    df_display = df_display.sort_values(by=default_sort, ascending=False, na_position="last")

# Build column configuration
col_cfg = build_column_config(df_display)

st.dataframe(
    df_display,
    use_container_width=True,
    column_config=col_cfg,
    hide_index=True,
)

# --------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown('<hr class="sgp-divider">', unsafe_allow_html=True)
st.caption(f"gs://{BUCKET}/{pick}  ·  Sheet: {active_sheet}  ·  {row_count} rows")

