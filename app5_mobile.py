# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 11:34:12 2026

@author: NCheam
"""

# -*- coding: utf-8 -*-
import streamlit as st

# ---------------- 1. INITIAL CONFIG ----------------
st.set_page_config(page_title="Bus Queue", layout="centered")

from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import math
from supabase import create_client
import pandas as pd
from datetime import datetime, timezone

# ---------------- 2. CONFIGURATION & STYLING ----------------
STOP_LAT, STOP_LON = 1.313516, 103.765742
ALLOWED_RADIUS = 15000 
SOLO_CLOUD_URL = "https://leisurefrontier.solo-cloud.com/ext/locatebus.php?param=Ab09RFDA2lHKYik2dSb1fY21aF0KMjMwAEtJQExGADQ1OTU4OQ=="

# Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Custom CSS for a tight, mobile-app look
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
            font-size: 10px !important; /* Standard is usually 16px */
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

    #.block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    #h1 { margin-top: -1.5rem !important; font-size: 1.8rem !important; text-align: center; }
    #h3 { margin-bottom: 0.2rem !important; font-size: 1.1rem !important; }
    #[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
    #div.stButton > button { width: 100%; height: 3.5em; border-radius: 12px; font-weight: bold; }
    #div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #1e7e34, #28a745); border: none; }
    #[data-testid="stMetric"] { background-color: #f1f3f6; padding: 10px; border-radius: 12px; }

# ---------------- 3. PHONE-BASED AUTH ----------------
if "phone" not in st.session_state:
    # Try to grab phone from URL first (for refreshes)
    url_phone = st.query_params.get("phone")
    st.session_state.phone = url_phone if url_phone else None

if not st.session_state.phone:
    st.title("🚌 Bus Queue")
    st.subheader("Enter Mobile Number to Join")
    phone_input = st.text_input("Mobile Number", placeholder="e.g. 91234567")
    if st.button("Start Tracking", type="primary"):
        if len(phone_input) >= 8:
            st.session_state.phone = phone_input
            st.query_params["phone"] = phone_input
            st.rerun()
        else:
            st.error("Please enter a valid number")
    st.stop() # Stop the rest of the app until phone is provided

user_phone = st.session_state.phone

# ---------------- 4. APP INTERFACE ----------------
st.header("🚌 Bus Tracker & Queue")
st.markdown(f"Welcome: {user_phone}")
st_autorefresh(interval=15 * 1000, key="datarefresh")

# Helpers
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_time_diff(datestring):
    try:
        diff = datetime.now(timezone.utc) - pd.to_datetime(datestring, utc=True)
        return max(0, int(diff.total_seconds() // 60))
    except: return 0

# Location Logic (Using a simpler component call)
from streamlit_js_eval import get_geolocation
loc = get_geolocation()
distance = None
if loc:
    distance = haversine(loc['coords']['latitude'], loc['coords']['longitude'], STOP_LAT, STOP_LON)

# ---------------- 6. QUEUE STATUS (ALWAYS SHOWS TOTAL) ----------------
#st.divider()
st.markdown("### 📊 Live Stats")

try:
    # 1. Fetch the entire waiting list from Supabase
    data = supabase.table("queue").select("*").eq("status", "waiting").order("created_at").execute()
    queue = data.data
    
    # 2. Show Global Metric (Visible to everyone)
    total_in_queue = len(queue)
    st.metric("Total Commuters Waiting", total_in_queue)
    
    # 3. Check for current user within that list
    user_data = next((x for x in queue if x["user_id"] == user_phone), None)
    pos = next((i+1 for i, x in enumerate(queue) if x["user_id"] == user_phone), None)

    if user_data:
        c1, c2 = st.columns(2)
        c1.info(f"🧍 Position: **#{pos}**")
        c2.info(f"⏱️ Waiting: **{get_time_diff(user_data['created_at'])}m**")
    else:
        st.write("You are not currently in the queue.")
        
except Exception as e:
    st.error("Stats unavailable")

# ---------------- 5. QUEUE ACTIONS ----------------
st.divider()
st.subheader("🚀 Join the Line")
col1, col2 = st.columns(2)

with col1:
    if st.button("Join Queue", use_container_width=True, type="primary"):
        if loc and distance <= ALLOWED_RADIUS:
            existing = supabase.table("queue").select("*").eq("user_id", user_phone).execute()
            if not existing.data:
                supabase.table("queue").insert({"user_id": user_phone, "status": "waiting"}).execute()
                st.rerun()
            else: st.warning("Already in line!")
        else: st.error("Out of range or GPS off")

with col2:
    if st.button("Leave Queue", use_container_width=True):
        supabase.table("queue").delete().eq("user_id", user_phone).execute()
        st.rerun()

# Live Map
st.markdown("### 📍 Live Bus Map")
components.iframe(SOLO_CLOUD_URL, height=350, scrolling=True)

# Logout (Clear Session)
if st.button("Logout / Change Number", use_container_width=True):
    st.session_state.phone = None
    st.query_params.clear()
    st.rerun()

# # ---------------- 6. QUEUE STATUS ----------------
# st.markdown("### 📊 Your Position")
# try:
#     data = supabase.table("queue").select("*").eq("status", "waiting").order("created_at").execute()
#     queue = data.data
#     user_data = next((x for x in queue if x["user_id"] == user_phone), None)
#     pos = next((i+1 for i, x in enumerate(queue) if x["user_id"] == user_phone), None)

#     if user_data:
#         c1, c2 = st.columns(2)
#         c1.metric("Position", f"#{pos}")
#         c2.metric("Wait Time", f"{get_time_diff(user_data['created_at'])}m")
#     else:
#         st.info("You are not in the queue.")
# except Exception as e:
#     st.error("Update failed")

# ---------------- 7. ADMIN ----------------
with st.expander("📍 GPS & Debug"):
    admin_pw1 = st.text_input("GPS Password", type="password", key = "pass1")
    if admin_pw1 == "gps123":
        if loc:
            st.write(f"Dist: {int(distance)}m | Valid: {'✅' if distance <= ALLOWED_RADIUS else '❌'}")
        #st.caption(f"Persistent User ID: {user_id}")
        st.caption(f"Logged in as: {user_phone}")

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
