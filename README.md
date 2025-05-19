# 📬 Email Translator and Forwarder

This Python script automatically fetches emails from specified recipients, translates the content from **German to English**, and resends the translated version to a predefined email address. It uses the **mBART-50** model from HuggingFace for translation and handles both email fetching and sending securely via IMAP/SMTP.

---

##  Features

- ✅ Fetch emails using **IMAP**
- 🌐 Translate German emails to English using **Facebook's mBART-50 multilingual model**
- 📤 Resend translated emails using **SMTP**
- 🧠 Handles long emails by splitting them into chunks
- 💾 Maintains a log to avoid re-translating the same emails
- 🔒 Uses environment variables for sensitive credentials

---

##  Requirements

Install dependencies using pip:

```bash
pip install transformers torch python-dotenv
```

---

## Create an .env file
Create a .env file in the project directory to store your credentials and configuration:
```bash
EMAIL_DOMAIN=imap.gmail.com
READ_EMAIL=recipient@example.com
READ_USERNAME=imap-username@example.com
READ_PASSWORD=imap-password
SENT_EMAIL=sender@example.com
SENT_USERNAME=smtp-username@example.com
SENT_PASSWORD=smtp-password
```

