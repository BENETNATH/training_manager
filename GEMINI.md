# Project Overview

This is a Python Flask web application designed for managing training activities, skills, and user competencies within an organization. It features user authentication, role-based access (admin, team lead), and a comprehensive data model for tracking users, teams, species, skills, training paths, training sessions, and various training-related events (requests, external trainings, skill practices, competencies). The application supports internationalization (French and English) and integrates with a MariaDB database. It can be deployed using Docker and uses `gunicorn` as a WSGI HTTP server.

## Key Technologies

*   **Backend:** Python, Flask
*   **Database:** MariaDB (via Docker), SQLite (for local development/testing)
*   **ORM:** SQLAlchemy, Flask-Migrate
*   **Authentication:** Flask-Login
*   **Internationalization:** Flask-Babel
*   **Email:** Flask-Mail
*   **API:** Flask-RESTX
*   **Deployment:** Docker, Docker Compose, Gunicorn
*   **Testing:** Pytest
*   **Data Seeding:** Faker

# Building and Running

The project can be built and run using Docker Compose, or directly using Python and `gunicorn`.

## Using Docker Compose

1.  **Prerequisites:** Ensure Docker and Docker Compose are installed on your system.
2.  **Environment Configuration:** Create a `.env` file in the project root directory. You can use the provided `.env` file as a template. Fill in the necessary environment variables, especially `SECRET_KEY`, database credentials (`DB_ROOT_PASSWORD`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), and mail server settings (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`). Also, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` for the initial admin user.
3.  **Build and Run:** Navigate to the project root in your terminal and execute:
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker images (if they don't exist or have changed) and start the `db` (MariaDB) and `app` (Flask application) services.
4.  **Access the Application:** Once the services are up and running, the Flask application will be accessible at `http://localhost:5001`.

## Local Development (without Docker)

1.  **Prerequisites:**
    *   Python 3.9+
    *   A database server (e.g., MariaDB/MySQL or SQLite).
2.  **Virtual Environment Setup:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Environment Configuration:** Create a `.env` file in the project root, similar to the provided `.env` file. Configure `SECRET_KEY`, mail settings, and admin credentials. For the database, you can either:
    *   Use SQLite (default if `DATABASE_URL` is not set in `.env`): `SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'` in `config.py` or `.env`.
    *   Connect to an external MariaDB/MySQL instance: Set `DATABASE_URL` in your `.env` file (e.g., `DATABASE_URL="mysql+pymysql://user:password@host/db_name"`).
5.  **Database Migrations:**
    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```
6.  **Seeding (Optional):** To populate the database with dummy data for development:
    ```bash
    python seed.py
    ```
7.  **Run the Application:**
    ```bash
    gunicorn --bind 0.0.0.0:5000 flask_app:app
    ```
    Alternatively, for a simpler development server (not recommended for production):
    ```bash
    export FLASK_APP=flask_app.py
    flask run
    ```

# Testing

The project uses `pytest` for running tests.

To execute the test suite:
```bash
pytest
```

# Development Conventions

*   **Flask Blueprints:** The application is structured using Flask Blueprints for modularity, organizing routes, forms, and templates into logical components (e.g., `auth`, `admin`, `profile`, `team`, `training`, `api`).
*   **SQLAlchemy ORM:** Database models and interactions are defined using SQLAlchemy, with schema management handled by Flask-Migrate.
*   **Internationalization (i18n):** Flask-Babel is used to support multiple languages (English and French), with locale detection based on browser preferences.
*   **Configuration:** Application settings are managed through environment variables, loaded from a `.env` file using `python-dotenv`, and accessed via the `Config` class.
*   **WSGI Server:** `gunicorn` is the recommended WSGI HTTP server for running the application in production environments.
*   **Data Generation:** The `seed.py` script leverages the `Faker` library to generate realistic dummy data for development and testing purposes.
