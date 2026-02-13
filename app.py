"""
SATHI 2026 Program Management System
Vision-Aid - Smart Assistive Technology for Holistic Inclusion
"""
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, Response, send_file)
from database import get_db, init_db, log_activity
from config import get_password, SECRET_KEY, PER_PAGE
from datetime import datetime
from functools import wraps
import os, io, csv

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit

with app.app_context():
    init_db()

# ─── AUTH ────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        pw = get_password()
        if pw and not session.get('authenticated'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    pw = get_password()
    if not pw:
        session['authenticated'] = True
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if request.form.get('password') == pw:
            session['authenticated'] = True
            return redirect(request.args.get('next', url_for('dashboard')))
        flash('Incorrect password. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# ─── HELPERS ─────────────────────────────────────────────────
def paginate(count, page):
    total_pages = max(1, (count + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    return page, PER_PAGE, (page - 1) * PER_PAGE, total_pages

def fmt_inr(val):
    """Format number as Indian Rupees."""
    if val is None: return '0'
    return f"{val:,.0f}"

app.jinja_env.globals['fmt_inr'] = fmt_inr

# ─── DASHBOARD ───────────────────────────────────────────────
@app.route('/')
@login_required
def dashboard():
    db = get_db()
    stats = {}
    for key, sql in [
        ('beneficiaries', "SELECT COUNT(*) FROM beneficiaries"),
        ('partners', "SELECT COUNT(*) FROM partners"),
        ('distributions', "SELECT COUNT(*) FROM distributions"),
        ('events', "SELECT COUNT(*) FROM events"),
        ('trainings', "SELECT COUNT(*) FROM training_records"),
        ('followups', "SELECT COUNT(*) FROM followups"),
    ]:
        stats[key] = db.execute(sql).fetchone()[0]
    stats['total_value'] = db.execute("SELECT COALESCE(SUM(dt.unit_cost),0) FROM distributions d JOIN device_types dt ON d.device_type_id=dt.id").fetchone()[0]
    stats['budget_spent'] = db.execute("SELECT COALESCE(SUM(spent),0) FROM budget").fetchone()[0]

    milestones = db.execute("SELECT * FROM milestones ORDER BY category, name").fetchall()
    device_breakdown = db.execute("SELECT dt.name, COUNT(d.id) as count FROM distributions d JOIN device_types dt ON d.device_type_id=dt.id GROUP BY dt.name ORDER BY count DESC").fetchall()
    upcoming_events = db.execute("SELECT e.*, p.name as partner_name FROM events e LEFT JOIN partners p ON e.partner_id=p.id WHERE e.event_date >= date('now') AND e.status != 'Cancelled' ORDER BY e.event_date LIMIT 5").fetchall()
    recent_activity = db.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 10").fetchall()
    db.close()
    return render_template('dashboard.html', stats=stats, milestones=milestones,
        device_breakdown=device_breakdown, upcoming_events=upcoming_events, recent_activity=recent_activity)

# ─── PARTNERS CRUD ───────────────────────────────────────────
@app.route('/partners')
@login_required
def partner_list():
    db = get_db()
    search = request.args.get('search', '')
    ptype = request.args.get('type', '')
    state = request.args.get('state', '')
    page = request.args.get('page', 1, type=int)
    where, params = [], []
    if search:
        where.append("(p.name LIKE ? OR p.contact_person LIKE ?)")
        params += [f'%{search}%', f'%{search}%']
    if ptype:
        where.append("p.type = ?"); params.append(ptype)
    if state:
        where.append("p.state = ?"); params.append(state)
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    count = db.execute(f"SELECT COUNT(*) FROM partners p {wsql}", params).fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    partners = db.execute(f"SELECT p.*, (SELECT COUNT(*) FROM beneficiaries b WHERE b.partner_id=p.id) as beneficiary_count FROM partners p {wsql} ORDER BY p.name LIMIT ? OFFSET ?", params+[per_page,offset]).fetchall()
    states = [r[0] for r in db.execute("SELECT DISTINCT state FROM partners WHERE state IS NOT NULL AND state!='' ORDER BY state").fetchall()]
    db.close()
    return render_template('partners/list.html', partners=partners, page=page, total_pages=total_pages, search=search, ptype=ptype, state=state, states=states)

@app.route('/partners/add', methods=['GET','POST'])
@login_required
def partner_add():
    if request.method == 'POST':
        db = get_db()
        db.execute("INSERT INTO partners (name,type,contact_person,email,phone,address,city,state,mou_status,mou_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (request.form['name'], request.form.get('type','School'), request.form.get('contact_person'),
             request.form.get('email'), request.form.get('phone'), request.form.get('address'),
             request.form.get('city'), request.form.get('state'), request.form.get('mou_status','Pending'),
             request.form.get('mou_date') or None, request.form.get('notes')))
        pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_activity(db, 'Created', 'Partner', pid, request.form['name'])
        db.close()
        flash(f'Partner "{request.form["name"]}" added!', 'success')
        return redirect(url_for('partner_list'))
    return render_template('partners/form.html', partner=None)

@app.route('/partners/<int:id>')
@login_required
def partner_detail(id):
    db = get_db()
    p = db.execute("SELECT * FROM partners WHERE id=?", (id,)).fetchone()
    if not p: flash('Partner not found.','danger'); db.close(); return redirect(url_for('partner_list'))
    bens = db.execute("SELECT * FROM beneficiaries WHERE partner_id=? ORDER BY name", (id,)).fetchall()
    evts = db.execute("SELECT * FROM events WHERE partner_id=? ORDER BY event_date DESC", (id,)).fetchall()
    db.close()
    return render_template('partners/detail.html', partner=p, beneficiaries=bens, events=evts)

@app.route('/partners/<int:id>/edit', methods=['GET','POST'])
@login_required
def partner_edit(id):
    db = get_db()
    p = db.execute("SELECT * FROM partners WHERE id=?", (id,)).fetchone()
    if not p: flash('Partner not found.','danger'); db.close(); return redirect(url_for('partner_list'))
    if request.method == 'POST':
        db.execute("UPDATE partners SET name=?,type=?,contact_person=?,email=?,phone=?,address=?,city=?,state=?,mou_status=?,mou_date=?,notes=?,updated_at=datetime('now') WHERE id=?",
            (request.form['name'], request.form.get('type','School'), request.form.get('contact_person'),
             request.form.get('email'), request.form.get('phone'), request.form.get('address'),
             request.form.get('city'), request.form.get('state'), request.form.get('mou_status','Pending'),
             request.form.get('mou_date') or None, request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Partner', id, request.form['name']); db.close()
        flash('Partner updated!', 'success'); return redirect(url_for('partner_detail', id=id))
    db.close()
    return render_template('partners/form.html', partner=p)

@app.route('/partners/<int:id>/delete', methods=['POST'])
@login_required
def partner_delete(id):
    db = get_db()
    p = db.execute("SELECT name FROM partners WHERE id=?", (id,)).fetchone()
    if p:
        db.execute("UPDATE beneficiaries SET partner_id=NULL WHERE partner_id=?", (id,))
        db.execute("UPDATE events SET partner_id=NULL WHERE partner_id=?", (id,))
        db.execute("DELETE FROM partners WHERE id=?", (id,))
        log_activity(db, 'Deleted', 'Partner', id, p['name'])
        flash(f'Partner deleted.', 'success')
    db.close()
    return redirect(url_for('partner_list'))

# ─── BENEFICIARIES CRUD ─────────────────────────────────────
@app.route('/beneficiaries')
@login_required
def beneficiary_list():
    db = get_db()
    search = request.args.get('search', ''); state = request.args.get('state', ''); category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    where, params = [], []
    if search: where.append("(b.name LIKE ? OR b.phone LIKE ? OR b.aadhar_no LIKE ?)"); params += [f'%{search}%']*3
    if state: where.append("b.state = ?"); params.append(state)
    if category: where.append("b.vision_category = ?"); params.append(category)
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    count = db.execute(f"SELECT COUNT(*) FROM beneficiaries b {wsql}", params).fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    beneficiaries = db.execute(f"SELECT b.*, p.name as partner_name, (SELECT COUNT(*) FROM distributions d WHERE d.beneficiary_id=b.id) as device_count FROM beneficiaries b LEFT JOIN partners p ON b.partner_id=p.id {wsql} ORDER BY b.name LIMIT ? OFFSET ?", params+[per_page,offset]).fetchall()
    states = [r[0] for r in db.execute("SELECT DISTINCT state FROM beneficiaries WHERE state IS NOT NULL AND state!='' ORDER BY state").fetchall()]
    db.close()
    return render_template('beneficiaries/list.html', beneficiaries=beneficiaries, page=page, total_pages=total_pages, search=search, state=state, category=category, states=states)

@app.route('/beneficiaries/add', methods=['GET','POST'])
@login_required
def beneficiary_add():
    db = get_db()
    if request.method == 'POST':
        db.execute("""INSERT INTO beneficiaries (name,age,gender,visual_acuity,vision_category,
            disability_certificate,partner_id,employment_status,class_or_year,education_qualification,
            aadhar_no,location,city,state,phone,email,smartphone_model,port_type,financial_status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request.form['name'], request.form.get('age',type=int), request.form.get('gender'),
             request.form.get('visual_acuity'), request.form.get('vision_category','Low Vision'),
             request.form.get('disability_certificate','N'), request.form.get('partner_id',type=int) or None,
             request.form.get('employment_status','Student'), request.form.get('class_or_year'),
             request.form.get('education_qualification'), request.form.get('aadhar_no'),
             request.form.get('location'), request.form.get('city'), request.form.get('state'),
             request.form.get('phone'), request.form.get('email'),
             request.form.get('smartphone_model'), request.form.get('port_type'),
             request.form.get('financial_status'), request.form.get('notes')))
        bid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_activity(db, 'Created', 'Beneficiary', bid, request.form['name']); db.close()
        flash(f'Beneficiary "{request.form["name"]}" registered!', 'success')
        return redirect(url_for('beneficiary_list'))
    partners = db.execute("SELECT id, name FROM partners ORDER BY name").fetchall()
    db.close()
    return render_template('beneficiaries/form.html', beneficiary=None, partners=partners)

@app.route('/beneficiaries/<int:id>')
@login_required
def beneficiary_detail(id):
    db = get_db()
    b = db.execute("SELECT b.*, p.name as partner_name FROM beneficiaries b LEFT JOIN partners p ON b.partner_id=p.id WHERE b.id=?", (id,)).fetchone()
    if not b: flash('Beneficiary not found.','danger'); db.close(); return redirect(url_for('beneficiary_list'))
    devices = db.execute("SELECT d.*, dt.name as device_name, dt.unit_cost, e.name as event_name FROM distributions d JOIN device_types dt ON d.device_type_id=dt.id LEFT JOIN events e ON d.event_id=e.id WHERE d.beneficiary_id=? ORDER BY d.distribution_date DESC", (id,)).fetchall()
    trainings = db.execute("SELECT t.*, dt.name as device_name FROM training_records t LEFT JOIN device_types dt ON t.device_type_id=dt.id WHERE t.beneficiary_id=? ORDER BY t.training_date DESC", (id,)).fetchall()
    followups = db.execute("SELECT * FROM followups WHERE beneficiary_id=? ORDER BY followup_date DESC", (id,)).fetchall()
    db.close()
    return render_template('beneficiaries/detail.html', b=b, devices=devices, trainings=trainings, followups=followups)

@app.route('/beneficiaries/<int:id>/edit', methods=['GET','POST'])
@login_required
def beneficiary_edit(id):
    db = get_db()
    b = db.execute("SELECT * FROM beneficiaries WHERE id=?", (id,)).fetchone()
    if not b: flash('Not found.','danger'); db.close(); return redirect(url_for('beneficiary_list'))
    if request.method == 'POST':
        db.execute("""UPDATE beneficiaries SET name=?,age=?,gender=?,visual_acuity=?,vision_category=?,
            disability_certificate=?,partner_id=?,employment_status=?,class_or_year=?,education_qualification=?,
            aadhar_no=?,location=?,city=?,state=?,phone=?,email=?,smartphone_model=?,port_type=?,
            financial_status=?,notes=?,updated_at=datetime('now') WHERE id=?""",
            (request.form['name'], request.form.get('age',type=int), request.form.get('gender'),
             request.form.get('visual_acuity'), request.form.get('vision_category','Low Vision'),
             request.form.get('disability_certificate','N'), request.form.get('partner_id',type=int) or None,
             request.form.get('employment_status','Student'), request.form.get('class_or_year'),
             request.form.get('education_qualification'), request.form.get('aadhar_no'),
             request.form.get('location'), request.form.get('city'), request.form.get('state'),
             request.form.get('phone'), request.form.get('email'),
             request.form.get('smartphone_model'), request.form.get('port_type'),
             request.form.get('financial_status'), request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Beneficiary', id, request.form['name']); db.close()
        flash('Beneficiary updated!', 'success'); return redirect(url_for('beneficiary_detail', id=id))
    partners = db.execute("SELECT id, name FROM partners ORDER BY name").fetchall()
    db.close()
    return render_template('beneficiaries/form.html', beneficiary=b, partners=partners)

@app.route('/beneficiaries/<int:id>/delete', methods=['POST'])
@login_required
def beneficiary_delete(id):
    db = get_db()
    b = db.execute("SELECT name FROM beneficiaries WHERE id=?", (id,)).fetchone()
    if b:
        for tbl in ['distributions','training_records','followups']:
            db.execute(f"DELETE FROM {tbl} WHERE beneficiary_id=?", (id,))
        db.execute("DELETE FROM beneficiaries WHERE id=?", (id,))
        log_activity(db, 'Deleted', 'Beneficiary', id, b['name'])
        flash('Beneficiary deleted.', 'success')
    db.close()
    return redirect(url_for('beneficiary_list'))

# ─── BENEFICIARY EXCEL UPLOAD / DOWNLOAD ────────────────────
@app.route('/beneficiaries/download-template')
@login_required
def beneficiary_download_template():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook()
    ws = wb.active
    ws.title = "Beneficiary data"
    # Title row
    ws.merge_cells('A1:P1')
    ws['A1'] = 'Data Collection - Master Template - for SVG and SP'
    ws['A1'].font = Font(bold=True, size=14)
    # Headers (row 2) - matching the original template
    headers = ['Sl No.', 'Beneficiary Name', 'Age', 'Gender',
        'Visual Acuity / Disability % (Blind/LV)', 'Govt Disability Certificate (Y/N)',
        'Partner Hospital / School Name', 'Employed/Unemployed/Job Seeker/Student/Homemaker',
        'Class/Yr of College (if student)', 'Educational Qualification', 'Aadhar No.',
        'Village/Town/District/City', 'Mobile Phone No.', 'E-mail Id',
        'Smart Phone Model', 'Port Type (Type C / Type B)']
    hdr_fill = PatternFill('solid', fgColor='1F4E79')
    hdr_font = Font(bold=True, color='FFFFFF', size=10)
    thin = Side(style='thin', color='999999')
    border = Border(top=thin, bottom=thin, left=thin, right=thin)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill
        cell.alignment = Alignment(wrap_text=True, vertical='center')
        cell.border = border
    # Column widths
    from openpyxl.utils import get_column_letter
    widths = [8, 25, 6, 10, 35, 18, 30, 28, 18, 22, 16, 25, 16, 25, 20, 18]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[2].height = 45
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name='SATHI_Beneficiary_Template.xlsx')

@app.route('/beneficiaries/download-data')
@login_required
def beneficiary_download_data():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    db = get_db()
    rows = db.execute("SELECT b.*, p.name as partner_name FROM beneficiaries b LEFT JOIN partners p ON b.partner_id=p.id ORDER BY b.id").fetchall()
    db.close()
    wb = Workbook(); ws = wb.active; ws.title = "Beneficiary data"
    ws.merge_cells('A1:P1')
    ws['A1'] = 'Data Collection - Master Template - for SVG and SP'
    ws['A1'].font = Font(bold=True, size=14)
    headers = ['Sl No.', 'Beneficiary Name', 'Age', 'Gender',
        'Visual Acuity / Disability % (Blind/LV)', 'Govt Disability Certificate (Y/N)',
        'Partner Hospital / School Name', 'Employment Status',
        'Class/Yr of College', 'Educational Qualification', 'Aadhar No.',
        'Village/Town/District/City', 'Mobile Phone No.', 'E-mail Id',
        'Smart Phone Model', 'Port Type']
    hdr_fill = PatternFill('solid', fgColor='1F4E79')
    hdr_font = Font(bold=True, color='FFFFFF', size=10)
    thin = Side(style='thin', color='999999')
    border = Border(top=thin, bottom=thin, left=thin, right=thin)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.alignment = Alignment(wrap_text=True, vertical='center'); cell.border = border
    from openpyxl.utils import get_column_letter as gcl
    widths = [8, 25, 6, 10, 35, 18, 30, 28, 18, 22, 16, 25, 16, 25, 20, 18]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[gcl(i)].width = w
    for idx, r in enumerate(rows, 1):
        ws.append([idx, r['name'], r['age'], r['gender'], r['visual_acuity'],
            r['disability_certificate'], r['partner_name'] or '', r['employment_status'],
            r['class_or_year'], r['education_qualification'], r['aadhar_no'],
            r['location'] or (f"{r['city'] or ''}, {r['state'] or ''}".strip(', ')),
            r['phone'], r['email'], r['smartphone_model'], r['port_type']])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'SATHI_Beneficiaries_{datetime.now().strftime("%Y%m%d")}.xlsx')

@app.route('/beneficiaries/upload', methods=['POST'])
@login_required
def beneficiary_upload():
    from openpyxl import load_workbook
    file = request.files.get('file')
    if not file or not file.filename:
        flash('No file selected.', 'danger'); return redirect(url_for('beneficiary_list'))
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Please upload an .xlsx or .xls file.', 'danger'); return redirect(url_for('beneficiary_list'))
    try:
        # Handle .xls conversion
        if file.filename.lower().endswith('.xls'):
            import tempfile, subprocess
            tmp = tempfile.NamedTemporaryFile(suffix='.xls', delete=False)
            file.save(tmp.name); tmp.close()
            subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', tmp.name, '--outdir', os.path.dirname(tmp.name)], capture_output=True, timeout=30)
            xlsx_path = tmp.name.replace('.xls', '.xlsx')
            wb = load_workbook(xlsx_path)
            os.unlink(tmp.name); os.unlink(xlsx_path)
        else:
            wb = load_workbook(file)

        ws = wb.active
        db = get_db()
        # Build partner lookup
        partner_map = {}
        for r in db.execute("SELECT id, name FROM partners").fetchall():
            partner_map[r['name'].lower().strip()] = r['id']
        imported = 0
        for row in ws.iter_rows(min_row=3, values_only=True):  # Skip title + header
            name = str(row[1]).strip() if row[1] else None
            if not name or name.lower() == 'none': continue
            partner_id = None
            if row[6]:
                pname = str(row[6]).strip().lower()
                partner_id = partner_map.get(pname)
            age = None
            if row[2]:
                try: age = int(row[2])
                except: pass
            db.execute("""INSERT INTO beneficiaries (name,age,gender,visual_acuity,disability_certificate,
                partner_id,employment_status,class_or_year,education_qualification,aadhar_no,
                location,phone,email,smartphone_model,port_type,vision_category) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, age, str(row[3]).strip() if row[3] else None,
                 str(row[4]).strip() if row[4] else None,
                 str(row[5]).strip() if row[5] else 'N',
                 partner_id,
                 str(row[7]).strip() if row[7] else 'Student',
                 str(row[8]).strip() if row[8] else None,
                 str(row[9]).strip() if row[9] else None,
                 str(row[10]).strip() if row[10] else None,
                 str(row[11]).strip() if row[11] else None,
                 str(row[12]).strip() if row[12] else None,
                 str(row[13]).strip() if row[13] else None,
                 str(row[14]).strip() if row[14] else None,
                 str(row[15]).strip() if row[15] else None,
                 'Blind' if row[4] and 'blind' in str(row[4]).lower() else 'Low Vision'))
            imported += 1
        log_activity(db, 'Uploaded', 'Beneficiary', None, f'{imported} beneficiaries imported')
        db.close()
        flash(f'Successfully imported {imported} beneficiaries!', 'success')
    except Exception as e:
        flash(f'Upload error: {str(e)}', 'danger')
    return redirect(url_for('beneficiary_list'))

# ─── EVENTS CRUD ─────────────────────────────────────────────
@app.route('/events')
@login_required
def event_list():
    db = get_db()
    status = request.args.get('status', ''); page = request.args.get('page', 1, type=int)
    where, params = [], []
    if status: where.append("e.status = ?"); params.append(status)
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    count = db.execute(f"SELECT COUNT(*) FROM events e {wsql}", params).fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    events = db.execute(f"SELECT e.*, p.name as partner_name, (SELECT COUNT(*) FROM distributions d WHERE d.event_id=e.id) as distribution_count FROM events e LEFT JOIN partners p ON e.partner_id=p.id {wsql} ORDER BY e.event_date DESC LIMIT ? OFFSET ?", params+[per_page,offset]).fetchall()
    db.close()
    return render_template('events/list.html', events=events, page=page, total_pages=total_pages, status=status)

@app.route('/events/add', methods=['GET','POST'])
@login_required
def event_add():
    db = get_db()
    if request.method == 'POST':
        db.execute("INSERT INTO events (name,event_type,partner_id,event_date,location,city,state,status,expected_beneficiaries,chief_guest,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (request.form['name'], request.form.get('event_type','Distribution'), request.form.get('partner_id',type=int) or None,
             request.form.get('event_date') or None, request.form.get('location'), request.form.get('city'), request.form.get('state'),
             request.form.get('status','Planned'), request.form.get('expected_beneficiaries',0,type=int), request.form.get('chief_guest'), request.form.get('notes')))
        eid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_activity(db, 'Created', 'Event', eid, request.form['name']); db.close()
        flash('Event created!', 'success'); return redirect(url_for('event_list'))
    partners = db.execute("SELECT id, name FROM partners ORDER BY name").fetchall(); db.close()
    return render_template('events/form.html', event=None, partners=partners)

@app.route('/events/<int:id>')
@login_required
def event_detail(id):
    db = get_db()
    e = db.execute("SELECT e.*, p.name as partner_name FROM events e LEFT JOIN partners p ON e.partner_id=p.id WHERE e.id=?", (id,)).fetchone()
    if not e: flash('Event not found.','danger'); db.close(); return redirect(url_for('event_list'))
    dists = db.execute("SELECT d.*, b.name as beneficiary_name, dt.name as device_name FROM distributions d JOIN beneficiaries b ON d.beneficiary_id=b.id JOIN device_types dt ON d.device_type_id=dt.id WHERE d.event_id=?", (id,)).fetchall()
    db.close()
    return render_template('events/detail.html', event=e, distributions=dists)

@app.route('/events/<int:id>/edit', methods=['GET','POST'])
@login_required
def event_edit(id):
    db = get_db()
    e = db.execute("SELECT * FROM events WHERE id=?", (id,)).fetchone()
    if not e: flash('Not found.','danger'); db.close(); return redirect(url_for('event_list'))
    if request.method == 'POST':
        db.execute("UPDATE events SET name=?,event_type=?,partner_id=?,event_date=?,location=?,city=?,state=?,status=?,expected_beneficiaries=?,actual_beneficiaries=?,chief_guest=?,notes=?,updated_at=datetime('now') WHERE id=?",
            (request.form['name'], request.form.get('event_type','Distribution'), request.form.get('partner_id',type=int) or None,
             request.form.get('event_date') or None, request.form.get('location'), request.form.get('city'), request.form.get('state'),
             request.form.get('status','Planned'), request.form.get('expected_beneficiaries',0,type=int),
             request.form.get('actual_beneficiaries',0,type=int), request.form.get('chief_guest'), request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Event', id, request.form['name']); db.close()
        flash('Event updated!', 'success'); return redirect(url_for('event_detail', id=id))
    partners = db.execute("SELECT id, name FROM partners ORDER BY name").fetchall(); db.close()
    return render_template('events/form.html', event=e, partners=partners)

@app.route('/events/<int:id>/delete', methods=['POST'])
@login_required
def event_delete(id):
    db = get_db()
    e = db.execute("SELECT name FROM events WHERE id=?", (id,)).fetchone()
    if e:
        db.execute("UPDATE distributions SET event_id=NULL WHERE event_id=?", (id,))
        db.execute("DELETE FROM events WHERE id=?", (id,))
        log_activity(db, 'Deleted', 'Event', id, e['name']); flash('Event deleted.', 'success')
    db.close(); return redirect(url_for('event_list'))

# ─── DISTRIBUTIONS ───────────────────────────────────────────
@app.route('/distributions')
@login_required
def distribution_list():
    db = get_db()
    page = request.args.get('page', 1, type=int); df = request.args.get('device_type', '')
    where, params = [], []
    if df: where.append("d.device_type_id = ?"); params.append(int(df))
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    count = db.execute(f"SELECT COUNT(*) FROM distributions d {wsql}", params).fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    dists = db.execute(f"SELECT d.*, b.name as beneficiary_name, dt.name as device_name, dt.unit_cost, e.name as event_name FROM distributions d JOIN beneficiaries b ON d.beneficiary_id=b.id JOIN device_types dt ON d.device_type_id=dt.id LEFT JOIN events e ON d.event_id=e.id {wsql} ORDER BY d.distribution_date DESC LIMIT ? OFFSET ?", params+[per_page,offset]).fetchall()
    device_types = db.execute("SELECT id, name FROM device_types ORDER BY name").fetchall()
    db.close()
    return render_template('distributions/list.html', distributions=dists, page=page, total_pages=total_pages, device_types=device_types, device_filter=df)

@app.route('/distributions/add', methods=['GET','POST'])
@login_required
def distribution_add():
    db = get_db()
    if request.method == 'POST':
        dt_id = request.form.get('device_type_id', type=int)
        db.execute("INSERT INTO distributions (beneficiary_id,device_type_id,event_id,serial_number,distribution_date,condition_at_delivery,notes) VALUES (?,?,?,?,?,?,?)",
            (request.form.get('beneficiary_id',type=int), dt_id, request.form.get('event_id',type=int) or None,
             request.form.get('serial_number'), request.form.get('distribution_date') or None,
             request.form.get('condition_at_delivery','New'), request.form.get('notes')))
        did = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        bn = db.execute("SELECT name FROM beneficiaries WHERE id=?", (request.form.get('beneficiary_id',type=int),)).fetchone()
        log_activity(db, 'Created', 'Distribution', did, bn['name'] if bn else ''); db.close()
        flash('Distribution recorded!', 'success'); return redirect(url_for('distribution_list'))
    bens = db.execute("SELECT id, name FROM beneficiaries ORDER BY name").fetchall()
    dts = db.execute("SELECT id, name FROM device_types ORDER BY name").fetchall()
    evts = db.execute("SELECT id, name FROM events ORDER BY event_date DESC").fetchall()
    db.close()
    return render_template('distributions/form.html', distribution=None, beneficiaries=bens, device_types=dts, events=evts)

@app.route('/distributions/<int:id>/edit', methods=['GET','POST'])
@login_required
def distribution_edit(id):
    db = get_db()
    dist = db.execute("SELECT * FROM distributions WHERE id=?", (id,)).fetchone()
    if not dist: flash('Not found.','danger'); db.close(); return redirect(url_for('distribution_list'))
    if request.method == 'POST':
        db.execute("UPDATE distributions SET beneficiary_id=?,device_type_id=?,event_id=?,serial_number=?,distribution_date=?,condition_at_delivery=?,notes=? WHERE id=?",
            (request.form.get('beneficiary_id',type=int), request.form.get('device_type_id',type=int),
             request.form.get('event_id',type=int) or None, request.form.get('serial_number'),
             request.form.get('distribution_date') or None, request.form.get('condition_at_delivery','New'), request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Distribution', id); db.close()
        flash('Distribution updated!', 'success'); return redirect(url_for('distribution_list'))
    bens = db.execute("SELECT id, name FROM beneficiaries ORDER BY name").fetchall()
    dts = db.execute("SELECT id, name FROM device_types ORDER BY name").fetchall()
    evts = db.execute("SELECT id, name FROM events ORDER BY event_date DESC").fetchall()
    db.close()
    return render_template('distributions/form.html', distribution=dist, beneficiaries=bens, device_types=dts, events=evts)

# ─── INVENTORY ───────────────────────────────────────────────
@app.route('/inventory')
@login_required
def inventory_list():
    db = get_db()
    stock = db.execute("SELECT dt.id, dt.name, dt.unit_cost, COALESCE(SUM(i.quantity),0) as total_stock, (SELECT COUNT(*) FROM distributions d WHERE d.device_type_id=dt.id) as distributed FROM device_types dt LEFT JOIN inventory i ON i.device_type_id=dt.id GROUP BY dt.id ORDER BY dt.name").fetchall()
    batches = db.execute("SELECT i.*, dt.name as device_name FROM inventory i JOIN device_types dt ON i.device_type_id=dt.id ORDER BY i.procurement_date DESC").fetchall()
    db.close()
    return render_template('inventory/list.html', stock_summary=stock, batches=batches)

@app.route('/inventory/add', methods=['GET','POST'])
@login_required
def inventory_add():
    db = get_db()
    if request.method == 'POST':
        qty = request.form.get('quantity',0,type=int); uc = request.form.get('unit_cost',0,type=float)
        db.execute("INSERT INTO inventory (device_type_id,batch_number,quantity,vendor,procurement_date,unit_cost,total_cost,notes) VALUES (?,?,?,?,?,?,?,?)",
            (request.form.get('device_type_id',type=int), request.form.get('batch_number'), qty, request.form.get('vendor'),
             request.form.get('procurement_date') or None, uc, qty*uc, request.form.get('notes')))
        log_activity(db, 'Created', 'Inventory', None, f"Batch: {request.form.get('batch_number')}"); db.close()
        flash('Inventory batch added!', 'success'); return redirect(url_for('inventory_list'))
    dts = db.execute("SELECT id, name, unit_cost FROM device_types ORDER BY name").fetchall(); db.close()
    return render_template('inventory/form.html', device_types=dts)

# ─── TRAINING ────────────────────────────────────────────────
@app.route('/training')
@login_required
def training_list():
    db = get_db(); page = request.args.get('page',1,type=int)
    count = db.execute("SELECT COUNT(*) FROM training_records").fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    recs = db.execute("SELECT t.*, b.name as beneficiary_name, dt.name as device_name FROM training_records t JOIN beneficiaries b ON t.beneficiary_id=b.id LEFT JOIN device_types dt ON t.device_type_id=dt.id ORDER BY t.training_date DESC LIMIT ? OFFSET ?", (per_page,offset)).fetchall()
    db.close()
    return render_template('training/list.html', records=recs, page=page, total_pages=total_pages)

@app.route('/training/add', methods=['GET','POST'])
@login_required
def training_add():
    db = get_db()
    if request.method == 'POST':
        db.execute("INSERT INTO training_records (beneficiary_id,device_type_id,training_type,trainer_name,training_date,duration_hours,status,completion_date,certificate_issued,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (request.form.get('beneficiary_id',type=int), request.form.get('device_type_id',type=int) or None,
             request.form.get('training_type','Device Usage'), request.form.get('trainer_name'),
             request.form.get('training_date') or None, request.form.get('duration_hours',1,type=float),
             request.form.get('status','Scheduled'), request.form.get('completion_date') or None,
             1 if request.form.get('certificate_issued') else 0, request.form.get('notes')))
        log_activity(db, 'Created', 'Training', None); db.close()
        flash('Training record added!', 'success'); return redirect(url_for('training_list'))
    bens = db.execute("SELECT id, name FROM beneficiaries ORDER BY name").fetchall()
    dts = db.execute("SELECT id, name FROM device_types ORDER BY name").fetchall(); db.close()
    return render_template('training/form.html', record=None, beneficiaries=bens, device_types=dts)

@app.route('/training/<int:id>/edit', methods=['GET','POST'])
@login_required
def training_edit(id):
    db = get_db()
    rec = db.execute("SELECT * FROM training_records WHERE id=?", (id,)).fetchone()
    if not rec: flash('Not found.','danger'); db.close(); return redirect(url_for('training_list'))
    if request.method == 'POST':
        db.execute("UPDATE training_records SET beneficiary_id=?,device_type_id=?,training_type=?,trainer_name=?,training_date=?,duration_hours=?,status=?,completion_date=?,certificate_issued=?,notes=? WHERE id=?",
            (request.form.get('beneficiary_id',type=int), request.form.get('device_type_id',type=int) or None,
             request.form.get('training_type','Device Usage'), request.form.get('trainer_name'),
             request.form.get('training_date') or None, request.form.get('duration_hours',1,type=float),
             request.form.get('status','Scheduled'), request.form.get('completion_date') or None,
             1 if request.form.get('certificate_issued') else 0, request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Training', id); db.close()
        flash('Training updated!', 'success'); return redirect(url_for('training_list'))
    bens = db.execute("SELECT id, name FROM beneficiaries ORDER BY name").fetchall()
    dts = db.execute("SELECT id, name FROM device_types ORDER BY name").fetchall(); db.close()
    return render_template('training/form.html', record=rec, beneficiaries=bens, device_types=dts)

# ─── FOLLOW-UPS ──────────────────────────────────────────────
@app.route('/followups')
@login_required
def followup_list():
    db = get_db(); page = request.args.get('page',1,type=int)
    count = db.execute("SELECT COUNT(*) FROM followups").fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    recs = db.execute("SELECT f.*, b.name as beneficiary_name FROM followups f JOIN beneficiaries b ON f.beneficiary_id=b.id ORDER BY f.followup_date DESC LIMIT ? OFFSET ?", (per_page,offset)).fetchall()
    db.close()
    return render_template('followups/list.html', records=recs, page=page, total_pages=total_pages)

@app.route('/followups/add', methods=['GET','POST'])
@login_required
def followup_add():
    db = get_db()
    if request.method == 'POST':
        db.execute("INSERT INTO followups (beneficiary_id,followup_date,followup_type,device_working,usage_frequency,satisfaction_rating,challenges,success_story,needs_support,conducted_by,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (request.form.get('beneficiary_id',type=int), request.form.get('followup_date') or None,
             request.form.get('followup_type','Phone Call'), 1 if request.form.get('device_working') else 0,
             request.form.get('usage_frequency','Daily'), request.form.get('satisfaction_rating',5,type=int),
             request.form.get('challenges'), request.form.get('success_story'),
             1 if request.form.get('needs_support') else 0, request.form.get('conducted_by'), request.form.get('notes')))
        log_activity(db, 'Created', 'Follow-up', None); db.close()
        flash('Follow-up recorded!', 'success'); return redirect(url_for('followup_list'))
    bens = db.execute("SELECT id, name FROM beneficiaries ORDER BY name").fetchall(); db.close()
    return render_template('followups/form.html', record=None, beneficiaries=bens)

@app.route('/followups/<int:id>/edit', methods=['GET','POST'])
@login_required
def followup_edit(id):
    db = get_db()
    rec = db.execute("SELECT * FROM followups WHERE id=?", (id,)).fetchone()
    if not rec: flash('Not found.','danger'); db.close(); return redirect(url_for('followup_list'))
    if request.method == 'POST':
        db.execute("UPDATE followups SET beneficiary_id=?,followup_date=?,followup_type=?,device_working=?,usage_frequency=?,satisfaction_rating=?,challenges=?,success_story=?,needs_support=?,conducted_by=?,notes=? WHERE id=?",
            (request.form.get('beneficiary_id',type=int), request.form.get('followup_date') or None,
             request.form.get('followup_type','Phone Call'), 1 if request.form.get('device_working') else 0,
             request.form.get('usage_frequency','Daily'), request.form.get('satisfaction_rating',5,type=int),
             request.form.get('challenges'), request.form.get('success_story'),
             1 if request.form.get('needs_support') else 0, request.form.get('conducted_by'), request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Follow-up', id); db.close()
        flash('Follow-up updated!', 'success'); return redirect(url_for('followup_list'))
    bens = db.execute("SELECT id, name FROM beneficiaries ORDER BY name").fetchall(); db.close()
    return render_template('followups/form.html', record=rec, beneficiaries=bens)

# ─── BUDGET ──────────────────────────────────────────────────
@app.route('/budget')
@login_required
def budget_list():
    db = get_db()
    summary = db.execute("SELECT category, SUM(amount) as total_amount, SUM(spent) as total_spent FROM budget GROUP BY category ORDER BY category").fetchall()
    entries = db.execute("SELECT * FROM budget ORDER BY created_at DESC").fetchall(); db.close()
    return render_template('budget/list.html', summary=summary, entries=entries)

@app.route('/budget/add', methods=['GET','POST'])
@login_required
def budget_add():
    if request.method == 'POST':
        db = get_db()
        db.execute("INSERT INTO budget (category,description,quarter,amount,spent,vendor,payment_status,payment_date,invoice_number,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (request.form.get('category'), request.form.get('description'), request.form.get('quarter'),
             request.form.get('amount',0,type=float), request.form.get('spent',0,type=float),
             request.form.get('vendor'), request.form.get('payment_status','Pending'),
             request.form.get('payment_date') or None, request.form.get('invoice_number'), request.form.get('notes')))
        log_activity(db, 'Created', 'Budget', None, request.form.get('category')); db.close()
        flash('Budget entry added!', 'success'); return redirect(url_for('budget_list'))
    return render_template('budget/form.html', entry=None)

@app.route('/budget/<int:id>/edit', methods=['GET','POST'])
@login_required
def budget_edit(id):
    db = get_db()
    entry = db.execute("SELECT * FROM budget WHERE id=?", (id,)).fetchone()
    if not entry: flash('Not found.','danger'); db.close(); return redirect(url_for('budget_list'))
    if request.method == 'POST':
        db.execute("UPDATE budget SET category=?,description=?,quarter=?,amount=?,spent=?,vendor=?,payment_status=?,payment_date=?,invoice_number=?,notes=? WHERE id=?",
            (request.form.get('category'), request.form.get('description'), request.form.get('quarter'),
             request.form.get('amount',0,type=float), request.form.get('spent',0,type=float),
             request.form.get('vendor'), request.form.get('payment_status','Pending'),
             request.form.get('payment_date') or None, request.form.get('invoice_number'), request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Budget', id); db.close()
        flash('Budget entry updated!', 'success'); return redirect(url_for('budget_list'))
    db.close(); return render_template('budget/form.html', entry=entry)

# ─── MILESTONES ──────────────────────────────────────────────
@app.route('/milestones')
@login_required
def milestone_list():
    db = get_db()
    ms = db.execute("SELECT * FROM milestones ORDER BY category, name").fetchall(); db.close()
    return render_template('milestones/list.html', milestones=ms)

@app.route('/milestones/<int:id>/edit', methods=['GET','POST'])
@login_required
def milestone_edit(id):
    db = get_db()
    m = db.execute("SELECT * FROM milestones WHERE id=?", (id,)).fetchone()
    if not m: flash('Not found.','danger'); db.close(); return redirect(url_for('milestone_list'))
    if request.method == 'POST':
        db.execute("UPDATE milestones SET name=?,category=?,target_value=?,current_value=?,unit=?,deadline=?,status=?,notes=?,updated_at=datetime('now') WHERE id=?",
            (request.form['name'], request.form.get('category'), request.form.get('target_value',0,type=int),
             request.form.get('current_value',0,type=int), request.form.get('unit','units'),
             request.form.get('deadline') or None, request.form.get('status','In Progress'), request.form.get('notes'), id))
        log_activity(db, 'Updated', 'Milestone', id, request.form['name']); db.close()
        flash('Milestone updated!', 'success'); return redirect(url_for('milestone_list'))
    db.close(); return render_template('milestones/form.html', milestone=m)

# ─── REPORTS ─────────────────────────────────────────────────
@app.route('/reports')
@login_required
def reports_index():
    return render_template('reports/index.html')

@app.route('/reports/distribution-summary')
@login_required
def report_distribution_summary():
    db = get_db()
    data = db.execute("SELECT dt.name, dt.unit_cost, COUNT(d.id) as count, COUNT(d.id)*dt.unit_cost as total_value FROM device_types dt LEFT JOIN distributions d ON d.device_type_id=dt.id GROUP BY dt.id ORDER BY count DESC").fetchall()
    db.close()
    return render_template('reports/distribution_summary.html', data=data)

@app.route('/reports/state-wise')
@login_required
def report_state_wise():
    db = get_db()
    data = db.execute("SELECT b.state, COUNT(DISTINCT b.id) as beneficiary_count, COUNT(d.id) as device_count FROM beneficiaries b LEFT JOIN distributions d ON d.beneficiary_id=b.id WHERE b.state IS NOT NULL AND b.state!='' GROUP BY b.state ORDER BY beneficiary_count DESC").fetchall()
    db.close()
    return render_template('reports/state_wise.html', data=data)

@app.route('/reports/impact')
@login_required
def report_impact():
    db = get_db()
    avg_sat = db.execute("SELECT AVG(satisfaction_rating) as avg FROM followups").fetchone()
    usage = db.execute("SELECT usage_frequency, COUNT(*) as count FROM followups GROUP BY usage_frequency ORDER BY count DESC").fetchall()
    stories = db.execute("SELECT f.success_story, b.name, f.followup_date FROM followups f JOIN beneficiaries b ON f.beneficiary_id=b.id WHERE f.success_story IS NOT NULL AND f.success_story!='' ORDER BY f.followup_date DESC LIMIT 10").fetchall()
    db.close()
    return render_template('reports/impact.html', avg_satisfaction=avg_sat, usage=usage, stories=stories)

@app.route('/reports/partner-performance')
@login_required
def report_partner_performance():
    db = get_db()
    data = db.execute("SELECT p.name, p.type, p.state, COUNT(DISTINCT b.id) as beneficiary_count, (SELECT COUNT(*) FROM events e WHERE e.partner_id=p.id) as event_count, (SELECT COUNT(*) FROM distributions d JOIN beneficiaries b2 ON d.beneficiary_id=b2.id WHERE b2.partner_id=p.id) as distribution_count FROM partners p LEFT JOIN beneficiaries b ON b.partner_id=p.id GROUP BY p.id ORDER BY beneficiary_count DESC").fetchall()
    db.close()
    return render_template('reports/partner_performance.html', data=data)

# ─── EXPORT CSV ──────────────────────────────────────────────
@app.route('/reports/export/<string:report_type>')
@login_required
def report_export(report_type):
    db = get_db(); si = io.StringIO(); writer = csv.writer(si)
    if report_type == 'beneficiaries':
        writer.writerow(['Name','Age','Gender','Visual Acuity','Category','Disability Cert','Partner','Employment','Education','Aadhar','Location','Phone','Email'])
        for r in db.execute("SELECT b.*, p.name as pn FROM beneficiaries b LEFT JOIN partners p ON b.partner_id=p.id ORDER BY b.name").fetchall():
            writer.writerow([r['name'],r['age'],r['gender'],r['visual_acuity'],r['vision_category'],r['disability_certificate'],r['pn'],r['employment_status'],r['education_qualification'],r['aadhar_no'],r['location'],r['phone'],r['email']])
    elif report_type == 'distributions':
        writer.writerow(['Beneficiary','Device','Serial Number','Date','Event','Condition'])
        for r in db.execute("SELECT b.name, dt.name as dn, d.serial_number, d.distribution_date, e.name as en, d.condition_at_delivery FROM distributions d JOIN beneficiaries b ON d.beneficiary_id=b.id JOIN device_types dt ON d.device_type_id=dt.id LEFT JOIN events e ON d.event_id=e.id ORDER BY d.distribution_date DESC").fetchall():
            writer.writerow(list(r))
    elif report_type == 'partners':
        writer.writerow(['Name','Type','Contact','City','State','MoU Status'])
        for r in db.execute("SELECT name,type,contact_person,city,state,mou_status FROM partners ORDER BY name").fetchall():
            writer.writerow(list(r))
    else:
        db.close(); flash('Unknown report type.','danger'); return redirect(url_for('reports_index'))
    db.close()
    return Response(si.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=sathi_{report_type}_{datetime.now().strftime("%Y%m%d")}.csv'})

# ─── GENERATE WORD REPORT ────────────────────────────────────
@app.route('/reports/generate-word', methods=['POST'])
@login_required
def generate_word_report():
    from report_generator import generate_quarterly_report, generate_annual_report
    report_type = request.form.get('report_type', 'quarterly')
    quarter = request.form.get('quarter', 'Q1')
    year = request.form.get('year', '2026')
    try:
        if report_type == 'annual':
            buf = generate_annual_report(year)
            fname = f'SATHI_{year}_Annual_Report.docx'
        else:
            buf = generate_quarterly_report(quarter, year)
            fname = f'SATHI_{quarter}_{year}_Report.docx'
        return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True, download_name=fname)
    except Exception as e:
        flash(f'Report generation error: {str(e)}', 'danger')
        return redirect(url_for('reports_index'))

# ─── GENERATE EXCEL REPORT ───────────────────────────────────
@app.route('/reports/generate-excel', methods=['POST'])
@login_required
def generate_excel_report():
    from report_generator import generate_excel_report
    report_type = request.form.get('excel_report_type', 'distributions')
    try:
        buf = generate_excel_report(report_type)
        fname = f'SATHI_{report_type}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True, download_name=fname)
    except Exception as e:
        flash(f'Export error: {str(e)}', 'danger')
        return redirect(url_for('reports_index'))

# ─── ACTIVITY LOG ────────────────────────────────────────────
@app.route('/activity-log')
@login_required
def activity_log():
    db = get_db(); page = request.args.get('page',1,type=int)
    count = db.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    page, per_page, offset, total_pages = paginate(count, page)
    logs = db.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ? OFFSET ?", (per_page,offset)).fetchall()
    db.close()
    return render_template('activity_log.html', logs=logs, page=page, total_pages=total_pages)

# ─── RUN ─────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
