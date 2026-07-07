import socket
import threading
import json
import os
import struct
import sqlite3
import bcrypt  
from cryptography.fernet import Fernet 
from datetime import datetime, timedelta
import time
import signal
import sys
import logging
import re
from collections import defaultdict

# تنظیمات Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# تنظیمات سرور
HOST = "127.0.0.1"
PORT = 5000
MAX_MESSAGE_LENGTH = 1000
MAX_USERNAME_LENGTH = 20
MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
MESSAGE_HISTORY_LIMIT = 50
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 300  # 5 دقیقه
RATE_LIMIT_MESSAGES = 10  # حداکثر پیام در بازه زمانی
RATE_LIMIT_WINDOW = 10  # ثانیه

# بارگذاری کلید رمزنگاری
if not os.path.exists("secret.key"):
    logger.error("'secret.key' not found. Run MakeKey.py first.")
    exit()
with open("secret.key", "rb") as kf:
    CIPHER = Fernet(kf.read())

# تنظیمات دیتابیس
DB_NAME = "gold_messenger.db"
db_lock = threading.Lock()

# Rate limiting و tracking
login_attempts = defaultdict(lambda: {'count': 0, 'timestamp': datetime.now()})
message_rate_limit = defaultdict(list)
rate_limit_lock = threading.Lock()

def init_db():
    """ایجاد جداول دیتابیس"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password_hash BLOB, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, text TEXT, time TEXT, created_at TEXT)''')
        conn.commit()
        conn.close()
    logger.info("Database initialized")

init_db()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 

try:
    server.bind((HOST, PORT))
    server.listen(5)
    logger.info(f"Server started successfully on {HOST}:{PORT}")
except OSError as e:
    logger.error(f"Error starting server: {e}")
    exit()

clients = {}
clients_lock = threading.Lock()
server_running = True

# --- توابع Validation ---

def validate_username(username):
    """اعتبارسنجی نام کاربری"""
    if not username:
        return False, "Username is required"
    
    if len(username) < MIN_USERNAME_LENGTH:
        return False, f"Username must be at least {MIN_USERNAME_LENGTH} characters"
    
    if len(username) > MAX_USERNAME_LENGTH:
        return False, f"Username too long (max {MAX_USERNAME_LENGTH} characters)"
    
    if " " in username:
        return False, "Username cannot contain spaces"
    
    # فقط حروف، اعداد و underscore
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers and underscore"
    
    return True, "OK"

def validate_password(password):
    """اعتبارسنجی رمز عبور"""
    if not password:
        return False, "Password is required"
    
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    
    return True, "OK"

def sanitize_message(text):
    """پاکسازی پیام از کاراکترهای خطرناک"""
    if not text:
        return ""
    
    # حذف کاراکترهای کنترلی (به جز newline و tab)
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    
    # محدود کردن طول
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH]
    
    return text.strip()

# --- Rate Limiting ---

def check_login_rate_limit(ip_address):
    """بررسی محدودیت تلاش login"""
    with rate_limit_lock:
        now = datetime.now()
        attempt_info = login_attempts[ip_address]
        
        # Reset اگر timeout گذشته
        if (now - attempt_info['timestamp']).seconds > LOGIN_TIMEOUT:
            login_attempts[ip_address] = {'count': 0, 'timestamp': now}
            return True
        
        if attempt_info['count'] >= MAX_LOGIN_ATTEMPTS:
            logger.warning(f"Login rate limit exceeded for {ip_address}")
            return False
        
        return True

def increment_login_attempts(ip_address):
    """افزایش تعداد تلاش login"""
    with rate_limit_lock:
        login_attempts[ip_address]['count'] += 1
        login_attempts[ip_address]['timestamp'] = datetime.now()

def check_message_rate_limit(username):
    """بررسی محدودیت ارسال پیام"""
    with rate_limit_lock:
        now = datetime.now()
        
        # پاک کردن پیام‌های قدیمی
        message_rate_limit[username] = [
            timestamp for timestamp in message_rate_limit[username]
            if (now - timestamp).seconds < RATE_LIMIT_WINDOW
        ]
        
        if len(message_rate_limit[username]) >= RATE_LIMIT_MESSAGES:
            logger.warning(f"Message rate limit exceeded for {username}")
            return False
        
        message_rate_limit[username].append(now)
        return True

# --- توابع رمزنگاری و ارسال/دریافت ---

def encrypt_data(data_dict):
    """رمزنگاری داده‌ها"""
    try:
        json_data = json.dumps(data_dict, ensure_ascii=False)
        return CIPHER.encrypt(json_data.encode('utf-8'))
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return None

def decrypt_data(encrypted_bytes):
    """رمزگشایی داده‌ها"""
    try:
        decrypted = CIPHER.decrypt(encrypted_bytes)
        return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return None

def send_data(sock, data_dict):
    """ارسال داده با مدیریت خطا"""
    try:
        encrypted_bytes = encrypt_data(data_dict)
        if not encrypted_bytes:
            return False
        
        msg_length = len(encrypted_bytes)
        header = struct.pack('>I', msg_length)
        sock.sendall(header + encrypted_bytes)
        return True
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

def recv_data(sock):
    """دریافت داده با مدیریت خطا"""
    try:
        header = sock.recv(4)
        if not header or len(header) < 4:
            return None
        
        msg_length = struct.unpack('>I', header)[0]
        
        # محدودیت حجم برای امنیت
        if msg_length > 10 * 1024 * 1024:  # 10MB limit
            logger.warning("Message too large, rejecting")
            return None
        
        encrypted_bytes = b''
        while len(encrypted_bytes) < msg_length:
            to_read = msg_length - len(encrypted_bytes)
            chunk = sock.recv(min(4096, to_read))
            if not chunk:
                return None
            encrypted_bytes += chunk
        
        if len(encrypted_bytes) != msg_length:
            return None
            
        return decrypt_data(encrypted_bytes)
    except Exception as e:
        logger.error(f"Receive error: {e}")
        return None

def broadcast(data_dict, exclude_sock=None):
    """ارسال پیام به همه کاربران آنلاین"""
    with clients_lock:
        disconnected = []
        for sock in list(clients.keys()):
            if sock != exclude_sock:
                if not send_data(sock, data_dict):
                    disconnected.append(sock)
        
        # حذف کلاینت‌های قطع شده
        for sock in disconnected:
            if sock in clients:
                username = clients[sock]
                logger.info(f"Removing disconnected client: {username}")
                del clients[sock]
                broadcast({'type': 'system', 'message': f"{username} disconnected unexpectedly."})
                update_online_count()

def update_online_count():
    """بروزرسانی تعداد کاربران آنلاین"""
    with clients_lock:
        online_count = len(clients)
    broadcast({'type': 'online_update', 'count': online_count})

# --- توابع مدیریت دیتابیس ---

def handle_db_login(username, password):
    """احراز هویت کاربر"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        try:
            c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
            row = c.fetchone()
            
            if row:
                stored_hash = row[0]
                try:
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                        return True
                except Exception as e:
                    logger.error(f"Password check error: {e}")
                    return False
            return False
        finally:
            conn.close()

