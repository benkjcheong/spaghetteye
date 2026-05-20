import { ref } from 'vue';
import { fetchDetector, type DetectorStatus } from '../api/client';

const status = ref<DetectorStatus | null>(null);
const error = ref<string | null>(null);
const history = ref<number[]>([]); // rolling last 60 confidence values

let refCount = 0;
let timer: number | undefined;
let lastTickTs: number | null = null;

const MAX_HISTORY = 60;

async function tick() {
  try {
    const next = await fetchDetector();
    status.value = next;
    error.value = null;
    if (next.last_tick_ts && next.last_tick_ts !== lastTickTs) {
      lastTickTs = next.last_tick_ts;
      history.value.push(next.last_confidence ?? 0);
      if (history.value.length > MAX_HISTORY) history.value.shift();
    }
  } catch (e) {
    error.value = (e as Error).message;
  }
}

export function useDetector(intervalMs = 3000) {
  refCount += 1;
  if (refCount === 1) {
    tick();
    timer = window.setInterval(tick, intervalMs);
  }

  const release = () => {
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0 && timer !== undefined) {
      window.clearInterval(timer);
      timer = undefined;
    }
  };

  return { status, history, error, release, refresh: tick };
}
