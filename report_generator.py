"""
SATHI 2026 - Report Generator
Generates Word (.docx) quarterly/annual reports and Excel (.xlsx) data exports.
"""
import io
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from database import get_db

QUARTER_MONTHS = {
    'Q1': ('January, February, March', [1,2,3]),
    'Q2': ('April, May, June', [4,5,6]),
    'Q3': ('July, August, September', [7,8,9]),
    'Q4': ('October, November, December', [10,11,12]),
}

def _style_doc(doc):
    """Apply consistent styling to a Word document."""
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    for hs in ['Heading 1', 'Heading 2', 'Heading 3']:
        if hs in doc.styles:
            doc.styles[hs].font.name = 'Calibri'
            doc.styles[hs].font.color.rgb = RGBColor(0x0D, 0x5C, 0x63)

def _add_title_page(doc, quarter, year, report_type='quarterly'):
    """Add title page matching SATHI report format."""
    for _ in range(3):
        doc.add_paragraph('')
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('PROJECT SATHI')
    r.bold = True; r.font.size = Pt(28); r.font.color.rgb = RGBColor(0x0D, 0x5C, 0x63)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run('Smart Assistive Technology for Holistic Inclusion')
    r2.font.size = Pt(16); r2.font.color.rgb = RGBColor(0x0D, 0x5C, 0x63)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run('of the Visually Impaired')
    r3.font.size = Pt(14); r3.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_paragraph('')
    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if report_type == 'annual':
        r4 = p4.add_run(f'Annual Summary Report for Calendar Year {year}')
    else:
        months = QUARTER_MONTHS.get(quarter, ('', []))[0]
        r4 = p4.add_run(f'Quarterly Progress Report for {quarter}, {year} ({months} {year})')
    r4.bold = True; r4.font.size = Pt(13)

    doc.add_paragraph('')
    p5 = doc.add_paragraph()
    p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p5.add_run('Submitted by: ').font.size = Pt(11)
    r5 = p5.add_run('Ramakrishna Raju, Volunteer Executive Director, Vision-Aid')
    r5.font.size = Pt(11)

    p6 = doc.add_paragraph()
    p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p6.add_run(f'Date: {datetime.now().strftime("%B %d, %Y")}').font.size = Pt(11)

    doc.add_page_break()

def _add_device_table(doc, db, title="Device Distribution Summary"):
    """Add device distribution summary table."""
    doc.add_heading(title, level=2)
    data = db.execute("""
        SELECT dt.name, dt.unit_cost,
            (SELECT COUNT(*) FROM distributions d WHERE d.device_type_id = dt.id) as distributed,
            dt.unit_cost * (SELECT COUNT(*) FROM distributions d WHERE d.device_type_id = dt.id) as total_value
        FROM device_types dt ORDER BY distributed DESC
    """).fetchall()

    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ['Device', 'Unit Cost (INR)', 'Qty Distributed', 'Total Value (INR)']
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs: r.bold = True; r.font.size = Pt(10)

    total_qty = 0; total_val = 0
    for row in data:
        cells = table.add_row().cells
        cells[0].text = row['name']
        cells[1].text = f"{row['unit_cost']:,.0f}"
        cells[2].text = str(row['distributed'])
        cells[3].text = f"{row['total_value']:,.0f}"
        total_qty += row['distributed']
        total_val += row['total_value']

    # Total row
    cells = table.add_row().cells
    cells[0].text = 'TOTAL'
    cells[2].text = str(total_qty)
    cells[3].text = f"{total_val:,.0f}"
    for i in range(4):
        for p in cells[i].paragraphs:
            for r in p.runs: r.bold = True
    return total_qty, total_val

