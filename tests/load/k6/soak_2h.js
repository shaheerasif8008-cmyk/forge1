import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<1200'],
  },
  scenarios: {
    soak: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 20),
      timeUnit: '1s',
      duration: __ENV.DURATION || '2h',
      preAllocatedVUs: Number(__ENV.VUS || 100),
      maxVUs: Number(__ENV.MAX_VUS || 1000),
    },
  },
};

const API = __ENV.FORGE1_API_URL || 'http://localhost:8000';
const EMAIL = __ENV.FORGE1_EMAIL || 'demo@example.com';
const PASSWORD = __ENV.FORGE1_PASSWORD || 'admin';

function getToken() {
  if (__ENV.FORGE1_TOKEN) return __ENV.FORGE1_TOKEN;
  const res = http.post(`${API}/api/v1/auth/login`, { username: EMAIL, password: PASSWORD });
  try { return res.json()['access_token']; } catch (e) { return ''; }
}

const TOKEN = getToken();

export default function () {
  const headers = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};
  // Execute task
  const runRes = http.post(
    `${API}/api/v1/ai/execute`,
    JSON.stringify({ task: 'Ping from k6 soak', context: {} }),
    { headers: { 'Content-Type': 'application/json', ...headers } },
  );
  check(runRes, { 'ai.execute ok': (r) => r.status === 200 });
  // Read metrics
  const m1 = http.get(`${API}/api/v1/metrics/summary`, { headers });
  check(m1, { 'metrics ok': (r) => r.status === 200 });
  sleep(0.5);
}


