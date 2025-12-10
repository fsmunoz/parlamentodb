# Notes on deployment

This API follows (or tries to) an **infrastructure-first approach**: cross-cutting concerns (CORS, rate limiting,
DDoS protection, TLS, request logging) are expected to be handled by infrastructure (Cloudflare +
nginx) rather than application code: this is in part because it being a decent principle, and also
because I would risk implementing badly in code what can be done better outside of it.

## Architecture

This is an ex example deployment pattern:
```
Internet -> Cloudflare → nginx -> FastAPI (uvicorn)
```

- **Cloudflare**: CORS, rate limiting, DDoS protection, TLS termination, caching
- **nginx**: Reverse proxy, request logging, load balancing, static file serving
- **FastAPI**: Business logic only (queries, validation, responses)


With Kubernetes, nginx or a different ingress can be used. Cloudflare is optional, of course: it's
useful to show what is being done at that layer.

## nginx Configuration

These are some examples to get you up and running; consider them a starting point.

### Basic reverse proxy

Here, we will use nginx as a simple reverse proxy.

Create `/etc/nginx/sites-available/parlamentodb` with:

```nginx
upstream parlamentodb {
    server 127.0.0.1:8000;
    # For multiple workers, add more servers:
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name api.parlamentodb.pt;

    # Request logging
    access_log /var/log/nginx/parlamentodb_access.log combined;
    error_log /var/log/nginx/parlamentodb_error.log;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://parlamentodb;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (no logging)
    location /health {
        proxy_pass http://parlamentodb;
        access_log off;
    }
}
```

Then, enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/parlamentodb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### With HTTPS (self-Signed, Let's Encrypt)

For local HTTPS testing or if not using Cloudflare (which provides this automatically) we need to
add HTTPS at the nginx level. Something like this should do it (adjust file paths adequately):

```nginx
server {
    listen 443 ssl http2;
    server_name api.parlamentodb.pt;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.parlamentodb.pt/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.parlamentodb.pt/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # ... rest of the configuration, as above
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.parlamentodb.pt;
    return 301 https://$server_name$request_uri;
}
```

### CORS configuration

If you need CORS at the nginx level instead of Cloudflare:

```nginx
location / {
    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;

    # Handle preflight requests
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Max-Age' 1728000;
        add_header 'Content-Type' 'text/plain; charset=utf-8';
        add_header 'Content-Length' 0;
        return 204;
    }

    proxy_pass http://parlamentodb;
    # ... rest of proxy configuration
}
```

## Cloudflare setup

Cloudflare has a lot of options, and it's likely that most of the default Just Work, especially if
you're using tunnels. These are some suggestions.

### Recommended Settings

**SSL/TLS**:
- Encryption mode: **Full (strict)**
- Minimum TLS version: **1.2**
- Enable HSTS

**Speed**:
- Caching Level: **Standard**
- Browser Cache TTL: **4 hours** (or adjust per endpoint)
- Auto Minify: Enable for HTML, CSS, JS (likely the default)

**Security**:
- Security Level: **Medium** or **High**
- Challenge Passage: **30 minutes**
- Browser Integrity Check: **On**

**Firewall Rules**:
- Rate limiting: **300 requests/minute per IP**
- Block common attacks: **On**
- OWASP rules: **On**

### Cache Rules

```
URL Pattern: api.parlamentodb.pt/api/v1/*

Settings:
- Cache Level: Cache Everything
- Edge Cache TTL: 1 hour
- Browser Cache TTL: 30 minutes
```

Avoid caching /health
```
URL Pattern: api.parlamentodb.pt/health

Settings:
- Cache Level: Bypass
```

## Running the API
As described in the README, `make run` will be of help, amongst other targets.

### Development

This also works:

```bash
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Production, with systemd service

Create `/etc/systemd/system/parlamentodb.service`:

```ini
[Unit]
Description=ParlamentoDB API
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/parlamentodb
Environment="PATH=/var/www/parlamentodb/.venv/bin"
ExecStart=/var/www/parlamentodb/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --log-config logging.yaml
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable parlamentodb
sudo systemctl start parlamentodb
sudo systemctl status parlamentodb
```

### Production (Docker)

There's a `Dockerfile` and `docker-compose.yml` available
Build and run:

```bash
docker build -t parlamentodb .
docker run -d -p 8000:8000 --name parlamentodb parlamentodb
```

or

```bash
docker-compose up
```

### Cloud Run (Google Cloud Platform)

The API can also be deployed to Google Cloud Run for serverless deployment (as well as other popular
alternatives in other cloud providers):

```bash
gcloud run deploy parlamentodb \
  --source . \
  --platform managed \
  --region europe-west1
```

This uses Cloud Run's source-based deployment (automatically builds from the provided Dockerfile),
and uses the auto-scaling and HTTP/SSL support that's built-in.

The data files (`data/silver/*.parquet`) must be included in the deployment, or things adjusted so
that they are added to Cloud Storage - that part is not included but should be trivial.

## Monitoring

There's nothing fancy built-in, but when used with the other components we can get pretty decent visibility.

### nginx Logs

Adjust paths as needed:

Access logs
```bash
tail -f /var/log/nginx/parlamentodb_access.log
```

Error logs:
```bash
tail -f /var/log/nginx/parlamentodb_error.log
```


I use [goaccess](https://goaccess.io/) to parse logs and view what's happening, using the nginx logs:
```bash
goaccess /var/log/nginx/parlamentodb_access.log --log-format=COMBINED
```

THere are more alternatives, so use what you prefer.

### Cloudflare Analytics

If using Cloudflare:

- Go to Cloudflare Dashboard -> Analytics
- View requests, bandwidth, threats blocked
- Set up alerts for traffic anomalies


### Application Health

There's an API endpoint for that:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

## Troubleshooting

### API not starting

Check logs, if you're using systemd:

```bash
sudo journalctl -u parlamentodb -f
```

Common issues I've found during development:

- Missing Parquet files: Run the ETL pipeline (`make etl-fetch && make etl-transform`) to create them.
- Port already in use: Check with `sudo lsof -i :8000` - this one is very common. Change the port if needed.

### 502 Bad Gateway

Got bit by this one when nginx can't reach FastAPI. Try:

```bash
# Check if FastAPI is running
curl http://127.0.0.1:8000/health

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart FastAPI
sudo systemctl restart parlamentodb
```

## Additional references

This is not exhaustive, but was used during development:

- FastAPI deployment: https://fastapi.tiangolo.com/deployment/
- nginx documentation: https://nginx.org/en/docs/
- Cloudflare docs: https://developers.cloudflare.com/
- DuckDB best practices: https://duckdb.org/docs/guides/performance/