def _add_beneficiary_summary(doc, db):
    """Add beneficiary statistics section."""
    doc.add_heading('Beneficiary Summary', level=2)

    stats = {
        'total': db.execute("SELECT COUNT(*) FROM beneficiaries").fetchone()[0],
        'male': db.execute("SELECT COUNT(*) FROM beneficiaries WHERE gender='Male'").fetchone()[0],
        'female': db.execute("SELECT COUNT(*) FROM beneficiaries WHERE gender='Female'").fetchone()[0],
        'blind': db.execute("SELECT COUNT(*) FROM beneficiaries WHERE vision_category='Blind'").fetchone()[0],
        'low_vision': db.execute("SELECT COUNT(*) FROM beneficiaries WHERE vision_category='Low Vision'").fetchone()[0],
        'students': db.execute("SELECT COUNT(*) FROM beneficiaries WHERE employment_status='Student'").fetchone()[0],
    }

    doc.add_paragraph(f"Total beneficiaries registered: {stats['total']}")
    doc.add_paragraph(f"Gender breakdown: {stats['male']} Male, {stats['female']} Female")
    doc.add_paragraph(f"Vision category: {stats['blind']} Blind, {stats['low_vision']} Low Vision")
    doc.add_paragraph(f"Students: {stats['students']}")

    # State-wise table
    state_data = db.execute("SELECT state, COUNT(*) as cnt FROM beneficiaries WHERE state IS NOT NULL AND state!='' GROUP BY state ORDER BY cnt DESC").fetchall()
    if state_data:
        doc.add_heading('State-wise Distribution', level=3)
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Light Grid Accent 1'
        table.rows[0].cells[0].text = 'State'
        table.rows[0].cells[1].text = 'Beneficiaries'
        for r in table.rows[0].cells:
            for p in r.paragraphs:
                for run in p.runs: run.bold = True
        for row in state_data:
            cells = table.add_row().cells
            cells[0].text = row['state']
            cells[1].text = str(row['cnt'])

def _add_partner_summary(doc, db):
    """Add partner summary section."""
    doc.add_heading('Partner Organizations', level=2)
    partners = db.execute("SELECT p.name, p.type, p.state, p.mou_status, COUNT(b.id) as ben_count FROM partners p LEFT JOIN beneficiaries b ON b.partner_id=p.id GROUP BY p.id ORDER BY ben_count DESC").fetchall()
    doc.add_paragraph(f"Total partner organizations: {len(partners)}")

    if partners:
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Light Grid Accent 1'
        for i, h in enumerate(['Partner Name', 'Type', 'State', 'MoU Status', 'Beneficiaries']):
            table.rows[0].cells[i].text = h
            for p in table.rows[0].cells[i].paragraphs:
                for r in p.runs: r.bold = True
        for row in partners:
            cells = table.add_row().cells
            cells[0].text = row['name']
            cells[1].text = row['type'] or ''
            cells[2].text = row['state'] or ''
            cells[3].text = row['mou_status'] or ''
            cells[4].text = str(row['ben_count'])

def _add_impact_section(doc, db):
    """Add impact stories and satisfaction data."""
    doc.add_heading('Impact Assessment', level=2)

    avg = db.execute("SELECT AVG(satisfaction_rating) as avg, COUNT(*) as cnt FROM followups").fetchone()
    if avg['cnt'] > 0:
        doc.add_paragraph(f"Follow-ups conducted: {avg['cnt']}")
        doc.add_paragraph(f"Average satisfaction rating: {avg['avg']:.1f} / 10")

    stories = db.execute("SELECT f.success_story, b.name FROM followups f JOIN beneficiaries b ON f.beneficiary_id=b.id WHERE f.success_story IS NOT NULL AND f.success_story!='' ORDER BY f.followup_date DESC LIMIT 5").fetchall()
    if stories:
        doc.add_heading('Success Stories', level=3)
        for s in stories:
            p = doc.add_paragraph()
            r = p.add_run(f"{s['name']}: ")
            r.bold = True
            p.add_run(s['success_story'])

def _add_milestone_section(doc, db):
    """Add milestones progress section."""
    doc.add_heading('2026 Milestones Progress', level=2)
    milestones = db.execute("SELECT * FROM milestones ORDER BY category, name").fetchall()
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Light Grid Accent 1'
    for i, h in enumerate(['Milestone', 'Target', 'Current', 'Unit', '% Complete']):
        table.rows[0].cells[i].text = h
        for p in table.rows[0].cells[i].paragraphs:
            for r in p.runs: r.bold = True
    for m in milestones:
        cells = table.add_row().cells
        cells[0].text = m['name']
        cells[1].text = str(m['target_value'])
        cells[2].text = str(m['current_value'])
        cells[3].text = m['unit']
        pct = (m['current_value'] / m['target_value'] * 100) if m['target_value'] > 0 else 0
        cells[4].text = f"{pct:.0f}%"

