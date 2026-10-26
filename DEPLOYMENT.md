# Vercel + Neon deployment

This repository contains two deployable projects. The Next.js site is in `web/`. The Flask API remains at the repository root and the root `vercel.json` routes API project requests into Flask.

## Vercel projects

Create two Vercel projects connected to the same GitHub repository, with `main` as each project's production branch:

1. **Haven Web** — set **Root Directory** to `web`. Vercel should detect Next.js and use `npm run build`.
2. **Haven API** — set **Root Directory** to the repository root (`.`). The root `vercel.json` routes requests to the Flask application. Vercel's Python runtime supports WSGI applications such as Flask.

Deploy the API project first and copy its production URL. Set the web project's environment variables, then deploy the web project and add its production origin to the API allowlist. Vercel supports separate projects rooted in directories of the same monorepo; commits to `main` deploy each connected project.

## Neon database

Create a Neon project and database. Copy the **pooled** connection string for the production branch, keep its TLS/SSL query parameters, and add it to the Haven API project's Production environment as:

```text
DATABASE_URL=postgresql://…-pooler…/haven?sslmode=require
```

Use the exact URL supplied by Neon; do not put it in a `NEXT_PUBLIC_` variable, a checked-in file, or the mobile app. The Flask app converts PostgreSQL URLs to the Psycopg 3 SQLAlchemy driver. On Vercel, startup fails when neither `DATABASE_URL` nor the legacy Turso setting is configured rather than silently writing to ephemeral SQLite.

The application creates missing tables at startup. This is suitable for the current additive schema, but it does not copy existing records from Turso or SQLite. If existing Haven data must be kept, migrate it to Neon before routing users to the new deployment.

## Google sign-in

In Google Cloud Console, configure the OAuth consent screen and create an OAuth client ID with application type **Web application**. Add the Haven production domain under **Authorized JavaScript origins**. Add local and preview origins only when you use them. Google Identity Services returns an ID token; Flask verifies its signature, issuer, audience, expiry, and verified-email claim before creating a Haven session. Haven uses Google's stable `sub` claim as the provider identity. Existing password accounts must sign in first and link the matching Google account from the web sidebar.

Set these variables:

**Haven API project**

```text
GOOGLE_CLIENT_ID=…apps.googleusercontent.com
HAVEN_ALLOWED_ORIGINS=https://your-haven-site.vercel.app,https://your-custom-domain.example
HAVEN_ADMIN_EMAIL=admin@example.com
HAVEN_ADMIN_PASSWORD=<unique password of at least 12 characters>
```

The first API request creates that administrator only when the database has no admin account and the email is not already registered. After the first successful deployment, remove both bootstrap variables. If you later need to initialize a fresh database, add them back for that deployment.

**Haven Web project**

```text
NEXT_PUBLIC_HAVEN_API_URL=https://your-haven-api.vercel.app
NEXT_PUBLIC_GOOGLE_CLIENT_ID=…apps.googleusercontent.com
```

Use the same Google **web** client ID in both projects. `HAVEN_ALLOWED_ORIGINS` must contain exact site origins, including `https://`; it is not a URL path. If you use a custom domain, add that origin to both Vercel's project domain settings and this API variable.

If the Google client ID is already saved in Vercel as `CLIENT_ID`, Haven accepts that name for Google sign-in. The preferred explicit names are `GOOGLE_CLIENT_ID` on the API project and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` on the web project. `CLIENT_KEY` (a client secret) is not used by Haven's Google Identity Services flow. The web project also needs `NEXT_PUBLIC_HAVEN_API_URL`; Google credentials alone do not connect the site to the Flask API.

## Local development

Copy `web/.env.example` to `web/.env.local`, fill in the API URL and public Google client ID, then run the web project from `web/`. For local API development, set `DATABASE_URL` to a development Neon branch or leave it unset to use local SQLite, and set `GOOGLE_CLIENT_ID` plus `HAVEN_ALLOWED_ORIGINS=http://localhost:3000`.

The mobile app can use the same Haven API URL and password accounts. Native Android Google sign-in still needs an Android OAuth client and native browser/deep-link integration; the web OAuth client configured here is for the Next.js site.
