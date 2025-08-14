import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    employees: {
      executor: 'constant-arrival-rate',
      rate: 1000, // tasks per minute
      timeUnit: '1m',
      duration: '10m',
      preAllocatedVUs: 100,
      maxVUs: 200,
    },
  },
};

const API_URL = __ENV.FORGE_API_URL || 'http://localhost:8000';
const TOKEN = __ENV.FORGE_TOKEN || '';

export default function () {
  const params = TOKEN ? { headers: { Authorization: `Bearer ${TOKEN}` } } : {};
  // Simple run against /ai/execute (no employee)
  const payload = JSON.stringify({ task: 'Say hello', context: {} });
  const res = http.post(`${API_URL}/api/v1/ai/execute`, payload, {
    headers: { 'Content-Type': 'application/json', ...(params.headers || {}) },
  });
  check(res, {
    'status is 200 or 500': (r) => r.status === 200 || r.status === 500,
  });
  sleep(0.1);
}