def _add_budget_section(doc, db):
    """Add financial summary."""
    doc.add_heading('Financial Summary', level=2)
    summary = db.execute("SELECT category, SUM(amount) as amt, SUM(spent) as sp FROM budget GROUP BY category ORDER BY category").fetchall()
    if summary:
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Light Grid Accent 1'
        for i, h in enumerate(['Category', 'Allocated (INR)', 'Spent (INR)', 'Remaining (INR)']):
            table.rows[0].cells[i].text = h
            for p in table.rows[0].cells[i].paragraphs:
                for r in p.runs: r.bold = True
        total_a = total_s = 0
        for row in summary:
            cells = table.add_row().cells
            cells[0].text = row['category']
            cells[1].text = f"{row['amt']:,.0f}"
            cells[2].text = f"{row['sp']:,.0f}"
            cells[3].text = f"{row['amt']-row['sp']:,.0f}"
            total_a += row['amt']; total_s += row['sp']
        cells = table.add_row().cells
        cells[0].text = 'TOTAL'
        cells[1].text = f"{total_a:,.0f}"
        cells[2].text = f"{total_s:,.0f}"
        cells[3].text = f"{total_a-total_s:,.0f}"
        for i in range(4):
            for p in cells[i].paragraphs:
                for r in p.runs: r.bold = True
    else:
        doc.add_paragraph("No budget entries recorded yet.")

# ─── PUBLIC API ──────────────────────────────────────────────

def generate_quarterly_report(quarter, year):
    """Generate a quarterly progress report in Word format."""
    doc = Document()
    _style_doc(doc)
    _add_title_page(doc, quarter, year, 'quarterly')

    db = get_db()
    doc.add_heading('Summary', level=1)
    total_ben = db.execute("SELECT COUNT(*) FROM beneficiaries").fetchone()[0]
    total_dist = db.execute("SELECT COUNT(*) FROM distributions").fetchone()[0]
    total_partners = db.execute("SELECT COUNT(*) FROM partners").fetchone()[0]
    doc.add_paragraph(
        f"This report covers the progress of Project SATHI during {quarter} {year}. "
        f"As of the reporting date, the program has registered {total_ben} beneficiaries, "
        f"distributed {total_dist} assistive devices through {total_partners} partner organizations."
    )
    doc.add_paragraph('')

    # Key Milestones
    doc.add_heading(f'{quarter} Key Milestones', level=1)
    _add_device_table(doc, db, 'Device Distribution Progress')
    doc.add_paragraph('')

    _add_beneficiary_summary(doc, db)
    doc.add_page_break()

    _add_partner_summary(doc, db)
    doc.add_paragraph('')

    _add_impact_section(doc, db)
    doc.add_page_break()

    _add_milestone_section(doc, db)
    doc.add_paragraph('')

    _add_budget_section(doc, db)
    db.close()

    buf = io.BytesIO()
    doc.save(buf); buf.seek(0)
    return buf

def generate_annual_report(year):
    """Generate an annual summary report in Word format."""
    doc = Document()
    _style_doc(doc)
    _add_title_page(doc, 'Annual', year, 'annual')

    db = get_db()
    doc.add_heading('Annual Summary', level=1)
    total_ben = db.execute("SELECT COUNT(*) FROM beneficiaries").fetchone()[0]
    total_dist = db.execute("SELECT COUNT(*) FROM distributions").fetchone()[0]
    total_partners = db.execute("SELECT COUNT(*) FROM partners").fetchone()[0]
    total_events = db.execute("SELECT COUNT(*) FROM events WHERE status='Completed'").fetchone()[0]
    total_trainings = db.execute("SELECT COUNT(*) FROM training_records WHERE status='Completed'").fetchone()[0]

    doc.add_paragraph(
        f"Project SATHI completed its {year} program year with significant achievements. "
        f"The program registered {total_ben} beneficiaries across multiple states, "
        f"distributed {total_dist} assistive devices, conducted {total_events} events, "
        f"and completed {total_trainings} training sessions through {total_partners} partner organizations."
    )
    doc.add_paragraph('')

    doc.add_heading('Device Distribution Summary', level=1)
    _add_device_table(doc, db, f'{year} Device Distribution')
    doc.add_paragraph('')

    _add_beneficiary_summary(doc, db)
    doc.add_page_break()

    _add_partner_summary(doc, db)
    doc.add_paragraph('')

    _add_impact_section(doc, db)
    doc.add_page_break()

    _add_milestone_section(doc, db)
    doc.add_paragraph('')

    _add_budget_section(doc, db)
    db.close()

    buf = io.BytesIO()
    doc.save(buf); buf.seek(0)
    return buf

