from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_anda' # Diperlukan untuk session

# Konfigurasi Database
DB_HOST = "localhost"
DB_NAME = "finance_db"
DB_USER = "postgres"
DB_PASS = "msibravo"
DB_PORT = "5433" # Sesuaikan dengan angka yang Anda lihat di pgAdmin

def get_db_connection():
    # Masukkan parameter port di sini
    conn = psycopg2.connect(
        host=DB_HOST, 
        database=DB_NAME, 
        user=DB_USER, 
        password=DB_PASS, 
        port=DB_PORT 
    )
    return conn
# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        account = cur.fetchone()
        cur.close()
        conn.close()
        
        if account:
            session['user_id'] = account['user_id']
            session['username'] = account['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect username or password!')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!')
            return render_template('register.html')

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                        (username, email, password))
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Username or Email already exists.')
        finally:
            cur.close()
            conn.close()

    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    # Jika baru membuka halaman (GET), mulai dari tahap 1 & bersihkan sesi sisa
    if request.method == 'GET':
        session.pop('reset_username', None)
        return render_template('forgot_password.html', stage=1)

    # Ambil tahap saat ini dari input hidden di HTML
    current_stage = int(request.form.get('stage', 1))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # --- LOGIKA TAHAP 1: VALIDASI USERNAME ---
    if current_stage == 1:
        username = request.form['username']
        
        # Cek apakah username ada
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user:
            # Username ketemu, simpan sementara di session dan lanjut ke Tahap 2
            session['reset_username'] = username
            cur.close()
            conn.close()
            return render_template('forgot_password.html', stage=2)
        else:
            flash("Username not found.")
            cur.close()
            conn.close()
            return render_template('forgot_password.html', stage=1)

    # --- LOGIKA TAHAP 2: VALIDASI EMAIL ---
    elif current_stage == 2:
        email = request.form['email']
        username = session.get('reset_username') # Ambil username yg disimpan tadi
        
        # Cek apakah email cocok dengan username tersebut
        cur.execute("SELECT * FROM users WHERE username = %s AND email = %s", (username, email))
        user = cur.fetchone()
        
        if user:
            # Cocok! Lanjut ke Tahap 3 (Reset Password)
            cur.close()
            conn.close()
            return render_template('forgot_password.html', stage=3)
        else:
            # Email salah/tidak cocok
            flash("Email provided does not match our records for this username.")
            cur.close()
            conn.close()
            return render_template('forgot_password.html', stage=2)

    # --- LOGIKA TAHAP 3: UPDATE PASSWORD ---
    elif current_stage == 3:
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        username = session.get('reset_username')
        
        if new_password != confirm_password:
            flash("Passwords do not match!")
            cur.close()
            conn.close()
            return render_template('forgot_password.html', stage=3)
        
        # Update password di database
        cur.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
        conn.commit()
        
        # Bersihkan session
        session.pop('reset_username', None)
        cur.close()
        conn.close()
        
        flash("Password has been reset successfully. Please login.")
        return redirect(url_for('login'))

    return render_template('forgot_password.html', stage=1)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Ambil transaksi user
    cur.execute('SELECT * FROM transactions WHERE user_id = %s ORDER BY transaction_date DESC', (session['user_id'],))
    transactions = cur.fetchall()
    
    # Hitung Saldo
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Income'", (session['user_id'],))
    total_income = cur.fetchone()[0] or 0
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Expense'", (session['user_id'],))
    total_expense = cur.fetchone()[0] or 0
    
    balance = total_income - total_expense
    
    cur.close()
    conn.close()
    
    return render_template('dashboard.html', transactions=transactions, balance=balance, username=session['username'])

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        t_type = request.form['type']
        amount = request.form['amount']
        notes = request.form['notes']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO transactions (user_id, transaction_name, type, amount, notes) VALUES (%s, %s, %s, %s, %s)',
                    (session['user_id'], name, t_type, amount, notes))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('dashboard'))

    return render_template('add_transaction.html')

@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Pastikan hanya menghapus transaksi milik user yang sedang login (keamanan)
    cur.execute('DELETE FROM transactions WHERE transaction_id = %s AND user_id = %s', 
                (transaction_id, session['user_id']))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('Transaction deleted successfully.')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)