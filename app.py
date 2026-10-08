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
SPEND_CATS = {
    "Food": "#ff8a3d", "Travel": "#4dabf7", "Shopping": "#f06595",
    "Bills": "#fcc419", "Rent": "#20c997", "Fun": "#9775fa", "Other": "#ff5d73",
}
EARN_CATS = {"Salary": "#12b886", "Freelance": "#20c997", "Gift": "#ff6b9d", "Other": "#51cf66"}
ALL_COLORS = {**EARN_CATS, **SPEND_CATS}

st.set_page_config(page_title="Family Money Tracker", page_icon="💰", layout="centered")

st.markdown(
    """
<style>
.tile{border-radius:20px;padding:16px 18px;color:#fff;margin-bottom:8px}
.tile .l{font-weight:700;opacity:.95}
.tile .v{font-size:2rem;font-weight:800;line-height:1.15}
.earn{background:linear-gradient(135deg,#12b886,#0a8f6b)}
.spend{background:linear-gradient(135deg,#ff5d73,#e0364f)}
.net{background:linear-gradient(90deg,#6c5ce7,#a29bfe)}
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
            c,
            params=(member,),
        )
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- Helpers ----------
def inr(x):
    return f"₹{x:,.2f}".replace(".00", "")


def tiles(df, label):
    e = df.loc[df.type == "earn", "amount"].sum()
    s = df.loc[df.type == "spend", "amount"].sum()
    n = e - s
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="tile earn"><div class="l">💰 Earned {label}</div><div class="v">{inr(e)}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="tile spend"><div class="l">🛍️ Spent {label}</div><div class="v">{inr(s)}</div></div>', unsafe_allow_html=True)
    word = "Left over" if n >= 0 else "Spent more than earned"
    st.markdown(f'<div class="tile net"><div class="l">{word}</div><div class="v">{inr(n)}</div></div>', unsafe_allow_html=True)


def category_chart(df, key):
    sp = df[df.type == "spend"].groupby("category", as_index=False)["amount"].sum()
    if sp.empty:
        st.info("No spending in this period yet.")
        return
    fig = px.pie(sp, names="category", values="amount", hole=0.5,
                 color="category", color_discrete_map=ALL_COLORS)
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True, key=key)


def entries_table(df):
    if df.empty:
        st.caption("Nothing here yet.")
        return
    show = df.assign(date=df.date.dt.strftime("%d %b %Y"))[["date", "type", "category", "amount", "note"]]
    st.dataframe(show, use_container_width=True, hide_index=True)


# ---------- Header + member ----------
now = datetime.now(IST)
st.title("Family money 💰")
st.caption(now.strftime("%A, %d %B %Y · %I:%M %p"))

member = st.radio("Who?", MEMBERS, horizontal=True, label_visibility="collapsed")
df = load(member)
today = now.date()

# ---------- 10 PM reminder banner ----------
today_spend = df[(df.date.dt.date == today) & (df.type == "spend")]
if now.hour >= 22 and today_spend.empty:
    st.warning(f"🔔 It's past 10 PM. Add today's spending for {member}!")

# ---------- Add entry (sidebar) ----------
with st.sidebar:
    st.header(f"Add entry · {member}")
    typ = st.radio("Type", ["spend", "earn"], format_func=lambda t: "🛍️ Spent" if t == "spend" else "💰 Earned", horizontal=True)
    cats = list(SPEND_CATS if typ == "spend" else EARN_CATS)
    with st.form("add", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        cat = st.selectbox("Category", cats)
        d = st.date_input("Date", value=today, max_value=today)
        note = st.text_input("Note (optional)")
        if st.form_submit_button("Add entry", use_container_width=True):
            if amount > 0:
                add_entry(member, typ, cat, amount, note.strip(), d)
                st.success("Added!")
                st.rerun()
            else:
                st.error("Enter an amount greater than 0.")

# ---------- Tabs ----------
t_today, t_month, t_year = st.tabs(["Today", "Month", "1 Year"])

with t_today:
    day = df[df.date.dt.date == today]
    tiles(day, "today")
    st.subheader("Where today's money went")
    category_chart(day, "cat_today")
    st.subheader("Today's entries")
    entries_table(day)

with t_month:
    months = [str(p) for p in pd.period_range(end=pd.Period(today, "M"), periods=12, freq="M")][::-1]
    pick = st.selectbox("Month", months)
    mdf = df[df.date.dt.strftime("%Y-%m") == pick]
    tiles(mdf, pick)
    st.subheader("Full expenditure by category")
    category_chart(mdf, "cat_month")
    if not mdf.empty:
        daily = mdf.groupby([mdf.date.dt.day.rename("day"), "type"], as_index=False)["amount"].sum()
        fig = px.bar(daily, x="day", y="amount", color="type", barmode="group",
                     color_discrete_map={"earn": "#12b886", "spend": "#ff5d73"})
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title_text="", xaxis_title="Day of month")
        st.plotly_chart(fig, use_container_width=True, key="daily")
    st.subheader("All entries this month")
    entries_table(mdf)

with t_year:
    start = pd.Period(today, "M") - 11
    ydf = df[df.date.dt.to_period("M") >= start].copy()
    tiles(ydf, "in 12 months")
    idx = pd.period_range(start, pd.Period(today, "M"), freq="M")
    ydf["month"] = ydf.date.dt.to_period("M")
    piv = (ydf.pivot_table(index="month", columns="type", values="amount", aggfunc="sum")
           .reindex(idx).fillna(0))
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
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title_text="", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True, key="year_bar")

    table = piv[["earn", "spend", "left"]].rename(columns={"earn": "Earned", "spend": "Spent", "left": "Left"})
    table.loc["TOTAL"] = table.sum()
    st.dataframe(table.style.format("₹{:,.0f}"), use_container_width=True)

    st.subheader("Full expenditure by category")
    category_chart(ydf, "cat_year")

    st.download_button("⬇️ Download all entries (CSV)", df.to_csv(index=False).encode(),
                       file_name=f"{member.replace(' ', '_').lower()}_money.csv", mime="text/csv")

# ---------- Delete entries ----------
with st.expander("Delete wrong entries"):
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
