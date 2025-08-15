import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<1500'],
  },
  scenarios: {
    surge: {
      executor: 'ramping-arrival-rate',
      startRate: Number(__ENV.RATE || 50),
      timeUnit: '1s',
      preAllocatedVUs: Number(__ENV.VUS || 100),
      maxVUs: Number(__ENV.MAX_VUS || 2000),
      stages: [
        { target: Number(__ENV.RATE || 50), duration: '30s' },
        { target: Number(__ENV.RATE || 500), duration: '60s' },
        { target: Number(__ENV.RATE || 50), duration: '30s' },
      ],
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
  const runRes = http.post(
    `${API}/api/v1/ai/execute`,
    JSON.stringify({ task: 'Ping from k6 surge', context: {} }),
    { headers: { 'Content-Type': 'application/json', ...headers } },
  );
  check(runRes, { 'ai.execute ok': (r) => r.status === 200 });
  sleep(0.05);
}


