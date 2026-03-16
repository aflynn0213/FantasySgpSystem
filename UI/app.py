"""
Fantasy SGP – Pro Sports Dashboard
Smart projection selector + position/role filters + config status header.
"""
from __future__ import annotations

import re
from io import BytesIO
from typing import Optional

import pandas as pd
import streamlit as st
from google.cloud import storage

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUCKET = "fantasysgpsystem-outputs"
KNOWN_PERIODS: set[str] = {"pre", "ros", "td", "eoy"}
PERIOD_LABELS: dict[str, str] = {
    "pre": "Pre-Season",
    "ros": "Rest of Season",
    "td":  "To-Date",
    "eoy": "End of Year",
}

_INTERNAL_COLS = {"PlayerId", "playerid", "player_id", "fg_id"}

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
    .sidebar-title {
        font-size: 1.1rem; font-weight: 700; color: #f0b429 !important;
        letter-spacing: .04em; text-transform: uppercase; margin-bottom: .4rem;
    }
    .config-card {
        background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 12px 16px; text-align: center;
    }
    .config-card .label {
        font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
        color: #8b949e; margin-bottom: 4px;
    }
    .config-card .value { font-size: 1.2rem; font-weight: 700; color: #f0b429; }
    .config-card .sub   { font-size: .78rem; color: #58a6ff; margin-top: 2px; }
    .sgp-divider { border: none; border-top: 1px solid #30363d; margin: 1rem 0; }
    [data-testid="stDataFrame"] thead th {
        background-color: #1c2128 !important;
        color: #f0b429 !important; font-weight: 600;
    }
    .stDownloadButton > button {
        background-color: #238636 !important; color: #fff !important;
        border: none; border-radius: 6px; font-weight: 600;
    }
    .stDownloadButton > button:hover { background-color: #2ea043 !important; }
    [data-testid="stAlert"] { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def list_blobs(prefix: str = "") -> list[str]:
    client = storage.Client()
    blobs = client.list_blobs(BUCKET, prefix=prefix)
    return sorted(b.name for b in blobs)


@st.cache_data(ttl=300)
def list_files(prefix: str = "") -> list[str]:
    return [b for b in list_blobs(prefix) if b.lower().endswith((".csv", ".xlsx"))]


@st.cache_data(ttl=300)
def load_blob(blob_name: str, sheet_name: str | int = 0) -> pd.DataFrame:
    client = storage.Client()
    raw = client.bucket(BUCKET).blob(blob_name).download_as_bytes()
    if blob_name.lower().endswith(".csv"):
        return pd.read_csv(BytesIO(raw))
    return pd.read_excel(BytesIO(raw), sheet_name=sheet_name, engine="openpyxl")


@st.cache_data(ttl=300)
def get_sheet_names(blob_name: str) -> list[str]:
    if blob_name.lower().endswith(".csv"):
        return []
    client = storage.Client()
    raw = client.bucket(BUCKET).blob(blob_name).download_as_bytes()
    return pd.ExcelFile(BytesIO(raw), engine="openpyxl").sheet_names


# ---------------------------------------------------------------------------
# Result-file metadata parser
# Output naming convention (both SGP and Points leagues):
#   {Mode}_{h}_{p}[_{ip_adj}]_{period}[_sb][_{type}].xlsx
#
# Input file conventions:
#   projections/   fangraphs_{type}_{proj}.xlsx          e.g. fangraphs_hitting_atc.xlsx
#   stats/         fangraphs_{type}_stats.xlsx            e.g. fangraphs_hitting_stats.xlsx
#   ros/           fangraphs_{type}_{proj}_ros.xlsx       e.g. fangraphs_hitting_atc_ros.xlsx
#   auc_calc_exports/ auc_calc_{type}_{proj}.xlsx         e.g. auc_calc_hitting_atc.xlsx
#   ip_adj input:  fangraphs_pitching_{ip_adj}.xlsx       e.g. fangraphs_pitching_zips.xlsx
# ---------------------------------------------------------------------------

# Recognised output file prefixes and the scoring mode they map to
_OUTPUT_PREFIXES: dict[str, str] = {"sgp_": "SGP", "points_": "Points"}


@st.cache_data(ttl=300)
def parse_result_files(prefix: str = "results/") -> list[dict]:
    """
    Scan GCS results/ folder and parse every SGP_*.xlsx / Points_*.xlsx blob.

    Returns a list of dicts with keys:
      blob_name, mode ('SGP'|'Points'), h_proj, p_proj, ip_adj (or None),
      period, sb (bool),
      player_type (None = 3-sheet workbook, else 'hitting'/'pitching'/'combined')
    """
    results: list[dict] = []
    for blob in list_blobs(prefix):
        name = blob.split("/")[-1]
        low  = name.lower()
        if not low.endswith(".xlsx"):
            continue

        mode: Optional[str] = None
        for pfx, label in _OUTPUT_PREFIXES.items():
            if low.startswith(pfx):
                mode = label
                break
        if mode is None:
            continue

        stem = low[:-5]  # strip .xlsx

        # Check for _sb suffix
        sb = stem.endswith("_sb")
        if sb:
            stem = stem[:-3]

        # Check for player_type suffix
        player_type: Optional[str] = None
        for pt in ("hitting", "pitching", "combined"):
            if stem.endswith(f"_{pt}"):
                player_type = pt
                stem = stem[: -(len(pt) + 1)]
                break

        # Strip leading prefix (e.g. "sgp_" or "points_")
        pfx_len = len(mode.lower()) + 1  # e.g. len("sgp") + 1 = 4
        parts = stem[pfx_len:].split("_")

        # Find period scanning right-to-left
        period_idx: Optional[int] = None
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] in KNOWN_PERIODS:
                period_idx = i
                break
        if period_idx is None:
            continue

        pre = parts[:period_idx]
        period = parts[period_idx]

        if len(pre) == 2:
            h_proj, p_proj, ip_adj = pre[0], pre[1], None
        elif len(pre) == 3:
            h_proj, p_proj, ip_adj = pre[0], pre[1], pre[2]
        else:
            continue

        results.append(
            dict(
                blob_name=blob,
                mode=mode,
                h_proj=h_proj.upper(),
                p_proj=p_proj.upper(),
                ip_adj=ip_adj.upper() if ip_adj else None,
                period=period,
                sb=sb,
                player_type=player_type,
            )
        )

    return results


def build_blob_name(
    mode: str,          # 'SGP' or 'Points'
    h_proj: str,
    p_proj: str,
    period: str,
    ip_adj: Optional[str],
    sb: bool,
    player_type: Optional[str] = None,  # None = 3-sheet workbook
) -> str:
    """Construct the expected GCS blob path for a given combination."""
    h  = h_proj.lower()
    p  = p_proj.lower()
    ip = f"_{ip_adj.lower()}" if ip_adj else ""
    sb_str = "_sb" if sb else ""
    pt_str = f"_{player_type}" if player_type else ""
    return f"results/{mode}_{h}_{p}{ip}_{period}{sb_str}{pt_str}.xlsx"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def find_pos_col(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col.lower() in ("pos", "elig", "position", "eligibility"):
            return col
    return None


def enrich_role(df: pd.DataFrame) -> pd.DataFrame:
    """Add a Role column to pitcher DataFrames if not already present."""
    if "Role" in df.columns:
        return df
    df = df.copy()
    pos_col = find_pos_col(df)
    if pos_col and df[pos_col].astype(str).str.contains("SP|RP", na=False).any():
        df["Role"] = df[pos_col].apply(
            lambda v: "SP" if isinstance(v, str) and "SP" in v.upper() else "RP"
        )
    elif "GS" in df.columns:
        df["Role"] = df["GS"].apply(lambda gs: "SP" if pd.notna(gs) and gs > 5 else "RP")
    return df


def is_pitcher_df(df: pd.DataFrame) -> bool:
    pit = {"IP", "GS", "SGP_ERA", "SGP_WHIP", "SGP_SO", "Starter", "Role"} & set(df.columns)
    hit = {"PA", "SGP_R", "SGP_HR", "SGP_OBP", "SGP_SLG"} & set(df.columns)
    return len(pit) > len(hit)


def is_hitter_df(df: pd.DataFrame) -> bool:
    hit = {"PA", "SGP_R", "SGP_HR", "SGP_OBP", "SGP_SLG", "POS", "ELIG"} & set(df.columns)
    return len(hit) >= 2


# ---------------------------------------------------------------------------
# Column config builder
# ---------------------------------------------------------------------------

def build_col_cfg(df: pd.DataFrame) -> dict:
    cfg: dict = {}
    for col in df.columns:
        if col in _INTERNAL_COLS or col.lower() in {c.lower() for c in _INTERNAL_COLS}:
            cfg[col] = None
            continue
        low = col.lower()
        if low == "points_total":
            cfg[col] = st.column_config.NumberColumn(label="⭐ Points", format="%.2f",
                           help="Total fantasy points (from backend points engine)")
        elif col in ("Total_SGP", "Total_SGP_wSB"):
            cfg[col] = st.column_config.NumberColumn(label=col.replace("_", " "), format="%.3f")
        elif col == "VAR":
            cfg[col] = st.column_config.NumberColumn(label="VAR", format="%.3f",
                           help="Value above replacement")
        elif low == "adp":
            cfg[col] = st.column_config.NumberColumn(label="ADP", format="%.1f",
                           help="Average Draft Position")
        elif low in ("dollars", "$"):
            cfg[col] = st.column_config.NumberColumn(label="$", format="$%.1f")
        elif col.startswith("SGP_"):
            cfg[col] = st.column_config.NumberColumn(label=col[4:], format="%.3f")
        elif pd.api.types.is_float_dtype(df[col]):
            cfg[col] = st.column_config.NumberColumn(format="%.2f")
    return cfg


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown('<p class="sidebar-title">⚾ SGP Dashboard</p>', unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio(
        "Mode",
        ["Smart Results", "File Browser"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Smart Results mode
    # -------------------------------------------------------------------------
    if mode == "Smart Results":

        meta_list = parse_result_files("results/")

        # Only 3-sheet workbooks (player_type is None) are the primary target
        workbooks = [m for m in meta_list if m["player_type"] is None]

        if not workbooks:
            st.warning("No result workbooks found in `results/`.")
            st.info(
                "Run the backend engine first.  \n"
                "Files must follow the pattern:  \n"
                "`SGP_{h}_{p}[_{ip_adj}]_{period}.xlsx`  \n"
                "`Points_{h}_{p}[_{ip_adj}]_{period}.xlsx`"
            )
            st.stop()

        # Scoring mode selector (SGP vs Points) — only show if both exist
        avail_modes = sorted({m["mode"] for m in workbooks})
        if len(avail_modes) > 1:
            sel_mode = st.radio("Scoring Mode", avail_modes, horizontal=True)
        else:
            sel_mode = avail_modes[0]
        workbooks = [m for m in workbooks if m["mode"] == sel_mode]

        # Unique option sets
        h_options   = sorted({m["h_proj"]  for m in workbooks})
        p_options   = sorted({m["p_proj"]  for m in workbooks})
        per_options = sorted({m["period"]  for m in workbooks},
                             key=lambda x: list(KNOWN_PERIODS).index(x) if x in KNOWN_PERIODS else 99)

        sel_h = st.selectbox(
            "Hitter Projections",
            h_options,
            help="Hitting projection system",
        )
        sel_p = st.selectbox(
            "Pitcher Projections",
            p_options,
            help="Pitching projection system",
        )
        sel_period = st.selectbox(
            "Period",
            per_options,
            format_func=lambda x: PERIOD_LABELS.get(x, x.title()),
        )

        # IP Adjustment
        ip_adjs_available = sorted(
            {m["ip_adj"] for m in workbooks
             if m["ip_adj"] and m["h_proj"] == sel_h and m["p_proj"] == sel_p}
        )
        use_ip = st.toggle("IP Adjustment", value=bool(ip_adjs_available))
        sel_ip: Optional[str] = None
        if use_ip:
            if ip_adjs_available:
                sel_ip = st.selectbox("IP Adj System", ip_adjs_available)
            else:
                st.caption("No IP-adjusted files found for this combination.")

        # SB Toggle
        sb_avail = any(
            m["sb"] for m in workbooks
            if m["h_proj"] == sel_h and m["p_proj"] == sel_p and m["period"] == sel_period
        )
        use_sb = st.toggle("Include SB", value=False,
                           disabled=not sb_avail,
                           help="Only shown if an _sb file exists for this combination")

        blob_name = build_blob_name(sel_mode, sel_h, sel_p, sel_period, sel_ip, use_sb)
        active_ctx = dict(
            mode=sel_mode, h_proj=sel_h, p_proj=sel_p, period=sel_period,
            ip_adj=sel_ip, sb=use_sb, player_type=None,
        )

    # -------------------------------------------------------------------------
    # File Browser mode
    # -------------------------------------------------------------------------
    else:
        FOLDERS = ["results/", "auction_calculator_exports/", "stats/", "ros/"]
        folder = st.selectbox("Folder", FOLDERS)
        files  = list_files(prefix=folder)
        if not files:
            st.warning("No files found.")
            st.stop()
        pick       = st.selectbox("File", files, index=len(files) - 1)
        blob_name  = pick
        active_ctx = dict(
            mode=None, h_proj=None, p_proj=None, period=None,
            ip_adj=None, sb=False, player_type=None,
        )

    st.markdown("---")
    st.markdown("**Filters**")
    _pos_ph   = st.empty()   # filled after df is loaded
    _role_ph  = st.empty()
    _search_ph = st.empty()


# ============================================================================
# LOAD DATA
# ============================================================================

sheet_names   = get_sheet_names(blob_name)
blob_exists   = blob_name in list_blobs("results/") or blob_name in list_blobs("")

if not blob_exists:
    st.error(
        f"**File not found in GCS:** `{blob_name}`\n\n"
        "This combination hasn't been generated yet. Run the backend engine with the "
        "selected settings, then refresh."
    )
    st.stop()

# Sheet selection (inline widget above table, not in sidebar, for multi-sheet files)
active_sheet: str | int = 0
if len(sheet_names) > 1:
    # For Smart Results go straight to a radio; for Browser show a selectbox
    if mode == "Smart Results":
        sheet_choice = st.radio(
            "View",
            sheet_names,
            horizontal=True,
            index=0,
        )
        active_sheet = sheet_choice
    else:
        active_sheet = st.selectbox("Sheet", sheet_names, label_visibility="collapsed")

df_raw = load_blob(blob_name, sheet_name=active_sheet)

# Infer player type from active sheet name
_sheet_low = active_sheet.lower() if isinstance(active_sheet, str) else ""
if "hitter" in _sheet_low or active_sheet == "Hitters":
    _type_hint = "hitting"
elif "pitcher" in _sheet_low or active_sheet == "Pitchers":
    _type_hint = "pitching"
elif "combined" in _sheet_low or active_sheet == "Combined":
    _type_hint = "combined"
else:
    _type_hint = active_ctx.get("player_type")  # may be None

# Enrich pitchers with Role if missing
_is_pit = is_pitcher_df(df_raw)
_is_hit = is_hitter_df(df_raw)
if _is_pit and not _is_hit:
    df_raw = enrich_role(df_raw)


# ============================================================================
# CONFIGURATION STATUS HEADER
# ============================================================================

h_label   = active_ctx.get("h_proj") or "—"
p_label   = active_ctx.get("p_proj") or "—"
ip_label  = active_ctx.get("ip_adj") or "None"
per_label = PERIOD_LABELS.get(active_ctx.get("period", ""), active_ctx.get("period") or "—")
sb_badge  = "✔ SB" if active_ctx.get("sb") else "— SB"

col_h, col_p, col_ip, col_meta = st.columns(4)

with col_h:
    st.markdown(
        f'<div class="config-card"><div class="label">Hitter Projections</div>'
        f'<div class="value">{h_label}</div><div class="sub">Hitting</div></div>',
        unsafe_allow_html=True,
    )
with col_p:
    st.markdown(
        f'<div class="config-card"><div class="label">Pitcher Projections</div>'
        f'<div class="value">{p_label}</div><div class="sub">Pitching</div></div>',
        unsafe_allow_html=True,
    )
with col_ip:
    _ip_colour = "#f0b429" if ip_label != "None" else "#8b949e"
    st.markdown(
        f'<div class="config-card"><div class="label">IP Adjustment</div>'
        f'<div class="value" style="color:{_ip_colour};">{ip_label}</div>'
        f'<div class="sub">Playing Time</div></div>',
        unsafe_allow_html=True,
    )
with col_meta:
    st.markdown(
        f'<div class="config-card"><div class="label">Period</div>'
        f'<div class="value">{per_label}</div><div class="sub">{sb_badge}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="sgp-divider">', unsafe_allow_html=True)


# ============================================================================
# SIDEBAR FILTERS  (rendered into placeholder containers)
# ============================================================================

df_display = df_raw.copy()
pos_col    = find_pos_col(df_display)

with _pos_ph:
    if pos_col and _is_hit and not _is_pit:
        all_pos = sorted({
            p.strip()
            for cell in df_display[pos_col].dropna().astype(str)
            for p in re.split(r"[/,;|]", cell)
            if p.strip()
        })
        pos_filter = st.multiselect("Position", all_pos, default=[], placeholder="All positions") if all_pos else []
    else:
        pos_filter = []

with _role_ph:
    if _is_pit and "Role" in df_display.columns:
        role_opts   = sorted(df_display["Role"].dropna().unique())
        role_filter = st.multiselect("Role", role_opts, default=[], placeholder="SP & RP")
    else:
        role_filter = []

with _search_ph:
    name_col = next(
        (c for c in df_display.columns if c.lower() in ("name", "player", "playername")), None
    )
    search_q = st.text_input("🔍 Player search", placeholder="Type a name…")


# ============================================================================
# APPLY FILTERS
# ============================================================================

if pos_filter and pos_col:
    df_display = df_display[
        df_display[pos_col].astype(str).apply(
            lambda v: any(p in re.split(r"[/,;|]", v) for p in pos_filter)
        )
    ]

if role_filter and "Role" in df_display.columns:
    df_display = df_display[df_display["Role"].isin(role_filter)]

if search_q and name_col:
    df_display = df_display[
        df_display[name_col].astype(str).str.contains(search_q, case=False, na=False)
    ]


# ============================================================================
# MAIN TABLE
# ============================================================================

# Default sort
sort_by = next((c for c in ("VAR", "Total_SGP", "points_total") if c in df_display.columns), None)
if sort_by:
    df_display = df_display.sort_values(by=sort_by, ascending=False, na_position="last")

row_count = len(df_display)
col_count = len(df_display.columns)

info_col, dl_col = st.columns([3, 1])
with info_col:
    adp_note    = " · ADP ✔"    if any(c.lower() == "adp"          for c in df_display.columns) else ""
    elig_note   = " · POS ✔"   if any(c.lower() in ("elig","pos") for c in df_display.columns) else ""
    points_note = " · ⭐ Points" if "points_total"                 in df_display.columns        else ""
    st.markdown(
        f"Showing **{row_count:,}** players · {col_count} columns"
        f"{adp_note}{elig_note}{points_note}"
    )
with dl_col:
    fname = blob_name.split("/")[-1].rsplit(".", 1)[0]
    if isinstance(active_sheet, str) and active_sheet:
        fname += f"_{active_sheet}"
    st.download_button(
        "⬇ Download CSV",
        df_display.to_csv(index=False).encode(),
        file_name=f"{fname}.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.dataframe(
    df_display,
    use_container_width=True,
    column_config=build_col_cfg(df_display),
    hide_index=True,
)

st.markdown('<hr class="sgp-divider">', unsafe_allow_html=True)
st.caption(f"gs://{BUCKET}/{blob_name}  ·  sheet: {active_sheet}  ·  {row_count} rows")
