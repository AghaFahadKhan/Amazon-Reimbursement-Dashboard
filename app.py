"""
Amazon Reimbursement Analytics Dashboard
Streamlit version — by Agha Fahad Khan
----------------------------------------
Multi-user access controlled via .streamlit/secrets.toml
"""

import io
import hmac
from datetime import date, timedelta

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Amazon Reimbursement Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# STYLING (mimics the HTML dashboard's dark look)
# ═══════════════════════════════════════════════════════════════
CUSTOM_CSS = """
<style>
    /* Hide default streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Accent colour */
    :root {
        --accent: #e94560;
        --teal: #00b4d8;
    }

    /* Top banner */
    .topbar {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 18px 24px;
        border-radius: 12px;
        margin-bottom: 18px;
        border: 1px solid #2a2a4a;
    }
    .topbar-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
    .topbar-title span { color: #e94560; }
    .topbar-subtitle { font-size: 12px; color: #aaa; margin-top: 4px; }

    /* KPI cards */
    div[data-testid="stMetric"] {
        background: #1e1e3a;
        border: 1px solid #2a2a4a;
        padding: 16px 18px;
        border-radius: 12px;
    }
    div[data-testid="stMetric"] label p { color: #888 !important; font-size: 11px !important;
        text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #e94560 !important; font-size: 22px !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #12122a;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding: 0 18px;
        font-size: 13px;
        font-weight: 600;
        color: #888;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #e94560 !important;
        background: rgba(233, 69, 96, 0.1) !important;
        border-bottom: 2px solid #e94560 !important;
    }

    /* Dataframe */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Buttons */
    .stButton>button {
        background: #e94560;
        color: #fff;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover { background: #c73652; color: #fff; }

    /* Download button */
    .stDownloadButton>button {
        background: rgba(233,69,96,0.1);
        color: #e94560;
        border: 1px solid #e94560;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
REASON_COLORS = {
    "CustomerReturn":          "#e94560",
    "Lost_Warehouse":          "#00b4d8",
    "Lost_Inbound":            "#a78bfa",
    "CustomerServiceIssue":    "#ffd700",
    "Damaged_Warehouse":       "#ff6b35",
    "Reimbursement_Reversal":  "#888888",
}

MONTH_NAMES = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

PLOTLY_DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ccc", size=11),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    margin=dict(l=10, r=10, t=30, b=10),
)

# ═══════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════
def check_password() -> bool:
    """Username / password gate that reads credentials from st.secrets.

    secrets.toml should look like:

        [users]
        alice = "alice_password"
        bob   = "bob_password"
        admin = "super_secret"
    """

    def login_submitted():
        users = st.secrets.get("users", {})
        username = st.session_state.get("username", "").strip()
        password = st.session_state.get("password", "")

        if username in users and hmac.compare_digest(password, str(users[username])):
            st.session_state["authenticated"] = True
            st.session_state["current_user"] = username
            # Don't keep the password in memory
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated"):
        return True

    # --- Login form -------------------------------------------------
    st.markdown(
        """
        <div class="topbar">
          <div class="topbar-title">📦 Amazon <span>Reimbursement</span> Analytics</div>
          <div class="topbar-subtitle">by Agha Fahad Khan — please sign in to continue</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 Sign In")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                login_submitted()

        if st.session_state.get("authenticated") is False:
            st.error("❌ Incorrect username or password.")

        if "users" not in st.secrets:
            st.warning(
                "⚠️ No users configured. Add credentials to "
                "`.streamlit/secrets.toml` under a `[users]` table."
            )

    return False


# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════
REQUIRED_COLS = [
    "Approval Date", "reimbursement-id", "reason", "asin", "product-name",
    "condition", "currency-unit", "amount-per-unit", "amount-total",
    "quantity-reimbursed-cash", "quantity-reimbursed-inventory",
    "quantity-reimbursed-total",
]


