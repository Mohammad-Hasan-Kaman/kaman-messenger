# 🚀 Kaman Messenger (V7 - Goldasli)

> A secure, real-time messaging application built with **Python**, featuring **Socket** communication, **SQLite** backend, and a modern **CustomTkinter** GUI with AES encryption.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-Moderm%20UI-purple.svg)
![Encryption](https://img.shields.io/badge/Security-AES%20Encryption-green.svg?logo=cryptography)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🚀 Purpose & Target Audience

**Kaman Messenger** is designed for users seeking a secure, lightweight, and real-time communication platform. It uniquely combines a **Socket-based server** with a **modern desktop client** for seamless, encrypted messaging.

| Audience | Usage Method |
|----------|--------------|
| **End Users** | Run the desktop client (`kaman-messenger-client.exe`) to connect to a running server. |
| **Developers** | Clone the repository, generate a security key, and run both server and client. |

---

## ✨ Key Features

- 🔐 **Secure Encryption:**
  - **AES Encryption** (via `cryptography.fernet`) for all network traffic.
  - Password hashing with **Bcrypt** for user security.
- 💬 **Real-Time Messaging:**
  - Instant message delivery via **TCP Sockets**.
  - Broadcast system for sending messages to all connected users.
- 🛡️ **Security & Stability:**
  - **Rate Limiting:** Prevents spam by limiting messages per user (10 msgs/10s).
  - **Login Security:** Timeout and attempt limiting.
  - **Secure Key Management:** Separate `secret.key` file generated at runtime.
- 🎨 **Modern UI:**
  - Beautiful and responsive interface using **CustomTkinter**.
  - Dark mode support and modern color palette.
- 🗄️ **Reliable Data Storage:**
  - **SQLite** backend for persistent message and user storage.
  - Simple setup with no external database server required.

---

## 📥 Installation & Setup

### Prerequisites
- **Python 3.10+**
- **pip** (Python package manager)

### 1. Clone the Repository
```bash
git clone https://github.com/Mohammad-Hasan-Kaman/kaman-messenger.git
cd kaman-messenger
```

### 2. Create Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Generate Security Key
Before running the server or client, you **must** generate a security key:
```bash
python MakeKey.py
```
This creates a `secret.key` file used for AES encryption.

### 5. Run the Application

**Start the Server:**
```bash
python GoldServer.py
```
*The server will start on `127.0.0.1:5000` by default.*

**Start the Client:**
```bash
python GoldClient.py
```
*The client will attempt to connect to the server automatically.*

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, Socket, Threading |
| **Database** | SQLite (via `sqlite3`) |
| **Security** | `cryptography.fernet`, `bcrypt` |
| **Frontend** | CustomTkinter, Tkinter |

---

## 📂 Project Structure

```
kaman-messenger/
├── GoldServer.py          # TCP Server with encryption
├── GoldClient.py          # Desktop client with GUI
├── MakeKey.py             # Script to generate security key
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
└── CONTRIBUTING.md       # Contribution guidelines
```

> **Note:** `secret.key`, `gold_messenger.db`, and `server.log` are **ignored** from Git and generated at runtime.

---

## 🤝 Contributing

Found a bug or have a feature request? Please open an [Issue](https://github.com/Mohammad-Hasan-Kaman/kaman-messenger/issues).
Contributions are welcome! See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## ⭐ Support

If you find this tool useful, please give it a **star**! ⭐

[![Stars](https://img.shields.io/github/stars/Mohammad-Hasan-Kaman/kaman-messenger?style=for-the-badge&logo=github&color=blue)](https://github.com/Mohammad-Hasan-Kaman/kaman-messenger/stargazers)

---
*Maintained by Mohammad Hasan Kaman | Last updated: July 2026*

> **Note:** This project is a work in progress. Some features may be under development or testing.