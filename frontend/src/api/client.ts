export type PrinterSnapshot = Record<string, unknown> & {
  gcode_state?: string;
  subtask_name?: string;
  layer_num?: number;
  total_layer_num?: number;
  mc_percent?: number;
  mc_remaining_time?: number;
  nozzle_temper?: number;
  bed_temper?: number;
  print_error?: number;
};

export interface DetectorStatus {
  enabled: boolean;
  last_tick_ts: number | null;
  last_confidence: number | null;
  last_summary: string | null;
  failure_detected: boolean | null;
  consecutive_hits: number;
  alerted: boolean;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function fetchSnapshot(): Promise<PrinterSnapshot> {
  const data = await getJSON<{ snapshot: PrinterSnapshot }>('/api/snapshot');
  return data.snapshot ?? {};
}

export async function fetchDetector(): Promise<DetectorStatus> {
  return getJSON<DetectorStatus>('/api/detector');
}

export function frameUrl(): string {
  return `/api/frame.jpg?ts=${Date.now()}`;
}
