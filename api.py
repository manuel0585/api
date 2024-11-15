from flask import Flask, request, redirect, session, send_from_directory, url_for, render_template_string, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import os

class ChatApp:
    def __init__(self):  # Cambiado a "__init__" con dos guiones bajos
        self.app = Flask(__name__)  # Usando Flask en lugar de FlaskLambda
        self.app.secret_key = "pinchellave"
        
        # Configuración de MySQL para Clever Cloud
        self.app.config['MYSQL_HOST'] = 'bnbfyw7jaj5jrh5onhwo-mysql.services.clever-cloud.com'
        self.app.config['MYSQL_USER'] = 'um3jmqoxa1rkafzt'
        self.app.config['MYSQL_PASSWORD'] = '8QxwoEzD7xcQ6gxzubIx'
        self.app.config['MYSQL_DB'] = 'bnbfyw7jaj5jrh5onhwo'
        self.app.config['MYSQL_PORT'] = 3306
        self.mysql = MySQL(self.app)
        
        # Habilitar CORS
        CORS(self.app)

        # Definir rutas
        self.set_routes()

    def set_routes(self):
        self.app.add_url_rule('/', 'login', self.login)
        self.app.add_url_rule('/acceso-login', 'acceso_login', self.acceso_login, methods=["POST"])
        self.app.add_url_rule('/chat', 'chat', self.chat)
        self.app.add_url_rule('/registrar', 'registrar', self.registrar, methods=["POST"])
        self.app.add_url_rule('/enviar-mensaje', 'enviar_mensaje', self.enviar_mensaje, methods=["POST"])
        self.app.add_url_rule('/chat-personal/<username>', 'chat_personal', self.chat_personal, methods=['GET'])
        self.app.add_url_rule('/<path:filename>', 'static_files', self.static_files)
        self.app.add_url_rule('/cambiar-perfil', 'cambiar_perfil', self.cambiar_perfil, methods=["POST"])

    def login(self):
        return send_from_directory(os.getcwd(), 'templates/login.html')

    def acceso_login(self):
        email = request.form['email']
        password = request.form['password']
        cur = self.mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios WHERE email = %s AND password = %s', (email, password))
        user = cur.fetchone()
        cur.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[3]
            session['image'] = user[4]
            session['rol'] = user[5]
            return redirect(url_for('chat'))
        else:
            return "Usuario o contraseña incorrectos", 401

    def chat(self):
        if 'user_id' in session:
            username = session.get('username')
            image = session.get('image')
            rol = session.get('rol')
            cur = self.mysql.connection.cursor()
            cur.execute('SELECT username, image FROM usuarios WHERE username != %s', (username,))
            users = cur.fetchall()
            cur.close()
            with open('templates/chat.html', 'r', encoding='utf-8') as file:
                chat_html = file.read()
            return render_template_string(chat_html, username=username, image=image, users=users, rol=rol)
        else:
            return redirect(url_for('login'))

    def registrar(self):
        email = request.form['email']
        password = request.form['password']
        username = request.form['username']
        rol = request.form['rol']
        image = request.files['image']
        if image and self.allowed_file(image.filename):
            image_path = os.path.join('img', image.filename)
            if not os.path.exists('img'):
                os.makedirs('img')
            image.save(image_path)
        else:
            return "El tipo de archivo no es válido. Por favor, sube una imagen.", 400
        cur = self.mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        user_exists = cur.fetchone()
        if user_exists:
            cur.close()
            return "El email ya está registrado.", 409
        cur.execute('INSERT INTO usuarios (email, password, username, image, rol) VALUES (%s, %s, %s, %s, %s)',
                    (email, password, username, image_path, rol))
        self.mysql.connection.commit()
        cur.close()
        return redirect(url_for('login'))

    def enviar_mensaje(self):
        if 'user_id' in session:
            emisor = session.get('username')
            receptor = request.form['receptor']
            mensaje = request.form['mensaje']
            cur = self.mysql.connection.cursor()
            cur.execute('INSERT INTO mensajes (emisor, receptor, mensaje) VALUES (%s, %s, %s)',
                        (emisor, receptor, mensaje))
            self.mysql.connection.commit()
            cur.close()
            return {'status': 'success'}, 200
        else:
            return redirect(url_for('login'))

    def chat_personal(self, username):
        if 'user_id' in session:
            emisor = session['username']
            cur = self.mysql.connection.cursor()
            cur.execute('''
                SELECT emisor, mensaje 
                FROM mensajes 
                WHERE (emisor = %s AND receptor = %s) OR (emisor = %s AND receptor = %s)
                ORDER BY id ASC
            ''', (emisor, username, username, emisor))
            mensajes = cur.fetchall()
            cur.close()
            mensajes_formateados = '\n'.join([f"{msg[0]}: {msg[1]}" for msg in mensajes])
            return jsonify({'mensajes': mensajes_formateados})
        else:
            return redirect(url_for('login'))

    def cambiar_perfil(self):
        if 'user_id' in session:
            username = request.form['username']
            cur = self.mysql.connection.cursor()
            cur.execute('SELECT * FROM usuarios WHERE username = %s', (username,))
            user = cur.fetchone()
            cur.close()
            if user:
                session['username'] = user[3]
                session['image'] = user[4]
                return jsonify({'status': 'success', 'username': user[3], 'image': user[4]}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Usuario no encontrado'}), 404
        else:
            return redirect(url_for('login'))

    def static_files(self, filename):
        return send_from_directory(os.getcwd(), filename)

    def allowed_file(self, filename):
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    def run(self):
        self.app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    chat_app = ChatApp()
    chat_app.run(host='0.0.0.0', port=5000)