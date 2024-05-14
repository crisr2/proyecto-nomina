# Importar las librerias y dependencias utilizadas
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import date
from reportlab.pdfgen import canvas
from flask import send_file
from apscheduler.schedulers.background import BackgroundScheduler
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName, FileType, Disposition)
import base64, os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
scheduler = BackgroundScheduler()

# Crea el modelo de Empleado de la base de datos
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50), nullable = False)
    email = db.Column(db.String(50), nullable = False)
    phone = db.Column(db.String(11), nullable = False)
    direction = db.Column(db.String(50), nullable = False)
    department = db.Column(db.String(50), nullable = False)
    salary = db.Column(db.Integer, nullable = False)
    password = db.Column(db.String(50), nullable = False)

    # Función para convertir los datos a formato JSON
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'direction': self.direction,
            'department': self.department,
            'salary': self.salary,
            'password': self.password
        }
    
# Función para añadir registros de empleados predeterminados
def add_default_employees():
    db.session.add(Employee(name="Natalia", phone="(345) 389-6780", direction="105-30 Union St.", email="natalia.osejoh@utadeo.edu.co", department="HR", salary=50000, password='password'))
    db.session.add(Employee(name="Cristian", phone="(123) 379-7895", direction="320 Madison St.", email="cristiand.reyesv@utadeo.edu.co", department="IT", salary=20000, password='password'))
    db.session.add(Employee(name="Jonathan", phone="(456) 389-7823", direction="N2W1700 County Rd.", email="jonathana.perillag@utadeo.edu.co", department="Finance", salary=70000, password='password'))
    db.session.commit()

# Verificar si la base de datos existe y cargarla, o crearla con registros predeterminados
with app.app_context():
    if not os.path.exists('instance/contacts.db'):
        db.drop_all()
        db.create_all()
        add_default_employees()
    else:
        db.create_all()

# Pagina raiz de la API
@app.route('/')
def root():
    return 'Bienvenido a la API REST de Nomina, desarrollada por Natalia Osejo, Jonathan Perilla, Cristian Reyes'

# Crear las diferentes rutas 
# http://127.0.0.1:5000/employees - Para ver empleados
@app.route('/employees', methods = ['GET'])
def get_employees():
    employees = Employee.query.all()
    list_employee = []
    for employee in employees:
        list_employee.append(employee.serialize())
    return jsonify(list_employee)

# http://127.0.0.1:5000/employees/1 - Para obtener un empleado por su ID
@app.route('/employees/<int:id>', methods=['GET'])
def get_employee(id):
    employee = db.session.get(Employee, id)
    if not employee:
        return jsonify({'message': 'Empleado no encontrado'}), 404
    return jsonify(employee.serialize())

#-------------- Inicio de sesión, permisos de gestión humana (creación, eliminación y edición de usuarios)
# Función para verificar la autenticación del usuario y su rol
def authenticate(email, password):
    user = Employee.query.filter_by(email=email, password=password).first()
    return user

# Función para requerir autenticación y verificar los permisos de usuario, utiliza Basi Auth dentro de postman (AUTH)
def login_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.authorization
            if not auth or not auth.username or not auth.password:
                return jsonify({'message': 'Credenciales de inicio de sesión faltantes'}), 401

            user = authenticate(auth.username, auth.password)
            if not user:
                return jsonify({'message': 'Credenciales de inicio de sesión inválidas'}), 401
            
            elif (user.department != role and role != 'all'):
                return jsonify({'message': 'Permiso denegado'}), 403
                    
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# Endpoint para iniciar sesión, utiliza Basic Auth dentro de postman (AUTH)
@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Credenciales de inicio de sesión faltantes'}), 401

    user = authenticate(auth.username, auth.password)
    if not user:
        return jsonify({'message': 'Credenciales de inicio de sesión inválidas'}), 401        

    return jsonify({'message': 'Inicio de sesión exitoso'}), 200

# Endpoint protegido que requiere autenticación, cualquier persona puede cambiar sus datos personales (name, phone, direction, password)
@app.route('/employees/update_my_info', methods=['PUT'])
@login_required('all')
def update_personal_info():
    auth = request.authorization
    user = Employee.query.filter_by(email=auth.username).first()
    if user:
        data = request.get_json()
        if any(field in data for field in ['salary', 'department', 'email']):
            return jsonify({'message': 'Permiso denegado: No tiene permitido modificar el salario, el departamento o el correo electrónico'}), 403
        else:
            if 'name' in data:
                user.name = data['name']
            if 'phone' in data:
                user.phone = data['phone']
            if 'direction' in data:
                user.direction = data['direction']
            if 'password' in data:
                user.password = data['password']
            db.session.commit()

            return jsonify({'message': 'Información personal actualizada exitosamente','my info':user.serialize()}), 200
    else:
        return jsonify({'message': 'Error: No se pudo actualizar la información personal'}), 500
    
