<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

type Snapshot = {
  gcode_state?: string;
  subtask_name?: string;
  mc_remaining_time?: number;
  lights_report?: { node?: string; mode?: string }[];
};

type Detector = {
  last_confidence: number | null;
  last_score?: number | null;
  normalized_score?: number | null;
  safe_frames_remaining?: number;
  monitoring_active?: boolean;
  alerted: boolean;
};

const snapshot = ref<Snapshot>({});
const detector = ref<Detector | null>(null);
const frameSrc = ref('');
const frameError = ref(false);

type StreamMessage =
  | { type: 'snapshot'; ts: number; data: Snapshot }
  | { type: 'detector'; ts: number; data: Detector }
  | { type: 'frame'; ts: number }
  | { type: 'event'; ts: number; data: Record<string, unknown> };

// kept as a no-op shim so optimistic toggle code can still call it without effect.
function tickSnapshot() {}

let es: EventSource | null = null;

function connectStream() {
  es = new EventSource('/api/stream');
  es.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data) as StreamMessage;
      if (msg.type === 'snapshot') snapshot.value = msg.data;
      else if (msg.type === 'detector') detector.value = msg.data;
      else if (msg.type === 'frame') {
        frameError.value = false;
        frameSrc.value = `/api/frame.jpg?ts=${msg.ts}`;
      }
    } catch {}
  };
  es.onerror = () => {
    es?.close();
    es = null;
    setTimeout(connectStream, 2000);
  };
}

onMounted(() => {
  connectStream();
});

onUnmounted(() => {
  es?.close();
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

const riskScore = computed(() => {
  const score = detector.value?.normalized_score;
  return score === null || score === undefined ? '—' : `${(score * 100).toFixed(1)}%`;
});

const riskDisplay = computed(() => {
  const remaining = detector.value?.safe_frames_remaining ?? 0;
  if (!(detector.value?.monitoring_active)) return 'Idle';
  if (remaining > 0) return 'Warming up';
  return riskScore.value;
});

const riskHint = computed(() => {
  const remaining = detector.value?.safe_frames_remaining ?? 0;
  if (!(detector.value?.monitoring_active)) return 'Monitoring starts when the printer is actively running.';
  if (remaining > 0) return `${remaining} frame${remaining === 1 ? '' : 's'} left before alerts arm.`;
  return 'Smoothed failure risk based on recent frames.';
});

const GREEN_CLS = 'text-state-running ring-state-running/40 bg-state-running/10';
const RED_CLS = 'text-state-fail ring-state-fail/40 bg-state-fail/10';
const GREEN_STATES = new Set(['RUNNING', 'PREPARE', 'FINISH', 'IDLE']);

const stateLabels: Record<string, string> = {
  RUNNING: 'Printing',
  PAUSE: 'Paused',
  PREPARE: 'Preparing',
  FINISH: 'Finished',
  FAILED: 'Failed',
  IDLE: 'Idle',
};

const stateView = computed(() => ({
  label: stateLabels[state.value] ?? state.value,
  cls: GREEN_STATES.has(state.value) ? GREEN_CLS : RED_CLS,
}));

type Action = 'pause' | 'resume' | 'stop';

const canPause = computed(() => state.value === 'RUNNING');
const canResume = computed(() => state.value === 'PAUSE');
const canStop = computed(() => state.value === 'RUNNING' || state.value === 'PAUSE');
const canStart = computed(() => ['IDLE', 'FINISH', 'FAILED', ''].includes(state.value));

const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const uploading = ref(false);
const uploadProgress = ref(0);

function onFileChosen(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] ?? null;
  if (f && !f.name.toLowerCase().endsWith('.3mf')) {
    showToast('Must be a .3mf file', 'err');
    selectedFile.value = null;
    if (fileInput.value) fileInput.value.value = '';
    return;
  }
  selectedFile.value = f;
}

function startUpload() {
  const f = selectedFile.value;
  if (!f) return;
  uploading.value = true;
  uploadProgress.value = 0;
  const form = new FormData();
  form.append('file', f);
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/print/start');
  xhr.upload.onprogress = (ev) => {
    if (ev.lengthComputable) uploadProgress.value = Math.round((ev.loaded / ev.total) * 100);
  };
  xhr.onload = () => {
    uploading.value = false;
    let body: { ok?: boolean; error?: string; detail?: string } = {};
    try {
      body = JSON.parse(xhr.responseText);
    } catch {}
    if (xhr.status >= 200 && xhr.status < 300 && body.ok) {
      showToast('Print sent', 'ok');
      selectedFile.value = null;
      if (fileInput.value) fileInput.value.value = '';
      tickSnapshot();
    } else {
      showToast(`Print failed: ${body.error ?? xhr.status}${body.detail ? ' — ' + body.detail : ''}`, 'err');
    }
  };
  xhr.onerror = () => {
    uploading.value = false;
    showToast('Upload error', 'err');
  };
  xhr.send(form);
}

const confirmStop = ref(false);
const toast = ref<{ msg: string; kind: 'ok' | 'err' } | null>(null);
const sending = ref<Action | null>(null);
let toastTimer: number | undefined;

function showToast(msg: string, kind: 'ok' | 'err') {
  toast.value = { msg, kind };
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (toast.value = null), 3500);
}

