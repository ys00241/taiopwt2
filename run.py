#!/usr/bin/env python3
"""寶榮堂花炮會管理系統 — Application Entry Point."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
