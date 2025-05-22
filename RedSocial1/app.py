from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Extiende el modelo de usuario para foto de perfil
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profile_pic = db.Column(db.String(200), nullable=True)

# Modelo de foro
class Foro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    tematica = db.Column(db.String(120), nullable=False)
    icono = db.Column(db.String(200), nullable=True)

# Ruta de inicio
@app.route('/')
def index():
    return render_template('index.html')

# Página de bienvenida tras login
@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    foros = Foro.query.all()
    user = User.query.get(session['user_id'])
    notif_file = f'notificaciones_{user.id}.json'
    notifs = []
    notif_count = 0
    if os.path.exists(notif_file):
        with open(notif_file, 'r', encoding='utf-8') as f:
            all_notifs = json.load(f)
            notifs = [n for n in all_notifs if not n.get('leida')]
            notif_count = len(notifs)
    return render_template('home.html', foros=foros, user=user, notif_count=notif_count, notifs=notifs)

# Ruta de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe')
            return redirect(url_for('register'))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registro exitoso, ahora puedes iniciar sesión')
        return redirect(url_for('login'))
    return render_template('register.html')

# Ruta de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Credenciales incorrectas')
            return redirect(url_for('login'))
    return render_template('login.html')

# Ruta de feed (publicaciones)
@app.route('/feed', methods=['GET', 'POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    marcar_notificaciones_leidas(session['user_id'], '/feed')
    if request.method == 'POST':
        texto = request.form['texto']
        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        imagen = None
        archivo = None
        enlace = None
        # Manejo de adjuntos
        if 'imagen' in request.files:
            img = request.files['imagen']
            if img and img.filename:
                img_filename = secure_filename(img.filename)
                img_path = os.path.join('static', img_filename)
                img.save(img_path)
                imagen = '/' + img_path.replace('\\', '/')
        if 'archivo' in request.files:
            file = request.files['archivo']
            if file and file.filename:
                file_filename = secure_filename(file.filename)
                file_path = os.path.join('static', file_filename)
                file.save(file_path)
                archivo = '/' + file_path.replace('\\', '/')
        if 'enlace' in request.form:
            enlace = request.form['enlace'] if request.form['enlace'] else None
        with open('posts.json', 'r+', encoding='utf-8') as f:
            posts = json.load(f)
            posts.append({
                'user_id': session['user_id'],
                'texto': texto,
                'fecha': fecha,
                'comentarios': [],
                'imagen': imagen,
                'archivo': archivo,
                'enlace': enlace
            })
            f.seek(0)
            json.dump(posts, f, ensure_ascii=False, indent=2)
    with open('posts.json', 'r', encoding='utf-8') as f:
        posts = json.load(f)
    # Cargar usuarios para mostrar nombre y foto
    users = {u.id: u for u in User.query.all()}
    # Asegurar que todos los user_id de posts y comentarios existen en users
    for p in posts:
        if p['user_id'] not in users:
            users[p['user_id']] = type('FakeUser', (), {'username': 'Usuario eliminado', 'profile_pic': '/static/default.png'})()
        for c in p.get('comentarios', []):
            if c['user_id'] not in users:
                users[c['user_id']] = type('FakeUser', (), {'username': 'Usuario eliminado', 'profile_pic': '/static/default.png'})()
    return render_template('feed.html', posts=posts, users=users, user=User.query.get(session['user_id']))

def agregar_notificacion(user_id, mensaje, url):
    notif_file = f'notificaciones_{user_id}.json'
    notifs = []
    if os.path.exists(notif_file):
        with open(notif_file, 'r', encoding='utf-8') as f:
            notifs = json.load(f)
    notifs.append({
        'mensaje': mensaje,
        'url': url,
        'leida': False,
        'fecha': datetime.now().strftime('%d/%m/%Y %H:%M')
    })
    with open(notif_file, 'w', encoding='utf-8') as f:
        json.dump(notifs, f, ensure_ascii=False, indent=2)

# --- Marcar notificaciones como leídas al visitar la URL ---
def marcar_notificaciones_leidas(user_id, url):
    notif_file = f'notificaciones_{user_id}.json'
    if os.path.exists(notif_file):
        with open(notif_file, 'r+', encoding='utf-8') as f:
            notifs = json.load(f)
            for n in notifs:
                if n['url'] == url:
                    n['leida'] = True
            f.seek(0)
            json.dump(notifs, f, ensure_ascii=False, indent=2)
            f.truncate()

@app.route('/comentar/<int:post_id>', methods=['POST'])
def comentar(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comentario = request.form['comentario']
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    with open('posts.json', 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            post.setdefault('comentarios', []).append({
                'user_id': session['user_id'],
                'comentario': comentario,
                'fecha': fecha
            })
            # Notificación al dueño del post si no es el mismo usuario
            if post['user_id'] != session['user_id']:
                agregar_notificacion(post['user_id'], "Alguien ha comentado tu publicación", '/feed')
            f.seek(0)
            json.dump(posts, f, ensure_ascii=False, indent=2)
    return redirect(url_for('feed'))

@app.route('/foro_comentar/<int:foro_id>/<int:post_id>', methods=['POST'])
def foro_comentar(foro_id, post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comentario = request.form['comentario']
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    posts_file = f'foro_{foro_id}.json'
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            post.setdefault('comentarios', []).append({
                'user_id': session['user_id'],
                'comentario': comentario,
                'fecha': fecha
            })
            # Notificación al dueño del post si no es el mismo usuario
            if post['user_id'] != session['user_id']:
                agregar_notificacion(post['user_id'], "Alguien ha comentado tu publicación", f'/foro/{foro_id}')
            f.seek(0)
            json.dump(posts, f, ensure_ascii=False, indent=2)
    return redirect(url_for('foro', foro_id=foro_id))

# Ruta de chat tipo foro
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not os.path.exists('chat.json'):
        with open('chat.json', 'w', encoding='utf-8') as f:
            json.dump([], f)
    if request.method == 'POST':
        mensaje = request.form['mensaje']
        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        with open('chat.json', 'r+', encoding='utf-8') as f:
            mensajes = json.load(f)
            mensajes.append({'user_id': session['user_id'], 'mensaje': mensaje, 'fecha': fecha})
            f.seek(0)
            json.dump(mensajes, f, ensure_ascii=False, indent=2)
    with open('chat.json', 'r', encoding='utf-8') as f:
        mensajes = json.load(f)
    users = {u.id: u for u in User.query.all()}
    return render_template('chat.html', mensajes=mensajes, users=users, user=User.query.get(session['user_id']))

# Ruta de perfil
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        username = request.form['username']
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join('static', filename)
                file.save(filepath)
                user.profile_pic = '/' + filepath.replace('\\', '/')
        user.username = username
        db.session.commit()
        flash('Perfil actualizado')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

# Crear foro
@app.route('/crear_foro', methods=['GET', 'POST'])
def crear_foro():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        titulo = request.form['titulo']
        tematica = request.form['tematica']
        icono = None
        if 'icono' in request.files:
            file = request.files['icono']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join('static', filename)
                file.save(filepath)
                icono = '/' + filepath.replace('\\', '/')
        foro = Foro(titulo=titulo, tematica=tematica, icono=icono)
        db.session.add(foro)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('crear_foro.html')

# Buscar foros (búsqueda simple)
@app.route('/buscar')
def buscar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    q = request.args.get('q', '')
    foros = Foro.query.filter(
        (Foro.titulo.ilike(f'%{q}%')) | (Foro.tematica.ilike(f'%{q}%'))
    ).all()
    user = User.query.get(session['user_id'])
    notif_file = f'notificaciones_{user.id}.json'
    notifs = []
    notif_count = 0
    if os.path.exists(notif_file):
        with open(notif_file, 'r', encoding='utf-8') as f:
            all_notifs = json.load(f)
            notifs = [n for n in all_notifs if not n.get('leida')]
            notif_count = len(notifs)
    return render_template('home.html', foros=foros, user=user, notif_count=notif_count, notifs=notifs)

# Ruta de logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# Publicaciones de foros se guardan en archivos foro_<id>.json
@app.route('/foro/<int:foro_id>', methods=['GET', 'POST'])
def foro(foro_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    marcar_notificaciones_leidas(session['user_id'], f'/foro/{foro_id}')
    foro = Foro.query.get_or_404(foro_id)
    posts_file = f'foro_{foro_id}.json'
    if not os.path.exists(posts_file):
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
    if request.method == 'POST':
        texto = request.form['texto']
        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        imagen = None
        archivo = None
        enlace = None
        if 'imagen' in request.files:
            img = request.files['imagen']
            if img and img.filename:
                img_filename = str(uuid.uuid4()) + '_' + secure_filename(img.filename)
                img_path = os.path.join('static', img_filename)
                img.save(img_path)
                imagen = '/' + img_path.replace('\\', '/')
        if 'archivo' in request.files:
            file = request.files['archivo']
            if file and file.filename:
                file_filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
                file_path = os.path.join('static', file_filename)
                file.save(file_path)
                archivo = '/' + file_path.replace('\\', '/')
        if 'enlace' in request.form:
            enlace = request.form['enlace'] if request.form['enlace'] else None
        with open(posts_file, 'r+', encoding='utf-8') as f:
            posts = json.load(f)
            posts.append({
                'user_id': session['user_id'],
                'texto': texto,
                'fecha': fecha,
                'comentarios': [],
                'imagen': imagen,
                'archivo': archivo,
                'enlace': enlace,
                'likes': 0
            })
            # Notificación al dueño del foro si no es el mismo usuario
            if hasattr(foro, 'user_id') and foro.user_id and foro.user_id != session['user_id']:
                agregar_notificacion(foro.user_id, "Alguien ha publicado en tu foro", f'/foro/{foro.id}')
            f.seek(0)
            json.dump(posts, f, ensure_ascii=False, indent=2)
    with open(posts_file, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    users = {u.id: u for u in User.query.all()}
    # Asegurar que todos los user_id de posts y comentarios existen en users
    for p in posts:
        if p['user_id'] not in users:
            users[p['user_id']] = type('FakeUser', (), {'username': 'Usuario eliminado', 'profile_pic': '/static/default.png'})()
        for c in p.get('comentarios', []):
            if c['user_id'] not in users:
                users[c['user_id']] = type('FakeUser', (), {'username': 'Usuario eliminado', 'profile_pic': '/static/default.png'})()
    user = User.query.get(session['user_id'])
    return render_template('foro.html', foro=foro, posts=posts, users=users, user=user)

@app.route('/foro_like/<int:foro_id>/<int:post_id>', methods=['POST'])
def foro_like(foro_id, post_id):
    posts_file = f'foro_{foro_id}.json'
    if not os.path.exists(posts_file):
        return redirect(url_for('foro', foro_id=foro_id))
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            if 'likes' not in posts[post_id]:
                posts[post_id]['likes'] = 0
            posts[post_id]['likes'] += 1
            f.seek(0)
            json.dump(posts, f, ensure_ascii=False, indent=2)
    return redirect(url_for('foro', foro_id=foro_id))


def foro_comentar(foro_id, post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comentario = request.form['comentario']
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    posts_file = f'foro_{foro_id}.json'
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            post.setdefault('comentarios', []).append({
                'user_id': session['user_id'],
                'comentario': comentario,
                'fecha': fecha
            })
            # Notificación al dueño del post si no es el mismo usuario
            if post['user_id'] != session['user_id']:
                agregar_notificacion(post['user_id'], "Alguien ha comentado tu publicación", f'/foro/{foro_id}')
            f.seek(0)
            json.dump(posts, f, ensure_ascii=False, indent=2)
    return redirect(url_for('foro', foro_id=foro_id))

@app.route('/foro_chat/<int:foro_id>', methods=['GET', 'POST'])
def foro_chat(foro_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    foro = Foro.query.get_or_404(foro_id)
    chat_file = f'foro_chat_{foro_id}.json'
    if not os.path.exists(chat_file):
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
    if request.method == 'POST':
        mensaje = request.form['mensaje']
        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        with open(chat_file, 'r+', encoding='utf-8') as f:
            mensajes = json.load(f)
            mensajes.append({'user_id': session['user_id'], 'mensaje': mensaje, 'fecha': fecha})
            f.seek(0)
            json.dump(mensajes, f, ensure_ascii=False, indent=2)
    with open(chat_file, 'r', encoding='utf-8') as f:
        mensajes = json.load(f)
    users = {u.id: u for u in User.query.all()}
    return render_template('foro_chat.html', foro=foro, mensajes=mensajes, users=users)

@app.route('/eliminar_comentario/<int:post_id>/<int:comentario_id>', methods=['POST'])
def eliminar_comentario(post_id, comentario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with open('posts.json', 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if 0 <= comentario_id < len(post.get('comentarios', [])):
                comentario = post['comentarios'][comentario_id]
                # Solo el autor del post puede eliminar cualquier comentario, o el autor del comentario puede eliminar el suyo
                if post['user_id'] == session['user_id'] or comentario['user_id'] == session['user_id']:
                    post['comentarios'].pop(comentario_id)
                    f.seek(0)
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                    f.truncate()
    return redirect(url_for('feed'))

@app.route('/eliminar_post/<int:post_id>', methods=['POST'])
def eliminar_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with open('posts.json', 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if post['user_id'] == session['user_id']:
                posts.pop(post_id)
                f.seek(0)
                json.dump(posts, f, ensure_ascii=False, indent=2)
                f.truncate()
    return redirect(url_for('feed'))

@app.route('/editar_comentario/<int:post_id>/<int:comentario_id>', methods=['GET', 'POST'])
def editar_comentario(post_id, comentario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with open('posts.json', 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if 0 <= comentario_id < len(post.get('comentarios', [])):
                comentario = post['comentarios'][comentario_id]
                if comentario['user_id'] != session['user_id']:
                    return redirect(url_for('feed'))
                if request.method == 'POST':
                    nuevo = request.form['comentario']
                    comentario['comentario'] = nuevo
                    f.seek(0)
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                    f.truncate()
                    return redirect(url_for('feed'))
                # Renderizar formulario de edición
                return render_template('editar_comentario.html', post_id=post_id, comentario_id=comentario_id, comentario=comentario['comentario'])
    return redirect(url_for('feed'))

@app.route('/foro_eliminar_post/<int:foro_id>/<int:post_id>', methods=['POST'])
def foro_eliminar_post(foro_id, post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    posts_file = f'foro_{foro_id}.json'
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if post['user_id'] == session['user_id']:
                posts.pop(post_id)
                f.seek(0)
                json.dump(posts, f, ensure_ascii=False, indent=2)
                f.truncate()
    return redirect(url_for('foro', foro_id=foro_id))

@app.route('/foro_editar_post/<int:foro_id>/<int:post_id>', methods=['GET', 'POST'])
def foro_editar_post(foro_id, post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    posts_file = f'foro_{foro_id}.json'
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if post['user_id'] != session['user_id']:
                return redirect(url_for('foro', foro_id=foro_id))
            if request.method == 'POST':
                texto = request.form['texto']
                post['texto'] = texto
                f.seek(0)
                json.dump(posts, f, ensure_ascii=False, indent=2)
                f.truncate()
                return redirect(url_for('foro', foro_id=foro_id))
            return render_template('editar_comentario.html', post_id=post_id, comentario_id=None, comentario=post['texto'], foro_id=foro_id, editar_post=True)
    return redirect(url_for('foro', foro_id=foro_id))

@app.route('/foro_editar_comentario/<int:foro_id>/<int:post_id>/<int:comentario_id>', methods=['GET', 'POST'])
def foro_editar_comentario(foro_id, post_id, comentario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    posts_file = f'foro_{foro_id}.json'
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if 0 <= comentario_id < len(post.get('comentarios', [])):
                comentario = post['comentarios'][comentario_id]
                if comentario['user_id'] != session['user_id']:
                    return redirect(url_for('foro', foro_id=foro_id))
                if request.method == 'POST':
                    nuevo = request.form['comentario']
                    comentario['comentario'] = nuevo
                    f.seek(0)
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                    f.truncate()
                    return redirect(url_for('foro', foro_id=foro_id))
                return render_template('editar_comentario.html', post_id=post_id, comentario_id=comentario_id, comentario=comentario['comentario'], foro_id=foro_id)
    return redirect(url_for('foro', foro_id=foro_id))

@app.route('/notificaciones')
def notificaciones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    notif_file = f'notificaciones_{session["user_id"]}.json'
    notifs = []
    if os.path.exists(notif_file):
        with open(notif_file, 'r', encoding='utf-8') as f:
            notifs = json.load(f)
    return render_template('notificaciones.html', notifs=notifs, user=User.query.get(session['user_id']))

@app.route('/notificaciones_leer', methods=['POST'])
def notificaciones_leer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    notif_file = f'notificaciones_{session["user_id"]}.json'
    if os.path.exists(notif_file):
        with open(notif_file, 'r+', encoding='utf-8') as f:
            notifs = json.load(f)
            for n in notifs:
                n['leida'] = True
            f.seek(0)
            json.dump(notifs, f, ensure_ascii=False, indent=2)
            f.truncate()
    return redirect(url_for('notificaciones'))

@app.route('/notificaciones_json')
def notificaciones_json():
    if 'user_id' not in session:
        return []
    notif_file = f'notificaciones_{session["user_id"]}.json'
    notifs = []
    if os.path.exists(notif_file):
        with open(notif_file, 'r', encoding='utf-8') as f:
            notifs = json.load(f)
    return notifs

@app.route('/foro_eliminar_comentario/<int:foro_id>/<int:post_id>/<int:comentario_id>', methods=['POST'])
def foro_eliminar_comentario(foro_id, post_id, comentario_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    posts_file = f'foro_{foro_id}.json'
    with open(posts_file, 'r+', encoding='utf-8') as f:
        posts = json.load(f)
        if 0 <= post_id < len(posts):
            post = posts[post_id]
            if 0 <= comentario_id < len(post.get('comentarios', [])):
                comentario = post['comentarios'][comentario_id]
                # El autor del post puede eliminar cualquier comentario, o el autor del comentario puede eliminar el suyo
                if post['user_id'] == session['user_id'] or comentario['user_id'] == session['user_id']:
                    post['comentarios'].pop(comentario_id)
                    f.seek(0)
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                    f.truncate()
    return redirect(url_for('foro', foro_id=foro_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)