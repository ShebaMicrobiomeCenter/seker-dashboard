import os
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT_ID = "84191474"
PARTICIPANTS_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/participants.csv/raw?ref=main"
SAMPLES_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/samples.csv/raw?ref=main"
STATS_FILE = "pipeline_stats.json"

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

    total_participants = participants_df['ParticipantID'].dropna().nunique()
    unique_sample_donors = samples_df['SampleID'].dropna().nunique()
    total_samples = samples_df['SampleID'].dropna().count()
    
    # ב. ניהול הזיכרון של נתוני ה-MegaMap
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            saved_stats = json.load(f)
    else:
        saved_stats = {"total": "0", "success": "0", "failed": "0"}

    megamap_total = os.getenv('MEGAMAP_TOTAL')
    megamap_success = os.getenv('MEGAMAP_SUCCESS')
    megamap_failed = os.getenv('MEGAMAP_FAILED')

    if megamap_total and megamap_total.strip() != "":
        saved_stats["total"] = megamap_total
        saved_stats["success"] = megamap_success
        saved_stats["failed"] = megamap_failed
        with open(STATS_FILE, "w") as f:
            json.dump(saved_stats, f)

    # חישוב אחוזים
    pct_donors = calculate_percentage(unique_sample_donors, total_participants)
    pct_pipeline = calculate_percentage(saved_stats["total"], unique_sample_donors)
    pct_success = calculate_percentage(saved_stats["success"], saved_stats["total"])

    current_time = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M:%S")

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

            /* Funnel Visual Redesign */
            .funnel {{
                display: flex;
                flex-direction: column;
                align-items: center;
                margin: 40px 0;
            }}
            .stage-wrapper {{
                position: relative;
                width: 100%;
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-bottom: 15px;
            }}
            .stage {{
                width: 100%;
                height: 120px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: white;
                background: linear-gradient(to right, var(--gradient-start), var(--gradient-end));
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}

            /* Funnel shapes using clip-path */
            .stage-1 {{ clip-path: polygon(0% 0%, 100% 0%, 92% 100%, 8% 100%); }}
            .stage-2 {{ clip-path: polygon(8% 0%, 92% 0%, 84% 100%, 16% 100%); }}
            .stage-3 {{ clip-path: polygon(16% 0%, 84% 0%, 76% 100%, 24% 100%); }}
            .stage-4 {{ clip-path: polygon(24% 0%, 76% 0%, 68% 100%, 32% 100%); }}

            .stage-label {{ font-size: 1.1rem; opacity: 0.9; margin-bottom: 4px; font-weight: 400; text-align: center; padding: 0 15%; }}
            .stage-value {{ font-size: 2.2rem; font-weight: 800; }}

            .en-text {{ direction: ltr; display: inline-block; }}

            .pct-badge {{
                position: absolute;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                background: var(--text-dark);
                color: white;
                padding: 4px 14px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                z-index: 20;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: 2px solid white;
            }}

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
                grid-template-columns: 1fr 1fr;
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
            .stat-card .val {{ font-size: 1.8rem; font-weight: 800; color: var(--sheba-blue); display: block; }}
            .stat-card .lab {{ font-size: 1rem; color: var(--text-gray); font-weight: 500; }}

            .footer {{
                margin-top: 60px;
                text-align: center;
                color: #a0aec0;
                font-size: 0.9rem;
            }}

            /* Mobile */
            @media (max-width: 600px) {{
                .container {{ padding: 25px; }}
                h1 {{ font-size: 1.8rem; }}
                .stage {{ height: 110px; }}
                .stage-value {{ font-size: 1.8rem; }}
                .stage-label {{ font-size: 0.85rem; padding: 0 5%; }}
                .grid {{ grid-template-columns: 1fr; }}

                /* Adjust shapes for mobile to avoid text cutting */
                .stage-1 {{ clip-path: polygon(0% 0%, 100% 0%, 96% 100%, 4% 100%); }}
                .stage-2 {{ clip-path: polygon(4% 0%, 96% 0%, 92% 100%, 8% 100%); }}
                .stage-3 {{ clip-path: polygon(8% 0%, 92% 0%, 88% 100%, 12% 100%); }}
                .stage-4 {{ clip-path: polygon(12% 0%, 88% 0%, 84% 100%, 16% 100%); }}
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
                <div class="stage-wrapper">
                    <div class="stage stage-1">
                        <div class="stage-label">משתתפים רשומים בסקר</div>
                        <div class="stage-value">{total_participants}</div>
                    </div>
                    <div class="pct-badge">בסיס (100%)</div>
                </div>

                <div class="stage-wrapper">
                    <div class="stage stage-2">
                        <div class="stage-label">משתתפים שתרמו דגימה</div>
                        <div class="stage-value">{unique_sample_donors}</div>
                    </div>
                    <div class="pct-badge">{pct_donors}% משלב קודם</div>
                </div>

                <div class="stage-wrapper">
                    <div class="stage stage-3">
                        <div class="stage-label">דגימות שזרמו ל-Pipeline</div>
                        <div class="stage-value">{saved_stats["total"]}</div>
                    </div>
                    <div class="pct-badge">{pct_pipeline}% משלב קודם</div>
                </div>

                <div class="stage-wrapper">
                    <div class="stage stage-4">
                        <div class="stage-label">הסתיימו בהצלחה <span class="en-text">(>4K reads)</span></div>
                        <div class="stage-value">{saved_stats["success"]}</div>
                    </div>
                    <div class="pct-badge">{pct_success}% משלב קודם</div>
                </div>
            </div>

            <div class="supplementary">
                <div class="sup-header">נתונים משלימים</div>
                <div class="grid">
                    <div class="stat-card">
                        <span class="val">{total_samples}</span>
                        <span class="lab">סך כל הדגימות במקפיא</span>
                    </div>
                    <div class="stat-card">
                        <span class="val">{saved_stats["failed"]}</span>
                        <span class="lab">נכשלו / לא עברו סף</span>
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
        
    print("Dashboard HTML updated successfully with a refined funnel design!")

except Exception as e:
    print(f"Error generating dashboard: {e}")
    exit(1)
