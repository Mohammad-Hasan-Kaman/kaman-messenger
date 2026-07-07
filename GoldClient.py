import customtkinter as ctk
from tkinter import messagebox
import socket
import json
import threading
import time
from datetime import datetime
import random
import struct
import os
from cryptography.fernet import Fernet

# --- تنظیمات ظاهری سطح بالا ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_panel": "#16213e",
    "accent": "#0f3460",
    "primary": "#e94560",
    "bubble_me": "#533483",
    "bubble_other": "#16213e",
    "text_main": "#ffffff",
    "text_sub": "#a0a0a0"
}

# --- بخش امنیتی و شبکه ---

if not os.path.exists("secret.key"):
    messagebox.showerror("Error", "Key file missing! Run MakeKey.py first.")
    exit()

with open("secret.key", "rb") as kf:
    CIPHER = Fernet(kf.read())

class Network:
    """کلاس مدیریت ارتباط شبکه امن و Real-time"""
    def __init__(self, app_callback):
        self.HOST = "127.0.0.1"
        self.PORT = 5000
        self.s = None
        self.connected = False
        self.username = "Guest"
        self.msg_callback = app_callback
        self.listener_thread = None
        self.should_listen = False
        self.connection_lock = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        self.connect()

    def connect(self):
        """اتصال به سرور با مدیریت خطا"""
        try:
            if self.s:
                try:
                    self.s.close()
                except:
                    pass
            
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(5)
            self.s.connect((self.HOST, self.PORT))
            self.s.settimeout(None)
            self.connected = True
            self.should_listen = True
            self.reconnect_attempts = 0
            
            # شروع Listener در thread جداگانه
            self.listener_thread = threading.Thread(target=self.listen_loop, daemon=True)
            self.listener_thread.start()
            print("Connected to server successfully")
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            self.reconnect_attempts += 1

    def encrypt_data(self, data_dict):
        json_data = json.dumps(data_dict)
        return CIPHER.encrypt(json_data.encode('utf-8'))

    def decrypt_data(self, encrypted_bytes):
        try:
            decrypted = CIPHER.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def send(self, data: dict):
        """ارسال داده با مدیریت خطا و Lock"""
        if not self.connected or not self.s:
            if data.get('type') != 'message':
                self.msg_callback({'type': 'error', 'message': 'Not connected to server.'})
            return False
        
        with self.connection_lock:
            try:
                encrypted_bytes = self.encrypt_data(data)
                msg_length = len(encrypted_bytes)
                header = struct.pack('>I', msg_length)
                self.s.sendall(header + encrypted_bytes)
                return True
            except Exception as e:
                print(f"Send error: {e}")
                self.connected = False
                self.msg_callback({'type': 'error', 'message': 'Connection lost during send.'})
                return False

    def listen_loop(self):
        """حلقه Listener برای دریافت Real-time پیام‌ها از سرور"""
        while self.should_listen and self.connected:
            try:
                header = self.s.recv(4)
                if not header or len(header) < 4:
                    print("Connection closed by server")
                    self.connected = False
                    break
                
                msg_length = struct.unpack('>I', header)[0]
                
                # محدودیت حجم برای امنیت
                if msg_length > 10 * 1024 * 1024:  # 10MB limit
                    print("Message too large, skipping")
                    continue
                
                encrypted_bytes = b''
                while len(encrypted_bytes) < msg_length:
                    chunk = self.s.recv(min(4096, msg_length - len(encrypted_bytes)))
                    if not chunk:
                        print("Connection interrupted")
                        self.connected = False
                        break
                    encrypted_bytes += chunk
                
                if len(encrypted_bytes) != msg_length:
                    continue
                
                data = self.decrypt_data(encrypted_bytes)
                if data and self.msg_callback:
                    self.msg_callback(data)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Listen error: {e}")
                self.connected = False
                break
        
        # اعلام قطع اتصال
        if self.msg_callback and not self.connected:
             self.msg_callback({'type': 'error', 'message': 'Connection to server lost.'})

    def disconnect(self):
        """بستن اتصال به صورت ایمن"""
        self.should_listen = False
        self.connected = False
        if self.s:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()
            except:
                pass
            finally:
                self.s = None

# --- کلاس‌های رابط کاربری ---

class LoginPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg_dark"])
        self.app = app
        self._destroyed = False
        
        self.card = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=20, border_color=COLORS["accent"], border_width=1)
        self.card.place(relx=0.5, rely=0.5, anchor="center") 
        
        ctk.CTkLabel(self.card, text="GOLD", font=("Montserrat", 40, "bold"), text_color=COLORS["primary"]).pack(pady=(40, 5), padx=60)
        ctk.CTkLabel(self.card, text="M E S S E N G E R", font=("Montserrat", 12, "bold"), text_color=COLORS["text_sub"]).pack(pady=(0, 30))

        self.entry_user = ctk.CTkEntry(self.card, placeholder_text="Username", height=50, corner_radius=25, 
                                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent"], text_color="white", width=250)
        self.entry_user.pack(fill="x", padx=40, pady=(10, 5))
        self.entry_user.bind("<Return>", lambda e: self.login_action())

        self.entry_pass = ctk.CTkEntry(self.card, placeholder_text="Password", show="●", height=50, corner_radius=25, 
                                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent"], text_color="white", width=250)
        self.entry_pass.pack(fill="x", padx=40, pady=(5, 10))
        self.entry_pass.bind("<Return>", lambda e: self.login_action())

        self.btn_login = ctk.CTkButton(self.card, text="LOGIN", height=50, corner_radius=25, 
                                       fg_color=COLORS["primary"], hover_color="#c0354e", 
                                       font=("Roboto", 14, "bold"), command=self.login_action, width=250)
        self.btn_login.pack(fill="x", padx=40, pady=(20, 10))

        self.btn_reg = ctk.CTkButton(self.card, text="Create new account", fg_color="transparent", 
                                     text_color=COLORS["text_sub"], hover_color=COLORS["bg_dark"], 
                                     command=self.go_register, width=250)
        self.btn_reg.pack(pady=(10, 30), padx=40)

        if not self.app.network.connected:
            self.status_label = ctk.CTkLabel(self, text="⚠️ Server Offline - Reconnecting...", text_color="#FF5555")
            self.status_label.pack(side="bottom", pady=20)
            self.after(3000, self.retry_connection)

    def destroy(self):
        """Override destroy to set flag"""
        self._destroyed = True
        super().destroy()

    def retry_connection(self):
        """تلاش مجدد برای اتصال به سرور"""
        if self._destroyed:
            return
            
        if not self.app.network.connected:
            self.app.network.connect()
            if self.app.network.connected and hasattr(self, 'status_label'):
                try:
                    self.status_label.configure(text="✓ Connected to server", text_color="#00FF00")
                    self.after(2000, lambda: self.status_label.pack_forget() if hasattr(self, 'status_label') and not self._destroyed else None)
                except:
                    pass
            else:
                if not self._destroyed:
                    self.after(5000, self.retry_connection)

    def login_action(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("Input Error", "Please enter both username and password")
            return
        if not self.app.network.connected:
            messagebox.showerror("Connection Error", "Not connected to server")
            return
        self.btn_login.configure(state="disabled", text="Logging in...")
        threading.Thread(target=self._do_login, args=(u, p), daemon=True).start()

    def _do_login(self, u, p):
        success = self.app.network.send({'type': 'login', 'username': u, 'password': p})
        if not success:
            self.after(100, lambda: self.btn_login.configure(state="normal", text="LOGIN") if not self._destroyed and self.btn_login.winfo_exists() else None)
        else:
            self.after(3000, lambda: self.btn_login.configure(state="normal", text="LOGIN") if not self._destroyed and self.btn_login.winfo_exists() else None)

    def go_register(self):
        self.app.show_page("register")

class RegisterPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg_dark"])
        self.app = app
        self._destroyed = False
        
        self.card = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["accent"])
        self.card.place(relx=0.5, rely=0.5, anchor="center") 
        
        ctk.CTkLabel(self.card, text="NEW ACCOUNT", font=("Montserrat", 30, "bold"), text_color="#00FF00").pack(pady=(40, 5), padx=60)
        
        self.entry_user = ctk.CTkEntry(self.card, placeholder_text="Username (No spaces)", height=50, corner_radius=25, 
                                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent"], text_color="white", width=250)
        self.entry_user.pack(fill="x", padx=40, pady=(10, 5))
        self.entry_user.bind("<Return>", lambda e: self.register_action())

        self.entry_pass = ctk.CTkEntry(self.card, placeholder_text="Password", show="●", height=50, corner_radius=25, 
                                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent"], text_color="white", width=250)
        self.entry_pass.pack(fill="x", padx=40, pady=(5, 10))
        self.entry_pass.bind("<Return>", lambda e: self.register_action())

        self.btn_reg = ctk.CTkButton(self.card, text="REGISTER NOW", height=50, corner_radius=25, 
                                       fg_color="#00FF00", hover_color="#00AA00", 
                                       font=("Roboto", 14, "bold"), command=self.register_action, width=250)
        self.btn_reg.pack(fill="x", padx=40, pady=(20, 10))

        self.btn_back = ctk.CTkButton(self.card, text="Back to Login", fg_color="transparent", 
                                     text_color=COLORS["text_sub"], hover_color=COLORS["bg_dark"], 
                                     command=self.go_login, width=250)
        self.btn_back.pack(pady=(10, 30), padx=40)

    def destroy(self):
        """Override destroy to set flag"""
        self._destroyed = True
        super().destroy()

    def go_login(self):
        self.app.show_page('login')

    def register_action(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        
        if not u or not p:
            messagebox.showwarning("Input Error", "Please enter both username and password")
            return
        if " " in u:
            messagebox.showwarning("Input Error", "Username cannot contain spaces")
            return
        if len(p) < 4:
            messagebox.showwarning("Input Error", "Password must be at least 4 characters")
            return
        if not self.app.network.connected:
            messagebox.showerror("Connection Error", "Not connected to server")
            return
            
        self.btn_reg.configure(state="disabled", text="Registering...")
        threading.Thread(target=self._do_register, args=(u, p), daemon=True).start()

    def _do_register(self, u, p):
        success = self.app.network.send({'type': 'register', 'username': u, 'password': p})
        if not success:
            self.after(100, lambda: self.btn_reg.configure(state="normal", text="REGISTER NOW") if not self._destroyed and self.btn_reg.winfo_exists() else None)
        else:
            self.after(3000, lambda: self.btn_reg.configure(state="normal", text="REGISTER NOW") if not self._destroyed and self.btn_reg.winfo_exists() else None)


class ChatPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg_dark"])
        self.app = app
        self.last_sender = None
        self._destroyed = False
        
        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=COLORS["bg_panel"])
        self.sidebar.pack(side="left", fill="y")
        
        self.profile_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.profile_frame.pack(pady=40, padx=20, fill="x")
        
        # آواتار با حرف اول نام
        initial = self.app.network.username[0].upper() if self.app.network.username else "G"
        self.lbl_user_initials = ctk.CTkLabel(self.profile_frame, text=initial, 
                                              width=60, height=60, corner_radius=30, fg_color=COLORS["primary"], 
                                              text_color="white", font=("Roboto", 30, "bold"))
        self.lbl_user_initials.pack()
        
        self.lbl_name = ctk.CTkLabel(self.profile_frame, text=self.app.network.username, font=("Roboto", 18, "bold"))
        self.lbl_name.pack(pady=10)
        
        ctk.CTkLabel(self.sidebar, text="ONLINE STATUS", font=("Roboto", 12), text_color=COLORS["text_sub"]).pack(pady=(40, 10), padx=20, anchor="w")
        
        self.lbl_online = ctk.CTkLabel(self.sidebar, text="● Active (1)", text_color="#00FF00", font=("Roboto", 14))
        self.lbl_online.pack(padx=20, anchor="w")

        self.btn_logout = ctk.CTkButton(self.sidebar, text="Log Out", fg_color="transparent", border_width=1, border_color="#FF5555", text_color="#FF5555", hover_color="#331111", command=self.logout)
        self.btn_logout.pack(side="bottom", pady=30, padx=20, fill="x")

        # --- Chat Area ---
        self.chat_area = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_area.pack(side="right", fill="both", expand=True)

        self.header = ctk.CTkFrame(self.chat_area, height=60, fg_color=COLORS["bg_panel"], corner_radius=0)
        self.header.pack(fill="x")
        ctk.CTkLabel(self.header, text="# General Room", font=("Roboto", 16, "bold"), text_color="white").pack(side="left", padx=20, pady=15)

        self.scroll_frame = ctk.CTkScrollableFrame(self.chat_area, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.input_container = ctk.CTkFrame(self.chat_area, height=80, fg_color=COLORS["bg_panel"], corner_radius=20)
        self.input_container.pack(fill="x", padx=20, pady=20)
        
        self.entry_msg = ctk.CTkEntry(self.input_container, placeholder_text="Type your message...", height=50, border_width=0, fg_color=COLORS["bg_dark"], text_color="white")
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=15, pady=15)
        self.entry_msg.bind("<Return>", lambda e: self.send_message())
        self.entry_msg.focus()

        self.btn_send = ctk.CTkButton(self.input_container, text="➤", width=50, height=50, corner_radius=25, fg_color=COLORS["primary"], font=("Arial", 20), command=self.send_message)
        self.btn_send.pack(side="right", padx=15)

    def destroy(self):
        """Override destroy to set flag"""
        self._destroyed = True
        super().destroy()

    def logout(self):
        """خروج با قطع اتصال"""
        self.app.network.disconnect()
        self.app.show_page("login")

    def send_message(self):
        msg = self.entry_msg.get().strip()
        if not msg:
            return
        if len(msg) > 1000:
            messagebox.showwarning("Message Too Long", "Message must be under 1000 characters")
            return
            
        self.entry_msg.delete(0, "end")
        
        if not self.app.network.connected:
            messagebox.showerror("Connection Error", "Not connected to server")
            return
        
        # ارسال در thread جداگانه
        threading.Thread(target=self.app.network.send, args=({'type': 'message', 'message': msg},), daemon=True).start()

    def clear_chat(self):
        """پاک کردن تمام پیام‌ها"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.last_sender = None

    def add_message_bubble(self, sender, text, time_val):
        """نمایش پیام با بهبود UI"""
        if self._destroyed:
            return
            
        is_me = (sender == self.app.network.username)
        
        # گروه‌بندی پیام‌های متوالی یک کاربر
        show_header = (self.last_sender != sender)
        self.last_sender = sender
        
        row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2 if not show_header else 8)
        
        pack_side = "right" if is_me else "left"
        color = COLORS["bubble_me"] if is_me else COLORS["bubble_other"]
        
        bubble = ctk.CTkFrame(row_frame, fg_color=color, corner_radius=15)
        bubble.pack(side=pack_side, anchor="e" if is_me else "w", padx=5)
        
        # نمایش نام فقط برای پیام اول یا بعد از عوض شدن فرستنده
        if not is_me and show_header:
            ctk.CTkLabel(bubble, text=sender, font=("Arial", 10, "bold"), text_color=COLORS["primary"]).pack(anchor="w", padx=10, pady=(5,0))
        
        ctk.CTkLabel(bubble, text=text, text_color="white", font=("Roboto", 13), wraplength=400, justify="left").pack(padx=12, pady=8)
        
        ctk.CTkLabel(bubble, text=time_val, text_color="gray", font=("Arial", 9)).pack(anchor="e", padx=10, pady=(0, 5))
        
        # اسکرول خودکار
        self.scroll_frame.update_idletasks()
        try:
            self.scroll_frame._parent_canvas.yview_moveto(1.0)
        except:
            pass

    def add_system_message(self, text):
        """پیام سیستمی"""
        if self._destroyed:
            return
            
        lbl = ctk.CTkLabel(self.scroll_frame, text=f"--- {text} ---", text_color="#00FF00", font=("Arial", 10, "italic"))
        lbl.pack(pady=10, fill='x')
        self.last_sender = None
        self.scroll_frame.update_idletasks()
        try:
            self.scroll_frame._parent_canvas.yview_moveto(1.0)
        except:
            pass

class GoldApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gold Messenger Premium")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        self.network = Network(self.handle_network_data)
        self.current_frame = None
        
        self.show_page("login")
        
        # مدیریت بستن برنامه
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """مدیریت بستن برنامه"""
        self.network.disconnect()
        self.destroy()

    def show_page(self, name):
        if self.current_frame:
            self.current_frame.destroy()
            
        if name == "login":
            self.current_frame = LoginPage(self, self)
        elif name == "register":
            self.current_frame = RegisterPage(self, self)
        elif name == "chat":
            self.current_frame = ChatPage(self, self)
            
        self.current_frame.pack(fill="both", expand=True)

    def handle_network_data(self, data):
        """پردازش داده‌های دریافتی از Listener شبکه"""
        try:
            self.after(0, lambda: self._process_data(data))
        except:
            pass

    def _process_data(self, data):
        """پردازش امن داده‌ها در thread اصلی UI"""
        try:
            t = data.get('type')
            
            if t == 'login_ok':
                self.network.username = data.get('username')
                if isinstance(self.current_frame, LoginPage):
                     self.show_page("chat")
                
            elif t == 'history':
                if isinstance(self.current_frame, ChatPage):
                    self.current_frame.clear_chat()
                    for m in data.get('payload', []):
                        self.current_frame.add_message_bubble(m['sender'], m['text'], m['time'])
                        
            elif t == 'new_message':
                if isinstance(self.current_frame, ChatPage):
                    self.current_frame.add_message_bubble(data['sender'], data['text'], data['time'])
                    
            elif t == 'system':
                if isinstance(self.current_frame, ChatPage):
                    self.current_frame.add_system_message(data['message'])
                    
            elif t == 'online_update':
                if isinstance(self.current_frame, ChatPage):
                    count = data.get('count', 1)
                    self.current_frame.lbl_online.configure(text=f"● Active ({count})")
                    
            elif t == 'error':
                messagebox.showerror("Error", data.get('message', 'Unknown Error'))
                
            elif t == 'ok':
                messagebox.showinfo("Success", data.get('message', 'Operation Successful'))
                if isinstance(self.current_frame, RegisterPage):
                    self.show_page("login")
        except Exception as e:
            print(f"Error processing data: {e}")

if __name__ == "__main__":
    app = GoldApp()
    app.mainloop()