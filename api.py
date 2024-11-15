from flask import Flask, request, redirect, session, send_from_directory, url_for, render_template_string, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import os

class ChatApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "pinchellave"
        self.configure_mysql()
        CORS(self.app)
        self.set_routes()

    def configure_mysql(self):
        # Configuración de MySQL para Clever Cloud
        self.app.config['MYSQL_HOST'] = 'bnbfyw7jaj5jrh5onhwo-mysql.services.clever-cloud.com'
        self.app.config['MYSQL_USER'] = 'um3jmqoxa1rkafzt'
        self.app.config['MYSQL_PASSWORD'] = '8QxwoEzD7xcQ6gxzubIx'
        self.app.config['MYSQL_DB'] = 'bnbfyw7jaj5jrh5onhwo'
        self.app.config['MYSQL_PORT'] = 3306
        self.mysql = MySQL(self.app)

    def set_routes(self):
        routes = {
            '/': {'view_func': self.login, 'endpoint': 'login'},
            '/acceso-login': {'view_func': self.acceso_login, 'endpoint': 'acceso_login', 'methods': ["POST"]},
            '/chat': {'view_func': self.chat, 'endpoint': 'chat'},
            '/registrar': {'view_func': self.registrar, 'endpoint': 'registrar', 'methods': ["POST"]},
            '/enviar-mensaje': {'view_func': self.enviar_mensaje, 'endpoint': 'enviar_mensaje', 'methods': ["POST"]},
            '/chat-personal/<username>': {'view_func': self.chat_personal, 'endpoint': 'chat_personal', 'methods': ['GET']},
            '/<path:filename>': {'view_func': self.static_files, 'endpoint': 'static_files'},
            '/cambiar-perfil': {'view_func': self.cambiar_perfil, 'endpoint': 'cambiar_perfil', 'methods': ["POST"]}
        }
        for route, options in routes.items():
            self.app.add_url_rule(route, **options)

    # Vistas para el inicio de sesión y registro
    def login(self):
        return self.render_template('login.html')

    def acceso_login(self):
        email, password = request.form['email'], request.form['password']
        user = self.get_user(email, password)
        if user:
            self.create_session(user)
            return redirect(url_for('chat'))
        return "Usuario o contraseña incorrectos", 401

    # Vista para el chat principal
    def chat(self):
        if 'user_id' in session:
            username, image, rol = session.get('username'), session.get('image'), session.get('rol')
            users = self.get_all_users_except(username)
            return self.render_template('chat.html', username=username, image=image, users=users, rol=rol)
        return redirect(url_for('login'))

    def registrar(self):
        email, password, username, rol = (request.form['email'], request.form['password'], 
                                          request.form['username'], request.form['rol'])
        image = self.save_image(request.files['image'])
        if not image:
            return "El tipo de archivo no es válido. Por favor, sube una imagen.", 400
        if self.is_user_registered(email):
            return "El email ya está registrado.", 409
        self.create_user(email, password, username, image, rol)
        return redirect(url_for('login'))

    def enviar_mensaje(self):
        if 'user_id' in session:
            emisor, receptor, mensaje = session.get('username'), request.form['receptor'], request.form['mensaje']
            self.save_message(emisor, receptor, mensaje)
            return {'status': 'success'}, 200
        return redirect(url_for('login'))

    def chat_personal(self, username):
        if 'user_id' in session:
            emisor = session['username']
            mensajes = self.get_chat_messages(emisor, username)
            mensajes_formateados = '\n'.join([f"{msg[0]}: {msg[1]}" for msg in mensajes])
            return jsonify({'mensajes': mensajes_formateados})
        return redirect(url_for('login'))

    def cambiar_perfil(self):
        if 'user_id' in session:
            username = request.form['username']
            user = self.get_user_by_username(username)
            if user:
                self.update_session(user)
                return jsonify({'status': 'success', 'username': user[3], 'image': user[4]}), 200
            return jsonify({'status': 'error', 'message': 'Usuario no encontrado'}), 404
        return redirect(url_for('login'))

    def static_files(self, filename):
        return send_from_directory(os.getcwd(), filename)

    # Métodos auxiliares para la funcionalidad
    def render_template(self, template_name, **context):
        with open(f'templates/{template_name}', 'r', encoding='utf-8') as file:
            template = file.read()
        return render_template_string(template, **context)

    def get_user(self, email, password):
        cur = self.mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios WHERE email = %s AND password = %s', (email, password))
        user = cur.fetchone()
        cur.close()
        return user

    def get_all_users_except(self, username):
        cur = self.mysql.connection.cursor()
        cur.execute('SELECT username, image FROM usuarios WHERE username != %s', (username,))
        users = cur.fetchall()
        cur.close()
        return users

    def save_image(self, image):
        if image and self.allowed_file(image.filename):
            image_path = os.path.join('img', image.filename)
            os.makedirs('img', exist_ok=True)
            image.save(image_path)
            return image_path
        return None

    def is_user_registered(self, email):
        cur = self.mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        user_exists = cur.fetchone()
        cur.close()
        return user_exists

    def create_user(self, email, password, username, image, rol):
        cur = self.mysql.connection.cursor()
        cur.execute('INSERT INTO usuarios (email, password, username, image, rol) VALUES (%s, %s, %s, %s, %s)',
                    (email, password, username, image, rol))
        self.mysql.connection.commit()
        cur.close()

    def save_message(self, emisor, receptor, mensaje):
        cur = self.mysql.connection.cursor()
        cur.execute('INSERT INTO mensajes (emisor, receptor, mensaje) VALUES (%s, %s, %s)', (emisor, receptor, mensaje))
        self.mysql.connection.commit()
        cur.close()

    def get_chat_messages(self, emisor, receptor):
        cur = self.mysql.connection.cursor()
        cur.execute('''
            SELECT emisor, mensaje 
            FROM mensajes 
            WHERE (emisor = %s AND receptor = %s) OR (emisor = %s AND receptor = %s)
            ORDER BY id ASC
        ''', (emisor, receptor, receptor, emisor))
        mensajes = cur.fetchall()
        cur.close()
        return mensajes

    def get_user_by_username(self, username):
        cur = self.mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        return user

    def update_session(self, user):
        session['username'] = user[3]
        session['image'] = user[4]

    def allowed_file(self, filename):
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    def create_session(self, user):
        session['user_id'] = user[0]
        session['username'] = user[3]
        session['image'] = user[4]
        session['rol'] = user[5]

    def run(self):
        self.app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    chat_app = ChatApp()
    chat_app.run()
