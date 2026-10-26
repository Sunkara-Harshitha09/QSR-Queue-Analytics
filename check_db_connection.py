from pathlib import Path
from sqlalchemy.engine import make_url
import psycopg

lines = Path(".env").read_text(encoding="utf-8-sig").splitlines()
raw = next(
    line.split("=", 1)[1].strip().strip('"').strip("'")
    for line in lines
    if line.strip().startswith("DATABASE_URL=")
)

url = make_url(raw)

# The unescaped @ in the password confused URL parsing.
# This project uses the known local Docker endpoint.
if url.host == "123@127.0.0.1":
    raise RuntimeError(
        "DATABASE_URL is malformed. Please correct the URL in .env "
        "by URL-encoding @ inside the password as %40."
    )

if url.host not in ("127.0.0.1", "localhost"):
    raise RuntimeError(
        f"Unexpected database host: {url.host}. No database changes made."
    )

url = url.set(drivername="postgresql")
print("Parsed host:", url.host)
print("Parsed port:", url.port)
print("Database:", url.database)
print("Username:", url.username)
print("Password configured:", bool(url.password))
