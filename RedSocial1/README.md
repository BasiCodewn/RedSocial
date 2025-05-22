# Red Social Flask

Una red social web desarrollada con Flask, SQLite y Bootstrap, que permite a los usuarios registrarse, iniciar sesión, crear publicaciones, comentar, dar likes, participar en foros temáticos y chatear en tiempo real. El diseño es responsivo y moderno, adaptado tanto para escritorio como para dispositivos móviles.

## Características principales

- **Registro y login de usuarios** con almacenamiento seguro en SQLite.
- **Perfil de usuario** editable (nombre y foto), con card de perfil destacado en la home.
- **Feed principal** de publicaciones con adjuntos (imágenes, archivos, enlaces), comentarios y likes.
- **Gestión de publicaciones y comentarios**: edición y eliminación solo por el dueño, y permisos diferenciados en comentarios.
- **Foros temáticos**: creación, búsqueda, listado, publicaciones y comentarios independientes por foro.
- **Chat general y chat por foro** en tiempo real, ambos responsivos.
- **Sistema de notificaciones** visuales y de escritorio:
  - Aviso de nuevos comentarios en tus publicaciones.
  - Aviso de nuevas publicaciones en foros que administras.
  - Contador de notificaciones no leídas, que se actualiza automáticamente.
- **Botón flotante** para volver arriba en el feed.
- **Manejo de usuarios eliminados** en posts y comentarios.
- **Diseño responsivo** y elegante con Bootstrap 5.

## Estructura del proyecto

```
RedSocial1/
│   app.py                # Lógica principal de la aplicación Flask
│   users.db              # Base de datos SQLite de usuarios
│   posts.json            # Publicaciones del feed principal
│   chat.json             # Mensajes del chat general
│   foro_<id>.json        # Publicaciones de cada foro temático
│   foro_chat_<id>.json   # Mensajes de chat por foro
│   notificaciones_<id>.json # Notificaciones por usuario
│   static/               # Archivos estáticos (CSS, imágenes, etc.)
│   templates/            # Plantillas HTML (Jinja2)
│   ...
```

## Instalación y ejecución

1. Clona este repositorio o descarga el código fuente.
2. Instala las dependencias necesarias:
   ```bash
   pip install flask flask_sqlalchemy
   ```
3. Ejecuta la aplicación:
   ```bash
   python app.py
   ```
4. Accede a `http://localhost:5000` en tu navegador.

## Créditos y agradecimientos

- Desarrollado con [Flask](https://flask.palletsprojects.com/), [Bootstrap 5](https://getbootstrap.com/) y [Jinja2](https://jinja.palletsprojects.com/).
- Iconos e imágenes de ejemplo de uso libre.

---

> Proyecto académico y de aprendizaje. ¡Explora, comparte y conecta!
