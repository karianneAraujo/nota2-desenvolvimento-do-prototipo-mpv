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


def normalize_digits(value: str) -> str:
    return ''.join(ch for ch in (value or '') if ch.isdigit())


def validar_cpf(cpf: str) -> bool:
    cpf = normalize_digits(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    numeros = [int(d) for d in cpf]
    for i in range(9, 11):
        soma = sum(numeros[j] * (i + 1 - j) for j in range(0, i))
        digito = 11 - (soma % 11)
        if digito >= 10:
            digito = 0
        if numeros[i] != digito:
            return False
    return True


def validar_cartao_sus(cartao_sus: str) -> bool:
    cartao = normalize_digits(cartao_sus)
    if len(cartao) != 15 or cartao == cartao[0] * 15:
        return False
    pesos = list(range(15, 1, -1))
    total = sum(int(digit) * peso for digit, peso in zip(cartao[:14], pesos))
    resto = total % 11
    digito = 0 if resto in (0, 1) else 11 - resto
    return int(cartao[14]) == digito

app.jinja_env.globals.update(validar_cpf=validar_cpf, validar_cartao_sus=validar_cartao_sus)


def table_exists(cursor, name: str) -> bool:
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (name,))
    return cursor.fetchone() is not None


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/painel')
def painel():
    """Exibe o painel com dados de usuários, pacientes e produção."""
    usuarios = []
    pacientes = []
    invalid_cpfs = []
    invalid_sus = []
    duplicate_cpfs = []
    duplicate_sus = []
    inconsistencias_producao = []
    total_pacientes = 0
    total_producao = 0

    try:
        conexao = sqlite3.connect(str(DB_PATH))
        cursor = conexao.cursor()

        cursor.execute('SELECT id, nome, email, data_criacao, is_admin FROM usuarios')
        usuarios = cursor.fetchall()

        if table_exists(cursor, 'pacientes'):
            cursor.execute('SELECT id, nome, cpf, cartao_sus, status FROM pacientes ORDER BY nome')
            pacientes = cursor.fetchall()
            total_pacientes = len(pacientes)
            invalid_cpfs = [p for p in pacientes if not validar_cpf(p[2])]
            invalid_sus = [p for p in pacientes if not validar_cartao_sus(p[3])]

            cursor.execute('SELECT cpf, COUNT(*) FROM pacientes WHERE cpf != "" GROUP BY cpf HAVING COUNT(*) > 1')
            duplicate_cpfs = cursor.fetchall()
            cursor.execute('SELECT cartao_sus, COUNT(*) FROM pacientes WHERE cartao_sus != "" GROUP BY cartao_sus HAVING COUNT(*) > 1')
            duplicate_sus = cursor.fetchall()

        if table_exists(cursor, 'producao'):
            total_producao = cursor.execute('SELECT COUNT(*) FROM producao').fetchone()[0]

            cursor.execute('''
                SELECT p.id, p.paciente_id, p.data_atendimento, p.servico
                FROM producao p
                LEFT JOIN pacientes c ON p.paciente_id = c.id
                WHERE c.id IS NULL
            ''')
            orfaos = cursor.fetchall()
            inconsistencias_producao.extend([
                f'Produção {row[0]} sem paciente válido (paciente_id={row[1]})'
                for row in orfaos
            ])

            cursor.execute('''
                SELECT paciente_id, data_atendimento, servico, COUNT(*)
                FROM producao
                GROUP BY paciente_id, data_atendimento, servico
                HAVING COUNT(*) > 1
            ''')
            repetidos = cursor.fetchall()
            inconsistencias_producao.extend([
                f'Produção duplicada para paciente {row[0]} em {row[1]} serviço "{row[2]}" ({row[3]} registros)'
                for row in repetidos
            ])

            cursor.execute('SELECT id, paciente_id, quantidade FROM producao WHERE quantidade <= 0')
            registros_invalidos = cursor.fetchall()
            inconsistencias_producao.extend([
                f'Produção {row[0]} com quantidade inválida ({row[2]})'
                for row in registros_invalidos
            ])

        conexao.close()
    except Exception as e:
        print(f"Erro ao buscar dados no painel: {e}")

    return render_template(
        'painel.html',
        usuarios=usuarios,
        pacientes=pacientes,
        invalid_cpfs=invalid_cpfs,
        invalid_sus=invalid_sus,
        duplicate_cpfs=duplicate_cpfs,
        duplicate_sus=duplicate_sus,
        inconsistencias_producao=inconsistencias_producao,
        total_pacientes=total_pacientes,
        total_producao=total_producao,
    )

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


@app.route('/paciente/novo')
def paciente_novo():
    acesso = admin_required()
    if acesso:
        return acesso
    return render_template('cadastrar_paciente.html')


@app.route('/paciente/novo', methods=['POST'])
def paciente_novo_post():
    acesso = admin_required()
    if acesso:
        return acesso

    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    cartao_sus = request.form.get('cartao_sus')
    data_nascimento = request.form.get('data_nascimento')
    status = request.form.get('status') or 'Ativo'

    if not nome or not cpf or not cartao_sus:
        flash('Nome, CPF e Cartão SUS são obrigatórios.')
        return redirect(url_for('paciente_novo'))

    cpf_limpo = normalize_digits(cpf)
    sus_limpo = normalize_digits(cartao_sus)

    if not validar_cpf(cpf_limpo):
        flash('CPF inválido. Verifique os dígitos e tente novamente.')
        return redirect(url_for('paciente_novo'))

    if not validar_cartao_sus(sus_limpo):
        flash('Cartão SUS inválido. Verifique o número e tente novamente.')
        return redirect(url_for('paciente_novo'))

    try:
        conexao = sqlite3.connect(str(DB_PATH))
        cursor = conexao.cursor()

        cursor.execute('SELECT id FROM pacientes WHERE cpf = ? OR cartao_sus = ?', (cpf_limpo, sus_limpo))
        if cursor.fetchone():
            conexao.close()
            flash('Paciente duplicado encontrado por CPF ou Cartão SUS.')
            return redirect(url_for('paciente_novo'))

        cursor.execute('''
            INSERT INTO pacientes (nome, cpf, cartao_sus, data_nascimento, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (nome, cpf_limpo, sus_limpo, data_nascimento, status))

        conexao.commit()
        conexao.close()

        flash('Paciente cadastrado com sucesso.')
        return redirect(url_for('painel'))
    except Exception as e:
        flash(f'Erro ao cadastrar paciente: {str(e)}')
        return redirect(url_for('paciente_novo'))


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