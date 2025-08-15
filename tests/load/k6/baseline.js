import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  discardResponseBodies: true,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
  scenarios: {
    baseline: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 10),
      timeUnit: '1s',
      duration: __ENV.DURATION || '1m',
      preAllocatedVUs: Number(__ENV.VUS || 20),
      maxVUs: Number(__ENV.MAX_VUS || 200),
    },
  },
};

const API = __ENV.FORGE1_API_URL || 'http://localhost:8000';
const EMAIL = __ENV.FORGE1_EMAIL || 'demo@example.com';
const PASSWORD = __ENV.FORGE1_PASSWORD || 'admin';

function getToken() {
  if (__ENV.FORGE1_TOKEN) return __ENV.FORGE1_TOKEN;
  const res = http.post(`${API}/api/v1/auth/login`, { username: EMAIL, password: PASSWORD });
  try {
    const data = res.json();
    return data['access_token'];
  } catch (e) {
    return '';
  }
}

const TOKEN = getToken();

export default function () {
  const headers = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};
  // Run task
  const runRes = http.post(
    `${API}/api/v1/ai/execute`,
    JSON.stringify({ task: 'Ping from k6', context: {} }),
    { headers: { 'Content-Type': 'application/json', ...headers } },
  );
  check(runRes, { 'ai.execute status 200': (r) => r.status === 200 });
  // Metrics reads
  const m1 = http.get(`${API}/api/v1/metrics/summary`, { headers });
  check(m1, { 'metrics summary ok': (r) => r.status === 200 });
  sleep(0.1);
}

export function handleSummary(data) {
  const outDir = __ENV.OUTPUT_DIR || `./artifacts/k6_${Date.now()}`;
  try { require('fs').mkdirSync(outDir, { recursive: true }); } catch (e) {}
  return {
    [`${outDir}/summary.json`]: JSON.stringify(data, null, 2),
  };
}


