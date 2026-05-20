import { ref } from 'vue';
import { fetchEvents, openEventStream, type EventRecord } from '../api/client';

const events = ref<EventRecord[]>([]);
const streaming = ref(false);
const error = ref<string | null>(null);
const newestSinceMount = ref<number | null>(null);

let refCount = 0;
let source: EventSource | null = null;
let initialFetchDone = false;

const MAX_EVENTS = 200;

async function loadInitial() {
  if (initialFetchDone) return;
  initialFetchDone = true;
  try {
    const initial = await fetchEvents(100);
    // newest first
    events.value = initial.slice().reverse();
  } catch (e) {
    error.value = (e as Error).message;
  }
}

function openStream() {
  source = openEventStream((ev) => {
    events.value.unshift(ev);
    newestSinceMount.value = ev.ts;
    if (events.value.length > MAX_EVENTS) events.value.length = MAX_EVENTS;
  });
  source.onopen = () => (streaming.value = true);
  source.onerror = () => (streaming.value = false);
}

export function useEventStream() {
  refCount += 1;
  if (refCount === 1) {
    loadInitial();
    openStream();
  }

  const release = () => {
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0) {
      source?.close();
      source = null;
      streaming.value = false;
    }
  };

  return { events, streaming, error, newestSinceMount, release };
}
