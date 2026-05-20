<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

type Snapshot = {
  gcode_state?: string;
  subtask_name?: string;
  mc_remaining_time?: number;
};

type Detector = {
  enabled: boolean;
  last_confidence: number | null;
  alerted: boolean;
};

const snapshot = ref<Snapshot>({});
const detector = ref<Detector | null>(null);
const frameSrc = ref(`/api/frame.jpg?ts=${Date.now()}`);
const frameError = ref(false);

async function fetchJSON<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(path);
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

async function tickSnapshot() {
  const data = await fetchJSON<{ snapshot: Snapshot }>('/api/snapshot');
  if (data?.snapshot) snapshot.value = data.snapshot;
}

async function tickDetector() {
  const data = await fetchJSON<Detector>('/api/detector');
  if (data) detector.value = data;
}

function tickFrame() {
  frameSrc.value = `/api/frame.jpg?ts=${Date.now()}`;
}

let snapTimer: number | undefined;
let detTimer: number | undefined;
let frameTimer: number | undefined;

onMounted(() => {
  tickSnapshot();
  tickDetector();
  snapTimer = window.setInterval(tickSnapshot, 2000);
  detTimer = window.setInterval(tickDetector, 3000);
  frameTimer = window.setInterval(tickFrame, 5000);
});

onUnmounted(() => {
  if (snapTimer) clearInterval(snapTimer);
  if (detTimer) clearInterval(detTimer);
  if (frameTimer) clearInterval(frameTimer);
});

const state = computed(() => (snapshot.value.gcode_state ?? 'IDLE').toUpperCase());
const file = computed(() => snapshot.value.subtask_name ?? '—');

const eta = computed(() => {
  const m = snapshot.value.mc_remaining_time;
  if (!m || m <= 0) return '—';
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return h ? `${h}h ${mm}m` : `${mm}m`;
});

const confidence = computed(() => {
  const c = detector.value?.last_confidence;
  return c === null || c === undefined ? '—' : `${(c * 100).toFixed(1)}%`;
});

const stateMap: Record<string, { label: string; cls: string; dot: string }> = {
  RUNNING: { label: 'Printing', cls: 'text-state-running ring-state-running/40 bg-state-running/10', dot: 'bg-state-running' },
  PAUSE: { label: 'Paused', cls: 'text-state-pause ring-state-pause/40 bg-state-pause/10', dot: 'bg-state-pause' },
  PREPARE: { label: 'Preparing', cls: 'text-state-finish ring-state-finish/40 bg-state-finish/10', dot: 'bg-state-finish' },
  FINISH: { label: 'Finished', cls: 'text-state-finish ring-state-finish/40 bg-state-finish/10', dot: 'bg-state-finish' },
  FAILED: { label: 'Failed', cls: 'text-state-fail ring-state-fail/40 bg-state-fail/10', dot: 'bg-state-fail' },
  IDLE: { label: 'Idle', cls: 'text-text-muted ring-line bg-bg-tile', dot: 'bg-state-idle' },
};

const stateView = computed(
  () => stateMap[state.value] ?? { label: state.value, cls: 'text-text-muted ring-line bg-bg-tile', dot: 'bg-state-idle' },
);
</script>

<template>
  <div class="h-screen w-screen p-6 grid grid-cols-12 gap-6 bg-white">
    <aside class="panel col-span-3 justify-between">
      <div class="space-y-6">
        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">State</div>
          <div class="mt-2">
            <span class="pill px-3 py-1.5 text-sm" :class="stateView.cls">
              <span class="inline-block w-1.5 h-1.5 rounded-full" :class="stateView.dot"></span>
              {{ stateView.label }}
            </span>
          </div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">File</div>
          <div class="mt-2 font-mono text-2xl break-all">{{ file }}</div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">ETA</div>
          <div class="mt-2 font-mono text-3xl">{{ eta }}</div>
        </div>
      </div>
    </aside>

    <main class="col-span-6 flex">
      <div class="w-full h-full bg-bg-tile rounded-xl ring-1 ring-line overflow-hidden flex items-center justify-center">
        <div v-if="frameError" class="text-text-muted font-mono text-sm text-center px-6">No frame yet.</div>
        <img
          v-else
          :src="frameSrc"
          alt="printer camera"
          class="w-full h-full object-contain"
          @error="frameError = true"
          @load="frameError = false"
        />
      </div>
    </main>

    <aside class="panel col-span-3 justify-between">
      <div class="space-y-6">
        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">Spaghetti Detector</div>
          <div class="mt-2">
            <span
              class="pill"
              :class="detector?.enabled ? 'text-brand ring-brand/40 bg-brand-soft' : 'text-text-muted ring-line bg-bg-tile'"
            >
              {{ detector?.enabled ? 'enabled' : 'disabled' }}
            </span>
          </div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">Confidence</div>
          <div class="mt-2 font-mono text-5xl">{{ confidence }}</div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">Alert</div>
          <div class="mt-2">
            <span
              class="pill"
              :class="detector?.alerted ? 'text-state-fail ring-state-fail/40 bg-state-fail/10' : 'text-text-muted ring-line bg-bg-tile'"
            >
              {{ detector?.alerted ? 'FIRED' : 'clear' }}
            </span>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>
