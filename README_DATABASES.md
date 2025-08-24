# Database Environment Management

## 🏗️ Environment Strategy

### Development Database
- **File**: `.env.development` 
- **Database**: Railway PostgreSQL (current setup)
- **Purpose**: Local development and testing
- **Migrations**: Auto-run on startup

### Production Database  
- **File**: `.env.production` (in Vercel environment variables)
- **Database**: Separate Railway PostgreSQL database
- **Purpose**: Live production data
- **Migrations**: Manual deployment process

## 🔧 Setup Process

### Current Setup (Development)
✅ Railway PostgreSQL connected  
✅ Environment variables configured  
✅ Models and migrations ready  

### Next Steps for Production
1. Create separate Railway PostgreSQL for production
2. Configure Vercel environment variables
3. Set up migration deployment process

## ⚠️ Important Notes
- **NEVER run development migrations against production**
- **Always test migrations in development first**
- **Use separate databases for each environment**
- **Keep environment files in .gitignore**

## 🚀 Migration Commands

```bash
# Development (local)
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# Production (manual deployment)
# Set DATABASE_URL to production DB first
uv run alembic upgrade head
```