@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    """Parse an uploaded Amazon reimbursement CSV into a clean DataFrame."""
    # Amazon exports are usually tab-separated despite the .csv extension; try both
    buf = io.BytesIO(file_bytes)
    try:
        df = pd.read_csv(buf, sep=None, engine="python")
    except Exception:
        buf.seek(0)
        df = pd.read_csv(buf)

    # Normalise money columns
    for c in ["amount-total", "amount-per-unit"]:
        if c in df.columns:
            df[c] = (
                df[c].astype(str)
                .str.replace(r"[\$,]", "", regex=True)
                .replace({"": "0", "nan": "0"})
                .astype(float)
            )

    # Normalise integer columns
    for c in ["quantity-reimbursed-cash", "quantity-reimbursed-inventory",
              "quantity-reimbursed-total"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # Date column — keep as string in YYYY-MM-DD for easy string comparisons,
    # and also a parsed datetime for filtering
    if "Approval Date" in df.columns:
        df["Approval Date"] = df["Approval Date"].astype(str).str.strip().str[:10]
        df["_date"] = pd.to_datetime(df["Approval Date"], errors="coerce")
        df = df.dropna(subset=["_date"]).reset_index(drop=True)

    # Fill missing required text columns with empty strings
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = ""

    return df


def fmt_money(x: float) -> str:
    return f"${x:,.2f}"


# ═══════════════════════════════════════════════════════════════
# DATE FILTERING
# ═══════════════════════════════════════════════════════════════
def apply_date_range(df: pd.DataFrame, preset: str,
                     custom_start: date | None, custom_end: date | None) -> pd.DataFrame:
    if df.empty or preset == "All Time":
        return df

    today = pd.Timestamp(date.today())

    if preset == "Today":
        return df[df["_date"].dt.date == today.date()]
    if preset == "Yesterday":
        y = today - pd.Timedelta(days=1)
        return df[df["_date"].dt.date == y.date()]
    if preset == "Month to Date":
        start = today.replace(day=1)
        return df[(df["_date"] >= start) & (df["_date"] <= today)]
    if preset == "Last Month":
        first_this = today.replace(day=1)
        last_prev = first_this - pd.Timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return df[(df["_date"] >= first_prev) & (df["_date"] <= last_prev)]
    if preset == "Custom" and custom_start and custom_end:
        s = pd.Timestamp(custom_start); e = pd.Timestamp(custom_end)
        return df[(df["_date"] >= s) & (df["_date"] <= e)]
    return df


def compute_compare_range(df: pd.DataFrame, preset: str, mode: str,
                          custom_start, custom_end,
                          cmp_start=None, cmp_end=None) -> pd.DataFrame:
    """Return the data-frame slice that represents the 'compare to' period."""
    if df.empty:
        return df.iloc[0:0]

    today = pd.Timestamp(date.today())

    if mode == "vs Custom Range" and cmp_start and cmp_end:
        s = pd.Timestamp(cmp_start); e = pd.Timestamp(cmp_end)
        return df[(df["_date"] >= s) & (df["_date"] <= e)]

    if preset in ("Today", "Yesterday"):
        y = today - pd.Timedelta(days=1)
        return df[df["_date"].dt.date == y.date()]

    if preset == "Month to Date":
        first_prev = (today.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
        # same day-of-month span in previous month
        prev_end = first_prev + pd.Timedelta(days=today.day - 1)
        return df[(df["_date"] >= first_prev) & (df["_date"] <= prev_end)]

    if preset == "Last Month":
        first_this = today.replace(day=1)
        last_prev = first_this - pd.Timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        # month before that
        last_prev_prev = first_prev - pd.Timedelta(days=1)
        first_prev_prev = last_prev_prev.replace(day=1)
        return df[(df["_date"] >= first_prev_prev) & (df["_date"] <= last_prev_prev)]

    if preset == "Custom" and custom_start and custom_end:
        s = pd.Timestamp(custom_start); e = pd.Timestamp(custom_end)
        span = e - s
        cmp_e = s - pd.Timedelta(days=1)
        cmp_s = cmp_e - span
        return df[(df["_date"] >= cmp_s) & (df["_date"] <= cmp_e)]

    return df.iloc[0:0]


# ═══════════════════════════════════════════════════════════════
# TAB 0 — OVERVIEW
# ═══════════════════════════════════════════════════════════════
def render_overview(df: pd.DataFrame, full_df: pd.DataFrame, compare_df: pd.DataFrame,
                    compare_on: bool) -> None:
    total = float(df["amount-total"].sum())
    cases = len(df)
    asins = df["asin"].nunique()
    avg = total / cases if cases else 0.0
    reasons_n = df["reason"].nunique()

    top_reason = "—"
    if cases:
        gb = df.groupby("reason")["amount-total"].sum().sort_values(ascending=False)
        if len(gb):
            top_reason = gb.index[0].replace("_", " ").replace("Customer", "Cust.")

    net = float(df[df["reason"] != "Reimbursement_Reversal"]["amount-total"].sum())

    # compare deltas
    def pct(a, b):
        if not b or b == 0:
            return None
        return (a - b) / abs(b) * 100

    cmp_total = float(compare_df["amount-total"].sum()) if compare_on else 0.0
    cmp_cases = len(compare_df) if compare_on else 0

    delta_total = pct(total, cmp_total) if compare_on else None
    delta_cases = pct(cases, cmp_cases) if compare_on else None

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Reimbursed", fmt_money(total),
              delta=f"{delta_total:+.1f}% vs prev" if delta_total is not None else None)
    c2.metric("Total Cases", f"{cases:,}",
              delta=f"{delta_cases:+.1f}% vs prev" if delta_cases is not None else None)
    c3.metric("Unique ASINs", f"{asins:,}")
    c4.metric("Avg Per Case", fmt_money(avg))
    c5.metric("Top Reason", top_reason)
    c6.metric("Net Reimbursed", fmt_money(net))

    st.markdown("")

    if df.empty:
        st.info("No data in the selected date range.")
        return

    col_a, col_b = st.columns(2)

    # --- Daily trend ------------------------------------------------
    daily = df.groupby("Approval Date")["amount-total"].sum().reset_index().sort_values("Approval Date")
    fig_d = go.Figure()
    fig_d.add_trace(go.Scatter(
        x=daily["Approval Date"], y=daily["amount-total"],
        mode="lines", fill="tozeroy", line=dict(color="#e94560", width=2),
        fillcolor="rgba(233,69,96,0.15)", name="Amount",
    ))
    if compare_on and not compare_df.empty:
        cmp_daily = (compare_df.groupby("Approval Date")["amount-total"]
                     .sum().reset_index().sort_values("Approval Date"))
        fig_d.add_trace(go.Scatter(
            x=cmp_daily["Approval Date"], y=cmp_daily["amount-total"],
            mode="lines", line=dict(color="#00b4d8", width=2, dash="dash"),
            name="Compare",
        ))
    fig_d.update_layout(title="Daily Reimbursement Amount", height=320, **PLOTLY_DARK_LAYOUT)
    fig_d.update_yaxes(tickprefix="$", tickformat=",.0f")
    col_a.plotly_chart(fig_d, use_container_width=True)

    # --- Monthly totals --------------------------------------------
    monthly = df.copy()
    monthly["month"] = monthly["_date"].dt.strftime("%Y-%m")
    mg = monthly.groupby("month")["amount-total"].sum().reset_index().sort_values("month")
    mg["label"] = mg["month"].apply(
        lambda k: f"{MONTH_NAMES[int(k.split('-')[1])-1][:3]} {k.split('-')[0]}"
    )
    fig_m = go.Figure()
    fig_m.add_trace(go.Bar(
        x=mg["label"], y=mg["amount-total"], marker_color="#00b4d8", name="Amount"
    ))
    if compare_on and not compare_df.empty:
        cmp_m = compare_df.copy()
        cmp_m["month"] = cmp_m["_date"].dt.strftime("%Y-%m")
        cg = cmp_m.groupby("month")["amount-total"].sum().reset_index().sort_values("month")
        cg["label"] = cg["month"].apply(
            lambda k: f"{MONTH_NAMES[int(k.split('-')[1])-1][:3]} {k.split('-')[0]}"
        )
        fig_m.add_trace(go.Bar(
            x=cg["label"], y=cg["amount-total"],
            marker_color="rgba(0,180,216,0.35)", name="Compare"
        ))
    fig_m.update_layout(title="Monthly Totals", height=320, barmode="group", **PLOTLY_DARK_LAYOUT)
    fig_m.update_yaxes(tickprefix="$", tickformat=",.0f")
    col_b.plotly_chart(fig_m, use_container_width=True)

    col_c, col_d = st.columns(2)

    # --- Reason doughnut -------------------------------------------
    rg = df.groupby("reason")["amount-total"].sum().reset_index().sort_values("amount-total", ascending=False)
    rg["label"] = rg["reason"].str.replace("_", " ", regex=False)
    fig_r = go.Figure(go.Pie(
        labels=rg["label"], values=rg["amount-total"],
        hole=0.55,
        marker=dict(colors=[REASON_COLORS.get(r, "#888") for r in rg["reason"]]),
    ))
    fig_r.update_layout(title="Amount by Reason", height=320, **PLOTLY_DARK_LAYOUT)
    col_c.plotly_chart(fig_r, use_container_width=True)

    # --- Top 10 ASINs ----------------------------------------------
    ag = df.groupby("asin")["amount-total"].sum().reset_index().sort_values("amount-total", ascending=True).tail(10)
    fig_a = go.Figure(go.Bar(
        y=ag["asin"], x=ag["amount-total"], orientation="h",
        marker_color="#ffd700",
    ))
    fig_a.update_layout(title="Top 10 ASINs by Amount", height=320, **PLOTLY_DARK_LAYOUT)
    fig_a.update_xaxes(tickprefix="$", tickformat=",.0f")
    col_d.plotly_chart(fig_a, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 1 — DAILY ANALYSIS
# ═══════════════════════════════════════════════════════════════
def render_daily(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data uploaded.")
        return

    months = sorted(df["_date"].dt.strftime("%Y-%m").unique().tolist())
    options = ["All Months"] + [
        f"{MONTH_NAMES[int(m.split('-')[1])-1]} {m.split('-')[0]}" for m in months
    ]
    choice = st.selectbox("Filter by Month", options, key="daily_month")

    data = df
    if choice != "All Months":
        idx = options.index(choice) - 1
        key = months[idx]
        data = df[df["_date"].dt.strftime("%Y-%m") == key]

    daily = (data.groupby("Approval Date")
             .agg(total=("amount-total", "sum"), cases=("amount-total", "count"))
             .reset_index()
             .sort_values("Approval Date"))
    daily["avg"] = daily["total"] / daily["cases"].replace(0, np.nan)
    daily["cumulative"] = daily["total"].cumsum()

    # Chart: bars + cumulative line
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["Approval Date"], y=daily["total"],
        marker_color="rgba(233,69,96,0.75)", name="Daily Amount", yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=daily["Approval Date"], y=daily["cumulative"],
        mode="lines", line=dict(color="#ffd700", width=2), name="Cumulative", yaxis="y2",
    ))
    fig.update_layout(
        title="Daily Amount + Cumulative Trend",
        height=380,
        yaxis=dict(title="Daily", tickprefix="$", gridcolor="rgba(255,255,255,0.05)"),
        yaxis2=dict(title="Cumulative", tickprefix="$", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(color="#ffd700")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Table
    total_val = daily["total"].sum()
    st.markdown(f"**Daily Breakdown** — Total: **{fmt_money(total_val)}**")
    display = daily.rename(columns={
        "Approval Date": "Date",
        "total": "Total Amount",
        "cases": "# Cases",
        "avg": "Avg / Case",
        "cumulative": "Cumulative",
    }).copy()
    display["Total Amount"] = display["Total Amount"].apply(fmt_money)
    display["Avg / Case"] = display["Avg / Case"].apply(lambda v: fmt_money(v) if pd.notna(v) else "—")
    display["Cumulative"] = display["Cumulative"].apply(fmt_money)
    st.dataframe(display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
# TAB 2 — BY REASON
# ═══════════════════════════════════════════════════════════════
def render_reason(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data uploaded.")
        return

    agg = (df.groupby("reason")
           .agg(total=("amount-total", "sum"), cases=("amount-total", "count"))
           .reset_index()
           .sort_values("total", ascending=False))
    agg["label"] = agg["reason"].str.replace("_", " ", regex=False)
    agg["avg"] = agg["total"] / agg["cases"].replace(0, np.nan)
    grand = agg["total"].sum()
    agg["pct"] = agg["total"] / grand * 100 if grand else 0

    c1, c2 = st.columns(2)

    fig_bar = go.Figure(go.Bar(
        x=agg["label"], y=agg["total"],
        marker_color=[REASON_COLORS.get(r, "#888") for r in agg["reason"]],
    ))
    fig_bar.update_layout(title="Amount by Reason", height=350, **PLOTLY_DARK_LAYOUT)
    fig_bar.update_yaxes(tickprefix="$", tickformat=",.0f")
    c1.plotly_chart(fig_bar, use_container_width=True)

    fig_pie = go.Figure(go.Pie(
        labels=agg["label"] + " (" + agg["cases"].astype(str) + ")",
        values=agg["cases"],
        marker=dict(colors=[REASON_COLORS.get(r, "#888") for r in agg["reason"]]),
    ))
    fig_pie.update_layout(title="Case Count by Reason", height=350, **PLOTLY_DARK_LAYOUT)
    c2.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### Reason Summary")
    display = agg[["label", "total", "cases", "avg", "pct"]].rename(columns={
        "label": "Reason", "total": "Total Amount", "cases": "# Cases",
        "avg": "Avg / Case", "pct": "% of Total",
    })
    display["Total Amount"] = display["Total Amount"].apply(fmt_money)
    display["Avg / Case"] = display["Avg / Case"].apply(lambda v: fmt_money(v) if pd.notna(v) else "—")
    display["% of Total"] = display["% of Total"].apply(lambda v: f"{v:.1f}%")
    st.dataframe(display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
# TAB 3 — BY ASIN
# ═══════════════════════════════════════════════════════════════
def render_asin(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data uploaded.")
        return

    c1, c2 = st.columns([1, 2])
    reasons = ["All Reasons"] + sorted(df["reason"].dropna().unique().tolist())
    sel_reason = c1.selectbox("Filter by Reason", reasons, key="asin_reason")
    search = c2.text_input("Search ASIN or product…", key="asin_search")

    data = df if sel_reason == "All Reasons" else df[df["reason"] == sel_reason]

    agg = (data.groupby(["asin", "product-name"], dropna=False)
           .agg(total=("amount-total", "sum"),
                cases=("amount-total", "count"),
                qty_cash=("quantity-reimbursed-cash", "sum"),
                qty_inv=("quantity-reimbursed-inventory", "sum"))
           .reset_index()
           .sort_values("total", ascending=False))
    agg["avg"] = agg["total"] / agg["cases"].replace(0, np.nan)

    top15 = agg.head(15).iloc[::-1]  # reverse for horizontal bar
    fig = go.Figure(go.Bar(
        y=top15["asin"], x=top15["total"], orientation="h",
        marker_color=[f"hsl({(i*22+10)%360}, 80%, 55%)" for i in range(len(top15))],
    ))
    fig.update_layout(title="Top 15 ASINs by Reimbursement Amount",
                      height=500, **PLOTLY_DARK_LAYOUT)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

    if search:
        s = search.lower()
        agg = agg[
            agg["asin"].astype(str).str.lower().str.contains(s, na=False)
            | agg["product-name"].astype(str).str.lower().str.contains(s, na=False)
        ]

    st.markdown(f"**ASIN Breakdown** — {len(agg):,} records")
    display = agg.rename(columns={
        "asin": "ASIN", "product-name": "Product",
        "total": "Total", "cases": "# Cases", "avg": "Avg / Case",
        "qty_cash": "Qty Cash", "qty_inv": "Qty Inventory",
    })[["ASIN", "Product", "Total", "# Cases", "Avg / Case", "Qty Cash", "Qty Inventory"]]
    display["Total"] = display["Total"].apply(fmt_money)
    display["Avg / Case"] = display["Avg / Case"].apply(lambda v: fmt_money(v) if pd.notna(v) else "—")
    st.dataframe(display, use_container_width=True, hide_index=True, height=420)


# ═══════════════════════════════════════════════════════════════
# TAB 4 — DATE × REASON
# ═══════════════════════════════════════════════════════════════
def render_date_reason(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data uploaded.")
        return

    reasons = sorted(df["reason"].dropna().unique().tolist())
    pivot = (df.pivot_table(index="Approval Date", columns="reason",
                            values="amount-total", aggfunc="sum", fill_value=0)
             .sort_index())
    # ensure all reason columns exist in a consistent order
    for r in reasons:
        if r not in pivot.columns:
            pivot[r] = 0
    pivot = pivot[reasons]

    fig = go.Figure()
    for r in reasons:
        fig.add_trace(go.Bar(
            x=pivot.index, y=pivot[r], name=r.replace("_", " "),
            marker_color=REASON_COLORS.get(r, "#888"),
        ))
    fig.update_layout(title="Daily Amount Stacked by Reason",
                      barmode="stack", height=380, **PLOTLY_DARK_LAYOUT)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Date × Reason Pivot Table")
    disp = pivot.copy()
    disp["Day Total"] = disp.sum(axis=1)
    # grand total row
    total_row = pd.DataFrame(disp.sum(axis=0)).T
    total_row.index = ["TOTAL"]
    disp = pd.concat([disp, total_row])
    # pretty-print money
    fmt = disp.copy()
    for c in fmt.columns:
        fmt[c] = fmt[c].apply(lambda v: fmt_money(v) if v else "—")
    fmt = fmt.rename(columns={c: c.replace("_", " ") for c in fmt.columns})
    st.dataframe(fmt, use_container_width=True, height=420)


# ═══════════════════════════════════════════════════════════════
# TAB 5 — ASIN × REASON
# ═══════════════════════════════════════════════════════════════
def render_asin_reason(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data uploaded.")
        return

    reasons = sorted(df["reason"].dropna().unique().tolist())

    # Top 20 ASINs by total
    totals = df.groupby("asin")["amount-total"].sum().sort_values(ascending=False).head(20)
    top20 = totals.index.tolist()

    sub = df[df["asin"].isin(top20)]
    pivot = (sub.pivot_table(index="asin", columns="reason",
                             values="amount-total", aggfunc="sum", fill_value=0)
             .reindex(top20))
    for r in reasons:
        if r not in pivot.columns:
            pivot[r] = 0
    pivot = pivot[reasons]

    fig = go.Figure()
    for r in reasons:
        fig.add_trace(go.Bar(
            x=pivot.index, y=pivot[r], name=r.replace("_", " "),
            marker_color=REASON_COLORS.get(r, "#888"),
        ))
    fig.update_layout(title="Top 20 ASINs — Amount by Reason (Stacked)",
                      barmode="stack", height=440, **PLOTLY_DARK_LAYOUT)
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

    # Cross table — top 30 ASINs with product name
    top30 = df.groupby("asin")["amount-total"].sum().sort_values(ascending=False).head(30).index.tolist()
    name_map = df.drop_duplicates("asin").set_index("asin")["product-name"].to_dict()
    sub30 = df[df["asin"].isin(top30)]
    cross = (sub30.pivot_table(index="asin", columns="reason",
                               values="amount-total", aggfunc="sum", fill_value=0)
             .reindex(top30))
    for r in reasons:
        if r not in cross.columns:
            cross[r] = 0
    cross = cross[reasons]
    cross["Grand Total"] = cross.sum(axis=1)
    cross.insert(0, "Product", [name_map.get(a, "") for a in cross.index])

    fmt = cross.copy()
    for c in fmt.columns:
        if c == "Product":
            continue
        fmt[c] = fmt[c].apply(lambda v: fmt_money(v) if v else "—")
    fmt = fmt.rename(columns={c: c.replace("_", " ") for c in fmt.columns})

    st.markdown("### ASIN × Reason Cross Table (Top 30)")
    st.dataframe(fmt, use_container_width=True, height=500)


# ═══════════════════════════════════════════════════════════════
# TAB 6 — RAW REPORT
# ═══════════════════════════════════════════════════════════════
def render_raw(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No data uploaded.")
        return

    cols = ["Approval Date", "reimbursement-id", "reason", "asin", "product-name",
            "condition", "currency-unit", "amount-per-unit", "amount-total",
            "quantity-reimbursed-total"]
    cols = [c for c in cols if c in df.columns]

    search = st.text_input("Search any field…", key="raw_search")
    data = df[cols].copy()

    if search:
        s = search.lower()
        mask = pd.Series(False, index=data.index)
        for c in cols:
            mask = mask | data[c].astype(str).str.lower().str.contains(s, na=False)
        data = data[mask]

    st.markdown(f"**Reimbursed Report from Amazon** — {len(data):,} records")

    # Pretty formatting for display only
    disp = data.copy()
    if "amount-total" in disp.columns:
        disp["amount-total"] = disp["amount-total"].apply(fmt_money)
    if "amount-per-unit" in disp.columns:
        disp["amount-per-unit"] = disp["amount-per-unit"].apply(fmt_money)
    st.dataframe(disp, use_container_width=True, hide_index=True, height=500)

    # Download (unformatted) CSV of the filtered view
    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered rows as CSV",
                       csv, file_name="reimbursement_filtered.csv", mime="text/csv")


# ═══════════════════════════════════════════════════════════════
# HOW-TO HELP
# ═══════════════════════════════════════════════════════════════
HELP_STEPS = [
    "Log in to your **Amazon Seller Central** account at sellercentral.amazon.com",
    "Click the **hamburger menu (☰)** in the top-left corner",
    "Hover over **Reports** in the navigation menu",
    "Click on **Fulfillment** — a new window/page will open",
    "On the **left sidebar**, scroll down to the **Payments** section",
    "Under Payments, click on **Reimbursements**",
    "Click the **Download** button at the top of the report",
    "Select your **desired date range** (up to 18 months)",
    "Click **Request .csv Download** and wait for the file to be ready",
    "Once downloaded, **upload the file here** — your full analysis will appear instantly!",
]

def render_help():
    with st.expander("❓ How to download your Amazon Reimbursement CSV"):
        for i, step in enumerate(HELP_STEPS, 1):
            st.markdown(f"**{i}.** {step}")
        st.info("💡 Tip: download the largest date range possible for the most comprehensive analysis.")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main() -> None:
    if not check_password():
        st.stop()

    # --- Header -----------------------------------------------------
    user = st.session_state.get("current_user", "")
    st.markdown(
        f"""
        <div class="topbar">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div class="topbar-title">📦 Amazon <span>Reimbursement</span> Analytics</div>
              <div class="topbar-subtitle">by Agha Fahad Khan — signed in as <b>{user}</b></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Sidebar: upload + filters ---------------------------------
    with st.sidebar:
        st.markdown("### 📂 Upload Data")
        uploaded = st.file_uploader("Amazon Reimbursement CSV", type=["csv", "tsv", "txt"])

        if st.button("Sign out", use_container_width=True):
            for k in ("authenticated", "current_user"):
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown("---")
        render_help()

    if uploaded is None:
        st.markdown(
            """
            <div style="text-align:center; padding:80px 20px;">
              <div style="font-size:60px;">📄</div>
              <h3 style="color:#e94560;">Upload your Amazon Reimbursement CSV to begin</h3>
              <p style="color:#888;">Use the uploader in the sidebar. Need the file? See the help section.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Load + cache the dataframe
    try:
        df = load_csv(uploaded.getvalue())
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    if df.empty:
        st.warning("The file was parsed but contains no valid rows.")
        return

    # --- Date filter bar ------------------------------------------
    st.markdown("#### 📅 Date Filter")
    fc1, fc2, fc3 = st.columns([2, 2, 1])

    with fc1:
        preset = st.radio(
            "Preset",
            ["All Time", "Today", "Yesterday", "Month to Date", "Last Month", "Custom"],
            horizontal=True, label_visibility="collapsed",
            key="date_preset",
        )

    custom_start = custom_end = None
    if preset == "Custom":
        with fc2:
            min_d = df["_date"].min().date()
            max_d = df["_date"].max().date()
            custom_start, custom_end = st.date_input(
                "Custom range",
                value=(min_d, max_d),
                min_value=min_d, max_value=max_d,
                key="custom_range",
            ) if True else (None, None)

    with fc3:
        compare_on = st.toggle("Compare Mode", value=False, key="cmp_on")

    cmp_mode = "vs Previous Period"
    cmp_start = cmp_end = None
    if compare_on:
        cc1, cc2 = st.columns([1, 2])
        with cc1:
            cmp_mode = st.selectbox(
                "Compare against",
                ["vs Previous Period", "vs Previous Month", "vs Custom Range"],
                key="cmp_mode",
            )
        if cmp_mode == "vs Custom Range":
            with cc2:
                min_d = df["_date"].min().date()
                max_d = df["_date"].max().date()
                cmp_start, cmp_end = st.date_input(
                    "Compare range",
                    value=(min_d, max_d),
                    min_value=min_d, max_value=max_d,
                    key="cmp_range",
                )

    filtered = apply_date_range(df, preset, custom_start, custom_end)
    compare_df = (compute_compare_range(df, preset, cmp_mode, custom_start,
                                        custom_end, cmp_start, cmp_end)
                  if compare_on else df.iloc[0:0])

    # --- Tabs ------------------------------------------------------
    tabs = st.tabs([
        "📊 Overview",
        "📅 Daily Analysis",
        "🏷️ By Reason",
        "📦 By ASIN",
        "🔄 Date × Reason",
        "🔲 ASIN × Reason",
        "📋 Raw Report",
    ])

    with tabs[0]:
        render_overview(filtered, df, compare_df, compare_on)
    with tabs[1]:
        render_daily(filtered)
    with tabs[2]:
        render_reason(filtered)
    with tabs[3]:
        render_asin(filtered)
    with tabs[4]:
        render_date_reason(filtered)
    with tabs[5]:
        render_asin_reason(filtered)
    with tabs[6]:
        render_raw(filtered)


if __name__ == "__main__":
    main()
