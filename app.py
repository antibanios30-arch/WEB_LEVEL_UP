import os
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import ff_control

app = Flask(__name__)
app.secret_key = "DBL_TEAM_SECRET_2026_XSHAZZ"

OWNER_TELEGRAM = "@DBL_0"
OWNER_ID = 7547557639

def get_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        telegram_id TEXT DEFAULT '',
        created_by TEXT DEFAULT 'admin',
        subscription_days INTEGER DEFAULT 0,
        subscription_expires TEXT DEFAULT NULL,
        ff_uid TEXT DEFAULT '',
        ff_password TEXT DEFAULT '',
        plan TEXT DEFAULT 'free',
        note TEXT DEFAULT '',
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_login TEXT DEFAULT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ff_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        password TEXT NOT NULL,
        region TEXT DEFAULT 'IND',
        assigned_user_id INTEGER DEFAULT NULL,
        status TEXT DEFAULT 'available',
        note TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        by_who TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    # Create default admin
    try:
        pw = hashlib.sha256("911".encode()).hexdigest()
        conn.execute("INSERT INTO users (username, password, is_admin, plan) VALUES (?, ?, 1, 'admin')",
                     ("dblteam@dbl.com", pw))
    except:
        pass
    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        if not user or not user['is_admin']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def is_sub_active(user):
    if user['is_admin']:
        return True
    if user['plan'] == 'lifetime':
        return True
    if not user['subscription_expires']:
        return False
    try:
        exp = datetime.strptime(user['subscription_expires'], "%Y-%m-%d %H:%M:%S")
        return datetime.now() < exp
    except:
        try:
            exp = datetime.strptime(user['subscription_expires'], "%Y-%m-%d")
            return datetime.now() < exp
        except:
            return False

