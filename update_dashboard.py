import os
import json
import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT_ID = "84191474"
PARTICIPANTS_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/participants.csv/raw?ref=main"
SAMPLES_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/samples.csv/raw?ref=main"
RECURRING_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/recurring.csv/raw?ref=main"
STATS_FILE = "pipeline_stats.json"
REPORTS_STATS_FILE = "reports-stats.json"

def get_last_commit_date(file_path):
    try:
        url = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/commits"
        params = {"path": file_path, "ref_name": "main", "per_page": 1}
        response = requests.get(url, params=params)
        response.raise_for_status()
        commits = response.json()
        if commits:
            commit_date_str = commits[0]["committed_date"]
            # Example: 2026-07-07T14:26:17.000+00:00
            dt = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
            return dt.astimezone(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")
    except Exception as e:
        print(f"Error fetching commit date for {file_path}: {e}")
    return "N/A"

def calculate_percentage(current, previous):
    try:
        curr = float(current)
        prev = float(previous)
        if prev == 0:
            return 0
        return round((curr / prev) * 100, 1)
    except:
        return 0

try:
    # א. משיכת נתונים עדכניים מ-GitLab
    print("Fetching recruitment data from GitLab...")
    participants_df = pd.read_csv(PARTICIPANTS_URL)
    samples_df = pd.read_csv(SAMPLES_URL)
    recurring_df = pd.read_csv(RECURRING_URL)

    participants_update_date = get_last_commit_date("participants.csv")
    samples_update_date = get_last_commit_date("samples.csv")
    recurring_update_date = get_last_commit_date("recurring.csv")

    total_participants = participants_df['ParticipantID'].dropna().nunique()

    # Calculate withdrawn participants (Status == 'פרש')
    withdrawn_participants = participants_df[participants_df['Status'] == 'פרש']['ParticipantID'].dropna().nunique()
    if withdrawn_participants == 0:
        withdrawn_participants = participants_df[participants_df['Status'] == 'פרש']['ParticipantID'].dropna().nunique()

    active_participants = total_participants - withdrawn_participants

    unique_sample_donors = samples_df['SampleID'].dropna().nunique()
    total_samples = samples_df['SampleID'].dropna().count()
    
    # חישוב התפלגות דגימות ל-UniqueID מתוך recurring.csv
    samples_df['DerivedParticipantID'] = samples_df['SampleID'].str.replace('SK', '', case=False).astype(int)

    # חיבור שמאל (Left Join) בין recurring_df ל-samples_df
    merged_recurring = pd.merge(recurring_df, samples_df, left_on='ParticipantID', right_on='DerivedParticipantID', how='left')

    # ספירת דגימות תקינות לכל UniqueID
    samples_per_unique = merged_recurring.groupby('UniqueID')['SampleID'].count()

    # יצירת מילון מלא עם כל הערכים האפשריים (1, 2, 3, 4 דגימות - ללא 0) כדי שלא יחסרו עמודות
    recurring_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
    actual_distribution = samples_per_unique.value_counts()
    for count_val, count_unique in actual_distribution.items():
        if count_val > 0:
            if count_val in recurring_distribution:
                recurring_distribution[count_val] = count_unique
            else:
                recurring_distribution[count_val] = count_unique

    # מציאת הערך המקסימלי לצורך קביעת גובה יחסי של העמודות בגרף (עבור CSS height ב-%)
    max_count_val = max(recurring_distribution.values()) if recurring_distribution else 1

    # ב. ניהול הזיכרון של נתוני ה-MegaMap
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            saved_stats = json.load(f)
    else:
        saved_stats = {"total": "0", "success": "0", "failed": "0", "last_updated": "N/A"}

    megamap_total = os.getenv('MEGAMAP_TOTAL')
    megamap_success = os.getenv('MEGAMAP_SUCCESS')
    megamap_failed = os.getenv('MEGAMAP_FAILED')

    if megamap_total and megamap_total.strip() != "":
        saved_stats["total"] = megamap_total
        saved_stats["success"] = megamap_success
        saved_stats["failed"] = megamap_failed
        saved_stats["last_updated"] = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")
        with open(STATS_FILE, "w") as f:
            json.dump(saved_stats, f)

    sequencing_update_date = saved_stats.get("last_updated", "N/A")

    # ניהול נתוני דוחות שנשלחו בהצלחה (reports-stats.json)
    if os.path.exists(REPORTS_STATS_FILE):
        with open(REPORTS_STATS_FILE, "r") as f:
            reports_stats = json.load(f)
    else:
        reports_stats = {"report_count": "1150", "last_updated": "N/A"}

    report_count_env = os.getenv('REPORT_COUNT')
    if report_count_env and report_count_env.strip() != "":
        reports_stats["report_count"] = report_count_env
        reports_stats["last_updated"] = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")
        with open(REPORTS_STATS_FILE, "w") as f:
            json.dump(reports_stats, f)

    if "last_updated" not in reports_stats or reports_stats["last_updated"] == "N/A":
        if os.path.exists(REPORTS_STATS_FILE):
            mtime = os.path.getmtime(REPORTS_STATS_FILE)
            reports_stats["last_updated"] = datetime.fromtimestamp(mtime, ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")
        else:
            reports_stats["last_updated"] = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M")

    reports_update_date = reports_stats.get("last_updated", "N/A")

    # חישוב אחוזים ופערים
    pct_active = calculate_percentage(active_participants, total_participants)
    pct_donors = calculate_percentage(unique_sample_donors, active_participants)
    pct_pipeline = calculate_percentage(saved_stats["total"], unique_sample_donors)
    pct_success = calculate_percentage(saved_stats["success"], saved_stats["total"])
    pct_reports = calculate_percentage(reports_stats["report_count"], saved_stats["success"])

    # חישוב פערים לטולטיפים
    gap_3_2 = max(0, active_participants - unique_sample_donors)
    gap_4_3 = max(0, unique_sample_donors - int(saved_stats["total"]))
    gap_5_4 = max(0, int(saved_stats["total"]) - int(saved_stats["success"]))
    gap_6_5 = max(0, int(saved_stats["success"]) - int(reports_stats["report_count"]))

    tooltip_2 = f"{withdrawn_participants} משתתפים שפרשו"
    tooltip_3 = f"{gap_3_2} משתתפים שדגימה שלהם לא נקלטה במערכת"
    tooltip_4 = f"חסרות {gap_4_3} דגימות: רובן בתהליך עבודה או מחכות ל-PCR במנה הבאה"
    tooltip_5 = f"חסרות {gap_5_4} דגימות: רובן לא הגיעו לסף הקריאות הנדרש"
    tooltip_6 = f"{gap_6_5} דוחות חסרים בתהליכי הפקה"

    width_1 = 100
    width_2 = min(100, calculate_percentage(active_participants, total_participants))
    width_3 = min(100, calculate_percentage(unique_sample_donors, total_participants))
    width_4 = min(100, calculate_percentage(saved_stats["total"], total_participants))
    width_5 = min(100, calculate_percentage(saved_stats["success"], total_participants))
    width_6 = min(100, calculate_percentage(reports_stats["report_count"], total_participants))

    current_time = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M:%S")

    # בניית ה-HTML של עמודות ההיסטוגרמה בצורה דינמית
    histogram_bars_html = ""
    for num_samples in sorted(recurring_distribution.keys()):
        count_unique_ids = recurring_distribution[num_samples]
        percentage_of_total = calculate_percentage(count_unique_ids, sum(recurring_distribution.values()))
        bar_height_percent = max(5, round((count_unique_ids / max_count_val) * 100))

        if num_samples == 1:
            label_text = "דגימה אחת"
        elif num_samples == 2:
            label_text = "2 דגימות"
        else:
            label_text = f"{num_samples} דגימות"

        histogram_bars_html += f"""
        <div class="hist-col">
            <div class="hist-bar-wrapper">
                <div class="hist-bar-value">{count_unique_ids}</div>
                <div class="hist-bar" style="height: {bar_height_percent}%;" title="{count_unique_ids} משתתפים ייחודיים ({percentage_of_total}%)"></div>
            </div>
            <div class="hist-label">{label_text}</div>
            <div class="hist-pct">{percentage_of_total}%</div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>דשבורד מחקר סקר</title>
        <style>
            :root {{
                --sheba-blue: #005596;
                --sheba-light: #e6f0f7;
                --gradient-start: #004a80;
                --gradient-end: #0077c8;
                --text-dark: #1a2a3a;
                --text-gray: #5a6a7a;
            }}
            body {{
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                background-color: #f0f4f8;
                margin: 0;
                padding: 40px 20px;
                display: flex;
                justify-content: center;
                color: var(--text-dark);
            }}
            .container {{
                width: 100%;
                max-width: 900px;
                background: white;
                padding: 40px;
                border-radius: 24px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.05);
            }}
            header {{ margin-bottom: 50px; text-align: center; }}
            h1 {{ font-size: 2.2rem; margin: 0 0 10px 0; font-weight: 800; letter-spacing: -0.5px; }}
            h2 {{ font-size: 1.2rem; color: var(--text-gray); margin: 0; font-weight: 400; }}

            /* Funnel Visual Redesign to Horizontal Bars */
            .funnel {{
                display: flex;
                flex-direction: column;
                gap: 20px;
                margin: 40px 0;
            }}
            .funnel-row {{
                display: flex;
                align-items: center;
                width: 100%;
                gap: 15px;
                position: relative;
                padding: 4px 0;
                cursor: help;
            }}
            .row-label {{
                width: 180px;
                min-width: 180px;
                text-align: right;
                font-size: 1rem;
                font-weight: 700;
                color: var(--text-dark);
            }}
            .bar-container {{
                flex-grow: 1;
                position: relative;
                height: 38px;
                background-color: #eef2f6;
                border-radius: 19px;
                overflow: visible;
                display: flex;
                align-items: center;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
            }}
            .bar-fill {{
                height: 100%;
                background: linear-gradient(to left, var(--gradient-start), var(--gradient-end));
                border-radius: 19px;
                display: flex;
                align-items: center;
                justify-content: flex-start; /* flex-start in RTL is right side */
                padding: 0 15px;
                box-sizing: border-box;
                transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 2px 4px rgba(0, 74, 128, 0.2);
                position: relative;
                min-width: 80px;
            }}
            .stage-value {{
                color: white;
                font-weight: 800;
                font-size: 1.15rem;
                text-shadow: 0 1px 2px rgba(0,0,0,0.2);
            }}
            .pct-badge {{
                position: absolute;
                left: -12px; /* Beyond the left end of the bar */
                top: 50%;
                transform: translateY(-50%);
                background: var(--text-dark);
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                box-shadow: 0 2px 5px rgba(0,0,0,0.15);
                border: 1.5px solid white;
                white-space: nowrap;
                z-index: 10;
            }}
            .row-update {{
                width: 125px;
                min-width: 125px;
                text-align: left;
                font-size: 0.75rem;
                color: var(--text-gray);
                opacity: 0.45;
                font-weight: 400;
                white-space: nowrap;
                transition: opacity 0.2s;
            }}
            .funnel-row:hover .row-update {{
                opacity: 0.85;
            }}
            .en-text {{ direction: ltr; display: inline-block; }}

            /* Stats Grid */
            .supplementary {{
                margin-top: 80px;
                border-top: 2px solid #f0f4f8;
                padding-top: 40px;
            }}
            .sup-header {{
                font-size: 1.3rem;
                font-weight: 700;
                margin-bottom: 25px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .sup-header::before {{
                content: "";
                display: block;
                width: 4px;
                height: 24px;
                background: var(--sheba-blue);
                border-radius: 2px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }}
            .stat-card {{
                background: var(--sheba-light);
                padding: 25px;
                border-radius: 16px;
                text-align: center;
                transition: transform 0.2s;
            }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .stat-card .val {{ font-size: 1.8rem; font-weight: 800; color: var(--sheba-blue); display: block; line-height: 1.2; }}
            .stat-card .lab {{ font-size: 1rem; color: var(--text-gray); font-weight: 500; display: block; }}
            .stat-card .update-date {{ color: var(--text-gray); opacity: 0.6; }}

            /* Histogram Section Styling */
            .histogram-section {{
                margin-top: 60px;
                border-top: 2px solid #f0f4f8;
                padding-top: 40px;
            }}
            .hist-chart-container {{
                background: #fdfdfd;
                border: 1px solid #eef2f6;
                border-radius: 20px;
                padding: 35px;
                margin-top: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.02);
            }}
            .hist-chart {{
                display: flex;
                justify-content: space-around;
                align-items: flex-end;
                height: 250px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e2e8f0;
                margin-bottom: 15px;
            }}
            .hist-col {{
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 16%;
            }}
            .hist-bar-wrapper {{
                height: 180px;
                width: 100%;
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
                align-items: center;
                position: relative;
            }}
            .hist-bar-value {{
                font-size: 1rem;
                font-weight: 700;
                color: var(--text-dark);
                margin-bottom: 8px;
            }}
            .hist-bar {{
                width: 100%;
                max-width: 50px;
                background: linear-gradient(to top, var(--gradient-start), var(--gradient-end));
                border-radius: 8px 8px 0 0;
                transition: all 0.3s ease;
                cursor: pointer;
            }}
            .hist-bar:hover {{
                background: linear-gradient(to top, var(--sheba-blue), #00a0e9);
                transform: scaleX(1.05);
                box-shadow: 0 4px 10px rgba(0, 119, 200, 0.3);
            }}
            .hist-label {{
                font-size: 0.95rem;
                font-weight: 600;
                color: var(--text-dark);
                margin-top: 8px;
                text-align: center;
            }}
            .hist-pct {{
                font-size: 0.8rem;
                color: var(--text-gray);
                margin-top: 2px;
            }}

            .footer {{
                margin-top: 60px;
                text-align: center;
                color: #a0aec0;
                font-size: 0.9rem;
            }}

            /* Mobile */
            @media (max-width: 600px) {{
                .container {{ padding: 25px 15px; }}
                h1 {{ font-size: 1.8rem; }}
                .grid {{ grid-template-columns: 1fr; }}

                /* Horizontal bar stack on mobile */
                .funnel-row {{
                    flex-direction: column;
                    align-items: stretch;
                    gap: 6px;
                    padding-bottom: 12px;
                    border-bottom: 1px solid #eef2f6;
                }}
                .row-label {{
                    width: 100%;
                    min-width: unset;
                    text-align: right;
                    font-size: 0.95rem;
                }}
                .bar-container {{
                    margin-left: 20px; /* leave room for badge */
                }}
                .row-update {{
                    width: 100%;
                    min-width: unset;
                    text-align: right;
                    margin-top: 2px;
                    opacity: 0.6;
                }}

                /* Mobile responsive histogram */
                .hist-chart-container {{ padding: 20px 10px; }}
                .hist-chart {{ height: 160px; }}
                .hist-bar-wrapper {{ height: 110px; }}
                .hist-col {{ width: 18%; }}
                .hist-bar {{ max-width: 35px; }}
                .hist-label {{ font-size: 0.8rem; }}
                .hist-pct {{ font-size: 0.7rem; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>מרכז בקרה - מחקר סקר</h1>
                <h2>Sheba Microbiome Center</h2>
            </header>
            
            <div class="funnel">
                <!-- Stage 1 -->
                <div class="funnel-row">
                    <div class="row-label">משתתפים רשומים בסקר</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_1}%;">
                            <span class="stage-value">{total_participants}</span>
                            <span class="pct-badge">בסיס (100%)</span>
                        </div>
                    </div>
                    <div class="row-update">עודכן: {participants_update_date}</div>
                </div>

                <!-- Stage 2 -->
                <div class="funnel-row" title="{tooltip_2}">
                    <div class="row-label">משתתפים שלא פרשו</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_2}%;">
                            <span class="stage-value">{active_participants}</span>
                            <span class="pct-badge">{pct_active}% משלב קודם</span>
                        </div>
                    </div>
                    <div class="row-update">עודכן: {participants_update_date}</div>
                </div>

                <!-- Stage 3 -->
                <div class="funnel-row" title="{tooltip_3}">
                    <div class="row-label">משתתפים שתרמו דגימה</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_3}%;">
                            <span class="stage-value">{unique_sample_donors}</span>
                            <span class="pct-badge">{pct_donors}% משלב קודם</span>
                        </div>
                    </div>
                    <div class="row-update">עודכן: {samples_update_date}</div>
                </div>

                <!-- Stage 4 -->
                <div class="funnel-row" title="{tooltip_4}">
                    <div class="row-label">דוגמאות שעברו ריצוף</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_4}%;">
                            <span class="stage-value">{saved_stats["total"]}</span>
                            <span class="pct-badge">{pct_pipeline}% משלב קודם</span>
                        </div>
                    </div>
                    <div class="row-update">עודכן: {sequencing_update_date}</div>
                </div>

                <!-- Stage 5 -->
                <div class="funnel-row" title="{tooltip_5}">
                    <div class="row-label">הסתיימו בהצלחה <span class="en-text">(>4K reads)</span></div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_5}%;">
                            <span class="stage-value">{saved_stats["success"]}</span>
                            <span class="pct-badge">{pct_success}% משלב קודם</span>
                        </div>
                    </div>
                    <div class="row-update">עודכן: {sequencing_update_date}</div>
                </div>

                <!-- Stage 6 -->
                <div class="funnel-row" title="{tooltip_6}">
                    <div class="row-label">דוחות שנשלחו בהצלחה</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_6}%;">
                            <span class="stage-value">{reports_stats["report_count"]}</span>
                            <span class="pct-badge">{pct_reports}% משלב קודם</span>
                        </div>
                    </div>
                    <div class="row-update">עודכן: {reports_update_date}</div>
                </div>
            </div>

            <div class="supplementary">
                <div class="sup-header">נתונים משלימים</div>
                <div class="grid">
                    <div class="stat-card">
                        <span class="val">{saved_stats["failed"]}</span>
                        <span class="lab">נכשלו / לא עברו סף</span>
                        <div class="update-date">עודכן: {sequencing_update_date}</div>
                    </div>
                    <div class="stat-card">
                        <span class="val">{withdrawn_participants}</span>
                        <span class="lab">משתתפים שפרשו מהמחקר</span>
                        <div class="update-date">עודכן: {participants_update_date}</div>
                    </div>
                </div>
            </div>

            <div class="histogram-section">
                <div class="sup-header">התפלגות מספר דגימות למשתתף ייחודי (UniqueID)</div>
                <div class="hist-chart-container">
                    <div class="hist-chart">
                        {histogram_bars_html}
                    </div>
                    <div class="update-date" style="text-align: center; margin-top: 10px; color: var(--text-gray); opacity: 0.6;">
                        עודכן: {recurring_update_date}
                    </div>
                </div>
            </div>
            
            <div class="footer">
                עודכן לאחרונה באופן אוטומטי ב- {current_time} (שעון ישראל)
            </div>
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Dashboard HTML updated successfully with a refined funnel design and UniqueID sample distribution histogram!")

except Exception as e:
    print(f"Error generating dashboard: {e}")
    exit(1)
