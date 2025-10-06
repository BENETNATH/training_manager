# Training Manager Application

This is a Python Flask web application designed for managing training activities, skills, and user competencies within an organization. It features user authentication, role-based access (admin, team lead), and a comprehensive data model for tracking users, teams, species, skills, training paths, training sessions, and various training-related events (requests, external trainings, skill practices, competencies). The application supports internationalization (French and English) and integrates with a MariaDB database.

## Features

*   User Authentication and Role-Based Access (Admin, Team Lead)
*   Management of Users, Teams, Species, Skills
*   Training Path and Session Management
*   Tracking of Training Requests, External Trainings, Skill Practices, and Competencies
*   Internationalization (English and French)
*   RESTful API

## Technologies Used

*   **Backend:** Python, Flask
*   **Database:** MariaDB (via Docker), SQLite
*   **ORM:** SQLAlchemy, Flask-Migrate
*   **Authentication:** Flask-Login
*   **Internationalization:** Flask-Babel
*   **Email:** Flask-Mail
*   **API:** Flask-RESTX
*   **Deployment:** Docker, Docker Compose, Gunicorn
*   **Testing:** Pytest
*   **Data Seeding:** Faker

## Getting Started

### Using Docker Compose

1.  **Prerequisites:** Ensure Docker and Docker Compose are installed.
2.  **Environment Configuration:** Create a `.env` file in the project root (use `env-sample` as a template) and fill in necessary variables (`SECRET_KEY`, database credentials, mail settings, `ADMIN_EMAIL`, `ADMIN_PASSWORD`).
3.  **Build and Run:** Navigate to the project root and execute:
    ```bash
    docker-compose up --build
    ```
4.  **Access the Application:** The Flask application will be accessible at `http://localhost:5001`.

### Local Development (without Docker)

1.  **Prerequisites:** Python 3.9+, a database server (MariaDB/MySQL or SQLite).
2.  **Virtual Environment Setup:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Environment Configuration:** Create a `.env` file. Configure `SECRET_KEY`, mail settings, and admin credentials. For the database, set `SQLALCHEMY_DATABASE_URI` for SQLite or `DATABASE_URL` for MariaDB/MySQL.
5.  **Database Migrations:**
    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```
6.  **Seeding (Optional):**
    ```bash
    python seed.py
    ```
7.  **Run the Application:**
    ```bash
    gunicorn --bind 0.0.0.0:5000 flask_app:app
    ```
    (For development server: `export FLASK_APP=flask_app.py && flask run`)

## Testing

To execute the test suite:
```bash
pytest
```

## License

The code is provided under the GNU Affero General Public License v3.0 (AGPLv3), allowing free use, modification, and distribution for non-commercial, academic, and community contribution purposes.

For any commercial use (e.g., integration into proprietary products, paid SaaS offerings without sharing AGPLv3-compliant modifications), a separate commercial license must be negotiated. Please create an issue for inquiries.