def log_action(action, details='', by_who='system'):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (action, details, by_who) VALUES (?,?,?)",
                 (action, details, by_who))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0]
    active_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0 AND is_banned=0").fetchone()[0]
    total_accounts = conn.execute("SELECT COUNT(*) FROM ff_accounts").fetchone()[0]
    conn.close()
    user = None
    if 'user_id' in session:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
    return render_template('index.html', total_users=total_users,
                           active_users=active_users, total_accounts=total_accounts, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                            (username, hash_pw(password))).fetchone()
        conn.close()
        if user:
            if user['is_banned']:
                flash('حسابك موقوف. تواصل مع الأدمن عبر تيليقرام.', 'error')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            conn = get_db()
            conn.execute("UPDATE users SET last_login=? WHERE id=?",
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user['id']))
            conn.commit()
            conn.close()
            log_action("login", f"User {username} logged in", username)
            return redirect(url_for('dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    ff_account = None
    if user['is_admin'] == 0:
        ff_account = conn.execute(
            "SELECT * FROM ff_accounts WHERE assigned_user_id=? AND status='assigned'",
            (session['user_id'],)).fetchone()
    logs = conn.execute(
        "SELECT * FROM activity_log WHERE by_who=? ORDER BY created_at DESC LIMIT 10",
        (user['username'],)).fetchall()
    conn.close()
    sub_active = is_sub_active(user)
    return render_template('dashboard.html', user=user, ff_account=ff_account,
                           sub_active=sub_active, logs=logs)

@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE is_admin=0 ORDER BY created_at DESC").fetchall()
    ff_accounts = conn.execute("SELECT f.*, u.username as owner FROM ff_accounts f LEFT JOIN users u ON f.assigned_user_id=u.id ORDER BY f.created_at DESC").fetchall()
    logs = conn.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 50").fetchall()
    stats = {
        'total_users': conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0],
        'active_users': conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0 AND is_banned=0").fetchone()[0],
        'ff_accounts': conn.execute("SELECT COUNT(*) FROM ff_accounts").fetchone()[0],
        'available_accounts': conn.execute("SELECT COUNT(*) FROM ff_accounts WHERE status='available'").fetchone()[0],
    }
    conn.close()
    return render_template('admin.html', users=users, ff_accounts=ff_accounts,
                           logs=logs, stats=stats)

# API: create user (used by Telegram bot)
@app.route('/api/create_user', methods=['POST'])
def api_create_user():
    data = request.json
    secret = data.get('secret')
    if secret != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    days = int(data.get('days', 30))
    plan = data.get('plan', 'basic')
    note = data.get('note', '')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'})
    if days == -1:
        expires = None
        plan = 'lifetime'
    else:
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password, subscription_days, subscription_expires, plan, note, created_by) VALUES (?,?,?,?,?,?,?)",
            (username, hash_pw(password), days, expires, plan, note, 'telegram_admin'))
        conn.commit()
        log_action("create_user", f"Created user {username} | plan={plan} | days={days}", "telegram_admin")
        conn.close()
        return jsonify({'success': True, 'username': username, 'expires': expires or 'lifetime'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_user', methods=['POST'])
def api_delete_user():
    data = request.json
    if data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = data.get('username', '').strip()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND is_admin=0", (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'})
    conn.execute("DELETE FROM users WHERE username=? AND is_admin=0", (username,))
    conn.commit()
    conn.close()
    log_action("delete_user", f"Deleted user {username}", "telegram_admin")
    return jsonify({'success': True})

@app.route('/api/ban_user', methods=['POST'])
def api_ban_user():
    data = request.json
    if data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = data.get('username', '').strip()
    banned = int(data.get('banned', 1))
    conn = get_db()
    conn.execute("UPDATE users SET is_banned=? WHERE username=?", (banned, username))
    conn.commit()
    conn.close()
    log_action("ban_user" if banned else "unban_user", f"{'Banned' if banned else 'Unbanned'} user {username}", "telegram_admin")
    return jsonify({'success': True})

@app.route('/api/extend_user', methods=['POST'])
def api_extend_user():
    data = request.json
    if data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = data.get('username', '').strip()
    days = int(data.get('days', 30))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'})
    if days == -1:
        expires = None
        plan = 'lifetime'
    else:
        now_exp = user['subscription_expires']
        if now_exp:
            try:
                base = datetime.strptime(now_exp, "%Y-%m-%d %H:%M:%S")
                if base < datetime.now():
                    base = datetime.now()
            except:
                base = datetime.now()
        else:
            base = datetime.now()
        expires = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        plan = 'basic'
    conn.execute("UPDATE users SET subscription_expires=?, plan=? WHERE username=?", (expires, plan, username))
    conn.commit()
    conn.close()
    log_action("extend_user", f"Extended {username} by {days} days", "telegram_admin")
    return jsonify({'success': True, 'expires': expires or 'lifetime'})

@app.route('/api/reset_password', methods=['POST'])
def api_reset_password():
    data = request.json
    if data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = data.get('username', '').strip()
    new_pw = data.get('password', '').strip()
    if not new_pw:
        return jsonify({'success': False, 'error': 'Password required'})
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE username=?", (hash_pw(new_pw), username))
    conn.commit()
    conn.close()
    log_action("reset_password", f"Password reset for {username}", "telegram_admin")
    return jsonify({'success': True})

@app.route('/api/add_ff_account', methods=['POST'])
def api_add_ff_account():
    data = request.json
    if data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    uid = data.get('uid', '').strip()
    password = data.get('password', '').strip()
    region = data.get('region', 'IND')
    note = data.get('note', '')
    if not uid or not password:
        return jsonify({'success': False, 'error': 'UID and password required'})
    conn = get_db()
    conn.execute("INSERT INTO ff_accounts (uid, password, region, note) VALUES (?,?,?,?)",
                 (uid, password, region, note))
    conn.commit()
    conn.close()
    log_action("add_ff_account", f"Added FF account UID:{uid} region:{region}", "telegram_admin")
    return jsonify({'success': True})

@app.route('/api/assign_ff', methods=['POST'])
def api_assign_ff():
    data = request.json
    if data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = data.get('username', '').strip()
    ff_uid = data.get('ff_uid', '').strip()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'})
    ff = conn.execute("SELECT * FROM ff_accounts WHERE uid=?", (ff_uid,)).fetchone()
    if not ff:
        conn.close()
        return jsonify({'success': False, 'error': 'FF account not found'})
    conn.execute("UPDATE ff_accounts SET assigned_user_id=?, status='assigned' WHERE uid=?",
                 (user['id'], ff_uid))
    conn.commit()
    conn.close()
    log_action("assign_ff", f"Assigned FF {ff_uid} to {username}", "telegram_admin")
    return jsonify({'success': True})

@app.route('/api/stats')
def api_stats():
    data = request.json or {}
    if request.args.get('secret') != 'DBL_BOT_SECRET_7547557639' and data.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    conn = get_db()
    stats = {
        'total_users': conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0],
        'active_subs': conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0 AND is_banned=0 AND (subscription_expires > datetime('now') OR plan='lifetime')").fetchone()[0],
        'banned': conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0],
        'ff_accounts': conn.execute("SELECT COUNT(*) FROM ff_accounts").fetchone()[0],
        'available_ff': conn.execute("SELECT COUNT(*) FROM ff_accounts WHERE status='available'").fetchone()[0],
        'recent_logins': conn.execute("SELECT COUNT(*) FROM users WHERE last_login > datetime('now', '-1 day')").fetchone()[0],
    }
    conn.close()
    return jsonify({'success': True, **stats})

