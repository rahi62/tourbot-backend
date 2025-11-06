# Environment Configuration Guide

This project uses environment-based configuration that switches between development and production modes based on a single `DEBUG` flag.

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and set your values:**
   - For development: Set `DEBUG=True`
   - For production: Set `DEBUG=False` and configure all required variables

3. **That's it!** The project will automatically use the correct settings based on `DEBUG`.

## Environment Variables

### Core Settings

- **`DEBUG`** (Required)
  - `True` = Development mode
  - `False` = Production mode
  - This single flag controls all environment-specific behavior

- **`SECRET_KEY`** (Required)
  - Django secret key for cryptographic signing
  - Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  - **Never commit this to version control!**

### Database Configuration

- **`DATABASE_URL`** (Required in production, optional in development)
  - PostgreSQL connection string
  - Format: `postgresql://user:password@host:port/database`
  - In development: If not set, uses SQLite
  - In production: **Required**

- **Individual DB Settings** (Optional, only if `DATABASE_URL` not set)
  - `DB_NAME` - Database name
  - `DB_USER` - Database user
  - `DB_PASSWORD` - Database password
  - `DB_HOST` - Database host
  - `DB_PORT` - Database port

### CORS & Frontend

- **`FRONTEND_URL`** (Required in production)
  - Your frontend application URL
  - Development: `http://localhost:3000`
  - Production: `https://your-frontend.vercel.app`

- **`CORS_ALLOWED_ORIGINS`** (Optional)
  - Comma-separated list of allowed origins
  - If not set, uses `FRONTEND_URL`
  - Example: `https://app1.vercel.app,https://app2.vercel.app`

### Production Settings (only used when `DEBUG=False`)

- **`ALLOWED_HOSTS`** (Required in production)
  - Comma-separated list of allowed hostnames
  - Example: `your-backend.onrender.com,api.yourdomain.com`

- **`SECURE_SSL_REDIRECT`** (Optional, default: `True`)
  - Set to `False` if behind a reverse proxy that handles SSL

### External Services

- **`OPENAI_API_KEY`** (Required for chatbot)
  - Your OpenAI API key for the chatbot functionality

## Development Mode (`DEBUG=True`)

When `DEBUG=True`, the following settings are automatically applied:

- ✅ **Database**: Uses SQLite by default (or PostgreSQL if `DATABASE_URL` is set)
- ✅ **Hosts**: Allows all hosts (`*`)
- ✅ **Logging**: Verbose logging with DEBUG level
- ✅ **CORS**: Allows `http://localhost:3000` and `http://127.0.0.1:3000`
- ✅ **Static Files**: Django serves static files directly
- ✅ **Security**: Relaxed security settings for development

## Production Mode (`DEBUG=False`)

When `DEBUG=False`, the following settings are automatically applied:

- ✅ **Database**: **Requires** `DATABASE_URL`
- ✅ **Hosts**: **Requires** `ALLOWED_HOSTS` (restricted)
- ✅ **Logging**: Less verbose (INFO level, ERROR for Django)
- ✅ **CORS**: Uses `CORS_ALLOWED_ORIGINS` or `FRONTEND_URL`
- ✅ **Static Files**: Uses WhiteNoise for serving static files
- ✅ **Security**: 
  - SSL redirect enabled
  - Secure cookies
  - XSS protection
  - Content type nosniff
  - X-Frame-Options: DENY

## Example `.env` Files

### Development `.env`
```env
DEBUG=True
SECRET_KEY=django-insecure-dev-key-change-in-production
FRONTEND_URL=http://localhost:3000
OPENAI_API_KEY=sk-your-openai-key-here
```

### Production `.env`
```env
DEBUG=False
SECRET_KEY=your-super-secret-production-key-here
DATABASE_URL=postgresql://user:password@host:port/database
ALLOWED_HOSTS=your-backend.onrender.com
FRONTEND_URL=https://your-frontend.vercel.app
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
OPENAI_API_KEY=sk-your-openai-key-here
SECURE_SSL_REDIRECT=True
```

## Switching Environments

To switch between development and production:

1. **Edit `.env` file**
2. **Change `DEBUG=True` to `DEBUG=False`** (or vice versa)
3. **Set required variables** for the target environment
4. **Restart your Django server**

That's it! All other settings are automatically configured based on the `DEBUG` flag.

## Validation

The settings file will raise `ValueError` if required production variables are missing:

- `ALLOWED_HOSTS` must be set when `DEBUG=False`
- `DATABASE_URL` must be set when `DEBUG=False`
- `CORS_ALLOWED_ORIGINS` or `FRONTEND_URL` must be set when `DEBUG=False`

## Security Notes

⚠️ **Important:**
- Never commit `.env` to version control
- Generate a new `SECRET_KEY` for production
- Use strong passwords for production databases
- Keep `OPENAI_API_KEY` secret
- Review security settings before deploying

## Troubleshooting

### "ALLOWED_HOSTS must be set in production!"
- Set `ALLOWED_HOSTS` in your `.env` file when `DEBUG=False`

### "DATABASE_URL must be set in production!"
- Set `DATABASE_URL` in your `.env` file when `DEBUG=False`

### "CORS_ALLOWED_ORIGINS or FRONTEND_URL must be set in production!"
- Set either `CORS_ALLOWED_ORIGINS` or `FRONTEND_URL` in your `.env` file

### Environment variables not loading
- Make sure `.env` file is in the project root (same directory as `manage.py`)
- Check that `python-decouple` is installed: `pip install python-decouple`
- Verify variable names match exactly (case-sensitive)

