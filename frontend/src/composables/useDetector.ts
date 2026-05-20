import { ref } from 'vue';
import { fetchDetector, type DetectorStatus } from '../api/client';

const status = ref<DetectorStatus | null>(null);

let refCount = 0;
let timer: number | undefined;

async function tick() {
  try {
    status.value = await fetchDetector();
  } catch {
    /* ignore */
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

  return { status, release, refresh: tick };
}