def generate_excel_report(report_type):
    """Generate a formatted Excel report."""
    db = get_db()
    wb = Workbook()
    ws = wb.active
    hdr_fill = PatternFill('solid', fgColor='0D5C63')
    hdr_font = Font(bold=True, color='FFFFFF', size=10, name='Arial')
    data_font = Font(size=10, name='Arial')
    thin = Side(style='thin', color='CCCCCC')
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    def write_header(ws, headers, widths):
        for col, (h, w) in enumerate(zip(headers, widths), 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = hdr_font; cell.fill = hdr_fill
            cell.alignment = Alignment(wrap_text=True, vertical='center')
            cell.border = border
            ws.column_dimensions[cell.column_letter].width = w
        ws.row_dimensions[1].height = 30

    if report_type == 'distributions':
        ws.title = 'Distributions'
        headers = ['Beneficiary','Device','Serial #','Date','Event','Condition','Value (INR)']
        widths = [25,25,18,14,25,12,14]
        write_header(ws, headers, widths)
        rows = db.execute("SELECT b.name, dt.name as dn, d.serial_number, d.distribution_date, e.name as en, d.condition_at_delivery, dt.unit_cost FROM distributions d JOIN beneficiaries b ON d.beneficiary_id=b.id JOIN device_types dt ON d.device_type_id=dt.id LEFT JOIN events e ON d.event_id=e.id ORDER BY d.distribution_date DESC").fetchall()
        for i, r in enumerate(rows, 2):
            for j, v in enumerate([r['name'], r['dn'], r['serial_number'], r['distribution_date'], r['en'], r['condition_at_delivery'], r['unit_cost']], 1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.font = data_font; cell.border = border

    elif report_type == 'beneficiaries':
        ws.title = 'Beneficiaries'
        headers = ['Sl No.','Name','Age','Gender','Visual Acuity','Disability Cert','Partner','Employment','Class/Year','Education','Aadhar','Location','Phone','Email','Smartphone','Port Type']
        widths = [8,25,6,10,30,14,25,20,14,20,16,22,14,22,18,14]
        write_header(ws, headers, widths)
        rows = db.execute("SELECT b.*, p.name as pn FROM beneficiaries b LEFT JOIN partners p ON b.partner_id=p.id ORDER BY b.id").fetchall()
        for i, r in enumerate(rows, 2):
            vals = [i-1, r['name'], r['age'], r['gender'], r['visual_acuity'], r['disability_certificate'],
                    r['pn'], r['employment_status'], r['class_or_year'], r['education_qualification'],
                    r['aadhar_no'], r['location'], r['phone'], r['email'], r['smartphone_model'], r['port_type']]
            for j, v in enumerate(vals, 1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.font = data_font; cell.border = border

    elif report_type == 'partners':
        ws.title = 'Partners'
        headers = ['Name','Type','Contact Person','Email','Phone','City','State','MoU Status','Beneficiaries']
        widths = [30,14,20,25,16,16,16,14,14]
        write_header(ws, headers, widths)
        rows = db.execute("SELECT p.*, (SELECT COUNT(*) FROM beneficiaries b WHERE b.partner_id=p.id) as bc FROM partners p ORDER BY p.name").fetchall()
        for i, r in enumerate(rows, 2):
            for j, v in enumerate([r['name'],r['type'],r['contact_person'],r['email'],r['phone'],r['city'],r['state'],r['mou_status'],r['bc']], 1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.font = data_font; cell.border = border

    elif report_type == 'inventory':
        ws.title = 'Inventory'
        headers = ['Device','In Stock','Distributed','Unit Cost','Stock Value']
        widths = [30,12,14,14,16]
        write_header(ws, headers, widths)
        rows = db.execute("SELECT dt.name, dt.unit_cost, COALESCE(SUM(i.quantity),0) as stock, (SELECT COUNT(*) FROM distributions d WHERE d.device_type_id=dt.id) as dist FROM device_types dt LEFT JOIN inventory i ON i.device_type_id=dt.id GROUP BY dt.id ORDER BY dt.name").fetchall()
        for i, r in enumerate(rows, 2):
            for j, v in enumerate([r['name'], r['stock'], r['dist'], r['unit_cost'], r['stock']*r['unit_cost']], 1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.font = data_font; cell.border = border

    elif report_type == 'budget':
        ws.title = 'Budget'
        headers = ['Category','Description','Quarter','Allocated','Spent','Remaining','Vendor','Status']
        widths = [22,30,12,14,14,14,22,12]
        write_header(ws, headers, widths)
        rows = db.execute("SELECT * FROM budget ORDER BY category, quarter").fetchall()
        for i, r in enumerate(rows, 2):
            for j, v in enumerate([r['category'],r['description'],r['quarter'],r['amount'],r['spent'],r['amount']-r['spent'],r['vendor'],r['payment_status']], 1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.font = data_font; cell.border = border
    else:
        ws['A1'] = 'Unknown report type'

    db.close()
    ws.auto_filter.ref = ws.dimensions
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf
