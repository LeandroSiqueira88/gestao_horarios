from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from extensoes import mysql 
from auth import login_obrigatorio, somente_master
import sqlite3
from flask import Flask
from datetime import datetime
import re
from flask import make_response
from fpdf import FPDF
from flask import Response
from collections import defaultdict
import re

app = Flask(__name__)
# 🔹 Criando o Blueprint
routes = Blueprint('routes', __name__)

# 🔹 Lista fixa de turmas disponíveis
TURMAS = ["1ºA", "1ºB", "1ºC", "2ºA", "2ºB", "2ºC", "3ºA", "3ºB", "3ºC"]

dias_da_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

# 🔹 Função para obter a conexão MySQL
def get_mysql():
    from app import mysql
    return mysql

# 🔹 ROTA PRINCIPAL – Escolha entre Master e Usuário
@routes.route('/')
def index():
    if session.get('usuario_id'):
        return redirect(url_for('routes.dashboard'))
    return render_template('index.html')



# Rota exclusiva para Master
@routes.route('/master', methods=['GET', 'POST'])
def acesso_master():
    return render_template('usuarios/login_master.html')


# 🔹 LOGIN
@routes.route('/login', methods=['GET', 'POST'])
def login():
    mysql = get_mysql()

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cur.fetchone()
        cur.close()

        if usuario and check_password_hash(usuario[3], senha):
            session['usuario_id'] = usuario[0]
            session['usuario_nome'] = usuario[1]
            session['usuario_perfil'] = usuario[4]

            flash("Login realizado com sucesso!", "success")

            if usuario[4] == 'master':
                return redirect(url_for('routes.admin'))
            else:
                return redirect(url_for('routes.dashboard'))
        else:
            flash("E-mail ou senha inválidos", "danger")

    return render_template('usuarios/login_publico.html')


@routes.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('routes.login'))

# 🔹 DASHBOARD (exemplo)
@routes.route('/dashboard')
@login_obrigatorio
def dashboard():
    print("Perfil logado:", session.get('usuario_perfil'))
    return render_template('dashboard.html')


# 🔹 ADMINISTRADOR (Apenas para "master")
@routes.route('/admin')
@login_obrigatorio
@somente_master
def admin():
    return render_template('admin.html')



# 🔹 CADASTRO DE USUÁRIO
@routes.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    mysql = get_mysql()
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        perfil = request.form['perfil']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        usuario_existente = cur.fetchone()

        if usuario_existente:
            flash('Email já cadastrado!', 'danger')
        else:
            senha_hash = generate_password_hash(senha)
            cur.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s, %s, %s, %s)", 
                        (nome, email, senha_hash, perfil))
            mysql.connection.commit()
            flash('Cadastro realizado com sucesso!', 'success')
        cur.close()
        return redirect(url_for('routes.login'))

    return render_template('cadastro.html')

# 🔹 Conexão com SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 🔹 CRUD de Professores (SQLite)
# 🔹 LISTAR PROFESSORES
@routes.route('/professores')
def listar_professores():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM professores")
    professores = cur.fetchall()
    cur.close()
    return render_template('professores/listar_professores.html', professores=professores)

