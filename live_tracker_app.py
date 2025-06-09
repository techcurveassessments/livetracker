import streamlit as st
import boto3
import re
import pandas as pd
import time
from datetime import datetime

BUCKET_NAME = "ltisubmissions"

# Initialize S3 client
import os


s3 = boto3.client("s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
)

def list_students():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Delimiter="/")
    return [prefix["Prefix"].strip("/") for prefix in response.get("CommonPrefixes", [])]

def extract_submission_info(student_folder):
    result = {
        "Student Name": "",
        "Submission Time": "",
        "Submission Date": "",
        "Total Score": 0,
        "Total Passed": 0,
        "Total Failed": 0,
        "Questions Attempted": 0,
        "Status": "Not Started",
        "Details": {}
    }

    try:
        name, dt = student_folder.split("_")
        result["Student Name"] = name
        result["Submission Time"] = f"{dt[:8]} {dt[9:]}"
        result["Submission Date"] = dt[:8]
    except:
        result["Student Name"] = student_folder
        result["Submission Time"] = "Unknown"
        result["Submission Date"] = "Unknown"

    objects = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=student_folder + "/")
    prefixes = set()
    for obj in objects.get("Contents", []):
        parts = obj["Key"].split("/")
        if len(parts) >= 2 and parts[1].startswith("q"):
            prefixes.add(parts[1])

    result["Questions Attempted"] = len(prefixes)
    total_passed = 0
    total_failed = 0

    for question_id in sorted(prefixes):
        log_key = f"{student_folder}/{question_id}/test_report.log"
        try:
            log_obj = s3.get_object(Bucket=BUCKET_NAME, Key=log_key)
            content = log_obj['Body'].read().decode('utf-8')
            pass_count = len(re.findall(r"\[PASS\]", content))
            fail_count = len(re.findall(r"\[FAIL\]", content))
            result["Details"][question_id] = {
                "Passed": pass_count,
                "Failed": fail_count,
                "Status": "✅ Passed" if pass_count > 0 and fail_count == 0 else "⚠️ Partial" if pass_count > 0 else "❌ Failed"
            }
            total_passed += pass_count
            total_failed += fail_count
        except Exception:
            result["Details"][question_id] = {
                "Passed": "N/A",
                "Failed": "N/A",
                "Status": "⚠️ Error"
            }

    result["Total Passed"] = total_passed
    result["Total Failed"] = total_failed
    result["Total Score"] = total_passed
    if total_passed > 0 and total_failed == 0:
        result["Status"] = "✅ Perfect"
    elif total_passed > 0:
        result["Status"] = "⚠️ Partial"
    elif total_failed > 0:
        result["Status"] = "❌ Failed"
    return result

def build_grouped_leaderboard():
    students = list_students()
    grouped = {}
    for s in students:
        student_data = extract_submission_info(s)
        date = student_data["Submission Date"]
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(student_data)
    return grouped

st.set_page_config(page_title="Live Submission Tracker", layout="wide")
st.title("📊 Live Assignment Submission Dashboard")

refresh_interval = 10
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0

refresh_clicked = st.button("🔄 Manual Refresh")
current_time = time.time()
if refresh_clicked or (current_time - st.session_state.last_refresh) > refresh_interval:
    grouped_data = build_grouped_leaderboard()
    st.session_state.grouped_data = grouped_data
    st.session_state.last_refresh = current_time
    st.session_state.last_refresh_time = datetime.now().strftime("%H:%M:%S")

if 'grouped_data' in st.session_state:
    grouped_data = st.session_state.grouped_data
    st.markdown(f"<small>Last refreshed at {st.session_state.last_refresh_time}</small>", unsafe_allow_html=True)
    for test_date in sorted(grouped_data.keys(), reverse=True):
        submissions = grouped_data[test_date]
        st.markdown(f"## 📅 Submissions for {test_date}")
        df = pd.DataFrame([{
            "Student Name": s["Student Name"],
            "Submission Time": s["Submission Time"],
            "Total Score": s["Total Score"],
            "Total Passed": s["Total Passed"],
            "Total Failed": s["Total Failed"],
            "Questions Attempted": s["Questions Attempted"],
            "Status": s["Status"]
        } for s in submissions])

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Total Students", len(df))
        with col2: st.metric("Avg Score", f"{df['Total Score'].mean():.1f}")
        with col3: st.metric("Perfect", len(df[df["Status"] == "✅ Perfect"]))
        with col4: st.metric("Failed", len(df[df["Status"] == "❌ Failed"]))

        st.dataframe(df.sort_values(by=["Total Score", "Student Name"], ascending=[False, True]), use_container_width=True)

        for student in submissions:
            status_color = "green" if student["Status"] == "✅ Perfect" else "orange" if student["Status"] == "⚠️ Partial" else "red"
            st.markdown(f"### <span style='color:{status_color}'>{student['Student Name']} — {student['Status']}</span>", unsafe_allow_html=True)
            st.markdown(f"**Submitted:** {student['Submission Time']} | **Score:** {student['Total Score']} | **Passed:** {student['Total Passed']} | **Failed:** {student['Total Failed']}")
            cols = st.columns(3)
            for i, (q, details) in enumerate(student["Details"].items()):
                with cols[i % 3]:
                    st.markdown(f"**{q}** — {details['Status']}  ")
                    st.markdown(f"Passed: {details['Passed']} | Failed: {details['Failed']}")

        # Export CSV per date
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"📥 Download CSV for {test_date}",
            csv_data,
            file_name=f"submissions_{test_date}.csv",
            mime="text/csv"
        )
else:
    st.warning("Waiting for refresh or no data loaded yet.")
