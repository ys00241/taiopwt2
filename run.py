#!/usr/bin/env python3
"""寶榮堂花炮會管理系統 — Application Entry Point."""
import sys
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 5000
    app.run(host="0.0.0.0", port=port, debug=True)
