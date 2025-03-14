import requests
import time
import pandas as pd
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_file

API_TOKEN = "sk-a5486b46cd3645f99a9650934bc9e156"
API_URL = "https://api.deepseek.com/v1/chat/completions"

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Server is running!"})

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Test endpoint is working!"})

def generate_checklist_part(item_name, num_tasks=7, part_number=1, previous_tasks=None):
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    previous = "\nقبلاً این وظایف تولید شده‌اند، از تکرارشون خودداری کن:\n" + "\n".join(previous_tasks) if previous_tasks else ""
    prompt = f"""برای یک '{item_name}'، که یک ابزار یا ماشین صنعتی تخصصی در کارخانجات یا محیط‌های حرفه‌ای است، حداقل {num_tasks} وظیفه نگهداری منحصربه‌فرد با توضیحات کوتاه و کاربردی تهیه کن. این وظایف باید مشابه اما متفاوت از این مثال‌ها باشند و برای استفاده عملی در نگهداری حرفه‌ای مناسب باشند:
1. بررسی روغن - مطمئن شو پر باشه و نشتی نداشته باشه.
2. بازرسی فیلترها - اگه کثیفن تمیز یا تعویضشون کن.
3. تست باتری - سطح شارژ رو چک کن و اتصالات رو محکم کن.
4. تمیز کردن دریچه‌ها - گرد و غبار رو پاک کن تا هوا جریان داشته باشه.
5. تعویض تسمه‌ها - تسمه‌های فرسوده رو با نو عوض کن.

{previous}

حالا حداقل {num_tasks} وظیفه جدید برای '{item_name}' به این فرمت بده (بخش {part_number}):
1. وظیفه - توضیح کوتاه و تخصصی
2. وظیفه - توضیح کوتاه و تخصصی
و همین‌طور تا حداقل {num_tasks}. وظایف باید متنوع، دقیق و مرتبط با نگهداری حرفه‌ای باشن. اگه می‌تونی بیشتر از {num_tasks} بده، بده."""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "تو یه دستیار حرفه‌ای و متخصص در زمینه نگهداری صنعتی هستی."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.8,
        "top_p": 0.95
    }

    print(f"در حال ارسال درخواست برای '{item_name}' (بخش {part_number} - حداقل {num_tasks} وظیفه)...")
    start_time = time.time()
    max_tries = 3
    for attempt in range(max_tries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=150)
            elapsed_time = time.time() - start_time
            if response.status_code == 200:
                result = response.json()
                print(f"کد وضعیت: {response.status_code} (زمان: {elapsed_time:.2f} ثانیه)")
                if result and "choices" in result and len(result["choices"]) > 0:
                    text = result["choices"][0]["message"]["content"]
                    lines = [line.strip() for line in text.split('\n') if line.strip() and line.strip()[0].isdigit() and len(line.split('-')) > 1]
                    unique_lines = list(dict.fromkeys(lines))
                    print(f"تعداد وظایف تولیدشده در بخش {part_number}: {len(unique_lines)}")
                    return unique_lines
                print("پاسخ API خالی یا ناقصه")
                return "پاسخ API خالی یا ناقصه"
            else:
                print(f"تلاش {attempt + 1} ناموفق: خطا {response.status_code}, متن: {response.text}")
        except Exception as e:
            print(f"تلاش {attempt + 1} ناموفق: {e}")
            if attempt < max_tries - 1:
                time.sleep(5)
                continue
            return None
    return None

def generate_full_checklist(item_name, min_tasks=30):
    all_tasks = set()
    part_number = 1
    max_parts = 7
    while len(all_tasks) < min_tasks and part_number <= max_parts:
        try:
            print(f"Starting part {part_number} for {item_name}")
            tasks = generate_checklist_part(item_name, num_tasks=7, part_number=part_number, previous_tasks=list(all_tasks))
            if isinstance(tasks, list) and tasks:
                new_tasks = [task for task in tasks if task not in all_tasks]
                all_tasks.update(new_tasks)
                print(f"Added {len(new_tasks)} new tasks in part {part_number}. Total tasks: {len(all_tasks)}")
                part_number += 1
                time.sleep(10)
            else:
                print(f"بخش {part_number} ناموفق بود، ادامه می‌دهیم... (وظایف دریافت‌شده: {tasks})")
                part_number += 1
                time.sleep(10)
        except Exception as e:
            print(f"خطا در تولید بخش {part_number}: {str(e)}")
            part_number += 1
            time.sleep(10)
    if len(all_tasks) < min_tasks:
        print(f"فقط {len(all_tasks)} وظیفه تولید شد، کمتر از حداقل {min_tasks} وظیفه")
    else:
        print(f"Successfully generated {len(all_tasks)} tasks for {item_name}")
    return list(all_tasks)[:max(min_tasks, len(all_tasks))]

def save_to_excel(item_name, checklist):
    tasks = []
    descriptions = []
    periods = []
    for i, line in enumerate(checklist):
        parts = line.split(" - ", 1)
        if len(parts) > 1:
            task = parts[0].split(". ", 1)[1] if ". " in parts[0] else parts[0]
            tasks.append(task)
            descriptions.append(parts[1].strip())
        else:
            tasks.append(line.split(". ", 1)[1] if ". " in line else line)
            descriptions.append("")
        if i < 10:
            periods.append("هفتگی (7 روزه)")
        elif i < 20:
            periods.append("ماهانه (30 روزه)")
        else:
            periods.append("سالانه (365 روزه)")
    
    df = pd.DataFrame({"وظیفه": tasks, "توضیحات": descriptions, "دوره": periods})
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Checklist_{item_name}_{timestamp}.xlsx"
    filepath = os.path.join(os.getcwd(), filename)  # ذخیره توی پوشه فعلی پروژه
    df.to_excel(filepath, index=False, engine='openpyxl')
    print(f"Excel file saved at: {filepath}")
    return filepath

@app.route('/generate-checklist', methods=['POST'])
def generate_checklist():
    print("Received request for /generate-checklist")
    try:
        data = request.json
        print(f"Received data: {data}")
        item_name = data.get('item_name')
        if not item_name:
            print("Item name not provided")
            return jsonify({"error": "اسم شیء وارد نشده"}), 400
        
        print(f"Generating checklist for: {item_name}")
        checklist = generate_full_checklist(item_name, min_tasks=30)
        if not checklist or len(checklist) < 30:
            print(f"Failed to generate checklist. Generated tasks: {len(checklist) if checklist else 0}")
            return jsonify({"error": "خطا در تولید چک‌لیست"}), 500
        
        print("Saving checklist to Excel")
        excel_file = save_to_excel(item_name, checklist)
        weekly = checklist[:10]
        monthly = checklist[10:20]
        yearly = checklist[20:]
        response = {
            "item_name": item_name,
            "checklist": {
                "weekly": [task.split(" - ")[1] if " - " in task else task for task in weekly],
                "monthly": [task.split(" - ")[1] if " - " in task else task for task in monthly],
                "yearly": [task.split(" - ")[1] if " - " in task else task for task in yearly]
            },
            "excel_file": os.path.basename(excel_file)
        }
        print("Returning response")
        return jsonify(response)
    except Exception as e:
        print(f"Error in /generate-checklist: {str(e)}")
        return jsonify({"error": f"خطای سرور: {str(e)}"}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    filepath = os.path.join(os.getcwd(), filename)  # استفاده از مسیر فعلی
    if os.path.exists(filepath):
        print(f"Downloading file: {filepath}")
        return send_file(filepath, as_attachment=True)
    print(f"File not found: {filepath}")
    return jsonify({"error": "فایل پیدا نشد"}), 404