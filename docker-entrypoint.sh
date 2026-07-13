#!/bin/bash
set -e

echo "=== 寶榮堂花炮會 — Docker Entrypoint ==="

# ── Auto-migration: add new columns if missing ──
echo "📦 Running schema migration..."
python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    import sqlalchemy as sa
    inspector = sa.inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('members')]
    migrations = [
        ('end_year', 'INTEGER'),
        ('name_alais', 'VARCHAR(200)'),
        ('group_name', 'VARCHAR(200)'),
        ('referrer', 'VARCHAR(200)'),
    ]
    for col, dtype in migrations:
        if col not in cols:
            db.session.execute(sa.text(f'ALTER TABLE members ADD COLUMN {col} {dtype}'))
            print(f'  ✅ Added column: {col}')
        else:
            print(f'  ℹ {col} already exists')
    db.session.commit()
print('✅ Migration complete')
"

# ── Start Flask ──
echo "🚀 Starting Flask..."
exec python3 run.py
