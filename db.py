"""MySQL connection helper for Azure MySQL Flexible Server."""
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Open a new MySQL connection. Caller is responsible for closing it."""
    config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }

    ssl_ca = os.getenv("DB_SSL_CA")
    if ssl_ca and os.path.exists(ssl_ca):
        config["ssl_ca"] = ssl_ca
        config["ssl_verify_cert"] = True
    else:
        # Azure requires SSL; fall back to SSL without cert verification
        # if the cert file isn't present.
        config["ssl_disabled"] = False

    return mysql.connector.connect(**config)


def query(sql, params=None, fetch=True):
    """Run a SQL statement. Returns rows (fetch=True) or rowcount/lastrowid."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        if fetch:
            return cur.fetchall()
        conn.commit()
        return {"rowcount": cur.rowcount, "lastrowid": cur.lastrowid}
    finally:
        cur.close()
        conn.close()
