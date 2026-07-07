# Contributing to Kaman Messenger (V7)

Thank you for your interest in contributing to **Kaman Messenger**! This project is open to contributions from the community. Whether you're reporting bugs, suggesting features, or submitting code, your help is appreciated.

## 🤝 How to Contribute

### 1. Reporting Bugs
If you encounter a bug, please open an [Issue](https://github.com/Mohammad-Hasan-Kaman/kaman-messenger/issues) and include:
- A clear title and description.
- Steps to reproduce the problem.
- Expected vs. actual behavior.
- Screenshots (if applicable).
- Your environment (OS, Python version).

### 2. Suggesting Features
Have an idea for a new feature? Please open an [Issue](https://github.com/Mohammad-Hasan-Kaman/kaman-messenger/issues) labeled `enhancement` and describe:
- The problem you're trying to solve.
- Your proposed solution.
- Why this feature is useful.

### 3. Submitting Code Changes
If you'd like to submit code changes:
1. **Fork** the repository.
2. Create a **new branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes and ensure the code builds and runs.
4. Write **clear commit messages**:
   ```bash
   git commit -m "feat: Added user authentication"
   ```
5. **Push** your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
6. Open a **Pull Request (PR)** against `main`.

### 4. Code Style
- Follow **PEP 8** for Python code.
- Keep functions and classes concise and readable.
- Add comments for complex logic.
- Ensure your code works with both the network server and CustomTkinter client.

## 🛠 Development Setup
- Install **Python 3.10+**.
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Generate a security key:
  ```bash
  python MakeKey.py
  ```
- Run the server and client.

## 📝 License
By contributing, you agree that your contributions will be licensed under the **MIT License** of this project.

---

Thank you for helping make **Kaman Messenger** better! 🚀