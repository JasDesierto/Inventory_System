from app import create_app

# Production WSGI entry point used by Waitress and similar servers.
app = create_app()