# Endpoint protegido que requiere autenticación y privilegios de HR (solo departamento de gestión humana puede editar registros)
@app.route('/employees/update_employee/<int:id>', methods=['PUT'])
@login_required('HR')
def update_employee(id):
    auth = request.authorization
    user = Employee.query.filter_by(email=auth.username).first()
    if user:
        data = request.get_json()
        employee = db.session.get(Employee, id)
        if not employee:
            return jsonify({'message': 'Error: Usuario no encontrado'}), 404
        elif (user.id == id): # Verificar si el usuario autenticado intentó cambiar sus propios datos
                return jsonify({'message': 'Permiso denegado: No puede cambiar sus propios datos desde aquí'}), 403
        else: 
            if 'password' in data:
                return jsonify({'message': 'Permiso denegado: No tiene permitido modificar la contraseña del usuario'}), 403
            else:
                if 'name' in data:
                    employee.name = data['name']
                if 'email' in data:
                    employee.email = data['email']
                if 'phone' in data:
                    employee.phone = data['phone']
                if 'direction' in data:
                    employee.direction = data['direction']
                if 'department' in data:
                    employee.department = data['department']
                if 'salary' in data:
                    employee.salary = data['salary']
                
                db.session.commit()
                return jsonify({'message': 'Información del empleado actualizada con exito','employee':employee.serialize()}), 200
    else:
        return jsonify({'message': 'Error: No se pudo actualizar el registro'}), 500

# Endpoint protegido que requiere autenticación y privilegios de HR (solo departamento de gestión humana puede borrar registros)
@app.route('/employees/delete_employee/<int:id>', methods=['DELETE'])
@login_required('HR')
def delete_employee(id):
    auth = request.authorization
    user = Employee.query.filter_by(email=auth.username).first()
    if user:
        employee = db.session.get(Employee, id)
        if not employee:
            return jsonify({'message': 'Error: Usuario no encontrado'}), 404
        elif (user.id == id): # Verificar si el usuario autenticado intentó borrar su registro
            return jsonify({'message': 'Permiso denegado: No puede borrar su propio registro'}), 403
        else:
            db.session.delete(employee)
            db.session.commit()

            return jsonify({'message': 'Empleado despedido con éxito'})
    else:
        return jsonify({'message': 'Error: No se pudo borrar el registro'}), 500
    
# Endpoint protegido que requiere autenticación y privilegios de HR (solo departamento de gestión humana puede crear registros)
@app.route('/employees/create_employee', methods=['POST'])
@login_required('HR')
def create_employee():
    data = request.get_json()
    employee =  Employee(name = data['name'], email = data['email'], phone = data['phone'], direction = data['direction'], department = data['department'], salary = data['salary'], password = "password")
    db.session.add(employee)
    db.session.commit()
    return jsonify({'message': 'Empleado contratado con exito','employee':employee.serialize()}), 201

#------------- Desprendible de pagos
# http://127.0.0.1:5000/employees/report/id - Para ver su desprendible de pago 
@app.route('/employees/report', methods = ['GET'])
@login_required('all')
def report():
    auth = request.authorization
    employee = Employee.query.filter_by(email=auth.username).first()
    if not employee:
        return jsonify({'message': 'Error: Usuario no encontrado'}), 404

    salary = employee.salary
    email = employee.email
    phone = employee.phone
    direction = employee.direction
    today = date.today()
    name = employee.name
    
    pdf_path = f"desprendibles/Reporte - {name}.pdf"
    pdf = canvas.Canvas(pdf_path)
    title = pdf.beginText(150, 750)
    title.setFont("Helvetica", 30)
    title.textLine("REPORTE DE PAGO") 
    pdf.line(5, 720, 590, 720)
    pdf.rect(20, 300, 550, 150)
    infoTitle = pdf.beginText(100, 420)
    infoTitle.setFont("Helvetica", 20)
    infoTitle.textLine("INFORMACION PERSONAL DEL EMPLEAD@")
    info = pdf.beginText(40, 380)
    info.setFont("Helvetica", 18)
    info.textLines(f"Nombre: {name}                          Correo: {email}\n \nCelular: {phone}           Dirección: {direction} ")
    text = pdf.beginText(20, 680)
    text.setFont("Helvetica", 18)
    text.textLines(f"Cordial saludo querido emplead@ {name} \n\nSe le informa que ya se realizo el pago de su salario ${salary}, el pago \nfue  realizado el {today}, se envió comprobante a \nla siguente dirección de correo electronico: {email}. \n\nUn abrazo y un feliz día.\n\n Cordialmente Jefe.")
    pdf.drawText(title)
    pdf.drawText(infoTitle)
    pdf.drawText(info)
    pdf.drawText(text)
    pdf.save()

    with open(pdf_path, "rb") as file:
        invoice_data = file.read()
        invoice_encoded = base64.b64encode(invoice_data).decode()

    send_email(email, invoice_encoded, pdf_path)
    return send_file(pdf_path, as_attachment=True)

