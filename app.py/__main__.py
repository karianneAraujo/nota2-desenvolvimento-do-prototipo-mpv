from flask import Flask, render_template
import sqlite3
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path(__file__).parent.parent / 'banco_dados.db'

@app.route('/')
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

if __name__ == '__main__':
    app.run(debug=True)
