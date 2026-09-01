# Setup procedure — server / always-on box

Use this after [SETUP.md](SETUP.md) works on the machine. Goal: the household can hit the tracker from phones and laptops on the LAN (or a VPS).

## Bind address

Desktop-only (this machine):

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

LAN / server (other devices can connect):

```bash
cd /path/to/house-maint-tracker/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Find the host IP (`ip a` / `hostname -I` on Linux, `ipconfig` on Windows) and open `http://<host-ip>:8000` from a phone.

**Change the seeded passwords first** if anything other than localhost can reach the port. See [OPERATIONS.md](OPERATIONS.md).

This build has no TLS. For internet exposure put it behind Caddy/nginx with HTTPS. On a home LAN, HTTP is enough.

## Environment

| Variable | Purpose | Example |
|----------|---------|---------|
| `HOUSE_MAINT_DB` | SQLAlchemy URL | `sqlite:////var/lib/house-maint/house_maint.db` |

Create the data directory before the first start:

```bash
sudo mkdir -p /var/lib/house-maint
sudo chown "$USER":"$USER" /var/lib/house-maint
export HOUSE_MAINT_DB=sqlite:////var/lib/house-maint/house_maint.db
```

Start uvicorn from `backend/` so Python can import `app`.

## systemd (Linux)

Unit file `/etc/systemd/system/house-maint.service` (adjust paths and user):

```ini
[Unit]
Description=House Maint Tracker (1944 Dinius)
After=network.target

[Service]
Type=simple
User=hermes
WorkingDirectory=/home/hermes/git/house-maint-tracker/backend
Environment=HOUSE_MAINT_DB=sqlite:////var/lib/house-maint/house_maint.db
ExecStart=/home/hermes/git/house-maint-tracker/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now house-maint.service
sudo systemctl status house-maint.service
curl -sS http://127.0.0.1:8000/api/health
```

Logs: `journalctl -u house-maint.service -f`

## Reverse proxy (optional)

Caddy example:

```
maint.1944dinius.home {
    reverse_proxy 127.0.0.1:8000
}
```

nginx example:

```
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header Authorization $http_authorization;
}
```

Point Android `MainActivity.APP_URL` at this origin. See [ANDROID.md](ANDROID.md).

## Backup

SQLite is a single file. Copy it while the app is idle, or use `sqlite3 … ".backup '…'"`.

```bash
# simple copy (stop the service for a consistent snapshot)
sudo systemctl stop house-maint.service
cp /var/lib/house-maint/house_maint.db /var/backups/house_maint-$(date +%F).db
sudo systemctl start house-maint.service
```

Restore: stop service, replace the file, start service.

## Firewall

If you use ufw:

```bash
sudo ufw allow 8000/tcp comment 'house-maint-tracker'
```

Prefer binding to the LAN interface only, or rely on the reverse proxy and keep uvicorn on 127.0.0.1.

## Updates

```bash
cd /path/to/house-maint-tracker
git pull
cd backend && source .venv/bin/activate && pip install -r requirements.txt
# if UI source changed:
cd ../frontend && npm install && npm run build
sudo systemctl restart house-maint.service
```
