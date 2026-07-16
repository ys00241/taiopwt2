#!/bin/bash
set -e

echo "=== 寶榮堂花炮會 — Docker Entrypoint ==="

# ── Migration handled by app/__init__.py (create_all + alter) ──
echo "📦 Tables created/migrated automatically on first request..."

# ── Start Flask ──
echo "🚀 Starting Flask..."
exec python3 run.py
