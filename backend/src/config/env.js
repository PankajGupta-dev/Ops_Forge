const path = require('path');
const fs = require('fs');

// Attempt to load .env variables securely
try {
  const dotenv = require('dotenv');
  dotenv.config({ path: path.resolve(__dirname, '../../../.env') });
} catch (err) {
  // Resilient fallback: parse .env manually if dotenv npm module is not installed
  const envPath = path.resolve(__dirname, '../../../.env');
  if (fs.existsSync(envPath)) {
    const fileContent = fs.readFileSync(envPath, 'utf8');
    fileContent.split(/\r?\n/).forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const delimiterIdx = trimmed.indexOf('=');
        if (delimiterIdx !== -1) {
          const key = trimmed.substring(0, delimiterIdx).trim();
          const val = trimmed.substring(delimiterIdx + 1).trim().replace(/^['"]|['"]$/g, '');
          if (!process.env[key]) {
            process.env[key] = val;
          }
        }
      }
    });
  }
}

// Required variables list
const requiredVariables = [
  'DIGITALOCEAN_API_TOKEN',
  'GEMINI_API_KEY',
  'MONGODB_ATLAS_URI',
  'ELEVENLABS_API_KEY',
  'JWT_SECRET'
];

const missingVariables = [];
for (const envVar of requiredVariables) {
  if (!process.env[envVar] || process.env[envVar].trim() === '') {
    missingVariables.push(envVar);
  }
}

// Fail fast if required parameters are absent
if (missingVariables.length > 0) {
  throw new Error(`FATAL CONFIGURATION ERROR: Missing required env variables: ${missingVariables.join(', ')}`);
}

// Export structured config settings
const config = {
  digitalOcean: {
    token: process.env.DIGITALOCEAN_API_TOKEN,
    defaultRegion: process.env.DIGITALOCEAN_DEFAULT_REGION || 'nyc3',
  },
  doks: {
    clusterName: process.env.DOKS_CLUSTER_NAME || 'opsforge-doks-cluster',
    clusterRegion: process.env.DOKS_CLUSTER_REGION || 'nyc3',
    kubernetesVersion: process.env.DOKS_KUBERNETES_VERSION || 'latest',
  },
  gemini: {
    apiKey: process.env.GEMINI_API_KEY,
  },
  mongodb: {
    uri: process.env.MONGODB_ATLAS_URI,
  },
  elevenlabs: {
    apiKey: process.env.ELEVENLABS_API_KEY,
    voiceId: process.env.ELEVENLABS_VOICE_ID || '21m00Tcm4TlvDq8ikWAM',
  },
  frontend: {
    apiBaseUrl: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
    port: parseInt(process.env.PORT || '3000', 10),
  },
  backend: {
    host: process.env.BACKEND_HOST || '127.0.0.1',
    port: parseInt(process.env.BACKEND_PORT || '8000', 10),
    nodeEnv: process.env.NODE_ENV || 'development',
  },
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    format: process.env.LOG_FORMAT || 'json',
  },
  deployment: {
    pollIntervalMs: parseInt(process.env.DEPLOYMENT_POLL_INTERVAL_MS || '5000', 10),
    timeoutMs: parseInt(process.env.DEPLOYMENT_TIMEOUT_MS || '600000', 10),
  },
  security: {
    jwtSecret: process.env.JWT_SECRET,
    sessionSecret: process.env.SESSION_SECRET || 'fallback-session-secret',
    allowedCorsOrigins: (process.env.ALLOWED_CORS_ORIGINS || '')
      .split(',')
      .map(origin => origin.trim())
      .filter(Boolean),
  },
};

module.exports = config;
