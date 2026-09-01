# Android — PWA and WebView

Two ways to use House Maint Tracker on a phone. Both talk to the same backend.

## A. Progressive web app (no Android Studio)

1. Run the server so the phone can reach it ([SETUP.md](SETUP.md) or [SERVER.md](SERVER.md)).
2. On Android Chrome, open `http://<host-ip>:8000`.
3. Menu → **Add to Home screen** / **Install app**.
4. Launch from the home screen. It uses `manifest.webmanifest` and `sw.js`.

The PWA needs network to the API. The service worker only caches the shell for a brief offline fallback; task data is not a full offline replica.

If Chrome refuses HTTP install, serve via HTTPS (Caddy on the LAN) or use the WebView project below (`usesCleartextTraffic` is on).

## B. Android Studio WebView app

Project path: `android/` in this repo.

1. Install Android Studio.
2. File → Open → select the `android/` folder.
3. Set the URL in `android/app/src/main/java/com/dinius/housemaint/MainActivity.java`:

   | Where the phone/emulator is | `APP_URL` |
   |-----------------------------|-----------|
   | Android emulator, server on the same PC | `http://10.0.2.2:8000` |
   | Physical phone on the same Wi-Fi | `http://192.168.x.x:8000` (desktop LAN IP) |
   | Reverse-proxied hostname | `https://maint.example` |

4. Run on an emulator or a USB-debugged device.

`AndroidManifest.xml` already allows cleartext HTTP and INTERNET.

This wrapper does not ship a separate API; it loads the web UI.

## Checklist

- [ ] Backend reachable from the device (`/api/health` in the phone browser)
- [ ] Sign-in works
- [ ] Board / calendar / theme switcher usable on a narrow screen
- [ ] PWA: icon on the home screen **or** WebView: app launches to the login page
