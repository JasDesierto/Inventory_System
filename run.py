from app import create_app

# Development entry point used by `python run.py`.
app = create_app()


if __name__ == "__main__":
    app.run()
