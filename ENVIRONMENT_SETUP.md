# Environment Configuration Guide

This project uses environment-based configuration that switches between development and production modes based on a single `DEBUG` flag.

## Quick Start

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and set your values:**
   ```env
   DEBUG=True  # Set to False for production
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://user:password@host:port/database
   FRONTEND_URL=http://localhost:3000
   OPENAI_API_KEY=your-openai-key
   ```

3. **That's it!** The project automatically switches configurations based on `DEBUG`.

## Environment Variables

### Core Settings

- **`DEBUG`** (required): `True` for development, `False` for production
  - Controls all environment-based settings
  - Default: `True` (development mode)

- **`SECRET_KEY`** (required): Django secret key
  - Generate one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  - Default: `django-insecure-change-this-in-production` (⚠️ change in production!)

### Database

- **`DATABASE_URL`** (optional in dev, required in prod):
  - Format: `postgresql://user:password@host:port/database`
  - Development: Can be omitted (uses SQLite)
  - Production: **Required**

- **Individual DB settings** (optional, only if `DATABASE_URL` not set):
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

### CORS & Frontend

- **`FRONTEND_URL`** (optional):
  - Development: `http://localhost:3000`
  - Production: `https://your-frontend-domain.vercel.app`

- **`CORS_ALLOWED_ORIGINS`** (optional):
  - Comma-separated list: `http://localhost:3000,http://127.0.0.1:3000`
  - Overrides `FRONTEND_URL` if set

### Production Only (when `DEBUG=False`)

- **`ALLOWED_HOSTS`** (required in production):
  - Comma-separated: `your-backend-domain.onrender.com,your-backend-domain.com`

- **`SECURE_SSL_REDIRECT`** (optional):
  - Default: `True` (forces HTTPS)

### External Services

- **`OPENAI_API_KEY`** (required for chatbot):
  - Your OpenAI API key

## Development Mode (`DEBUG=True`)

When `DEBUG=True`, the following settings are automatically applied:

✅ **Database**: SQLite (or local PostgreSQL if `DATABASE_URL` is set)  
✅ **Hosts**: All hosts allowed (`*`)  
✅ **CORS**: `http://localhost:3000` and `http://127.0.0.1:3000`  
✅ **Logging**: Verbose (DEBUG level)  
✅ **Static Files**: Served by Django (WhiteNoise disabled)  
✅ **Security**: Relaxed (for development convenience)

### Development `.env` Example

```env
DEBUG=True
SECRET_KEY=django-insecure-dev-key-change-in-production
FRONTEND_URL=http://localhost:3000
OPENAI_API_KEY=sk-your-openai-key
```

## Production Mode (`DEBUG=False`)

When `DEBUG=False`, the following settings are automatically applied:

🔒 **Database**: Must use `DATABASE_URL` (PostgreSQL)  
🔒 **Hosts**: Restricted to `ALLOWED_HOSTS`  
🔒 **CORS**: Uses `CORS_ALLOWED_ORIGINS` or `FRONTEND_URL`  
🔒 **Logging**: Less verbose (INFO level)  
🔒 **Static Files**: Served by WhiteNoise  
🔒 **Security**: Enhanced (SSL redirect, secure cookies, etc.)

### Production `.env` Example

```env
DEBUG=False
SECRET_KEY=your-strong-random-secret-key-here
DATABASE_URL=postgresql://user:password@host:5432/database
ALLOWED_HOSTS=your-backend.onrender.com
FRONTEND_URL=https://your-frontend.vercel.app
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
SECURE_SSL_REDIRECT=True
OPENAI_API_KEY=sk-your-openai-key
```

## Switching Environments

To switch between development and production, simply change the `DEBUG` flag:

```bash
# Development
DEBUG=True

# Production
DEBUG=False
```

All other settings are automatically adjusted based on this flag.

## Validation

The project validates required settings in production:

- ✅ `ALLOWED_HOSTS` must be set
- ✅ `DATABASE_URL` must be set
- ✅ `CORS_ALLOWED_ORIGINS` or `FRONTEND_URL` must be set

If any required setting is missing in production mode, Django will raise a `ValueError` with a clear error message.

## Testing Configuration

Check your configuration:

```bash
python manage.py check
```

This will validate all settings and report any issues.

## Security Notes

⚠️ **Never commit `.env` to version control!**  
✅ The `.env` file is already in `.gitignore`  
✅ Use `.env.example` to document required variables  
✅ Generate a strong `SECRET_KEY` for production  
✅ Use environment variables in your deployment platform (Render, Heroku, etc.)

## Troubleshooting

### "ALLOWED_HOSTS must be set in production!"
- Set `DEBUG=False` and provide `ALLOWED_HOSTS` in `.env`

### "DATABASE_URL must be set in production!"
- Set `DEBUG=False` and provide `DATABASE_URL` in `.env`

### CORS errors in production
- Ensure `CORS_ALLOWED_ORIGINS` or `FRONTEND_URL` is set correctly
- Check that your frontend domain matches exactly (including `https://`)

### Static files not loading in production
- Ensure `DEBUG=False` (WhiteNoise is only enabled in production)
- Run `python manage.py collectstatic` before deployment

