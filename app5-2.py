# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 10:56:48 2026

@author: NCheam
"""

# -*- coding: utf-8 -*-
import streamlit as st

# ---------------- 1. INITIAL CONFIG (MUST BE FIRST) ----------------
st.set_page_config(page_title="Bus Queue App", layout="centered")

from streamlit_js_eval import get_geolocation, streamlit_js_eval
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import math
import uuid
from supabase import create_client
import pandas as pd
from datetime import datetime, timezone

# ---------------- 2. CONFIGURATION ----------------
STOP_LAT = 1.313516
STOP_LON = 103.765742
ALLOWED_RADIUS = 15000  # meters
SOLO_CLOUD_URL = "https://leisurefrontier.solo-cloud.com/ext/locatebus.php?param=Ab09RFDA2lHKYik2dSb1fY21aF0KMjMwAEtJQExGADQ1OTU4OQ=="

# 🔑 Supabase config
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- 3. PERSISTENT USER SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

local_id = streamlit_js_eval(js_expressions="localStorage.getItem('bus_app_user_id')", key="get_id")

if local_id:
    if st.session_state.user_id != local_id:
        st.session_state.user_id = local_id
        st.rerun() 
elif local_id == "":
    streamlit_js_eval(js_expressions=f"localStorage.setItem('bus_app_user_id', '{st.session_state.user_id}')", key="set_id")

user_id = st.session_state.user_id

# ---------------- 4. AUTO-REFRESH ----------------
# Refresh the queue data every 15 seconds
st_autorefresh(interval=15 * 1000, key="datarefresh")

# ---------------- 5. CUSTOM UI STYLING ----------------
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 3.8em;
        border-radius: 12px;
        font-weight: bold;
        transition: all 0.2s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1e7e34, #28a745);
        border: none;
    }
    div.stButton > button:active {
        transform: scale(0.96);
    }
    [data-testid="stMetric"] {
        background-color: #f1f3f6;
        padding: 15px;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚌 Bus Tracker & Queue")

# ---------------- 6. LIVE MAP ----------------
st.subheader("📍 Live Bus Map")
components.iframe(SOLO_CLOUD_URL, height=400, scrolling=True)
st.divider()

# ---------------- 7. HELPERS ----------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_time_diff(datestring):
    try:
        joined_time = pd.to_datetime(datestring, utc=True)
        now = datetime.now(timezone.utc)
        diff = now - joined_time
        return max(0, int(diff.total_seconds() // 60))
    except:
        return 0

# ---------------- 8. LOCATION FETCHING ----------------
loc = get_geolocation()
distance = None
if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    distance = haversine(u_lat, u_lon, STOP_LAT, STOP_LON)

# ---------------- 9. QUEUE ACTIONS ----------------
st.subheader("🚀 Join the Line")
col_join, col_leave = st.columns(2)

with col_join:
    if st.button("Join Queue", use_container_width=True, type="primary"):
        if loc and distance is not None:
            if distance <= ALLOWED_RADIUS:
                with st.spinner("Syncing..."):
                    existing = supabase.table("queue").select("*").eq("user_id", user_id).execute()
                if existing.data:
                    st.warning("You are already in queue")
                else:
                    try:
                        supabase.table("queue").insert({"user_id": user_id, "status": "waiting"}).execute()
                        st.success("Joined!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.error(f"❌ Outside Range ({int(distance)}m)")
        else:
            st.warning("📍 Detecting location...")

with col_leave:
    if st.button("Leave Queue", use_container_width=True):
        try:
            supabase.table("queue").delete().eq("user_id", user_id).execute()
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# ---------------- 10. QUEUE STATUS ----------------
st.divider()
st.subheader("📊 Your Status")

try:
    data = supabase.table("queue").select("*").eq("status", "waiting").order("created_at").execute()
    queue_list = data.data

    if queue_list:
        st.metric("Total Commuters", len(queue_list))
        
        user_data = next((x for x in queue_list if x["user_id"] == user_id), None)
        position = next((i+1 for i, x in enumerate(queue_list) if x["user_id"] == user_id), None)

        if user_data and position:
            mins = get_time_diff(user_data['created_at'])
            c1, c2 = st.columns(2)
            c1.info(f"🧍 Position: **#{position}**")
            c2.info(f"⏱️ Waiting: **{mins} min**")
        else:
            st.write("Join the queue to see your position.")
    else:
        st.write("The queue is empty.")
except Exception as e:
    st.error(f"Database Error: {e}")

# ---------------- 11. ADMIN & DEBUG ----------------
                
with st.expander("📍 GPS & Debug"):
    admin_pw1 = st.text_input("GPS Password", type="password", key = "pass1")
    if admin_pw1 == "gps123":
        if loc:
            st.write(f"Dist: {int(distance)}m | Valid: {'✅' if distance <= ALLOWED_RADIUS else '❌'}")
        st.caption(f"Persistent User ID: {user_id}")

with st.expander("🛠️ Admin Tools"):
    admin_pw = st.text_input("Admin Password", type="password", key = "pass2")
    if admin_pw == "bus123":
        admin_data = supabase.table("queue").select("*").order("created_at").execute()
        if admin_data.data:
            df_admin = pd.DataFrame(admin_data.data)
            st.table(df_admin[['user_id', 'created_at']])
            if st.button("🗑️ Clear All"):
                supabase.table("queue").delete().neq("status", "VOID").execute()
                st.rerun()