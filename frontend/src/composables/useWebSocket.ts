import { ref, onMounted, onUnmounted, watch } from "vue";
import { api } from "@/services/api";
import { useLiveStore } from "@/stores/liveStore";

export function useWebSocket(planIdGetter: () => string | null) {
  const liveStore = useLiveStore();
  const isConnecting = ref(false);
  let ws: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let pingTimer: number | null = null;
  let backoffMs = 1000;
  let isDestroyed = false;

  function connect() {
    const planId = planIdGetter();
    if (!planId || isDestroyed) return;

    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    isConnecting.value = true;
    const url = api.getWebSocketUrl(planId);

    try {
      ws = new WebSocket(url);
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      liveStore.setConnected(true);
      isConnecting.value = false;
      backoffMs = 1000; // Reset backoff

      // Setup keepalive ping every 30s
      if (pingTimer) clearInterval(pingTimer);
      pingTimer = window.setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "initial_states") {
          liveStore.handleInitialStates(msg.states);
        } else if (msg.type === "state_changed") {
          liveStore.handleStateChange(msg.entity_id, msg.new_state);
        }
      } catch {
        // Ignore unparseable frames
      }
    };

    ws.onclose = () => {
      liveStore.setConnected(false);
      isConnecting.value = false;
      cleanupTimers();
      if (!isDestroyed) {
        scheduleReconnect();
      }
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(() => {
      backoffMs = Math.min(backoffMs * 1.5, 30000);
      connect();
    }, backoffMs);
  }

  function cleanupTimers() {
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function disconnect() {
    isDestroyed = true;
    cleanupTimers();
    if (ws) {
      ws.onclose = null;
      ws.onerror = null;
      ws.close();
      ws = null;
    }
    liveStore.setConnected(false);
  }

  watch(planIdGetter, (newPlanId) => {
    if (newPlanId) {
      if (ws) {
        ws.close();
      }
      connect();
    }
  });

  onMounted(() => {
    isDestroyed = false;
    connect();
  });

  onUnmounted(() => {
    disconnect();
  });

  return {
    isConnecting,
    reconnect: connect,
    disconnect,
  };
}
