"""
db.py - Supabase database connection and helper functions
"""
import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("❌ Thiếu cấu hình SUPABASE_URL hoặc SUPABASE_KEY.")
        st.stop()
    return create_client(url, key)


def get_db() -> Client:
    return get_supabase_client()


def fetch_all(table: str, filters: dict = None, order: str = None):
    db = get_db()
    q = db.table(table).select("*")
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    if order:
        q = q.order(order)
    return q.execute().data or []


def fetch_one(table: str, record_id: str):
    db = get_db()
    result = db.table(table).select("*").eq("id", record_id).execute()
    data = result.data
    return data[0] if data else None


def insert_record(table: str, data: dict):
    db = get_db()
    result = db.table(table).insert(data).execute()
    return result.data[0] if result.data else None


def update_record(table: str, record_id: str, data: dict):
    db = get_db()
    from datetime import datetime
    data["updated_at"] = datetime.utcnow().isoformat()
    result = db.table(table).update(data).eq("id", record_id).execute()
    return result.data[0] if result.data else None


def delete_record(table: str, record_id: str):
    db = get_db()
    db.table(table).delete().eq("id", record_id).execute()


def fetch_view(view: str, filters: dict = None, order: str = None):
    db = get_db()
    q = db.table(view).select("*")
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    if order:
        q = q.order(order)
    return q.execute().data or []


def get_departments(active_only=True):
    db = get_db()
    q = db.table("departments").select("*").order("sort_order")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data or []


def get_department_map():
    depts = get_departments()
    return {d["id"]: d["name"] for d in depts}


def get_plans(year: int = None):
    db = get_db()
    q = db.table("audit_plans").select("*").order("year").order("sequence_no")
    if year:
        q = q.eq("year", year)
    return q.execute().data or []


def get_objectives_for_plan(plan_id: str):
    db = get_db()
    return db.table("audit_objectives").select("*").eq("plan_id", plan_id).order("objective_no").execute().data or []


def get_kpis_for_objective(objective_id: str):
    db = get_db()
    return db.table("audit_kpis").select("*").eq("objective_id", objective_id).execute().data or []


def get_findings_for_plan(plan_id: str):
    return fetch_view("v_findings_with_context", {"plan_id": plan_id})
