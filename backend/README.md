---
title: Karandeni Investment Backend
emoji: 🏢
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Karandeni Investment Backend (Flask + MongoDB) on Hugging Face Spaces

This Space runs the Flask API for Karandeni Investment.

## Required Space secrets (Settings → Variables and secrets)

| Name | Example | Notes |
|---|---|---|
| `MONGO_URI` | `mongodb+srv://user:pass@cluster.mongodb.net/` | MongoDB Atlas connection string |
| `MONGO_DB` | `karandeni_investment` | Database name |
| `JWT_SECRET` | (long random string) | Generate with `python -c "import secrets;print(secrets.token_hex(32))"` |
| `JWT_EXPIRY_HOURS` | `24` | Optional, defaults to 24 |
| `ALLOWED_ORIGINS` | `*` or `https://your-app.vercel.app` | Frontend origin(s) |
| `SMSLENZ_API_KEY` | `your_smslenz_key` | Optional, SMS gateway key |
| `SMSLENZ_USER_ID` | `2173` | Optional, SMS gateway user ID |
| `SMSLENZ_SENDER_ID` | `KarandeniInv` | Optional, SMS sender mask |

Health check: `GET /api/health`