const lightOverride = ref<'on' | 'off' | null>(null);
const lightBusy = ref(false);

const backendLightOn = computed(() => {
  const arr = snapshot.value.lights_report || [];
  const cl = arr.find((l) => l.node === 'chamber_light');
  return (cl?.mode || 'off').toLowerCase() === 'on';
});

const lightOn = computed(() =>
  lightOverride.value !== null ? lightOverride.value === 'on' : backendLightOn.value,
);

// Clear override once backend snapshot reflects our target.
watch(backendLightOn, (now) => {
  if (lightOverride.value !== null && (now ? 'on' : 'off') === lightOverride.value) {
    lightOverride.value = null;
  }
});

async function toggleLight() {
  const target: 'on' | 'off' = lightOn.value ? 'off' : 'on';
  lightOverride.value = target;
  lightBusy.value = true;
  try {
    const r = await fetch(`/api/light/${target}`, { method: 'POST' });
    const body = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
    if (!r.ok || !body.ok) {
      lightOverride.value = null;
      showToast(`Light failed: ${body.error ?? r.status}`, 'err');
    }
  } catch (e) {
    lightOverride.value = null;
    showToast(`Light error: ${(e as Error).message}`, 'err');
  } finally {
    lightBusy.value = false;
  }
}

async function sendControl(action: Action) {
  sending.value = action;
  try {
    const r = await fetch(`/api/print/${action}`, { method: 'POST' });
    const body = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
    if (r.ok && body.ok) {
      showToast(`${action} sent`, 'ok');
      tickSnapshot();
    } else {
      showToast(`${action} failed: ${body.error ?? r.status}`, 'err');
    }
  } catch (e) {
    showToast(`${action} error: ${(e as Error).message}`, 'err');
  } finally {
    sending.value = null;
  }
}

function requestStop() {
  confirmStop.value = true;
}

async function confirmStopYes() {
  confirmStop.value = false;
  await sendControl('stop');
}
</script>