def handle_db_register(username, password):
    """ثبت‌نام کاربر جدید"""
    # اعتبارسنجی username
    valid, msg = validate_username(username)
    if not valid:
        return msg
    
    # اعتبارسنجی password
    valid, msg = validate_password(password)
    if not valid:
        return msg
    
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)", 
                     (username, hashed, created))
            conn.commit()
            logger.info(f"New user registered: {username}")
            return "ok"
        except sqlite3.IntegrityError:
            return "Username already exists"
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return "Registration failed"
        finally:
            conn.close()

def save_message(sender, text, timestamp):
    """ذخیره پیام در دیتابیس"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        try:
            created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO messages (sender, text, time, created_at) VALUES (?, ?, ?, ?)", 
                     (sender, text, timestamp, created))
            conn.commit()
        except Exception as e:
            logger.error(f"Save message error: {e}")
        finally:
            conn.close()

def get_last_messages(limit=MESSAGE_HISTORY_LIMIT):
    """دریافت آخرین پیام‌ها"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        try:
            c.execute("SELECT sender, text, time FROM messages ORDER BY id DESC LIMIT ?", (limit,))
            rows = c.fetchall()
            return [{'sender': r[0], 'text': r[1], 'time': r[2]} for r in reversed(rows)]
        except Exception as e:
            logger.error(f"Get messages error: {e}")
            return []
        finally:
            conn.close()

