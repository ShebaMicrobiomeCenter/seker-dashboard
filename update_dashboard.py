import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# הגדרות ה-API של GitLab
PROJECT_ID = "84191474"
PARTICIPANTS_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/participants.csv/raw?ref=main"
SAMPLES_URL = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/repository/files/samples.csv/raw?ref=main"

try:
    # 1. משיכת הנתונים מ-GitLab
    print("Fetching data from GitLab...")
    participants_df = pd.read_csv(PARTICIPANTS_URL)
    samples_df = pd.read_csv(SAMPLES_URL)

    # 2. חישוב המטריקות המעודכנות
    # סך הכל משתתפים שחתמו על הסכמה/נרשמו במערכת
    total_participants = participants_df['ParticipantID'].dropna().nunique()
    
    # סך הכל דגימות פיזיות שנאספו בבנק הנתונים (שורות)
    total_samples = samples_df['SampleID'].dropna().count()
    
    # מספר המשתתפים הייחודיים שתרמו לפחות דגימה אחת
    # (בהנחה שקיימת קורלציה בקובץ הדגימות דרך עמודה בשם ParticipantID או קשר דומה)
    # הערה: אם שם העמודה המקשרת בקובץ הדגימות שונה מ-'ParticipantID', החלף אותו כאן
    if 'ParticipantID' in samples_df.columns:
        unique_sample_donors = samples_df['ParticipantID'].dropna().nunique()
    else:
        # Fallback if ParticipantID is missing in samples.csv
        unique_sample_donors = samples_df['SampleID'].dropna().nunique()
    
    current_time = datetime.now(ZoneInfo('Asia/Jerusalem')).strftime("%d/%m/%Y %H:%M:%S")

    # 3. יצירת דף דשבורד מעוצב ב-HTML (עם 3 כרטיסים)
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
            h1 {{ color: #2c3e50; margin-bottom: 30px; }}
            .grid {{ display: flex; justify-content: space-around; gap: 20px; margin-bottom: 30px; }}
            .card {{ flex: 1; background: #f8f9fa; padding: 25px; border-radius: 10px; border-top: 5px solid #3498db; }}
            .card.donors {{ border-top-color: #f1c40f; }}
            .card.samples {{ border-top-color: #2ecc71; }}
            .number {{ font-size: 3rem; font-weight: bold; color: #2c3e50; margin: 10px 0; }}
            .label {{ color: #7f8c8d; font-size: 1.1rem; font-weight: 500; }}
            .footer {{ color: #bdc3c7; font-size: 0.9rem; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>סטטוס איסוף נתונים - מחקר סקר</h1>
            <div class="grid">
                <div class="card">
                    <div class="label">משתתפים הרשומים בסקר</div>
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
            <div class="footer">עודכן לאחרונה באופן אוטומטי ב- {current_time} (שעון ישראל)</div>
        </div>
    </body>
    </html>
    """

    # 4. שמירת הקובץ
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Dashboard HTML updated successfully with unique metrics!")

except Exception as e:
    print(f"Error generating dashboard: {e}")
    exit(1)
