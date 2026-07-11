"""PL blueprint — 損益表 (Profit & Loss) 檢視與 Excel 匯出."""
from flask import Blueprint
from flask_login import login_required

bp = Blueprint("pl", __name__)


@bp.route("/pl")
@login_required
def view_pl():
    """View profit & loss entries by year with income/expense sections."""
    from flask import render_template, request
    from app.extensions import db
    from app.models.pl import PL
    from app.models.edition import Edition
    from app.models.this_year_item import ThisYearItem
    from app.models.bid import Bid
    from app.models.live_income import LiveIncome
    from sqlalchemy import func
    from datetime import datetime

    year = request.args.get("year", type=int)

    # Default to latest year
    if not year or year == 0:
        latest = db.session.query(func.max(Edition.year)).scalar()
        year = latest or 2025

    # ════════════════════════════════════════════════════════════
    #  Live bidding income (real-time from this_year_items)
    # ════════════════════════════════════════════════════════════
    bidding_receivable = (
        db.session.query(func.coalesce(func.sum(ThisYearItem.bid_amount), 0))
        .filter(ThisYearItem.year == year, ThisYearItem.bid_amount > 0)
        .scalar()
    ) or 0

    bidding_paid_in_items = (
        db.session.query(func.coalesce(func.sum(ThisYearItem.paid_amount), 0))
        .filter(ThisYearItem.year == year, ThisYearItem.paid_amount > 0)
        .scalar()
    ) or 0

    bidding_live_collected = (
        db.session.query(func.coalesce(func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.source_year == year)
        .scalar()
    ) or 0

    bidding_received = bidding_paid_in_items + bidding_live_collected
    bidding_outstanding = bidding_receivable - bidding_received

    # ════════════════════════════════════════════════════════════
    #  PL table (static imported data)
    # ════════════════════════════════════════════════════════════
    income_rows = (
        PL.query.filter(PL.year == year, PL.pl_type == "收入")
        .order_by(PL.subject)
        .all()
    )
    expense_rows = (
        PL.query.filter(PL.year == year, PL.pl_type == "支出")
        .order_by(PL.subject)
        .all()
    )

    # Fallback: if no PL data found for this year, try to compute summary
    # from LiveIncome, Bid, and DailyEntry tables so the view isn't blank.
    if not income_rows and not expense_rows:
        from types import SimpleNamespace
        from app.models.live_income import LiveIncome
        from app.models.daily_entry import DailyEntry

        live_income_total = (
            db.session.query(func.coalesce(func.sum(LiveIncome.amount), 0))
            .filter(LiveIncome.year == year)
            .scalar()
        )
        bid_income_total = (
            db.session.query(func.coalesce(func.sum(Bid.bid_amount), 0))
            .filter(Bid.year == year)
            .scalar()
        )
        daily_income_total = (
            db.session.query(func.coalesce(func.sum(DailyEntry.amount), 0))
            .filter(DailyEntry.year == year, DailyEntry.entry_type == "income")
            .scalar()
        )
        daily_expense_total = (
            db.session.query(func.coalesce(func.sum(DailyEntry.amount), 0))
            .filter(DailyEntry.year == year, DailyEntry.entry_type == "expense")
            .scalar()
        )

        # Build synthetic rows for fallback display
        income_fallback = []
        if float(live_income_total) > 0:
            income_fallback.append(SimpleNamespace(
                subject="現場收款 (LiveIncome)", amount_hkd=float(live_income_total),
                payment_method="",
            ))
        if float(bid_income_total) > 0:
            income_fallback.append(SimpleNamespace(
                subject="競投收入 (Bid)", amount_hkd=float(bid_income_total),
                payment_method="",
            ))
        if float(daily_income_total) > 0:
            income_fallback.append(SimpleNamespace(
                subject="其他日常收入 (DailyEntry)", amount_hkd=float(daily_income_total),
                payment_method="",
            ))
        expense_fallback = []
        if float(daily_expense_total) > 0:
            expense_fallback.append(SimpleNamespace(
                subject=f"日常支出 (DailyEntry, {year}年)", amount_hkd=float(daily_expense_total),
                payment_method="",
            ))

        if income_fallback:
            income_rows = income_fallback
        if expense_fallback:
            expense_rows = expense_fallback

    # Build summary categorised by subject
    # Income: 收入(上年) CASH/CHQ, 收入(本年) CASH/CHQ, 會費, 香油, 其他收入
    income_sections = {
        "收入(上年)": [],
        "收入(本年)": [],
        "會費": [],
        "香油": [],
        "其他收入": [],
    }
    for row in income_rows:
        subj = row.subject or ""
        if "上年" in subj or "上屆" in subj:
            income_sections["收入(上年)"].append(row)
        elif "本年" in subj or "本屆" in subj or "今屆" in subj:
            income_sections["收入(本年)"].append(row)
        elif "會費" in subj:
            income_sections["會費"].append(row)
        elif "香油" in subj or "香火" in subj:
            income_sections["香油"].append(row)
        else:
            income_sections["其他收入"].append(row)

    income_totals = {}
    for section, rows in income_sections.items():
        income_totals[section] = sum(r.amount_hkd or 0 for r in rows)

    # Expense: group by subject category
    expense_sections = {}
    for row in expense_rows:
        cat = row.subject or "其他支出"
        if cat not in expense_sections:
            expense_sections[cat] = []
        expense_sections[cat].append(row)

    expense_totals = {}
    for section, rows in expense_sections.items():
        expense_totals[section] = sum(r.amount_hkd or 0 for r in rows)

    # PL table subtotal
    pl_total_income = sum(
        sum(r.amount_hkd or 0 for r in rows) for rows in income_sections.values()
    )
    total_expense = sum(
        sum(r.amount_hkd or 0 for r in rows) for rows in expense_sections.values()
    )

    # Year list — from actual data, not Edition table
    # Grand total income = PL static income + bidding receivable (real)
    total_income = pl_total_income + bidding_receivable

    # Year list
    years = [
        r[0]
        for r in db.session.query(func.distinct(PL.year))
        .order_by(PL.year.desc())
        .all()
    ]
    if not years:
        years = [
            r[0]
            for r in db.session.query(func.distinct(ThisYearItem.year))
            .order_by(ThisYearItem.year.desc())
            .all()
        ]
    # Default to latest year (from PL or ThisYearItem or hardcoded)
    if not year:
        year = years[0] if years else datetime.now().year

    # 應收金額: total unpaid bids for the year
    total_unpaid = (
        db.session.query(
            func.coalesce(func.sum(Bid.bid_amount - Bid.paid_amount), 0)
        )
        .filter(
            Bid.year == year,
            Bid.bid_amount > Bid.paid_amount,
        )
        .scalar()
    )

    return render_template(
        "pl/index.html",
        year=year,
        years=years,
        income_sections=income_sections,
        income_totals=income_totals,
        expense_sections=expense_sections,
        expense_totals=expense_totals,
        total_income=total_income,
        total_expense=total_expense,
        net_profit=total_income - total_expense,
        total_unpaid=float(total_unpaid),
        # New bidding income data
        bidding_receivable=bidding_receivable,
        bidding_received=bidding_received,
        bidding_outstanding=bidding_outstanding,
        pl_total_income=pl_total_income,
    )


@bp.route("/pl/export")
@login_required
def export_pl_excel():
    """Export P&L as Excel (.xlsx) with multi-year comparison."""
    from flask import request, Response
    from app.extensions import db
    from app.models.pl import PL
    from app.models.edition import Edition
    from app.models.this_year_item import ThisYearItem
    from app.models.live_income import LiveIncome
    from sqlalchemy import func
    import io

    years_param = request.args.get("years", "")
    if years_param:
        selected_years = [int(y.strip()) for y in years_param.split(",") if y.strip()]
    else:
        selected_years = [
            r[0]
            for r in db.session.query(func.distinct(PL.year))
            .order_by(PL.year.desc())
            .limit(3)
            .all()
        ]
        if not selected_years:
            selected_years = [
                r[0]
                for r in db.session.query(func.distinct(ThisYearItem.year))
                .order_by(ThisYearItem.year.desc())
                .limit(3)
                .all()
            ]

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill, numbers

    wb = Workbook()
    ws = wb.active
    ws.title = "損益表"

    # ── Styles ──
    title_font = Font(name="Microsoft JhengHei", size=14, bold=True)
    header_font = Font(name="Microsoft JhengHei", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    section_font = Font(name="Microsoft JhengHei", size=11, bold=True, color="1F4E79")
    section_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
    data_font = Font(name="Microsoft JhengHei", size=10)
    total_font = Font(name="Microsoft JhengHei", size=11, bold=True)
    total_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    money_fmt = '#,##0'

    # ── Title ──
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=1 + len(selected_years))
    title_cell = ws.cell(row=1, column=1, value="寶榮堂花炮會 — 損益表 (Profit & Loss)")
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal="center")

    # ── Headers ──
    headers = ["科目"] + [f"{y}年" for y in selected_years]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    # ── Helper: fetch totals per year per subject ──
    def get_subject_totals(pl_type):
        """Return dict[subject] = dict[year -> amount]"""
        rows = PL.query.filter(
            PL.pl_type == pl_type,
            PL.year.in_(selected_years),
        ).all()
        result = {}
        for r in rows:
            if r.subject not in result:
                result[r.subject] = {y: 0 for y in selected_years}
            result[r.subject][r.year] = (result[r.subject].get(r.year, 0) + (r.amount_hkd or 0))
        return result

    income_data = get_subject_totals("收入")
    expense_data = get_subject_totals("支出")

    # Add bidding income row for each year
    bidding_income_per_year = {}
    for y in selected_years:
        bid_amt = (
            db.session.query(func.coalesce(func.sum(ThisYearItem.bid_amount), 0))
            .filter(ThisYearItem.year == y, ThisYearItem.bid_amount > 0)
            .scalar()
        ) or 0
        bidding_income_per_year[y] = bid_amt

    row_num = 4

    # ── Income Section ──
    ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=1 + len(selected_years))
    cell = ws.cell(row=row_num, column=1, value="收入")
    cell.font = section_font
    cell.fill = section_fill
    cell.border = thin_border
    for c in range(2, 2 + len(selected_years)):
        ws.cell(row=row_num, column=c).fill = section_fill
        ws.cell(row=row_num, column=c).border = thin_border
    row_num += 1

    for subject, yearly in sorted(income_data.items()):
        ws.cell(row=row_num, column=1, value=subject).font = data_font
        ws.cell(row=row_num, column=1).border = thin_border
        for ci, y in enumerate(selected_years, 2):
            cell = ws.cell(row=row_num, column=ci, value=yearly.get(y, 0) or 0)
            cell.font = data_font
            cell.number_format = money_fmt
            cell.border = thin_border
        row_num += 1

    # Bidding income row (live from this_year_items)
    ws.cell(row=row_num, column=1, value="競投收入 (即時)").font = data_font
    ws.cell(row=row_num, column=1).border = thin_border
    ws.cell(row=row_num, column=1).font.italic = True
    for ci, y in enumerate(selected_years, 2):
        cell = ws.cell(row=row_num, column=ci, value=bidding_income_per_year.get(y, 0))
        cell.font = data_font
        cell.number_format = money_fmt
        cell.border = thin_border
    row_num += 1

    # Income total row (PL + bidding)
    income_year_totals = {}
    for subject, yearly in income_data.items():
        for y in selected_years:
            income_year_totals[y] = income_year_totals.get(y, 0) + (yearly.get(y, 0) or 0)
    for y in selected_years:
        income_year_totals[y] = income_year_totals.get(y, 0) + bidding_income_per_year.get(y, 0)

    ws.cell(row=row_num, column=1, value="收入合計").font = total_font
    ws.cell(row=row_num, column=1).fill = total_fill
    ws.cell(row=row_num, column=1).border = thin_border
    for ci, y in enumerate(selected_years, 2):
        cell = ws.cell(row=row_num, column=ci, value=income_year_totals.get(y, 0))
        cell.font = total_font
        cell.fill = total_fill
        cell.number_format = money_fmt
        cell.border = thin_border
    row_num += 2  # blank row

    # ── Expense Section ──
    ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=1 + len(selected_years))
    cell = ws.cell(row=row_num, column=1, value="支出")
    cell.font = section_font
    cell.fill = section_fill
    cell.border = thin_border
    for c in range(2, 2 + len(selected_years)):
        ws.cell(row=row_num, column=c).fill = section_fill
        ws.cell(row=row_num, column=c).border = thin_border
    row_num += 1

    for subject, yearly in sorted(expense_data.items()):
        ws.cell(row=row_num, column=1, value=subject).font = data_font
        ws.cell(row=row_num, column=1).border = thin_border
        for ci, y in enumerate(selected_years, 2):
            cell = ws.cell(row=row_num, column=ci, value=yearly.get(y, 0) or 0)
            cell.font = data_font
            cell.number_format = money_fmt
            cell.border = thin_border
        row_num += 1

    # Expense total row
    expense_year_totals = {}
    for subject, yearly in expense_data.items():
        for y in selected_years:
            expense_year_totals[y] = expense_year_totals.get(y, 0) + (yearly.get(y, 0) or 0)

    ws.cell(row=row_num, column=1, value="支出合計").font = total_font
    ws.cell(row=row_num, column=1).fill = total_fill
    ws.cell(row=row_num, column=1).border = thin_border
    for ci, y in enumerate(selected_years, 2):
        cell = ws.cell(row=row_num, column=ci, value=expense_year_totals.get(y, 0))
        cell.font = total_font
        cell.fill = total_fill
        cell.number_format = money_fmt
        cell.border = thin_border
    row_num += 1

    # ── Net Profit ──
    ws.cell(row=row_num, column=1, value="盈虧 (淨收入)").font = total_font
    ws.cell(row=row_num, column=1).fill = total_fill
    ws.cell(row=row_num, column=1).border = thin_border
    for ci, y in enumerate(selected_years, 2):
        net = (income_year_totals.get(y, 0) or 0) - (expense_year_totals.get(y, 0) or 0)
        cell = ws.cell(row=row_num, column=ci, value=net)
        cell.font = total_font
        cell.fill = total_fill
        cell.number_format = money_fmt
        cell.border = thin_border
    row_num += 1

    # Column widths
    ws.column_dimensions["A"].width = 30
    for ci in range(2, 2 + len(selected_years)):
        ws.column_dimensions[chr(64 + ci)].width = 18

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    years_label = "_".join(str(y) for y in selected_years)
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="pl_{years_label}.xlsx"',
        },
    )
