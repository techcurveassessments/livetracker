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
    except:
        result["Student Name"] = student_folder
        result["Submission Time"] = "Unknown"

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

def build_leaderboard():
    students = list_students()
    all_data = []
    detailed_data = []
    for s in students:
        student_data = extract_submission_info(s)
        # Create flat version for CSV/download
        flat_data = {
            "Student Name": student_data["Student Name"],
            "Submission Time": student_data["Submission Time"],
            "Total Score": student_data["Total Score"],
            "Total Passed": student_data["Total Passed"],
            "Total Failed": student_data["Total Failed"],
            "Questions Attempted": student_data["Questions Attempted"],
            "Status": student_data["Status"]
        }
        # Add question details to flat version
        for q, details in student_data["Details"].items():
            flat_data[f"{q}_Passed"] = details["Passed"]
            flat_data[f"{q}_Failed"] = details["Failed"]
            flat_data[f"{q}_Status"] = details["Status"]
        
        all_data.append(flat_data)
        detailed_data.append(student_data)
    
    return pd.DataFrame(all_data), detailed_data

# ------------- STREAMLIT UI -------------
st.set_page_config(page_title="Live Submission Tracker", layout="wide")
st.title("📊 Live Assignment Submission Dashboard")

# Add some styling
st.markdown("""
<style>
    .big-font {
        font-size:18px !important;
    }
    .metric-box {
        border-radius: 10px;
        padding: 15px;
        background-color: #f0f2f6;
        margin-bottom: 20px;
    }
    .status-perfect {
        color: #28a745;
        font-weight: bold;
    }
    .status-partial {
        color: #ffc107;
        font-weight: bold;
    }
    .status-failed {
        color: #dc3545;
        font-weight: bold;
    }
    .refresh-info {
        font-size: 14px;
        color: #6c757d;
        margin-top: -10px;
        margin-bottom: 15px;
    }
    .student-card {
        border-radius: 10px;
        padding: 15px;
        background-color: #f8f9fa;
        margin-bottom: 15px;
        border-left: 5px solid #6c757d;
    }
    .student-card.perfect {
        border-left-color: #28a745;
    }
    .student-card.partial {
        border-left-color: #ffc107;
    }
    .student-card.failed {
        border-left-color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0
    st.session_state.df = None
    st.session_state.detailed_data = None

current_time = time.time()
refresh_interval = 10  # seconds

# Refresh button
refresh_clicked = st.button("🔄 Manual Refresh", help="Click to refresh data immediately")

# Check if we need to refresh (either by button or interval)
if refresh_clicked or (current_time - st.session_state.last_refresh) > refresh_interval:
    with st.spinner("Fetching and processing submission data..."):
        df, detailed_data = build_leaderboard()
        st.session_state.df = df
        st.session_state.detailed_data = detailed_data
        st.session_state.last_refresh = current_time
        st.session_state.last_refresh_time = datetime.now().strftime("%H:%M:%S")

# Show last refresh time if we have data
if 'last_refresh_time' in st.session_state:
    st.markdown(f'<div class="refresh-info">Last refreshed at: {st.session_state.last_refresh_time} (auto-refreshes every {refresh_interval} seconds)</div>', unsafe_allow_html=True)

# Display the data if we have it
if st.session_state.df is not None:
    df = st.session_state.df
    detailed_data = st.session_state.detailed_data
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><h3>Total Students</h3><p class="big-font">{len(df)}</p></div>', unsafe_allow_html=True)
    with col2:
        avg_score = df["Total Score"].mean()
        st.markdown(f'<div class="metric-box"><h3>Avg Score</h3><p class="big-font">{avg_score:.1f}</p></div>', unsafe_allow_html=True)
    with col3:
        perfect = len(df[df["Status"] == "✅ Perfect"])
        st.markdown(f'<div class="metric-box"><h3>Perfect Submissions</h3><p class="big-font">{perfect}</p></div>', unsafe_allow_html=True)
    with col4:
        failed = len(df[df["Status"] == "❌ Failed"])
        st.markdown(f'<div class="metric-box"><h3>Failed Submissions</h3><p class="big-font">{failed}</p></div>', unsafe_allow_html=True)
    
    # Display the leaderboard
    st.subheader("📋 Submission Leaderboard")
    
    # Create a copy for display
    display_df = df.copy()
    display_df = display_df.sort_values(by=["Total Score", "Student Name"], ascending=[False, True])
    
    # Display the dataframe without styling
    st.dataframe(
        display_df,
        column_order=["Student Name", "Status", "Total Score", "Total Passed", "Total Failed", "Questions Attempted", "Submission Time"],
        use_container_width=True,
        height=700
    )
    
    # Detailed student view
    st.subheader("🧑‍🎓 Student Details")
    
    for student in detailed_data:
        status_class = ""
        if student["Status"] == "✅ Perfect":
            status_class = "perfect"
        elif student["Status"] == "⚠️ Partial":
            status_class = "partial"
        elif student["Status"] == "❌ Failed":
            status_class = "failed"
        
        st.markdown(f"""
        <div class="student-card {status_class}">
            <h3>{student["Student Name"]} <span class="status-{status_class}">{student["Status"]}</span></h3>
            <p><strong>Submitted:</strong> {student["Submission Time"]} | 
            <strong>Score:</strong> {student["Total Score"]} | 
            <strong>Passed:</strong> {student["Total Passed"]} | 
            <strong>Failed:</strong> {student["Total Failed"]}</p>
        """, unsafe_allow_html=True)
        
        # Question details in columns
        cols = st.columns(3)
        for i, (q, details) in enumerate(student["Details"].items()):
            with cols[i % 3]:
                st.markdown(f"""
                <div style="margin-bottom: 10px;">
                    <strong>{q}:</strong> {details["Status"]}<br>
                    <small>Passed: {details["Passed"]} | Failed: {details["Failed"]}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Download CSV
    st.subheader("📤 Export Data")
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "💾 Download Full Report as CSV",
        csv_data,
        "submissions_summary.csv",
        "text/csv",
        help="Download complete submission data including all question details"
    )
else:
    st.info("👆 Data loading in progress... If this message persists, click the Manual Refresh button.")
    st.image("https://via.placeholder.com/800x400?text=Loading+Submission+Data", use_column_width=True)

# Add JavaScript for auto-refresh
st.components.v1.html(
    f"""
    <script>
    function checkRefresh() {{
        const currentTime = new Date().getTime() / 1000;
        const lastRefresh = {st.session_state.get('last_refresh', 0)};
        const refreshInterval = {refresh_interval};
        
        if (currentTime - lastRefresh > refreshInterval) {{
            window.location.reload();
        }}
    }}
    // Check every 5 seconds
    setInterval(checkRefresh, 5000);
    </script>
    """,
    height=0,
    width=0,
)
