import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Config ----------
IST = ZoneInfo("Asia/Kolkata")
DB_PATH = "money.db"
MEMBERS = ["Sripada", "My Brother"]
THEME = {
    "Sripada": "linear-gradient(120deg,#6c5ce7,#f06595,#ff922b)",
    "My Brother": "linear-gradient(120deg,#ff922b,#fcc419,#51cf66)",
}
SPEND_CATS = {
    "Food": ("🍔", "#ff8a3d"), "Travel": ("🚌", "#4dabf7"), "Shopping": ("🛍️", "#f06595"),
    "Bills": ("💡", "#f5b800"), "Rent": ("🏠", "#20c997"), "Fun": ("🎮", "#9775fa"),
    "Other": ("✨", "#ff5d73"),
}
EARN_CATS = {
    "Salary": ("💼", "#12b886"), "Freelance": ("💻", "#0ca678"),
    "Gift": ("🎁", "#ff6b9d"), "Other": ("✨", "#51cf66"),
}
ICON = {**{k: v[0] for k, v in EARN_CATS.items()}, **{k: v[0] for k, v in SPEND_CATS.items()}}
COLOR = {**{k: v[1] for k, v in EARN_CATS.items()}, **{k: v[1] for k, v in SPEND_CATS.items()}}

st.set_page_config(page_title="Family Money Tracker", page_icon="💰", layout="centered")

