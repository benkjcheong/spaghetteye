import { ref } from 'vue';
import { fetchSnapshot, type PrinterSnapshot } from '../api/client';

const snapshot = ref<PrinterSnapshot>({});

let refCount = 0;
let timer: number | undefined;

async function tick() {
  try {
    snapshot.value = await fetchSnapshot();
  } catch {
    /* ignore */
  }
}

export function useSnapshot(intervalMs = 2000) {
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

  return { snapshot, release, refresh: tick };
}
