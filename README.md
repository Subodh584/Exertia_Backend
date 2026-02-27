# Exertia Backend

Django REST API backend for the Exertia platform.

## Tech Stack

- **Python** 3.12+
- **Django** 5.x
- **Django REST Framework** 3.x
- **SQLite** (development) / **PostgreSQL** (production)

## Getting Started

### 1. Create & activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example env file and adjust as needed:

```bash
cp .env.example .env
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

## API Endpoints

| Endpoint          | Method | Description         |
| ----------------- | ------ | ------------------- |
| `/api/health/`    | GET    | Health check        |
| `/admin/`         | GET    | Django admin panel  |

## Project Structure

```
Exertia_Backend/
├── config/             # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/               # Core app (shared models, utilities)
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── serializers.py
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```
