# iOS PWA Setup -- Wally Trader Dashboard

Add the dashboard to your iPhone home screen as a Progressive Web App.

## Prerequisites
- Mac running wally-trader-dashboard daemon (`make dashboard-install`)
- iPhone on same WiFi network OR Tailscale connection
- Mac's local hostname or IP known (e.g. `imac.local` or `192.168.1.10`)

## Steps

### 1. Get your mobile API key (Mac)
```bash
cat ~/.wally/mobile_token
# Copy the value (starts with random characters)
```

### 2. Verify dashboard reachable from iPhone
On Mac, find your IP:
```bash
ipconfig getifaddr en0   # or en1 for ethernet
```

On iPhone Safari, navigate to: `http://<MAC_IP>:8080`

If it loads, continue. If not, check:
- Mac firewall allows port 8080
- Both devices on same network

### 3. Add to Home Screen (Safari only)
- Tap the Share icon
- Scroll down -> "Add to Home Screen"
- Name it "Wally" -> Add

### 4. (Optional) Use Tailscale for remote access
- Install Tailscale on Mac + iPhone
- Use Tailscale Magic DNS hostname instead of LAN IP

## Limitations
- iOS Safari PWA caches API key -- if you rotate `~/.wally/mobile_token`, re-add to home screen
- No native push notifications (PWA limitation on iOS)
- Requires Mac to be on for dashboard to respond

## Security note
The mobile API key in `~/.wally/mobile_token` is the only auth on the mobile endpoints. Keep it private. Bind to localhost (default) -- if exposing to LAN/Tailscale, ensure firewall + WPA2.
