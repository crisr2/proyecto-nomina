# Proyecto Nomina - Programación Avanzada Tercer Corte

### **Integrantes: Natalia Osejo Hincapie, Jonathan Alejandro Perilla Gaitan, Cristian David Reyes Valero**

Esta es una aplicación de API REST desarrollada en Python que implementa el framework de Flask, e implementa una base de datos SQLite para gestionar empleados y sus respectivos detalles. 
La aplicación proporciona diferentes rutas para realizar operaciones CRUD (crear, leer, actualizar y eliminar) en la base de datos. Además, la aplicación genera un reporte de pago en formato PDF y envía un correo electrónico al empleado con el reporte adjunto.

La API tiene varias rutas para obtener información de los empleados, actualizar la información de un empleado, eliminar un empleado y crear un nuevo empleado. También hay una ruta para generar un informe de pago en formato PDF y enviarlo por correo electrónico al empleado.

El código incluye una función de autenticación que verifica las credenciales de inicio de sesión y los permisos de usuario. La función de autenticación utiliza Basic Auth dentro de Postman para autenticar al usuario, además se utiliza APScheduler para programar el envío de informes de pago a los empleados a las 6pm todos los días por medio de SendGrid API para el envio de los correos electrónicos a los empleados.

La lista de dependencias y librerias utilizadas se encuentran en el archivo requirements.txt