# 🔹 CADASTRAR PROFESSOR
@routes.route('/cadastrar_professor', methods=['GET', 'POST'])
@login_obrigatorio
def cadastrar_professor():
    if session.get('usuario_perfil') not in ['master', 'administrativo']:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('routes.dashboard'))

    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        especialidade = request.form['especialidade']
        observacao = request.form['observacao']

        # Formatar CPF para 000.000.000-00
        import re
        def formatar_cpf(cpf):
            numeros = re.sub(r'\D', '', cpf)
            return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
        cpf = formatar_cpf(cpf)

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Verificar se nome já existe (apenas alerta, não bloqueia)
        cur.execute("SELECT id FROM professores WHERE nome = %s", (nome,))
        professor_com_nome_igual = cur.fetchone()
        if professor_com_nome_igual:
            flash("⚠️ Já existe um professor com este nome!", "warning")

        # Verificar se CPF já existe (impede)
        cur.execute("SELECT id FROM professores WHERE cpf = %s", (cpf,))
        professor_existente = cur.fetchone()
        if professor_existente:
            flash("❗ Já existe um professor com este CPF!", "danger")
            cur.close()
            return redirect(url_for('routes.cadastrar_professor'))

        # Inserir novo professor
        cur.execute('''
            INSERT INTO professores (nome, cpf, endereco, telefone, email, especialidade, observacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (nome, cpf, endereco, telefone, email, especialidade, observacao))

        mysql.connection.commit()
        cur.close()
        flash("✅ Professor cadastrado com sucesso!", "success")
        return redirect(url_for('routes.listar_professores'))

    return render_template('professores/cadastrar_professor.html')


# 🔹 EDITAR PROFESSOR
@routes.route('/editar_professor/<int:id>', methods=['GET', 'POST'])
def editar_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        dados = (
            request.form['nome'],
            request.form['cpf'],
            request.form['endereco'],
            request.form['telefone'],
            request.form['email'],
            request.form['especialidade'],
            request.form['observacao'],
            id
        )

        cur.execute('''
            UPDATE professores 
            SET nome = %s, cpf = %s, endereco = %s, telefone = %s, email = %s, especialidade = %s, observacao = %s
            WHERE id = %s
        ''', dados)
        mysql.connection.commit()
        cur.close()
        flash("Professor atualizado com sucesso!", "success")
        return redirect(url_for('routes.listar_professores'))

    cur.execute("SELECT * FROM professores WHERE id = %s", (id,))
    professor = cur.fetchone()
    cur.close()

    if not professor:
        flash("Professor não encontrado!", "danger")
        return redirect(url_for('routes.listar_professores'))

    return render_template('professores/editar_professor.html', professor=professor)

# 🔹 EXCLUIR PROFESSOR
@routes.route('/excluir_professor/<int:id>', methods=['POST'])
def excluir_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM professores WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Professor excluído com sucesso!", "success")
    return redirect(url_for('routes.listar_professores'))

@routes.route('/professor/<int:id>/aulas')
@login_obrigatorio
def ver_aulas_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar o professor
    cur.execute("SELECT * FROM professores WHERE id = %s", (id,))
    professor = cur.fetchone()

    if not professor:
        flash("Professor não encontrado!", "danger")
        return redirect(url_for('routes.listar_professores'))

    # Buscar as aulas cadastradas do professor
    cur.execute("""
        SELECT dia_semana, aula_numero, materia, s.nome AS sala_nome
        FROM horarios h
        JOIN salas s ON h.sala_id = s.id
        WHERE h.professor_id = %s
        ORDER BY FIELD(dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'), aula_numero
    """, (id,))
    aulas = cur.fetchall()
    cur.close()

    return render_template('professores/aulas_professor.html', professor=professor, aulas=aulas)



# 🔹 CRUD Alunos (MySQL)
@routes.route('/alunos')
def listar_alunos():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT a.*, s.nome AS sala_nome
        FROM alunos a
        LEFT JOIN salas s ON a.sala_id = s.id
    """)
    alunos = cur.fetchall()
    cur.close()
    return render_template('alunos/listar_alunos.html', alunos=alunos)


@routes.route('/cadastrar_aluno', methods=['GET', 'POST'])
def cadastrar_aluno():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()

    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        data_nascimento = request.form['data_nascimento']
        sala_id = request.form.get('sala_id') or None

        # 🔸 Formatar CPF (opcional, para garantir padrão)
        cpf = cpf.strip().replace("-", "").replace(".", "")
        cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        # 🔸 Verifica duplicidade de CPF (bloqueia)
        cur.execute("SELECT id FROM alunos WHERE cpf = %s", (cpf,))
        aluno_existente = cur.fetchone()
        if aluno_existente:
            flash("⚠️ Já existe um aluno com este CPF!", "danger")
            cur.close()
            return redirect(url_for('routes.cadastrar_aluno'))

        # 🔸 Verifica duplicidade de nome (somente alerta)
        cur.execute("SELECT id FROM alunos WHERE nome = %s", (nome,))
        nome_duplicado = cur.fetchone()
        if nome_duplicado:
            flash("ℹ️ Atenção: já existe um aluno com este nome!", "warning")

        # 🔸 Cadastrar aluno
        cur.execute("""
            INSERT INTO alunos (nome, cpf, endereco, telefone, email, data_nascimento, sala_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, cpf, endereco, telefone, email, data_nascimento, sala_id))
        mysql.connection.commit()
        cur.close()

        flash("✅ Aluno cadastrado com sucesso!", "success")
        return redirect(url_for('routes.listar_alunos'))

    cur.close()
    return render_template('alunos/cadastrar_aluno.html', salas=salas)



@routes.route('/editar_aluno/<int:id>', methods=['GET', 'POST'])
def editar_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM alunos WHERE id = %s", (id,))
    aluno = cur.fetchone()

    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()

    if request.method == 'POST':
        nome = request.form['nome']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        data_nascimento = request.form.get('data_nascimento')
        sala_id = request.form.get('sala_id') or None

        cur.execute("""
            UPDATE alunos 
            SET nome=%s, endereco=%s, telefone=%s, email=%s, data_nascimento=%s, sala_id=%s
            WHERE id=%s
        """, (nome, endereco, telefone, email, data_nascimento, sala_id, id))

        mysql.connection.commit()
        flash("Aluno atualizado com sucesso!", "success")
        cur.close()
        return redirect(url_for('routes.listar_alunos'))

    cur.close()
    return render_template('alunos/editar_aluno.html', aluno=aluno, salas=salas)


@routes.route('/excluir_aluno/<int:id>', methods=['POST'])
def excluir_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM alunos WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Aluno excluído com sucesso!', 'success')
    return redirect(url_for('routes.listar_alunos'))



from datetime import datetime

@app.template_filter('date')
def format_date(value, format='%d/%m/%Y'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value




# 🔹 CRUD Usuários (MySQL)
@routes.route('/usuarios')
@login_obrigatorio
@somente_master
def gerenciar_usuarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios")
    usuarios = cur.fetchall()
    cur.close()
    return render_template('usuarios/gerenciar_usuarios.html', usuarios=usuarios)



@routes.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def cadastrar_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        perfil = request.form['perfil']

        senha_hash = generate_password_hash(senha)

        mysql = get_mysql()
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s, %s, %s, %s)",
                    (nome, email, senha_hash, perfil))
        mysql.connection.commit()
        cur.close()

        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_usuarios'))

    return render_template('usuarios/cadastrar_usuario.html')

@routes.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def editar_usuario(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        perfil = request.form['perfil']

        cur.execute("UPDATE usuarios SET nome=%s, email=%s, perfil=%s WHERE id=%s",
                    (nome, email, perfil, id))
        mysql.connection.commit()
        cur.close()

        flash("Usuário atualizado com sucesso!", "info")
        return redirect(url_for('routes.gerenciar_usuarios'))

    cur.execute("SELECT * FROM usuarios WHERE id = %s", (id,))
    usuario = cur.fetchone()
    cur.close()

    return render_template('usuarios/cadastrar_usuario.html', usuario=usuario, editar=True)


@routes.route('/usuarios/excluir/<int:id>', methods=['POST'])
@login_obrigatorio
@somente_master
def excluir_usuario(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash("Usuário excluído!", "danger")
    return redirect(url_for('routes.gerenciar_usuarios'))


@routes.route('/horario/<int:sala_id>')
@login_obrigatorio
def visualizar_horario_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    if not sala:
        flash("Sala não encontrada!", "danger")
        return redirect(url_for('routes.listar_turmas'))

    cur.execute("""
    SELECT h.dia_semana, h.aula_numero, h.materia, p.nome AS professor
    FROM horarios h
    LEFT JOIN professores p ON h.professor_id = p.id
    WHERE h.sala_id = %s
    ORDER BY 
        FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
        h.aula_numero
""", (sala_id,))

    resultados = cur.fetchall()
    cur.close()

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    linhas = ['1ª Aula', '2ª Aula', '3ª Aula', '🧃 Intervalo', '4ª Aula', '5ª Aula', '6ª Aula']
    grade = {linha: {dia: '' for dia in dias} for linha in linhas}

    for linha in resultados:
        dia = linha['dia_semana']
        aula = linha['aula_numero']
        materia = linha['materia']
        professor = linha.get('professor', '')
        linha_key = f'{aula}ª Aula'
        grade[linha_key][dia] = f"{materia}<br><small>{professor or '---'}</small>"

    for dia in dias:
        grade['🧃 Intervalo'][dia] = '🧃🍞 Intervalo'

    return render_template('horarios/horario_sala.html', sala=sala, grade=grade, dias=dias)





@routes.route('/turmas')
@login_obrigatorio
def listar_turmas():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('horarios/listar_turmas.html', salas=salas)


@routes.route('/turmas/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
def cadastrar_turma():
    if request.method == 'POST':
        nome = request.form['nome']
        ano = request.form['ano']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO turmas (nome, ano) VALUES (%s, %s)", (nome, ano))
        mysql.connection.commit()
        cur.close()
        flash('Turma cadastrada com sucesso!', 'success')
        return redirect(url_for('routes.listar_turmas'))
    
    return render_template('turmas/cadastrar_turma.html')

# 🔹 GERAR HORÁRIOS
@routes.route('/gerar_horarios')
@login_obrigatorio
@somente_master
def exibir_salas_para_geracao():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('horarios/gerar_horarios.html', salas=salas)


# ROTA: /gerar_horarios_global
@routes.route('/gerar_horarios_global')
@login_obrigatorio
@somente_master
def gerar_horarios_global():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar salas e professores
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()

    cur.execute("SELECT id, nome, especialidade FROM professores")
    professores = cur.fetchall()
    cur.execute("DELETE FROM horarios")  # limpar antes de gerar tudo

    # Mapear professores por especialidade
    prof_por_esp = {}
    for p in professores:
        prof_por_esp.setdefault(p['especialidade'], []).append(p)

    # Carga horária por matéria
    carga_horaria = {
        "Língua Portuguesa": 6,
        "Matemática": 6,
        "Inglês": 2,
        "Física": 2,
        "Química": 2,
        "Biologia": 2,
        "História": 2,
        "Geografia": 2,
        "Filosofia": 1,
        "Sociologia": 1,
        "Artes": 1,
        "Educação Física": 1
    }

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    aulas_por_dia = 6

    # Inicializar a grade vazia de cada sala
    grade_salas = {
        sala['id']: {
            dia: [None for _ in range(aulas_por_dia)] for dia in dias
        } for sala in salas
    }

    # Controle de ocupação de cada professor
    prof_ocupado = {
        p['id']: {
            dia: [False for _ in range(aulas_por_dia)] for dia in dias
        } for p in professores
    }

    import random
    for sala in salas:
        id_sala = sala['id']
        blocos = []

        for materia, total in carga_horaria.items():
            profs = prof_por_esp.get(materia, [])
            if not profs:
                continue

            # blocos de 2 aulas
            for _ in range(total // 2):
                blocos.append((materia, 2))
            if total % 2 != 0:
                blocos.append((materia, 1))

        random.shuffle(blocos)

        for materia, tamanho_bloco in blocos:
            alocado = False
            profs = prof_por_esp.get(materia, [])

            for dia in dias:
                for i in range(aulas_por_dia - (tamanho_bloco - 1)):
                    if all(grade_salas[id_sala][dia][i+j] is None for j in range(tamanho_bloco)):
                        prof_escolhido = None
                        for prof in profs:
                            if all(not prof_ocupado[prof['id']][dia][i+j] for j in range(tamanho_bloco)):
                                prof_escolhido = prof
                                break

                        for j in range(tamanho_bloco):
                            grade_salas[id_sala][dia][i+j] = {
                                'materia': materia,
                                'professor_id': prof_escolhido['id'] if prof_escolhido else None
                            }
                            if prof_escolhido:
                                prof_ocupado[prof_escolhido['id']][dia][i+j] = True
                        alocado = True
                        break
                if alocado:
                    break

    # Inserir no banco
    for sala_id, dias_semana in grade_salas.items():
        for dia, aulas in dias_semana.items():
            for i, slot in enumerate(aulas):
                if slot:
                    cur.execute("""
                        INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (sala_id, dia, i+1, slot['materia'], slot['professor_id']))

    mysql.connection.commit()
    cur.close()
    flash("✅ Horários gerados com sucesso para todas as salas!", "success")
    return redirect(url_for('routes.exibir_salas_para_geracao'))


@routes.route('/horarios/professor/<int:professor_id>')
@login_obrigatorio
def visualizar_horario_professor(professor_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar professor
    cur.execute("SELECT * FROM professores WHERE id = %s", (professor_id,))
    professor = cur.fetchone()

    if not professor:
        flash("Professor não encontrado!", "danger")
        cur.close()
        return redirect(url_for('routes.listar_professores_horarios'))

    # Buscar aulas do professor
    cur.execute("""
        SELECT h.dia_semana, h.aula_numero, h.materia, s.nome AS sala_nome
        FROM horarios h
        JOIN salas s ON h.sala_id = s.id
        WHERE h.professor_id = %s
        ORDER BY FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'), h.aula_numero
    """, (professor_id,))
    resultados = cur.fetchall()
    cur.close()

    # Preparar a grade
    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    linhas = ['1ª Aula', '2ª Aula', '3ª Aula', '🧃 Intervalo', '4ª Aula', '5ª Aula', '6ª Aula']
    grade = {dia: {linha: '' for linha in linhas} for dia in dias}

    for row in resultados:
        aula = row['aula_numero']
        dia = row['dia_semana']
        texto = f"{row['materia']}<br><small>{row['sala_nome']}</small>"
        linha = f"{aula}ª Aula"

        if linha in grade[dia]:  # Só adiciona se a linha existir
            grade[dia][linha] = texto

    for dia in dias:
        grade[dia]['🧃 Intervalo'] = '🧃🍞 Intervalo'

    total_aulas = len(resultados)

    return render_template(
    'horarios/horario_professor.html',
    professor=professor,
    horario=grade,
    dias=dias,
    linhas=linhas,
    carga_horaria=len(resultados)
)



@routes.route('/professores/horarios')
@login_obrigatorio
def listar_professores_horarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, nome, especialidade FROM professores ORDER BY nome")
    professores = cur.fetchall()
    cur.close()
    return render_template('horarios/professores_horarios.html', professores=professores)

# 📥 Cadastrar sala
@routes.route('/salas/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def cadastrar_sala():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        ano = request.form['ano'].strip()
        capacidade = request.form['capacidade'].strip()

        # Verifica duplicidade
        cur.execute("SELECT * FROM salas WHERE nome = %s", (nome,))
        if cur.fetchone():
            flash('Já existe uma sala com esse nome!', 'danger')
            return redirect(url_for('routes.cadastrar_sala'))

        cur.execute("INSERT INTO salas (nome, ano, capacidade) VALUES (%s, %s, %s)", (nome, ano, capacidade))
        mysql.connection.commit()
        cur.close()
        flash("Sala cadastrada com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_salas'))

    # 🔹 Ano padrão atual
    ano_padrao = datetime.now().year
    return render_template('salas/cadastrar_sala.html', ano_padrao=ano_padrao)


@routes.route('/salas/<int:sala_id>/alunos')
@login_obrigatorio
def visualizar_alunos_da_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Busca nome da sala
    cur.execute("SELECT nome FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    if not sala:
        flash("Sala não encontrada!", "danger")
        return redirect(url_for('routes.gerenciar_salas'))

    # Busca alunos da sala
    cur.execute("SELECT * FROM alunos WHERE sala_id = %s", (sala_id,))
    alunos = cur.fetchall()

    # Formata data de nascimento (YYYY-MM-DD → DD/MM/YYYY)
    for aluno in alunos:
        data_str = aluno.get("data_nascimento")
        if data_str:
            try:
                data_formatada = datetime.strptime(str(data_str), "%Y-%m-%d").strftime("%d/%m/%Y")
                aluno["data_nascimento"] = data_formatada
            except:
                aluno["data_nascimento"] = data_str  # fallback

    cur.close()
    return render_template('salas/visualizar_alunos.html', sala=sala, alunos=alunos)




# 📋 Listar salas com quantidade de alunos
@routes.route('/salas')
@login_obrigatorio
def gerenciar_salas():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT s.*, COUNT(a.id) AS qtd_alunos
        FROM salas s
        LEFT JOIN alunos a ON a.sala_id = s.id
        GROUP BY s.id
    """)

    salas = cur.fetchall()
    cur.close()
    return render_template('salas/gerenciar_salas.html', salas=salas)


# ✏️ Editar sala
@routes.route('/salas/editar/<int:sala_id>', methods=['GET', 'POST'])
@login_obrigatorio
def editar_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome']
        ano = request.form['ano']
        capacidade = request.form['capacidade']

        cur.execute("""
            UPDATE salas SET nome=%s, ano=%s, capacidade=%s WHERE id=%s
        """, (nome, ano, capacidade, sala_id))
        mysql.connection.commit()
        cur.close()
        flash("Sala atualizada com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_salas'))

    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()
    cur.close()

    if not sala:
        flash("Sala não encontrada!", "danger")
        return redirect(url_for('routes.gerenciar_salas'))

    return render_template('salas/editar_sala.html', sala=sala)


# 🗑️ Excluir sala
@routes.route('/salas/excluir/<int:sala_id>', methods=['POST'])
def excluir_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM salas WHERE id = %s", (sala_id,))
    mysql.connection.commit()
    flash("Sala excluída!", "danger")
    return redirect(url_for('routes.gerenciar_salas'))


from flask import Response, make_response
from fpdf import FPDF
from collections import defaultdict

import re
def limpar_html(texto):
    return re.sub(r'<[^>]*>', '', texto or "")

@routes.route('/exportar/alunos_por_sala')
@login_obrigatorio
def exportar_alunos_por_sala():
    sala_id = request.args.get('sala_id')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if sala_id:
        cur.execute("""
            SELECT a.nome AS aluno, s.nome AS sala
            FROM alunos a
            JOIN salas s ON a.sala_id = s.id
            WHERE s.id = %s
            ORDER BY a.nome
        """, (sala_id,))
    else:
        cur.execute("""
            SELECT a.nome AS aluno, s.nome AS sala
            FROM alunos a
            LEFT JOIN salas s ON a.sala_id = s.id
            ORDER BY s.nome, a.nome
        """)
    
    dados = cur.fetchall()
    cur.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    titulo = "Alunos por Sala" if not sala_id else f"Alunos da Sala: {dados[0]['sala'] if dados else '---'}"
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')
    pdf.ln(10)

    sala_atual = ""
    for row in dados:
        if not sala_id and row['sala'] != sala_atual:
            sala_atual = row['sala']
            pdf.set_font("Arial", style='B', size=11)
            pdf.cell(0, 10, f"Sala: {sala_atual}", ln=True)
            pdf.set_font("Arial", size=11)
        pdf.cell(0, 8, f" - {row['aluno']}", ln=True)

    return Response(pdf.output(dest='S'),
                mimetype='application/pdf',
                headers={"Content-Disposition": "attachment;filename=grade_salas.pdf"})






# EXPORTAR GRADE DE SALAS (geral ou de uma sala específica)
@routes.route('/exportar_grade_salas')
@login_obrigatorio
def exportar_grade_salas():
    from fpdf import FPDF
    from collections import defaultdict

    sala_id = request.args.get('sala_id')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if sala_id:
        cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    else:
        cur.execute("SELECT * FROM salas ORDER BY nome")
    salas = cur.fetchall()

    consulta_horarios = """
        SELECT h.*, s.nome AS sala_nome, p.nome AS professor_nome
        FROM horarios h
        JOIN salas s ON h.sala_id = s.id
        LEFT JOIN professores p ON h.professor_id = p.id
        {}
        ORDER BY s.nome, 
                 FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
                 h.aula_numero
    """.format(f"WHERE s.id = {sala_id}" if sala_id else "")
    cur.execute(consulta_horarios)
    horarios = cur.fetchall()
    cur.close()

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    aulas_por_sala = defaultdict(lambda: {dia: [''] * 6 for dia in dias})
    for h in horarios:
        texto = f"{h['materia']}\n({h['professor_nome'] or 'Sem prof'})"
        aulas_por_sala[h['sala_nome']][h['dia_semana']][h['aula_numero'] - 1] = texto

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=10)

    count = 0
    for sala in salas:
        if count % 2 == 0:
            pdf.add_page()
        nome = sala['nome']
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Sala: {nome}", ln=True)
        pdf.set_font("Arial", size=9)

        # Cabeçalho
        pdf.cell(30, 8, "Dia", 1, 0, 'C')
        for i in range(1, 7):
            pdf.cell(40, 8, f"{i}ª Aula", 1, 0, 'C')
        pdf.ln()

        # Corpo
        for dia in dias:
            pdf.cell(30, 14, dia, 1)
            for aula in aulas_por_sala[nome][dia]:
                pdf.multi_cell(40, 7, aula, 1, 'L', max_line_height=pdf.font_size)
            pdf.ln(0)
        pdf.ln(8)
        count += 1

    return Response(pdf.output(dest='S').encode('latin1'),
                    mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=grade_salas.pdf"})



# EXPORTAR GRADE DE PROFESSORES (geral ou de um específico)
@routes.route('/exportar_grade_professores')
@login_obrigatorio
def exportar_grade_professores():
    from fpdf import FPDF
    from collections import defaultdict

    professor_id = request.args.get('professor_id')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if professor_id:
        cur.execute("SELECT * FROM professores WHERE id = %s", (professor_id,))
    else:
        cur.execute("SELECT * FROM professores ORDER BY nome")
    professores = cur.fetchall()

    if professor_id:
        cur.execute("""
            SELECT h.*, s.nome AS sala_nome
            FROM horarios h
            JOIN salas s ON h.sala_id = s.id
            WHERE h.professor_id = %s
            ORDER BY h.dia_semana, h.aula_numero
        """, (professor_id,))
    else:
        cur.execute("""
            SELECT h.*, s.nome AS sala_nome, p.nome AS professor_nome
            FROM horarios h
            JOIN salas s ON h.sala_id = s.id
            JOIN professores p ON h.professor_id = p.id
            ORDER BY p.nome, h.dia_semana, h.aula_numero
        """)
    horarios = cur.fetchall()
    cur.close()

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    horario_por_prof = defaultdict(lambda: {dia: [''] * 6 for dia in dias})
    for h in horarios:
        prof = h.get('professor_nome') or professores[0]['nome']
        texto = f"{h['materia']}\n({h['sala_nome']})"
        horario_por_prof[prof][h['dia_semana']][h['aula_numero'] - 1] = texto

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=10)

    count = 0
    for prof in professores:
        if count % 2 == 0:
            pdf.add_page()
        nome = prof['nome']
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Professor: {nome}", ln=True)
        pdf.set_font("Arial", size=9)

        pdf.cell(30, 8, "Dia", 1, 0, 'C')
        for i in range(1, 7):
            pdf.cell(40, 8, f"{i}ª Aula", 1, 0, 'C')
        pdf.ln()

        for dia in dias:
            pdf.cell(30, 14, dia, 1)
            for aula in horario_por_prof[nome][dia]:
                pdf.multi_cell(40, 7, aula, 1, 'L', max_line_height=pdf.font_size)
            pdf.ln(0)
        pdf.ln(8)
        count += 1

    return Response(pdf.output(dest='S').encode('latin1'),
                    mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=grade_professores.pdf"})



@routes.route('/exportar/usuarios')
@login_obrigatorio
@somente_master
def exportar_usuarios():
    perfil_filtro = request.args.get('perfil')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if perfil_filtro:
        cur.execute("SELECT nome, email, perfil FROM usuarios WHERE perfil = %s ORDER BY nome", (perfil_filtro,))
    else:
        cur.execute("SELECT nome, email, perfil FROM usuarios ORDER BY nome")
        
    usuarios = cur.fetchall()
    cur.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    titulo = "Lista de Usuários"
    if perfil_filtro:
        titulo += f" ({perfil_filtro.capitalize()})"
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')
    pdf.ln(10)

    for u in usuarios:
        texto = f"{u['nome']} - {u['email']} ({u['perfil'].capitalize()})"
        pdf.cell(0, 8, txt=texto, ln=True)

    return Response(pdf.output(dest='S').encode('latin1'),
                    mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=usuarios.pdf"})

@routes.route('/exportar/grade_por_sala_html')
@login_obrigatorio
def exibir_exportar_grade_por_sala():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar todas as salas
    cur.execute("SELECT id, nome FROM salas ORDER BY nome")
    salas = cur.fetchall()

    sala_id = request.args.get("sala_id")
    horario = {}
    sala_selecionada = None

    if sala_id:
        # Sala selecionada
        cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
        sala_selecionada = cur.fetchone()

        cur.execute("""
            SELECT * FROM horarios 
            WHERE sala_id = %s 
            ORDER BY 
                FIELD(dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
                aula_numero
        """, (sala_id,))
        dados = cur.fetchall()

        # Estrutura do horário
        horario = {
            'Segunda': [''] * 6,
            'Terça': [''] * 6,
            'Quarta': [''] * 6,
            'Quinta': [''] * 6,
            'Sexta': [''] * 6
        }

        for h in dados:
            texto = f"{h['materia']}<br><small>{h['professor']}</small>"
            horario[h['dia_semana']][h['aula_numero'] - 1] = texto

    cur.close()
    return render_template("exportar/grade_por_sala.html", salas=salas, sala_selecionada=sala_selecionada, horario=horario)




@routes.route('/exportar/grade_por_professor_html')
@login_obrigatorio
def exibir_exportar_grade_por_professor():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT id, nome FROM professores ORDER BY nome")
    professores = cur.fetchall()

    professor_id = request.args.get("professor_id")
    horario = {}
    professor = None

    if professor_id:
        # Buscar professor
        cur.execute("SELECT * FROM professores WHERE id = %s", (professor_id,))
        professor = cur.fetchone()

        cur.execute("""
            SELECT h.*, s.nome AS sala_nome 
            FROM horarios h
            JOIN salas s ON h.sala_id = s.id
            WHERE h.professor_id = %s
            ORDER BY 
                FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
                h.aula_numero
        """, (professor_id,))
        dados = cur.fetchall()

        # Estrutura do horário
        horario = {
            'Segunda': [''] * 6,
            'Terça': [''] * 6,
            'Quarta': [''] * 6,
            'Quinta': [''] * 6,
            'Sexta': [''] * 6
        }

        for h in dados:
            texto = f"{h['materia']}<br><small>{h['sala_nome']}</small>"
            horario[h['dia_semana']][h['aula_numero'] - 1] = texto

    cur.close()
    return render_template("exportar/grade_por_professor.html", professores=professores, professor=professor, horario=horario)




@routes.route('/exportar/alunos_por_sala_html')
@login_obrigatorio
def exibir_exportar_alunos_por_sala():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas ORDER BY nome")
    salas = cur.fetchall()
    cur.close()
    return render_template('exportar/alunos_por_sala.html', salas=salas)

@routes.route('/exportar/usuarios_html')
@login_obrigatorio
@somente_master
def exibir_exportar_usuarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, nome FROM usuarios ORDER BY nome")
    usuarios = cur.fetchall()
    cur.close()
    return render_template('exportar/usuarios.html', usuarios=usuarios)



@routes.route('/horario/sala/<int:sala_id>/editar')
@login_obrigatorio
@somente_master
def editar_grade_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Dados da sala
    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    # Lista de professores e matérias
    cur.execute("SELECT id, nome, especialidade FROM professores")
    professores = cur.fetchall()

    # Grade de horário atual
    cur.execute("""
        SELECT h.*, p.nome AS professor_nome
        FROM horarios h
        LEFT JOIN professores p ON h.professor_id = p.id
        WHERE h.sala_id = %s
        ORDER BY
            FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
            h.aula_numero
    """, (sala_id,))
    horarios = cur.fetchall()

    cur.close()
    return render_template('horarios/editar_grade.html', sala=sala, horarios=horarios, professores=professores)

@routes.route('/editar_grade/<int:sala_id>', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def editar_grade(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        # Apaga os horários antigos dessa sala
        cur.execute("DELETE FROM horarios WHERE sala_id = %s", (sala_id,))
        mysql.connection.commit()

        # Lista de dias
        dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

        for dia in dias:
            for i in range(1, 7):  # 1ª até 6ª aula
                materia = request.form.get(f'{dia}_{i}_materia')
                professor_nome = request.form.get(f'{dia}_{i}_professor')

                if materia and professor_nome:
                    # Buscar o ID do professor pelo nome
                    cur.execute("SELECT id FROM professores WHERE nome = %s", (professor_nome,))
                    prof_row = cur.fetchone()
                    professor_id = prof_row['id'] if prof_row else None

                    cur.execute("""
                        INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (sala_id, dia, i, materia, professor_id))

        mysql.connection.commit()
        cur.close()
        flash("✅ Grade atualizada com sucesso!", "success")
        return redirect(url_for('routes.visualizar_horario_sala', sala_id=sala_id))

    # Parte GET (carrega o formulário)
    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    cur.execute("SELECT * FROM horarios WHERE sala_id = %s", (sala_id,))
    horarios_raw = cur.fetchall()

    # Agrupa por dia e aula
    horario = {dia: {i: {'materia': '', 'professor': ''} for i in range(1, 7)} for dia in dias}
    for h in horarios_raw:
        horario[h['dia_semana']][h['aula_numero']] = {
            'materia': h['materia'],
            'professor': h.get('professor') or ''
        }

    cur.execute("SELECT nome FROM professores ORDER BY nome")
    professores = [row['nome'] for row in cur.fetchall()]
    cur.close()

    return render_template('horarios/editar_grade.html', sala=sala, horario=horario, professores=professores)
