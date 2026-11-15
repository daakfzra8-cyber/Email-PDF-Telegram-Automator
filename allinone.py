import os
import sys
import json
import sqlite3
import imaplib
import email
from email.header import decode_header
from pathlib import Path
import threading
import requests
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Database configuration
DB_FILE = "accounts_db.sqlite"
DEFAULT_FOLDER = Path(r"E:\Email\mymails")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            profile_name TEXT PRIMARY KEY,
            email_id TEXT,
            app_password TEXT,
            bot_token TEXT,
            chat_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

class EmailTelegramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Email to Telegram Desktop Sync")
        self.root.geometry("650x680")
        self.root.minsize(600, 650)
        
        init_db()
        
        # UI Styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        self.create_widgets()
        self.load_profiles_into_dropdown()

    def create_widgets(self):
        # Main Container Frame
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Gmail PDF to Telegram Automator", font=("Helvetica", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Profile Selection Frame
        profile_frame = ttk.LabelFrame(main_frame, text=" Saved Profiles ", padding=10)
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(profile_frame, text="Select Profile:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.profile_combo = ttk.Combobox(profile_frame, state="readonly", width=35)
        self.profile_combo.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_select)
        
        delete_btn = ttk.Button(profile_frame, text="Delete Profile", command=self.delete_profile)
        delete_btn.grid(row=0, column=2, padx=5, pady=5)
        
        profile_frame.columnconfigure(1, weight=1)
        
        # Credentials Form Frame
        form_frame = ttk.LabelFrame(main_frame, text=" Account Credentials ", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))
        
        fields = [
            ("Profile / Nickname:", "name_entry"),
            ("Gmail ID:", "email_entry"),
            ("Gmail App Password:", "pass_entry"),
            ("Telegram Bot Token:", "token_entry"),
            ("Telegram Chat ID:", "chat_entry")
        ]
        
        self.entries = {}
        for idx, (label_text, attr_name) in enumerate(fields):
            ttk.Label(form_frame, text=label_text).grid(row=idx, column=0, sticky=tk.W, padx=5, pady=5)
            
            if "pass" in attr_name:
                ent = ttk.Entry(form_frame, show="*", width=45)
            else:
                ent = ttk.Entry(form_frame, width=45)
                
            ent.grid(row=idx, column=1, sticky=tk.EW, padx=5, pady=5)
            self.entries[attr_name] = ent
            
        form_frame.columnconfigure(1, weight=1)
        
        # Action Buttons Frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        save_btn = ttk.Button(btn_frame, text="Save / Update Profile", command=self.save_profile)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear Form", command=self.clear_form)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        run_btn = ttk.Button(btn_frame, text="Fetch Emails & Send to Telegram", command=self.run_sync_thread)
        run_btn.pack(side=tk.RIGHT, padx=5)
        
        # Log Output Frame
        log_frame = ttk.LabelFrame(main_frame, text=" Execution Logs ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=12, font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.config(state=tk.DISABLED)

    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def load_profiles_into_dropdown(self):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT profile_name FROM accounts")
            rows = cursor.fetchall()
            conn.close()
            
            names = [row[0] for row in rows]
            self.profile_combo['values'] = names
            if names:
                self.profile_combo.current(0)
                self.on_profile_select(None)
        except Exception as e:
            self.log(f"Error loading profiles: {e}")

    def on_profile_select(self, event):
        selected_name = self.profile_combo.get()
        if not selected_name:
            return
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT email_id, app_password, bot_token, chat_id FROM accounts WHERE profile_name = ?", (selected_name,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                self.clear_form(keep_name=True)
                self.entries["name_entry"].insert(0, selected_name)
                self.entries["email_entry"].insert(0, row[0] or "")
                self.entries["pass_entry"].insert(0, row[1] or "")
                self.entries["token_entry"].insert(0, row[2] or "")
                self.entries["chat_entry"].insert(0, row[3] or "")
        except Exception as e:
            self.log(f"Error fetching profile details: {e}")

    def clear_form(self, keep_name=False):
        if not keep_name:
            self.entries["name_entry"].delete(0, tk.END)
        self.entries["email_entry"].delete(0, tk.END)
        self.entries["pass_entry"].delete(0, tk.END)
        self.entries["token_entry"].delete(0, tk.END)
        self.entries["chat_entry"].delete(0, tk.END)

    def save_profile(self):
        name = self.entries["name_entry"].get().strip()
        email_id = self.entries["email_entry"].get().strip()
        password = self.entries["pass_entry"].get().strip()
        token = self.entries["token_entry"].get().strip()
        chat_id = self.entries["chat_entry"].get().strip()
        
        if not name:
            messagebox.showerror("Validation Error", "Please provide a Profile Name / Nickname.")
            return
            
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (profile_name, email_id, app_password, bot_token, chat_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email_id, password, token, chat_id))
            conn.commit()
            conn.close()
            
            self.log(f"Profile '{name}' saved successfully in database.")
            messagebox.showinfo("Success", f"Profile '{name}' saved successfully!")
            self.load_profiles_into_dropdown()
            self.profile_combo.set(name)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save profile: {e}")

    def delete_profile(self):
        name = self.profile_combo.get()
        if not name:
            messagebox.showwarning("Warning", "No profile selected to delete.")
            return
            
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile '{name}'?"):
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM accounts WHERE profile_name = ?", (name,))
                conn.commit()
                conn.close()
                
                self.log(f"Profile '{name}' deleted.")
                self.clear_form()
                self.load_profiles_into_dropdown()
                if not self.profile_combo['values']:
                    self.profile_combo.set('')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete profile: {e}")

    def run_sync_thread(self):
        threading.Thread(target=self.execute_sync_process, daemon=True).start()

    def execute_sync_process(self):
        name = self.entries["name_entry"].get().strip()
        email_id = self.entries["email_entry"].get().strip()
        password = self.entries["pass_entry"].get().strip()
        token = self.entries["token_entry"].get().strip()
        chat_id = self.entries["chat_entry"].get().strip()
        
        if not email_id or not password or not token or not chat_id:
            messagebox.showerror("Missing Information", "Please ensure Email ID, App Password, Bot Token, and Chat ID are all filled.")
            return
            
        self.log(f"=== Starting Sync for Profile: {name or email_id} ===")
        DEFAULT_FOLDER.mkdir(parents=True, exist_ok=True)
        
        try:
            self.log("Connecting to Gmail IMAP server (imap.gmail.com)...")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_id, password)
            mail.select("inbox")
            
            self.log("Searching for unread emails with PDF attachments...")
            status, messages = mail.search(None, '(UNSEEN)')
            if status != 'OK':
                self.log("Failed to search emails.")
                mail.logout()
                return
                
            email_ids = messages[0].split()
            self.log(f"Found {len(email_ids)} unread emails to check.")
            
            api_url = f"https://api.telegram.org/bot{token}"
            downloaded_count = 0
            
            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                if res != 'OK':
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = decode_header(msg["Subject"])[0][0]
                        if isinstance(subject, bytes):
                            try:
                                subject = subject.decode()
                            except:
                                subject = "No Subject"
                                
                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue
                                
                            filename = part.get_filename()
                            if filename:
                                decoded_filename = decode_header(filename)
                                fname_parts = []
                                for text, encoding in decoded_filename:
                                    if isinstance(text, bytes):
                                        fname_parts.append(text.decode(encoding or 'utf-8', errors='ignore'))
                                    else:
                                        fname_parts.append(text)
                                filename = "".join(fname_parts)
                                
                                if filename.lower().endswith('.pdf'):
                                    filepath = DEFAULT_FOLDER / filename
                                    with open(filepath, 'wb') as f:
                                        f.write(part.get_payload(decode=True))
                                    self.log(f"Saved PDF locally: {filename}")
                                    downloaded_count += 1
                                    
                                    self.log(f"Sending {filename} to Telegram...")
                                    with open(filepath, 'rb') as f_doc:
                                        try:
                                            r = requests.post(
                                                f"{api_url}/sendDocument",
                                                data={"chat_id": chat_id, "caption": f"From Email: {subject}"},
                                                files={"document": (filename, f_doc)},
                                                timeout=60
                                            )
                                            if r.ok:
                                                self.log(f"Successfully sent {filename} to Telegram!")
                                            else:
                                                self.log(f"Failed to send {filename}: {r.status_code} {r.text}")
                                        except Exception as net_err:
                                            self.log(f"Network error sending to Telegram: {net_err}")
                                            
            mail.logout()
            self.log(f"=== Sync Complete! Processed {downloaded_count} PDFs. ===")
            messagebox.showinfo("Sync Complete", f"Successfully synced and delivered {downloaded_count} PDF(s) to Telegram!")
            
        except Exception as e:
            self.log(f"Error during synchronization: {e}")
            messagebox.showerror("Error", f"Sync failed: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EmailTelegramApp(root)
    root.mainloop()