st.markdown(
    """
<style>
.stApp{background:linear-gradient(160deg,#fff7ec 0%,#ffe8f1 45%,#e8e4ff 100%)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#e8e4ff,#ffe0ec,#fff1d6)}
.hero{border-radius:26px;padding:20px 22px;color:#fff;margin-bottom:14px;box-shadow:0 10px 24px rgba(108,92,231,.25)}
.hero h1{margin:0;font-size:2rem;font-weight:800;color:#fff}
.hero p{margin:2px 0 0;opacity:.95;font-weight:600}
.tile{border-radius:22px;padding:16px 18px;color:#fff;margin-bottom:10px;box-shadow:0 8px 18px rgba(0,0,0,.12)}
.tile .l{font-weight:700;opacity:.95}
.tile .v{font-size:2.1rem;font-weight:800;line-height:1.15}
.earn{background:linear-gradient(135deg,#12b886,#63e6be)}
.spend{background:linear-gradient(135deg,#ff5d73,#ffa94d)}
.net{background:linear-gradient(90deg,#6c5ce7,#f06595)}
.netneg{background:linear-gradient(90deg,#e03131,#862e9c)}
.bar{height:18px;border-radius:99px;overflow:hidden;display:flex;background:#ff5d73;margin:4px 0 2px;box-shadow:inset 0 2px 4px rgba(0,0,0,.15)}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#12b886,#63e6be)}
.barl{display:flex;justify-content:space-between;font-weight:700;font-size:.85rem;margin-bottom:10px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}
.chip{border-radius:16px;padding:8px 14px;color:#fff;font-weight:800;box-shadow:0 4px 10px rgba(0,0,0,.12)}
.chip small{display:block;font-weight:600;opacity:.95}
.top{background:linear-gradient(90deg,#ffd43b,#ff922b);border-radius:16px;padding:10px 14px;font-weight:800;color:#2a1b3d;margin-bottom:10px}
h2,h3{color:#5f3dc4 !important}
button[data-baseweb="tab"]{background:#fff;border-radius:99px;margin-right:6px;padding:6px 16px;font-weight:800;box-shadow:0 3px 8px rgba(0,0,0,.08)}
button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,#6c5ce7,#f06595);color:#fff}
button[data-baseweb="tab"][aria-selected="true"] p{color:#fff}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none}
.stButton>button,[data-testid="stFormSubmitButton"]>button,.stDownloadButton>button{
  background:linear-gradient(90deg,#ffc43d,#ff922b);color:#2a1b3d;font-weight:800;border:0;border-radius:14px}
div[role="radiogroup"] label{background:#fff;border-radius:99px;padding:4px 14px;box-shadow:0 3px 8px rgba(0,0,0,.08)}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- Database ----------
def conn():
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """CREATE TABLE IF NOT EXISTS entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member TEXT, type TEXT, category TEXT,
            amount REAL, note TEXT, date TEXT)"""
    )
    return c


def add_entry(member, typ, cat, amount, note, d):
    with conn() as c:
        c.execute(
            "INSERT INTO entries(member,type,category,amount,note,date) VALUES(?,?,?,?,?,?)",
            (member, typ, cat, amount, note, d.isoformat()),
        )


def delete_entries(ids):
    with conn() as c:
        c.executemany("DELETE FROM entries WHERE id=?", [(int(i),) for i in ids])


def load(member) -> pd.DataFrame:
    with conn() as c:
        df = pd.read_sql_query(
            "SELECT id,type,category,amount,note,date FROM entries WHERE member=? ORDER BY date DESC,id DESC",
            c, params=(member,),
        )
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- Colourful helpers ----------
def inr(x):
    return f"₹{x:,.2f}".replace(".00", "")


def tiles(df, label):
    e = df.loc[df.type == "earn", "amount"].sum()
    s = df.loc[df.type == "spend", "amount"].sum()
    n = e - s
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="tile earn"><div class="l">💰 Earned {label}</div><div class="v">{inr(e)}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="tile spend"><div class="l">🛍️ Spent {label}</div><div class="v">{inr(s)}</div></div>', unsafe_allow_html=True)
    cls, word, ico = ("net", "Left over", "🎉") if n >= 0 else ("netneg", "Spent more than earned", "⚠️")
    st.markdown(f'<div class="tile {cls}"><div class="l">{ico} {word}</div><div class="v">{inr(abs(n))}</div></div>', unsafe_allow_html=True)
    pct = 50 if e + s == 0 else e / (e + s) * 100
    st.markdown(f'<div class="bar"><i style="width:{pct}%"></i></div><div class="barl"><span style="color:#0a8f6b">Earned</span><span style="color:#e0364f">Spent</span></div>', unsafe_allow_html=True)


def category_section(df, key):
    sp = df[df.type == "spend"].groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if sp.empty:
        st.info("No spending in this period yet.")
        return
    top = sp.iloc[0]
    st.markdown(f'<div class="top">🏆 Biggest spend: {ICON.get(top.category, "")} {top.category} · {inr(top.amount)}</div>', unsafe_allow_html=True)
    chips = "".join(
        f'<div class="chip" style="background:{COLOR.get(r.category, "#888")}">{ICON.get(r.category, "")} {r.category}<small>{inr(r.amount)}</small></div>'
        for r in sp.itertuples()
    )
    st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)
    fig = px.pie(sp, names="category", values="amount", hole=0.5, color="category", color_discrete_map=COLOR)
    fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="#fff", width=2)))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, key=key)


def type_color(col):
    return ["background-color:#d3f9d8;color:#0a8f6b;font-weight:700" if v == "earn"
            else "background-color:#ffe3e3;color:#e0364f;font-weight:700" for v in col]


def entries_table(df):
    if df.empty:
        st.caption("Nothing here yet.")
        return
    show = df.assign(
        date=df.date.dt.strftime("%d %b %Y"),
        category=df.category.map(lambda c: f"{ICON.get(c, '')} {c}"),
    )[["date", "type", "category", "amount", "note"]]
    sty = show.style.apply(type_color, subset=["type"]).format({"amount": "₹{:,.0f}"})
    st.dataframe(sty, use_container_width=True, hide_index=True)


# ---------- Header + member ----------
now = datetime.now(IST)
member = st.radio("Who?", MEMBERS, horizontal=True, label_visibility="collapsed")
st.markdown(
    f'<div class="hero" style="background:{THEME[member]}"><h1>💰 {member}\'s money</h1>'
    f'<p>{now.strftime("%A, %d %B %Y · %I:%M %p")}</p></div>',
    unsafe_allow_html=True,
)
df = load(member)
today = now.date()

# ---------- 10 PM reminder banner ----------
today_spend = df[(df.date.dt.date == today) & (df.type == "spend")]
if now.hour >= 22 and today_spend.empty:
    st.warning(f"🔔 It's past 10 PM. Add today's spending for {member}!")

# ---------- Add entry (sidebar) ----------
with st.sidebar:
    st.header(f"➕ Add entry · {member}")
    typ = st.radio("Type", ["spend", "earn"], format_func=lambda t: "🛍️ Spent" if t == "spend" else "💰 Earned", horizontal=True)
    cats = list(SPEND_CATS if typ == "spend" else EARN_CATS)
    with st.form("add", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        cat = st.selectbox("Category", cats, format_func=lambda c: f"{ICON[c]} {c}")
        d = st.date_input("Date", value=today, max_value=today)
        note = st.text_input("Note (optional)")
        if st.form_submit_button("Add entry", use_container_width=True):
            if amount > 0:
                add_entry(member, typ, cat, amount, note.strip(), d)
                st.rerun()
            else:
                st.error("Enter an amount greater than 0.")

# ---------- Tabs ----------
t_today, t_month, t_year = st.tabs(["🌞 Today", "📅 Month", "🗓️ 1 Year"])

with t_today:
    day = df[df.date.dt.date == today]
    tiles(day, "today")
    st.subheader("Where today's money went")
    category_section(day, "cat_today")
    st.subheader("Today's entries")
    entries_table(day)

with t_month:
    months = [str(p) for p in pd.period_range(end=pd.Period(today, "M"), periods=12, freq="M")][::-1]
    pick = st.selectbox("Month", months)
    mdf = df[df.date.dt.strftime("%Y-%m") == pick]
    tiles(mdf, pick)
    st.subheader("Full expenditure by category")
    category_section(mdf, "cat_month")
    sp = mdf[mdf.type == "spend"]
    if not sp.empty:
        st.subheader("Daily spending")
        daily = sp.groupby([sp.date.dt.day.rename("day"), "category"], as_index=False)["amount"].sum()
        fig = px.bar(daily, x="day", y="amount", color="category", color_discrete_map=COLOR)
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title_text="",
                          xaxis_title="Day of month", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.6)")
        st.plotly_chart(fig, use_container_width=True, key="daily")
    st.subheader("All entries this month")
    entries_table(mdf)

with t_year:
    start = pd.Period(today, "M") - 11
    ydf = df[df.date.dt.to_period("M") >= start].copy()
    tiles(ydf, "in 12 months")
    idx = pd.period_range(start, pd.Period(today, "M"), freq="M")
    ydf["month"] = ydf.date.dt.to_period("M")
    piv = ydf.pivot_table(index="month", columns="type", values="amount", aggfunc="sum").reindex(idx).fillna(0)
    for col in ("earn", "spend"):
        if col not in piv:
            piv[col] = 0.0
    piv["left"] = piv["earn"] - piv["spend"]
    piv.index = piv.index.strftime("%b %Y")

    st.subheader("Month by month")
    long = piv.reset_index().rename(columns={"index": "month"}).melt(
        id_vars="month", value_vars=["earn", "spend"], var_name="type", value_name="amount")
    fig = px.bar(long, x="month", y="amount", color="type", barmode="group",
                 color_discrete_map={"earn": "#12b886", "spend": "#ff5d73"})
    fig.add_scatter(x=piv.index, y=piv["left"], mode="lines+markers", name="left",
                    line=dict(color="#6c5ce7", width=4), marker=dict(size=9))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title_text="", xaxis_title="",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.6)")
    st.plotly_chart(fig, use_container_width=True, key="year_bar")

    table = piv[["earn", "spend", "left"]].rename(columns={"earn": "Earned", "spend": "Spent", "left": "Left"})
    table.loc["TOTAL"] = table.sum()
    sty = (table.style.format("₹{:,.0f}")
           .set_properties(subset=["Earned"], **{"background-color": "#d3f9d8", "color": "#0a8f6b", "font-weight": "700"})
           .set_properties(subset=["Spent"], **{"background-color": "#ffe3e3", "color": "#e0364f", "font-weight": "700"})
           .set_properties(subset=["Left"], **{"background-color": "#e5dbff", "color": "#5f3dc4", "font-weight": "700"}))
    st.dataframe(sty, use_container_width=True)

    st.subheader("Full expenditure by category")
    category_section(ydf, "cat_year")
    st.download_button("⬇️ Download all entries (CSV)", df.to_csv(index=False).encode(),
                       file_name=f"{member.replace(' ', '_').lower()}_money.csv", mime="text/csv")

# ---------- Delete entries ----------
with st.expander("🗑️ Delete wrong entries"):
    if df.empty:
        st.caption("No entries yet.")
    else:
        edit = df.head(50).assign(delete=False)
        edit["date"] = edit.date.dt.strftime("%d %b %Y")
        res = st.data_editor(
            edit, hide_index=True, use_container_width=True, key="editor",
            disabled=["id", "type", "category", "amount", "note", "date"],
            column_config={"id": None},
        )
        if st.button("Delete selected"):
            ids = res.loc[res["delete"], "id"].tolist()
            if ids:
                delete_entries(ids)
                st.rerun()