#------- Emails y notificaciones
# Función para generar desprendibles de pagos de todos los usuarios usada por la función send_invoices()  
def report_all(id):
    employee = db.session.get(Employee, id)
    if not employee:
        return jsonify({'message': 'Error: Usuario no encontrado'}), 404

    salary = employee.salary
    email = employee.email
    phone = employee.phone
    direction = employee.direction
    today = date.today()
    name = employee.name
    
    pdf_path = f"desprendibles/Reporte - {name}.pdf"
    pdf = canvas.Canvas(pdf_path)
    title = pdf.beginText(150, 750)
    title.setFont("Helvetica", 30)
    title.textLine("REPORTE DE PAGO") 
    pdf.line(5, 720, 590, 720)
    pdf.rect(20, 300, 550, 150)
    infoTitle = pdf.beginText(100, 420)
    infoTitle.setFont("Helvetica", 20)
    infoTitle.textLine("INFORMACION PERSONAL DEL EMPLEAD@")
    info = pdf.beginText(40, 380)
    info.setFont("Helvetica", 18)
    info.textLines(f"Nombre: {name}                          Correo: {email}\n \nCelular: {phone}           Dirección: {direction} ")
    text = pdf.beginText(20, 680)
    text.setFont("Helvetica", 18)
    text.textLines(f"Cordial saludo querido emplead@ {name} \n\nSe le informa que ya se realizo el pago de su salario ${salary}, el pago \nfue  realizado el {today}, se envió comprobante a \nla siguente dirección de correo electronico: {email}. \n\nUn abrazo y un feliz día.\n\n Cordialmente Jefe.")
    pdf.drawText(title)
    pdf.drawText(infoTitle)
    pdf.drawText(info)
    pdf.drawText(text)
    pdf.save()

    return pdf_path

# Función para enviar un correo electronico a una dirección de destino (receiver), con un archivo comprimido a base64 (base64_file) y la ruta en que se encuentra el archivo PDF (pdf_path)
def send_email(receiver, base64_file, pdf_path)-> bool:
    # Configura la API de SendGrid con tu clave API
    sg = SendGridAPIClient('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')

    # Crea el objeto adjunto
    adjunto = Attachment(
        FileContent(base64_file),
        FileName(os.path.basename(pdf_path)),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    # Crea el correo electrónico
    message = Mail(
        from_email="jonathana.perillag@utadeo.edu.co",  
        to_emails=receiver,
        subject="Pago automatico de nomina.",
        html_content="<p>Se ha generado un pago de nomina automaticamente de parte de su empresa, por favor verifique el archivo adjunto para mas detalles.</p>"
    )
    # Adjunta el archivo al correo electrónico
    message.attachment = adjunto
    response = sg.send(message)
    print(response.status_code)

# Endpoint para enviar desprendibles de pagos a todos los empleados
@app.route('/send-invoices', methods=['GET'])
def send_invoices():
    with app.app_context():
        employees = Employee.query.all()
        for employee in employees:
            pdf_path = report_all(employee.id)
            with open(pdf_path, "rb") as file:
                invoice_data = file.read()
                invoice_encoded = base64.b64encode(invoice_data).decode()
            send_email(employee.email, invoice_encoded, pdf_path)

        return jsonify({'message': 'Pagos de nominas enviados exitosamente'}), 200

# Programar el envio de correo para que se ejecute a las 6pm todos los días
with app.app_context():
    scheduler.add_job(send_invoices, 'cron', hour=18, minute=00)
    scheduler.start()

# Ejecutar la API 
if __name__ == '__main__':
    app.run(debug=True)
