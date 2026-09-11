import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom Metrics
export const errorRate = new Rate('errors');
export const researchCreationTrend = new Trend('research_create_duration');
export const sseConnectTrend = new Trend('sse_connect_duration');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '2m', target: 500 },
    { duration: '3m', target: 1000 },
    { duration: '2m', target: 5000 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],
    'errors': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';
const AUTH_HEADER = {
  headers: {
    'Authorization': 'Bearer mock_load_test_jwt_token',
    'Content-Type': 'application/json',
  },
};

export default function runLoadTest() {
  group('1. Organization & Dashboard Auth', function () {
    const res = http.get(`${BASE_URL}/api/v1/auth/me`, AUTH_HEADER);
    const passed = check(res, {
      'auth status is 200': (r) => r.status === 200,
    });
    if (!passed) {
      errorRate.add(1);
    }
    sleep(1);
  });

  let taskId = null;

  group('2. Create Research Job', function () {
    const payload = JSON.stringify({
      product_idea: `AI B2B Logistics Optimization Tool #${Math.floor(Math.random() * 100000)}`,
      mode: 'quick',
      idempotency_key: `load_test_${__VU}_${__ITER}_${Date.now()}`
    });

    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/research`, payload, AUTH_HEADER);
    researchCreationTrend.add(Date.now() - start);

    const success = check(res, {
      'job created status 202 or 200': (r) => r.status === 202 || r.status === 200,
      'has task_id': (r) => r.json('task_id') !== undefined,
    });

    if (success) {
      taskId = res.json('task_id');
    } else {
      errorRate.add(1);
    }
    sleep(2);
  });

  if (taskId) {
    group('3. Status Polling & SSE', function () {
      const res = http.get(`${BASE_URL}/api/v1/research/${taskId}`, AUTH_HEADER);
      const pollPassed = check(res, {
        'status poll is 200': (r) => r.status === 200,
      });
      if (!pollPassed) {
        errorRate.add(1);
      }

      const evtRes = http.get(`${BASE_URL}/api/v1/research/${taskId}/events`, AUTH_HEADER);
      const evtPassed = check(evtRes, {
        'events fetch is 200': (r) => r.status === 200,
      });
      if (!evtPassed) {
        errorRate.add(1);
      }

      sleep(1);
    });
  }

  group('4. Billing & Subscription Check', function () {
    const res = http.get(`${BASE_URL}/api/v1/billing/subscription`, AUTH_HEADER);
    const passed = check(res, {
      'billing check is 200': (r) => r.status === 200,
    });
    if (!passed) {
      errorRate.add(1);
    }
    sleep(1);
  });
}
