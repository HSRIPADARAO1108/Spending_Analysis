"""Shared database layer for the app and the notifier.
Uses DATABASE_URL (env var or Streamlit secret). Falls back to local SQLite."""
import os

import pandas as pd
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine, delete, insert, select


def _url():
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL")
        except Exception:
            url = None
    url = url or "sqlite:///money.db"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


_engine = None
meta = MetaData()
entries = Table(
    "entries", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("member", String), Column("type", String), Column("category", String),
    Column("amount", Float), Column("note", String), Column("date", String),
)


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_url(), pool_pre_ping=True)
        meta.create_all(_engine)
    return _engine


def add_entry(member, typ, cat, amount, note, d):
    with engine().begin() as c:
        c.execute(insert(entries).values(member=member, type=typ, category=cat,
                                         amount=amount, note=note, date=d.isoformat()))


def delete_entries(ids):
    with engine().begin() as c:
        c.execute(delete(entries).where(entries.c.id.in_([int(i) for i in ids])))


def load(member) -> pd.DataFrame:
    q = (select(entries.c.id, entries.c.type, entries.c.category, entries.c.amount,
                entries.c.note, entries.c.date)
         .where(entries.c.member == member).order_by(entries.c.date.desc(), entries.c.id.desc()))
    with engine().connect() as c:
        df = pd.read_sql_query(q, c)
    df["date"] = pd.to_datetime(df["date"])
    return df
