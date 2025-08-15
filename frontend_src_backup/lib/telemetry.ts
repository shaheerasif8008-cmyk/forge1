import axios from 'axios';

const endpoint = '/api/v1/telemetry';

export type TelemetryEvent = {
  type: 'clicked_x' | 'created_employee' | 'ran_task';
  props?: Record<string, unknown>;
};

export async function track(ev: TelemetryEvent) {
  try {
    await axios.post(endpoint, ev);
  } catch (e) {
    // best-effort
  }
}


