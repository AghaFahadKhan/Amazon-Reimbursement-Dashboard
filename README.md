# 📦 Amazon Reimbursement Analytics — Streamlit App

A secure, multi-user web application that turns any Amazon Seller
Reimbursements CSV into an interactive analytics dashboard with KPIs,
date filters, compare-mode, and seven tabs of charts and tables.

> Built by **Muhammad Zia** — Streamlit port of the original HTML dashboard.

---

## ✨ Features

- 🔐 **Username + password login** — share access only with the people you choose
- 📊 **Overview KPIs** — total reimbursed, cases, unique ASINs, average per case, top reason, net reimbursed
- 📅 **Date filter** — All time, Today, Yesterday, Month-to-Date, Last Month, Custom range
- 🔁 **Compare mode** — vs Previous Period / Previous Month / Custom range, with % delta on KPIs
- 🏷️ **By Reason** — bar + pie + summary table with % of total
- 📦 **By ASIN** — top-15 bar, paginated table, filter by reason, text search
- 🔄 **Date × Reason pivot** — stacked daily chart + full pivot table
- 🔲 **ASIN × Reason** — stacked chart + cross-table for top 30 ASINs
- 📋 **Raw report** — searchable table of every row, with CSV download

---

## 🚀 Quick start (local)

### 1. Clone / copy the project

```bash
git clone <your-repo-url> reimbursement_app
cd reimbursement_app
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate         # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure users

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml` and add one line per user:

```toml
[users]
admin    = "strong-password-1"
alice    = "strong-password-2"
bob      = "strong-password-3"
```

### 4. Run the app

```bash
streamlit run app.py
```

The app opens at <http://localhost:8501>.

---

## ☁️ Deploy to Streamlit Community Cloud (free, recommended)

This is the easiest way to share the app with your team — they just get
a link and log in with their credentials.

### Step 1 — Push the code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

> ⚠️ The included `.gitignore` makes sure `.streamlit/secrets.toml` is
> **not** pushed. Only the `.example` file is committed. This is what
> you want.

### Step 2 — Deploy

1. Go to <https://share.streamlit.io>
2. Sign in with your GitHub account
3. Click **"Create app"** → **"Deploy a public app from GitHub"**
4. Pick your repository, branch `main`, and main file path `app.py`
5. (Optional) pick a custom subdomain like `zia-reimbursement`

### Step 3 — Add your secrets in the cloud

1. On your deployed app, click **Settings** (bottom-right) → **Secrets**
2. Paste the contents of your local `secrets.toml`:

    ```toml
    [users]
    admin = "strong-password-1"
    alice = "strong-password-2"
    bob   = "strong-password-3"
    ```

3. Click **Save**. The app will restart automatically.

### Step 4 — Share the link

Send the app URL **plus each user's individual username and password**
separately. Done.

---

## 👥 Adding, removing, or changing users

You never touch the code to manage access — just edit secrets.

**Streamlit Cloud:**
App page → **Settings → Secrets** → edit the `[users]` block → **Save**.
The app reloads in a few seconds.

**Local:**
Edit `.streamlit/secrets.toml` and restart `streamlit run app.py`.

### Removing a user

Delete their line from the `[users]` block. Their existing session stays
active until they sign out or the app restarts, so for a hard kick you
can also change the password.

---

## 📄 How your users get their CSV

Your users should click the **"How to download your Amazon Reimbursement CSV"**
help expander in the sidebar — it has the full 10-step guide. Short version:

> Seller Central → ☰ menu → Reports → Fulfillment → Payments →
> Reimbursements → Download → pick date range → Request .csv Download.

Then drag the file into the uploader in the sidebar.

---

## 🔒 Security notes

- Passwords are compared in constant time (`hmac.compare_digest`) so the
  app is not vulnerable to timing attacks.
- Passwords are stored in `st.secrets` — not in the code and not in Git.
- Each user's uploaded CSV stays in their own browser session and is not
  persisted server-side between sessions.
- For a public deployment, use **long, unique passwords** (16+ chars).
  Consider a password manager to generate them.
- If you need stricter auth (email verification, SSO, 2FA) on Streamlit
  Cloud, upgrade to a Teams plan and use the built-in Google SSO, or
  deploy on your own infrastructure behind Auth0 / Cloudflare Access.

---

## 🗂️ Project structure

```
reimbursement_app/
├── app.py                          # the whole app
├── requirements.txt                # python deps
├── README.md                       # this file
├── .gitignore                      # keeps secrets out of git
└── .streamlit/
    ├── config.toml                 # dark theme + upload size
    └── secrets.toml.example        # template — copy to secrets.toml
```

---

## 🛠️ Troubleshooting

**"No users configured" warning on the login screen**
You haven't created `secrets.toml` yet (or on the cloud, you haven't
pasted secrets into Settings → Secrets). See step 3 above.

**"Could not read CSV"**
Amazon sometimes exports tab-separated files with a `.csv` extension.
The app auto-detects the delimiter, but if parsing still fails open the
file in Excel, save as proper CSV, and re-upload.

**Charts look empty**
The currently selected date filter has no data in it. Switch back to
"All Time" to confirm the file loaded correctly.

**Need to raise the 200 MB upload limit**
Edit `.streamlit/config.toml` → `maxUploadSize = 500` (or whatever).

---

## 📧 Questions

Open an issue on the repo, or contact Muhammad Zia.
