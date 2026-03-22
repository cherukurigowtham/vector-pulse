# Deployment Guide

Stack:
- Backend: Go (Render)
- Frontend: Next.js (Vercel)
- Database: PostgreSQL (Render managed database)
- Cache: Redis (Upstash)

## 1) Provision Redis

Create a free Upstash Redis instance and keep:
- `REDIS_HOST`
- `REDIS_PORT=6379`
- `REDIS_PASSWORD`
- `REDIS_SSL=true`

## 2) Deploy Backend on Render

This repo contains `render.yaml` configured for Go runtime and managed Postgres.

Set/confirm environment variables:
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_PASSWORD`
- `REDIS_SSL`
- `CORS_ALLOW_ORIGINS` (your Vercel domain)
- `JWT_SECRET` (generated)
- `ADMIN_SECRET_KEY` (generated)

The API base URL will look like:
- `https://vector-pulse-api.onrender.com`

## 3) Deploy Frontend on Vercel

Import this repository and set Root Directory to `portal`.

Set env var:
- `NEXT_PUBLIC_API_BASE=https://vector-pulse-api.onrender.com`

Build command:
- `npm run build`

## 4) Smoke Tests

### Signup

```bash
curl -X POST https://vector-pulse-api.onrender.com/api/v1/security/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"StrongPass@123"}'
```

### Risk Scan

Use JWT token from signup/login response:

```bash
curl -X POST https://vector-pulse-api.onrender.com/api/v1/risk/scan \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"uid":"user_1","email":"user@example.com","phone":"9999999999","amt":1200,"addr":"HSR Layout","pin":"560102"}'
```

### Health

```bash
curl https://vector-pulse-api.onrender.com/api/v1/health
```