def handle_client(client, address):
    """مدیریت ارتباط با کلاینت"""
    logger.info(f"New connection from: {address}")
    username = None
    ip_address = address[0]
    
    try:
        while server_running:
            request = recv_data(client)
            if not request:
                break
            
            req_type = request.get('type')
            
            if req_type == 'login':
                # بررسی rate limit
                if not check_login_rate_limit(ip_address):
                    send_data(client, {'type': 'error', 'message': 'Too many login attempts. Please try again later.'})
                    continue
                
                u = request.get('username', '').strip()
                p = request.get('password', '')
                
                if not u or not p:
                    send_data(client, {'type': 'error', 'message': 'Invalid credentials'})
                    increment_login_attempts(ip_address)
                    continue
                
                if handle_db_login(u, p):
                    username = u
                    
                    # بررسی اتصال قبلی
                    with clients_lock:
                        # قطع اتصال قبلی همین کاربر
                        for sock, uname in list(clients.items()):
                            if uname == username and sock != client:
                                try:
                                    send_data(sock, {'type': 'error', 'message': 'Logged in from another location'})
                                    sock.close()
                                except:
                                    pass
                                del clients[sock]
                        
                        clients[client] = username
                    
                    send_data(client, {'type': 'login_ok', 'username': u})
                    logger.info(f"{u} logged in from {ip_address}")
                    
                    # ارسال تاریخچه
                    history = get_last_messages()
                    send_data(client, {'type': 'history', 'payload': history})
                    
                    # اعلام حضور
                    broadcast({'type': 'system', 'message': f"{u} joined the chat."}, exclude_sock=client)
                    
                    # بروزرسانی تعداد آنلاین
                    update_online_count()
                    
                else:
                    send_data(client, {'type': 'error', 'message': 'Invalid username or password'})
                    increment_login_attempts(ip_address)
            
            elif req_type == 'register':
                u = request.get('username', '').strip()
                p = request.get('password', '')
                
                res = handle_db_register(u, p)
                if res == "ok":
                    send_data(client, {'type': 'ok', 'message': 'Account created successfully!'})
                    logger.info(f"New registration: {u} from {ip_address}")
                else:
                    send_data(client, {'type': 'error', 'message': res})
            
            elif req_type == 'message':
                if not username:
                    send_data(client, {'type': 'error', 'message': 'Not authenticated'})
                    continue
                
                # بررسی rate limit
                if not check_message_rate_limit(username):
                    send_data(client, {'type': 'error', 'message': 'You are sending messages too quickly. Please slow down.'})
                    continue
                
                msg_text = sanitize_message(request.get('message', ''))
                
                if not msg_text:
                    continue
                
                if len(msg_text) > MAX_MESSAGE_LENGTH:
                    send_data(client, {'type': 'error', 'message': f'Message too long (max {MAX_MESSAGE_LENGTH} characters)'})
                    continue
                
                timestamp = datetime.now().strftime("%H:%M")
                
                # ذخیره در دیتابیس
                save_message(username, msg_text, timestamp)
                
                # ارسال به همه (شامل فرستنده)
                msg_packet = {
                    'type': 'new_message',
                    'sender': username,
                    'text': msg_text,
                    'time': timestamp
                }
                
                broadcast(msg_packet)
                logger.info(f"Message from {username}: {msg_text[:50]}...")

    except Exception as e:
        logger.error(f"Client error {address}: {e}")
    finally:
        # پاکسازی بعد از قطع اتصال
        if client in clients:
            with clients_lock:
                username_leaving = clients.get(client)
                del clients[client]
            
            if username_leaving:
                logger.info(f"{username_leaving} disconnected")
                broadcast({'type': 'system', 'message': f"{username_leaving} left the chat."})
                update_online_count()
        
        try:
            client.close()
        except:
            pass

def accept_connections():
    """پذیرش اتصالات جدید"""
    while server_running:
        try:
            server.settimeout(1.0)
            try:
                client, address = server.accept()
                threading.Thread(target=handle_client, args=(client, address), daemon=True).start()
            except socket.timeout:
                continue
        except Exception as e:
            if server_running:
                logger.error(f"Accept error: {e}")
            break

def signal_handler(sig, frame):
    """مدیریت سیگنال‌های سیستمی"""
    global server_running
    logger.info("Shutdown signal received")
    server_running = False

def main():
    """شروع سرور"""
    global server_running
    
    # ثبت signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("    GOLD MESSENGER SERVER")
    print("=" * 50)
    print(f"Listening on {HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        accept_connections()
    except KeyboardInterrupt:
        pass
    finally:
        server_running = False
        # بستن تمام اتصالات
        with clients_lock:
            for sock in list(clients.keys()):
                try:
                    send_data(sock, {'type': 'error', 'message': 'Server shutting down'})
                    sock.close()
                except:
                    pass
            clients.clear()
        
        try:
            server.close()
        except:
            pass
        
        logger.info("Server stopped successfully")

if __name__ == "__main__":
    main()