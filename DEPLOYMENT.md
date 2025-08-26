# Vercel Deployment Guide

## Database Migrations for Serverless

**Important**: In Vercel's serverless environment, database migrations should **NOT** be run during function startup/cold starts.

### Best Practices for Vercel + FastAPI + Alembic

#### 1. Run Migrations Manually Before Deployment

```bash
# From your local development environment:
cd api
uv run alembic upgrade head
```

#### 2. Alternative: Run from Vercel CLI

```bash
# Connect to your production database and run:
vercel env pull .env.vercel
source .env.vercel
uv run alembic upgrade head
```

#### 3. CI/CD Pipeline (Recommended)

Add migration step to your deployment pipeline:

```yaml
# .github/workflows/deploy.yml
- name: Run Database Migrations  
  run: |
    cd api
    uv run alembic upgrade head
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### Why Not Run Migrations on Startup?

1. **Cold Start Performance**: Each serverless function invocation would run migrations
2. **Race Conditions**: Multiple functions could try to migrate simultaneously  
3. **Timeout Issues**: Migrations might exceed Vercel's function timeout limits
4. **Resource Waste**: Migrations would run on every cold start unnecessarily

### Database Connection Best Practices

- Use connection pooling (Railway PostgreSQL supports this natively)
- Keep connections short-lived in serverless functions
- Consider using `asyncpg` for better async performance

### Environment Variables

Set these in your Vercel project settings:

```
DATABASE_URL=postgresql://user:pass@host:port/db
RUN_MIGRATIONS=false
```

### Deployment Steps

1. **Run migrations locally or in CI**:
   ```bash
   uv run alembic upgrade head
   ```

2. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

3. **Verify deployment**:
   - Check function logs in Vercel dashboard
   - Test API endpoints
   - Verify database schema is up to date

### Rollback Strategy

If you need to rollback migrations:

```bash
# Rollback to previous revision
uv run alembic downgrade -1

# Or rollback to specific revision
uv run alembic downgrade <revision_id>
```

### Development Workflow

1. Create migration: `uv run alembic revision --autogenerate -m "description"`
2. Review generated migration file
3. Test locally: `uv run alembic upgrade head`  
4. Deploy: migrations run before/during deployment, not at runtime