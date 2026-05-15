/**
 * dev-lan.js — Local-network / tunnel dev launcher
 *
 * 1. Starts the backend (nodemon) and the web-frontend (Vite).
 * 2. Once Vite is ready, starts a Cloudflare quick tunnel on port 5173.
 * 3. Parses the tunnel URL from cloudflared output and opens the browser
 *    at <tunnel-url>/host — a real HTTPS URL any mobile browser trusts,
 *    so camera and Speech Recognition APIs work without certificate warnings.
 *
 * Requirements:
 *   brew install cloudflared   (one-time, free, no account needed)
 *
 * Usage (from backend-sockets/):
 *   npm run dev:lan
 */

const { spawn, exec } = require('child_process');
const path = require('path');
const os = require('os');


const ROOT        = path.join(__dirname, '..', '..');
const BACKEND_DIR = path.join(ROOT, 'backend-sockets');
const FRONTEND_DIR = path.join(ROOT, 'web-frontend');
const TUNNEL_URL_RE = /https:\/\/[a-zA-Z0-9-]+\.trycloudflare\.com/;
const opener = process.platform === 'darwin' ? 'open'
  : process.platform === 'win32' ? 'start'
  : 'xdg-open';

function getLanIP() {
  for (const ifaces of Object.values(os.networkInterfaces())) {
    for (const net of ifaces) {
      if (net.family === 'IPv4' && !net.internal) return net.address;
    }
  }
  return 'localhost';
}

console.log(`\n  LAN IP : ${getLanIP()}`);
console.log(`  Starting backend + frontend...\n`);

const backend = spawn('npm', ['run', 'dev'], {
  cwd: BACKEND_DIR,
  stdio: 'inherit',
  shell: true,
});

const frontend = spawn('npm', ['run', 'dev'], {
  cwd: FRONTEND_DIR,
  stdio: ['inherit', 'pipe', 'inherit'],
  shell: true,
});

let tunnelStarted = false;
frontend.stdout.on('data', (chunk) => {
  process.stdout.write(chunk);
  if (!tunnelStarted && chunk.toString().includes('Network:')) {
    tunnelStarted = true;
    startTunnel();
  }
});

function startTunnel() {
  console.log('\n  Starting Cloudflare tunnel...\n');

  const tunnel = spawn('cloudflared', ['tunnel', '--url', 'http://localhost:5173'], {
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: true,
  });

  tunnel.on('error', (err) => {
    if (err.code === 'ENOENT') {
      console.error('  [tunnel] cloudflared not found. Install it with:\n');
      console.error('    brew install cloudflared\n');
    } else {
      console.error('  [tunnel] Error:', err.message);
    }
  });

  let tunnelUrl = null;
  const onData = (chunk) => {
    const text = chunk.toString();
    process.stdout.write(text);
    if (!tunnelUrl) {
      const match = text.match(TUNNEL_URL_RE);
      if (match) {
        tunnelUrl = match[0];
        const hostUrl = `${tunnelUrl}/host`;
        console.log(`\n  ✓ Tunnel creado`);
        console.log(`  Mobile URL : ${hostUrl}`);
        console.log(`  (abriendo navegador en 20s — si da error, refresca la página)\n`);
        setTimeout(() => exec(`${opener} ${hostUrl}`), 20000);
      }
    }
  };

  tunnel.stdout.on('data', onData);
  tunnel.stderr.on('data', onData);
}

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => {
    backend.kill();
    frontend.kill();
    process.exit();
  });
}
