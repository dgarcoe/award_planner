# 🎙️ QuendAward

**Special Callsign Operator Coordination Tool for Ham Radio**

A web application for coordinating multiple operators activating the same special callsign. Avoid conflicts by blocking band/mode combinations in real-time.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Real-time Heatmap** | Interactive visualization of band/mode availability |
| 🔒 **Band/Mode Blocking** | Reserve combinations while you're active |
| 📢 **Announcements** | Admin announcements with notification badges |
| 🏆 **Multi-Award Support** | Manage multiple special callsigns/events |
| 🌍 **Multi-Language** | English, Spanish, Galician |
| 📱 **Mobile-Friendly** | Responsive design for smartphones |
| 👥 **Multi-Operator** | Secure authentication for teams |
| 💾 **Backup/Restore** | Database management for admins |

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone and configure
git clone <repository-url>
cd award_planner
cp .env.example .env
# Edit .env with your admin credentials

# Run
docker-compose up -d

# Access at http://localhost:8501
```

### Manual Installation

```bash
pip install -r requirements.txt
export ADMIN_CALLSIGN=W1ADMIN
export ADMIN_PASSWORD=YourSecurePassword
streamlit run app.py
```

---

## ⚙️ Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `ADMIN_CALLSIGN` | Super admin callsign | Yes |
| `ADMIN_PASSWORD` | Super admin password | Yes |
| `DATABASE_PATH` | SQLite database path | No (default: `ham_coordinator.db`) |

---

## 📁 Project Structure

```
award_planner/
├── app.py               # Main application
├── database.py          # Database operations
├── admin_functions.py   # Admin panel tabs
├── ui_components.py     # Reusable UI components
├── charts.py            # Plotly visualizations
├── translations.py      # i18n (EN/ES/GL)
├── mobile_styles.py     # Responsive CSS
├── config.py            # Configuration
└── Dockerfile
```

---

## 📻 Supported Bands & Modes

**Bands:** 160m, 80m, 60m, 40m, 30m, 20m, 17m, 15m, 12m, 10m, 6m, 2m, 70cm

**Modes:** CW, SSB, DIGI, SAT

---

## 🔐 User Roles

| Role | Capabilities |
|------|-------------|
| **Super Admin** | Full access, configured via environment variables |
| **Admin** | Create operators, manage awards, announcements |
| **Operator** | Block/unblock bands, view dashboard |

---

## 📖 Usage

### For Admins

1. Login with admin credentials
2. **Create Operators**: Admin Panel → Create Operator
3. **Create Awards**: Admin Panel → Special Callsigns
4. **Post Announcements**: Admin Panel → Announcements

### For Operators

1. Login with provided credentials
2. Select the active award/special callsign
3. Click on heatmap cells to block/unblock
4. Check 🔔 for announcements

---

## 🌍 Languages

- 🇬🇧 English
- 🇪🇸 Español
- 🇬🇱 Galego (default)

Select language on the login page.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** (GPLv3).

See [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Daniel García Coego**

---

## 🤝 Contributing

Contributions welcome! Please open an issue or pull request.
