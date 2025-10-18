import os
import csv
import requests
from datetime import datetime
import pytz  
import json


# GitHub Secrets থেকে টেলিগ্রাম বট টোকেন নিন
BOT_TOKEN = "8261672317:AAHC1Ei2EJYXUUxwVYY-RdLqya7G59AK9kk"
if not BOT_TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN environment variable not found. For local testing, ensure it's set.")


# Telegram Bot API URL
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

# যে CSV ফাইলে ডেটা সেভ করা হবে
CSV_FILE_PATH = "chats_data.csv"

def get_existing_chat_ids( ):
    """বিদ্যমান CSV ফাইল থেকে চ্যাট আইডি লোড করে।"""
    try:
        with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return {int(row['chat_id']) for row in reader}
    except FileNotFoundError:
        return set()

def fetch_updates():
    """Telegram API থেকে নতুন আপডেট (মেসেজ ইত্যাদি) সংগ্রহ করে।"""
    try:
        response = requests.get(API_URL, params={'offset': -1}, timeout=15)
        response.raise_for_status()
        return response.json().get("result", [])
    except requests.RequestException as e:
        print(f"Error fetching updates from Telegram: {e}")
        return []

def process_updates(updates, existing_ids):
    """আপডেটগুলো থেকে নতুন চ্যাট তথ্য বের করে আনে।"""
    new_chats = {}
    
    # BDT টাইমজোন সেট করা
    bdt_timezone = pytz.timezone("Asia/Dhaka")
    
    for update in updates:
        chat_info = None
        if "message" in update:
            chat_info = update["message"]["chat"]
        elif "my_chat_member" in update:
            chat_info = update["my_chat_member"]["chat"]
        elif "callback_query" in update:
            chat_info = update["callback_query"]["message"]["chat"]

        if chat_info:
            chat_id = chat_info["id"]
            if chat_id not in existing_ids and chat_id not in new_chats:
                chat_type = chat_info.get("type", "N/A")
                
                if chat_type == "private":
                    name = chat_info.get("first_name", "")
                    if "last_name" in chat_info:
                        name += f" {chat_info.get('last_name', '')}"
                else:
                    name = chat_info.get("title", "N/A")

                utc_now = datetime.now(pytz.utc)
                bdt_now = utc_now.astimezone(bdt_timezone)

                new_chats[chat_id] = {
                    "chat_id": chat_id,
                    "name": name.strip(),
                    "username": chat_info.get("username", "N/A"),
                    "type": chat_type,
                    "first_seen_bdt": bdt_now.strftime('%Y-%m-%d %H:%M:%S %Z') # BDT সময় ও টাইমজোন
                }
    return list(new_chats.values())

def append_to_csv(new_chats_data):
    """নতুন চ্যাটের তথ্য CSV ফাইলে যোগ করে।"""
    file_exists = os.path.isfile(CSV_FILE_PATH)
    
    last_serial = 0
    if file_exists:
        with open(CSV_FILE_PATH, 'r', newline='', encoding='utf-8') as f:
            last_serial = sum(1 for row in f) - 1

    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ['serial_no', 'chat_id', 'name', 'username', 'type', 'first_seen_bdt']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists or last_serial < 0:
            writer.writeheader()
            print("Created new CSV file with headers.")
            last_serial = 0

        for i, chat_data in enumerate(new_chats_data, start=1):
            row_to_write = {'serial_no': last_serial + i, **chat_data}
            writer.writerow(row_to_write)
    
    print(f"Appended {len(new_chats_data)} new chat(s) to {CSV_FILE_PATH}.")

def save_chat_ids_to_json(chat_ids, json_path="chat_ids.json"):
    """সব chat_id JSON ফাইলে সেভ করে রাখে।"""
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(list(chat_ids), f, ensure_ascii=False, indent=4)
        print(f"✅ Saved {len(chat_ids)} chat IDs to {json_path}")
    except Exception as e:
        print(f"Error saving chat IDs to JSON: {e}")

def main():
    """মূল ফাংশন যা চ্যাট আইডি সংগ্রহ ও সেভ করার প্রক্রিয়া পরিচালনা করে।"""
    if not BOT_TOKEN:
        return
        
    existing_ids = get_existing_chat_ids()
    print(f"Found {len(existing_ids)} existing chat IDs.")

    updates = fetch_updates()
    if not updates:
        print("No updates found from Telegram.")
        return

    new_chats_data = process_updates(updates, existing_ids)

    if new_chats_data:
        append_to_csv(new_chats_data)
        all_chat_ids = existing_ids.union({c["chat_id"] for c in new_chats_data})
        save_chat_ids_to_json(all_chat_ids)
    else:
        print("No new unique chats to add.")

if __name__ == "__main__":
    main()
