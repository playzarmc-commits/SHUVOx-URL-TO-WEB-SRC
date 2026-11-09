"""Bot settings. Replace placeholders locally; do not share live credentials."""

# Use a fresh token from Telegram's @BotFather. The old exposed token is not included.
BOT_TOKEN = "9032250552:AAG0PDTXV-L3TLYzvW62nAH8xGrJnlJVvuo"

# Add your numeric Telegram user ID(s), e.g. [123456789].
ADMIN_IDS = [8600328303]

# Optional numeric group ID for activity logs. None disables logging.
LOGS_GROUP_ID = -1003970225189

DATA_FILE = "bot_data.json"
PORT = 8080

# Optional GitHub Models token for the existing SEO AI note; leave blank to disable.
# The previous exposed token is not included.
GITHUB_TOKEN = ""

# ── Turso (libSQL) database — persistent users/stats/force-join storage ──
TURSO_URL = "libsql://shuvoxmods-shuvoxmods.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQyNDg5MzYsImlkIjoiMDFhMWMxOTEtZTAwMS03NmY1LWIxNTEtODRiYzRkMjcxNTg1Iiwia2lkIjoibGRJQmtuN2N2NTdLU2pDSS1pTmxYeWRXcXlJWU1DWVl0c2Rhcm9nUW1tZyIsInJpZCI6ImUzNDk3MDk2LWY4OGMtNDg2Ny1hZjIzLTdlZTQ5ZTNmNDcwZiJ9.p30d0EiP-ZmkoYpSE08GLd9jP6Xv_KVgcaXFfJOOIzAU881sol6Au5p-gUh4mLW8OUgDe-rssk93uzdSfMtWBw"
