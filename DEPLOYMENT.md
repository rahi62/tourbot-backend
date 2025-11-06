# Deployment Guide for Render

This guide will help you deploy the Django backend to Render.

## Prerequisites

1. A Render account
2. A PostgreSQL database (can be created through Render)
3. Your OpenAI API key

## Environment Variables

Set the following environment variables in your Render dashboard:

### Required Variables

- `SECRET_KEY`: Django secret key (generate a strong random string)
- `DEBUG`: Set to `False` for production
- `DATABASE_URL`: Automatically set by Render if using Render PostgreSQL
- `ALLOWED_HOSTS`: Your Render backend domain (e.g., `tourbot-backend.onrender.com`)
- `CORS_ALLOWED_ORIGINS`: Your frontend domain (e.g., `https://your-app.vercel.app`)
- `OPENAI_API_KEY`: Your OpenAI API key for the chatbot

### Optional Variables (for local development)

- `DB_NAME`: Database name (default: `tourbot_db`)
- `DB_USER`: Database user (default: `postgres`)
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host (default: `localhost`)
- `DB_PORT`: Database port (default: `5432`)

## Deployment Steps

### Option 1: Using render.yaml (Recommended)

1. Push your code to a Git repository (GitHub, GitLab, or Bitbucket)
2. In Render dashboard, click "New" → "Blueprint"
3. Connect your repository
4. Render will automatically detect `render.yaml` and configure the service
5. Update environment variables in the Render dashboard:
   - Set `ALLOWED_HOSTS` to your actual Render domain
   - Set `CORS_ALLOWED_ORIGINS` to your frontend domain
   - Add `OPENAI_API_KEY`

### Option 2: Manual Setup

1. In Render dashboard, create a new "Web Service"
2. Connect your Git repository
3. Configure the service:
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn tourbot_backend.wsgi:application --bind 0.0.0.0:$PORT`
4. Create a PostgreSQL database in Render
5. Link the database to your web service
6. Set environment variables as listed above

## Database Migrations

After deployment, run migrations:

1. Open the Render shell for your service
2. Run: `python manage.py migrate`
3. Create a superuser: `python manage.py createsuperuser`

## Static Files

Static files are automatically collected during build and served via WhiteNoise.

## Media Files

Media files are served through Django. For production with large files, consider using:
- AWS S3
- Cloudinary
- DigitalOcean Spaces
- Other cloud storage solutions

## Testing Locally with Production Settings

To test locally with `DEBUG=False`:

1. Set environment variables:
   ```bash
   export DEBUG=False
   export SECRET_KEY=your-secret-key-here
   export ALLOWED_HOSTS=localhost,127.0.0.1
   export DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   ```

2. Collect static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

3. Run with Gunicorn:
   ```bash
   gunicorn tourbot_backend.wsgi:application
   ```

## CORS Configuration

Make sure to add your frontend domain to `CORS_ALLOWED_ORIGINS`:

```bash
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://your-frontend.vercel.app
```

## Health Check

The health check endpoint is configured at `/api/`. Make sure this endpoint is accessible.

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` is set correctly
- Check database credentials
- Ensure database is accessible from your Render service

### Static Files Not Loading

- Verify `collectstatic` ran during build
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Ensure WhiteNoise middleware is in `MIDDLEWARE`

### CORS Errors

- Verify `CORS_ALLOWED_ORIGINS` includes your frontend domain
- Check that `CORS_ALLOW_CREDENTIALS` is `True`
- Ensure frontend is sending credentials correctly

### Media Files Not Accessible

- For production, consider using cloud storage
- If serving through Django, ensure proper URL configuration
- Check file permissions

