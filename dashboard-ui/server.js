import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3000;

// Proxy all /api/* routes to the backend (must come before static files)
// Use path matching instead of mounting to preserve the full path
app.use(createProxyMiddleware({
  target: process.env.API_BASE_URL || 'http://localhost:8000',
  changeOrigin: true,
  logLevel: 'debug',
  // Match any path starting with /api
  pathFilter: '/api',
  onError: (err, req, res) => {
    console.error('Proxy error:', err.message);
    res.status(500).json({ error: 'Proxy error', message: err.message });
  },
  onProxyReq: (proxyReq, req, res) => {
    console.log(`[PROXY] ${req.method} ${req.url} -> ${process.env.API_BASE_URL || 'http://localhost:8000'}${req.url}`);
  },
  onProxyRes: (proxyRes, req, res) => {
    console.log(`[PROXY] Response ${proxyRes.statusCode} for ${req.url}`);
  }
}));

// Serve static files from dist directory
app.use(express.static(path.join(__dirname, 'dist')));

// Handle client-side routing - serve index.html for all routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Dashboard UI server running on port ${port}`);
  console.log(`API proxy target: ${process.env.API_BASE_URL || 'http://localhost:8000'}`);
});