<template>
  <div class="h-screen w-screen p-6 grid grid-cols-12 gap-6 bg-white">
    <aside class="panel col-span-3 justify-between">
      <div class="space-y-6">
        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">State</div>
          <div class="mt-2">
            <span class="pill px-3 py-1.5 text-sm" :class="stateView.cls">
              {{ stateView.label }}
            </span>
          </div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">File</div>
          <div class="mt-2 font-mono text-xl break-all">{{ file }}</div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">ETA</div>
          <div class="mt-2 font-mono text-xl">{{ eta }}</div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">New print</div>
          <div class="mt-2 space-y-2">
            <input
              ref="fileInput"
              type="file"
              accept=".3mf"
              class="block w-full text-xs file:mr-2 file:py-1.5 file:px-3 file:rounded-full file:border-0 file:ring-1 file:ring-line file:text-sm file:bg-bg-tile hover:file:bg-bg-tile/70"
              :disabled="uploading"
              @change="onFileChosen"
            />
            <div v-if="selectedFile" class="font-mono text-xs text-text-muted break-all">
              {{ selectedFile.name }} ({{ Math.round(selectedFile.size / 1024) }} KB)
            </div>
            <div v-if="uploading" class="w-full h-2 bg-bg-tile rounded overflow-hidden ring-1 ring-line">
              <div class="h-full bg-state-running transition-all" :style="{ width: uploadProgress + '%' }"></div>
            </div>
            <button
              class="pill px-3 py-1.5 text-sm ring-1 ring-line disabled:opacity-40 disabled:cursor-not-allowed hover:bg-bg-tile"
              :disabled="!selectedFile || !canStart || uploading"
              @click="startUpload"
            >
              {{
                !uploading
                  ? 'Send & print'
                  : uploadProgress < 100
                    ? `Uploading ${uploadProgress}%`
                    : 'Sending to printer…'
              }}
            </button>
          </div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">Control</div>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              class="pill px-3 py-1.5 text-sm ring-1 ring-line disabled:opacity-40 disabled:cursor-not-allowed hover:bg-bg-tile"
              :disabled="!canPause || sending !== null"
              @click="sendControl('pause')"
            >
              {{ sending === 'pause' ? '…' : 'Pause' }}
            </button>
            <button
              class="pill px-3 py-1.5 text-sm ring-1 ring-line disabled:opacity-40 disabled:cursor-not-allowed hover:bg-bg-tile"
              :disabled="!canResume || sending !== null"
              @click="sendControl('resume')"
            >
              {{ sending === 'resume' ? '…' : 'Resume' }}
            </button>
            <button
              class="pill px-3 py-1.5 text-sm ring-1 ring-state-fail/40 text-state-fail bg-state-fail/10 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-state-fail/20"
              :disabled="!canStop || sending !== null"
              @click="requestStop"
            >
              {{ sending === 'stop' ? '…' : 'Stop' }}
            </button>
            <button
              class="pill px-3 py-1.5 text-sm ring-1 ring-line disabled:opacity-40 disabled:cursor-not-allowed hover:bg-bg-tile"
              :class="lightOn ? 'bg-yellow-100 ring-yellow-400/60' : ''"
              :disabled="lightBusy"
              @click="toggleLight"
            >
              {{ lightBusy ? '…' : (lightOn ? 'Light off' : 'Light on') }}
            </button>
          </div>
        </div>
      </div>
    </aside>

    <div
      v-if="confirmStop"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="confirmStop = false"
    >
      <div class="bg-white rounded-xl ring-1 ring-line p-6 max-w-sm shadow-xl">
        <div class="text-lg font-semibold">Stop print?</div>
        <div class="mt-2 text-sm text-text-muted">
          This cancels the current print on the printer. The print cannot be resumed afterwards.
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button
            class="pill px-3 py-1.5 text-sm ring-1 ring-line hover:bg-bg-tile"
            @click="confirmStop = false"
          >
            Cancel
          </button>
          <button
            class="pill px-3 py-1.5 text-sm ring-1 ring-state-fail/40 text-state-fail bg-state-fail/10 hover:bg-state-fail/20"
            @click="confirmStopYes"
          >
            Stop print
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="toast"
      class="fixed top-4 right-4 z-50 pill px-3 py-1.5 text-sm ring-1 shadow-md"
      :class="toast.kind === 'ok' ? GREEN_CLS : RED_CLS"
    >
      {{ toast.msg }}
    </div>

    <main class="col-span-6 flex">
      <div class="w-full h-full bg-bg-tile rounded-xl ring-1 ring-line overflow-hidden flex items-center justify-center">
        <div v-if="!frameSrc || frameError" class="text-text-muted font-mono text-sm text-center px-6">No frame yet.</div>
        <img
          v-show="frameSrc && !frameError"
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
          <div class="text-xs uppercase tracking-wider text-text-muted">Alert</div>
          <div class="mt-2">
            <span
              class="pill px-3 py-1.5 text-sm"
              :class="detector?.alerted ? RED_CLS : GREEN_CLS"
            >
              {{ detector?.alerted ? 'Spaghetti detected' : 'No issues' }}
            </span>
          </div>
        </div>

        <div>
          <div class="text-xs uppercase tracking-wider text-text-muted">Risk score</div>
          <div class="mt-2 font-mono text-xl">{{ riskDisplay }}</div>
          <div class="mt-2 text-sm text-text-muted">{{ riskHint }}</div>
        </div>
      </div>
    </aside>
  </div>
</template>
