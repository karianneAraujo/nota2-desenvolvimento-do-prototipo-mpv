from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from pathlib import Path

# Caminho da pasta template
TEMPLATE_FOLDER = Path(__file__).parent.parent / 'venv' / 'templates'

app = Flask(__name__, template_folder=str(TEMPLATE_FOLDER))
app.secret_key = 'digisus_mirador_secret_key_2024'

@app.context_processor
def inject_user():
    return {
        'logged_user': session.get('user_name'),
        'is_admin': session.get('is_admin', False),
        'admin_exists': has_admin_user()
    }

DB_PATH = Path(__file__).parent.parent / 'banco_dados.db'

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/painel')
def painel():
    """Exibe o painel com dados do banco."""
    try:
        conexao = sqlite3.connect(str(DB_PATH))
        cursor = conexao.cursor()
        cursor.execute('SELECT * FROM usuarios')
        dados = cursor.fetchall()
        conexao.close()
    except Exception as e:
        dados = []
        print(f"Erro ao buscar dados: {e}")
    
    return render_template('painel.html', dados=dados)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Por favor, preencha todos os campos.')
        return redirect(url_for('login'))
    
    try:
        conexao = sqlite3.connect(str(DB_PATH))
        cursor = conexao.cursor()
        cursor.execute('SELECT id, nome, email, senha, is_admin FROM usuarios WHERE email = ? AND senha = ?', (username, password))
        usuario = cursor.fetchone()
        conexao.close()
        
        if usuario:
            session.clear()
            session['user_id'] = usuario[0]
            session['user_name'] = usuario[1]
            session['is_admin'] = bool(usuario[4])
            return redirect(url_for('painel'))
        else:
            flash('Credenciais inválidas. Tente novamente.')
            return redirect(url_for('login'))
            
    except Exception as e:
        flash(f'Erro ao fazer login: {str(e)}')
        return redirect(url_for('login'))

def has_admin_user():
    try:
        conexao = sqlite3.connect(str(DB_PATH))
        cursor = conexao.cursor()
        cursor.execute('SELECT 1 FROM usuarios WHERE is_admin = 1 LIMIT 1')
        existe = cursor.fetchone() is not None
        conexao.close()
        return existe
    except Exception:
        return False


def admin_required():
    if not has_admin_user():
        return None
    if not session.get('is_admin'):
        flash('Acesso negado. Faça login como administrador.')
        return redirect(url_for('login'))

@app.route('/cadastro')
def cadastro():
    acesso = admin_required()
    if acesso:
        return acesso
    return render_template('cadastro.html')

@app.route('/cadastro', methods=['POST'])
def cadastro_post():
    acesso = admin_required()
    if acesso:
        return acesso
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')
    confirmar_senha = request.form.get('confirmar_senha')
    
    # Validações
    if not nome or not email or not senha or not confirmar_senha:
        flash('Todos os campos são obrigatórios.')
        return redirect(url_for('cadastro'))
    
    if senha != confirmar_senha:
        flash('As senhas não coincidem.')
        return redirect(url_for('cadastro'))
    
    if len(senha) < 6:
        flash('A senha deve ter pelo menos 6 caracteres.')
        return redirect(url_for('cadastro'))
    
    try:
        conexao = sqlite3.connect(str(DB_PATH))
        cursor = conexao.cursor()
        
        # Verificar se o email já existe
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            conexao.close()
            flash('Este email já está cadastrado.')
            return redirect(url_for('cadastro'))
        
        # Inserir novo administrador
        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, is_admin) 
            VALUES (?, ?, ?, 1)
        ''', (nome, email, senha))
        
        conexao.commit()
        conexao.close()
        
        flash('Administrador cadastrado com sucesso! Faça o login.')
        return redirect(url_for('login'))
        
    except Exception as e:
        flash(f'Erro ao cadastrar administrador: {str(e)}')
        return redirect(url_for('cadastro'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout efetuado com sucesso.')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)