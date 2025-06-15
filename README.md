# 🐾 PawPrint

**PawPrint** is a Flask-based web application that helps developers track and visualize code review changes in a clean, browser-based interface. It simplifies the review process by making iterations and feedback history more accessible and traceable.

---

## 🌐 Features

- Web UI for browsing code review change history
- Tracks review comments, iterations, and file-level diffs
- Lightweight and easy to run locally
- Ideal for teams managing code reviews manually or outside of GitHub/GitLab PR tooling

---

## 🧰 Tech Stack

- Python 3.x (v3.13.3 used for development. Older versions may work but are not supported)
- Flask
- HTML/CSS (Jinja templates)
- (Optional) SQLite or other lightweight storage for session or metadata

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
$ git clone https://github.com/JackEdClifton/PawPrint.git
$ cd PawPrint
```

### 2. Install Depencencies

```bash
$ pip install Flask Flask-SQLAlchemy
```

### 3. Run the application

```bash
$ python pawprint.py
```