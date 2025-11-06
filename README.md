# TourBot Backend

Django Rest Framework backend for the AI-powered travel assistant.

## Features

- Django Rest Framework API
- PostgreSQL database
- JWT authentication using `djangorestframework-simplejwt`
- CORS configured for frontend integration
- Three apps: `visa`, `tour`, and `chatbot`

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip

## Getting Started

### 1. Create a virtual environment:
```bash
python -m venv venv
```

### 2. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL database:

Create a PostgreSQL database:
```sql
CREATE DATABASE tourbot_db;
```

### 5. Configure environment variables:

Create a `.env` file in the `backend` directory:
```env
DB_NAME=tourbot_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 6. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create a superuser:
```bash
python manage.py createsuperuser
```

### 8. Run the development server:
```bash
python manage.py runserver
```

The API will be available at [http://localhost:8000](http://localhost:8000)

## API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT token (username, password)
- `POST /api/token/refresh/` - Refresh JWT token
- `POST /api/token/verify/` - Verify JWT token

### Visa App
- `GET /api/visa/visas/` - List all visas
- `POST /api/visa/visas/` - Create a new visa entry
- `GET /api/visa/visas/{id}/` - Get visa details
- `PUT /api/visa/visas/{id}/` - Update visa
- `DELETE /api/visa/visas/{id}/` - Delete visa

### Tour App
- `GET /api/tour/tours/` - List all tours (add `?active_only=true` to filter)
- `POST /api/tour/tours/` - Create a new tour
- `GET /api/tour/tours/{id}/` - Get tour details
- `PUT /api/tour/tours/{id}/` - Update tour
- `DELETE /api/tour/tours/{id}/` - Delete tour

### Chatbot App
- `GET /api/chatbot/chat/` - List user's chat messages
- `POST /api/chatbot/chat/` - Create a new chat message
- `GET /api/chatbot/chat/{id}/` - Get chat message details
- `GET /api/chatbot/chat/my_messages/` - Get current user's messages

## Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

## CORS Configuration

CORS is configured to allow requests from:
- http://localhost:3000
- http://127.0.0.1:3000

## OpenAI Setup

The chatbot feature requires an OpenAI API key. Add it to your `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

You can get an API key from [OpenAI Platform](https://platform.openai.com/api-keys).

