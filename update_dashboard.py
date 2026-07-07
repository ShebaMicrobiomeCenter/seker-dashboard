import os
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo  # ספרייה מובנית לניהול אזורי זמן

# הגדרות ה-API של GitLab
PROJECT_ID = "84191474"
PARTICIPANTS_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/participants.csv/raw?ref=main"
SAMPLES_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/samples.csv/raw?ref=main"

try:
    print("Fetching data from GitLab...")
    participants_df = pd.read_csv(PARTICIPANTS_URL)
    samples_df = pd.read_csv(SAMPLES_URL)

    # חישוב נתוני רישום ואיסוף
    total_participants = participants_df['ParticipantID'].dropna().nunique()
    total_samples = samples_df['SampleID'].dropna().count()
    unique_sample_donors = samples_df['ParticipantID'].dropna().nunique()
    
    # שליפת המטריקות האנונימיות מתוך משתני הסביבה (שהגיעו מהריפו הפרטי)
    megamap_total = os.getenv('MEGAMAP_TOTAL', 'N/A')
    megamap_success = os.getenv('MEGAMAP_SUCCESS', 'N/A')
    megamap_failed = os.getenv('MEGAMAP_FAILED', 'N/A')
    
    # הגדרת הזמן הנוכחי לפי שעון ישראל (Asia/Jerusalem) ומעבר אוטומטי בין שעון קיץ לחורף
    current_time = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%d/%m/%Y %H:%M:%S")

    # יצירת דף דשבורד מעוצב עם חלוקה לשני מקורות מידע
    html_content = f"""
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>דשבורד מחקר סקר</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 40px; text-align: center; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ color: #2c3e50; margin-bottom: 5px; }}
            h2 {{ color: #7f8c8d; font-size: 1.3rem; margin-bottom: 30px; font-weight: 400; }}
            .section-title {{ text-align: right; color: #2c3e50; font-size: 1.2rem; margin: 30px 0 10px 0; padding-bottom: 5px; border-bottom: 2px solid #eee; }}
            .grid {{ display: flex; justify-content: space-around; gap: 20px; margin-bottom: 20px; }}
            .card {{ flex: 1; background: #f8f9fa; padding: 25px; border-radius: 10px; border-top: 5px solid #3498db; }}
            .card.donors {{ border-top-color: #f1c40f; }}
            .card.samples {{ border-top-color: #2ecc71; }}
            .card.pipeline {{ border-top-color: #9b59b6; }}
            .card.success {{ border-top-color: #2abc68; }}
            .card.failed {{ border-top-color: #e74c3c; }}
            .number {{ font-size: 2.5rem; font-weight: bold; color: #2c3e50; margin: 10px 0; }}
            .label {{ color: #7f8c8d; font-size: 1rem; font-weight: 500; }}
            .footer {{ color: #bdc3c7; font-size: 0.9rem; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>מרכז בקרה - מחקר סקר</h1>
            <h2>Sheba Microbiome Center</h2>
            
            <div class="section-title">סטטוס איסוף וגיוס (מתוך GitLab)</div>
            <div class="grid">
                <div class="card">
                    <div class="label">משתתפים רשומים בסקר</div>
                    <div class="number">{total_participants}</div>
                </div>
                <div class="card donors">
                    <div class="label">משתתפים שתרמו דגימה</div>
                    <div class="number">{unique_sample_donors}</div>
                </div>
                <div class="card samples">
                    <div class="label">סך כל הדגימות במקפיא</div>
                    <div class="number">{total_samples}</div>
                </div>
            </div>

            <div class="section-title">סטטוס עיבוד וריצה (MegaMap Pipeline)</div>
            <div class="grid">
                <div class="card pipeline">
                    <div class="label">דגימות שזרמו ל-Pipeline</div>
                    <div class="number">{megamap_total}</div>
                </div>
                <div class="card success">
                    <div class="label">הסתיימו בהצלחה (>4K reads)</div>
                    <div class="number">{megamap_success}</div>
                </div>
                <div class="card failed">
                    <div class="label">נכשלו / לא עברו סף</div>
                    <div class="number">{megamap_failed}</div>
                </div>
            </div>
            
            <div class="footer">עודכן לאחרונה באופן אוטומטי ב- {current_time} (שעון ישראל)</div>
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Dashboard HTML updated successfully with full metrics and Israel time!")

except Exception as e:
    print(f"Error generating dashboard: {e}")
    exit(1)
    
