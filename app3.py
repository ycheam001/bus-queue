# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 16:25:03 2026

@author: NCheam
"""

import streamlit as st
from streamlit_js_eval import get_geolocation
import streamlit.components.v1 as components
import math
import uuid
from supabase import create_client

# ---------------- 1. CONFIGURATION ----------------
STOP_LAT = 1.313516
STOP_LON = 103.765742
ALLOWED_RADIUS = 15000  # meters

SOLO_CLOUD_URL = "https://leisurefrontier.solo-cloud.com/ext/locatebus.php?param=Ab09RFDA2lHKYik2dSb1fY21aF0KMjMwAEtJQExGADQ1OTU4OQ=="

# 🔑 Supabase config
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- 2. USER SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

# ---------------- 3. UI ----------------
st.set_page_config(page_title="Bus Queue App", layout="centered")

st.title("🚌 Bus Tracker & Smart Queue")

# ---------------- 4. MAP ----------------
st.subheader("📍 Live Bus Map")
components.iframe(SOLO_CLOUD_URL, height=450, scrolling=True)

st.divider()

# ---------------- 5. GPS FUNCTION ----------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ---------------- 7. QUEUE ACTIONS ----------------
st.subheader("🚀 Queue Actions")

loc = get_geolocation()
distance = None

if loc:
    u_lat = loc['coords']['latitude']
    u_lon = loc['coords']['longitude']

    distance = haversine(u_lat, u_lon, STOP_LAT, STOP_LON)

# --- JOIN QUEUE ---
if st.button("Join Queue", use_container_width=True):
    if loc and distance is not None:

        if distance <= ALLOWED_RADIUS:

            existing = supabase.table("queue")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()

            if existing.data:
                st.warning("⚠️ You already joined the queue")

            else:
                try:
                    supabase.table("queue").insert({
                        "user_id": user_id,
                        "status": "waiting"
                    }).execute()

                    st.success(f"🎉 Joined queue! Distance: {int(distance)}m")

                except Exception as e:
                    st.error(f"Error: {e}")

        else:
            st.error(f"❌ Too far! {int(distance)}m away")

    else:
        st.warning("📍 Location not detected")

# --- LEAVE QUEUE ---
if st.button("Leave Queue", use_container_width=True):
    try:
        supabase.table("queue")\
            .delete()\
            .eq("user_id", user_id)\
            .execute()

        st.success("👋 You left the queue")

    except Exception as e:
        st.error(f"Error: {e}")

st.divider()

# ---------------- 8. QUEUE STATUS ----------------
st.subheader("📊 Queue Status")

try:
    data = supabase.table("queue")\
        .select("*")\
        .eq("status", "waiting")\
        .order("created_at")\
        .execute()

    queue_list = data.data

    if queue_list:
        st.write(f"👥 Total in queue: {len(queue_list)}")

        position = next(
            (i+1 for i, x in enumerate(queue_list) if x["user_id"] == user_id),
            None
        )

        if position:
            st.info(f"🧍 Your position: #{position}")
        else:
            st.write("You are not in the queue")

    else:
        st.write("Queue is empty")

except Exception as e:
    st.error(f"Error fetching queue: {e}")

# ---------------- 6. LOCATION + DISTANCE ----------------
st.subheader("📍 Your Location & Distance")

#loc = get_geolocation()
#distance = None

if loc:
    u_lat = loc['coords']['latitude']
    u_lon = loc['coords']['longitude']

    distance = haversine(u_lat, u_lon, STOP_LAT, STOP_LON)

    st.success("Location detected")

    col1, col2 = st.columns(2)
    col1.metric("Latitude", f"{u_lat:.6f}")
    col2.metric("Longitude", f"{u_lon:.6f}")

    st.metric("Distance to Stop (meters)", f"{int(distance)} m")

    if distance <= ALLOWED_RADIUS:
        st.success("✅ Within allowed range")
    else:
        st.error("❌ Outside allowed range")
else:
    st.warning("📍 Allow location access and wait a moment")

st.divider()

# ---------------- 9. DEBUG INFO ----------------
st.caption(f"User ID: {user_id}")
st.caption(f"Target Stop: {STOP_LAT}, {STOP_LON}")