@app.route('/api/list_users')
def api_list_users():
    if request.args.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    conn = get_db()
    users = conn.execute("SELECT username, plan, subscription_expires, is_banned, created_at FROM users WHERE is_admin=0 ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return jsonify({'success': True, 'users': [dict(u) for u in users]})

@app.route('/api/get_user')
def api_get_user():
    if request.args.get('secret') != 'DBL_BOT_SECRET_7547557639':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = request.args.get('username', '')
    conn = get_db()
    user = conn.execute("SELECT username, plan, subscription_expires, is_banned, created_at, last_login, note FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'})
    return jsonify({'success': True, 'user': dict(user)})

# Admin web panel actions
@app.route('/admin/ban/<int:uid>', methods=['POST'])
@admin_required
def web_ban_user(uid):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if user:
        new_ban = 0 if user['is_banned'] else 1
        conn.execute("UPDATE users SET is_banned=? WHERE id=?", (new_ban, uid))
        conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/admin/delete/<int:uid>', methods=['POST'])
@admin_required
def web_delete_user(uid):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=? AND is_admin=0", (uid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/admin/add_ff', methods=['POST'])
@admin_required
def web_add_ff():
    uid = request.form.get('uid', '').strip()
    password = request.form.get('password', '').strip()
    region = request.form.get('region', 'IND')
    if uid and password:
        conn = get_db()
        conn.execute("INSERT INTO ff_accounts (uid, password, region) VALUES (?,?,?)", (uid, password, region))
        conn.commit()
        conn.close()
        flash('تم إضافة الحساب بنجاح', 'success')
    return redirect(url_for('admin'))

@app.route('/api/ff/status')
@login_required
def ff_status_api():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    if not is_sub_active(user):
        return jsonify({'success': False, 'error': 'اشتراك غير نشط'})
    return jsonify({'success': True, **ff_control.ff_status})

@app.route('/api/ff/start', methods=['POST'])
@login_required
def ff_start():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    if not is_sub_active(user):
        return jsonify({'success': False, 'error': 'اشتراك غير نشط'})
    if ff_control.ff_status.get('auto_running'):
        return jsonify({'success': False, 'error': 'البوت يعمل بالفعل، أوقفه أولاً'})
    data = request.json or {}
    team_code = str(data.get('team_code', '')).strip()
    if not team_code or not team_code.isdigit():
        return jsonify({'success': False, 'error': 'كود الفريق يجب أن يكون أرقام فقط'})
    ff_control.set_command('lw', team_code)
    log_action('ff_start', f'User {user["username"]} started auto with team_code={team_code}', user['username'])
    return jsonify({'success': True, 'message': f'تم إرسال الأمر! كود الفريق: {team_code}'})

@app.route('/api/ff/stop', methods=['POST'])
@login_required
def ff_stop():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    if not is_sub_active(user):
        return jsonify({'success': False, 'error': 'اشتراك غير نشط'})
    if not ff_control.ff_status.get('auto_running'):
        return jsonify({'success': False, 'error': 'البوت متوقف بالفعل'})
    ff_control.set_command('stop')
    log_action('ff_stop', f'User {user["username"]} stopped auto', user['username'])
    return jsonify({'success': True, 'message': 'تم إيقاف البوت بنجاح'})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
