<template>
  <svg class="svg-defs-container" style="display: none;">
    <defs>
      <!-- Grid pattern for editor canvas -->
      <pattern id="canvas-grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" stroke-width="1" />
        <circle cx="0" cy="0" r="1.5" fill="rgba(255, 255, 255, 0.08)" />
      </pattern>

      <!-- Glow filters -->
      <filter id="glow-danger" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <filter id="glow-warning" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <filter id="glow-primary" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <!-- Spatio-Temporal Motion Traversal Trail Gradient & Glow -->
      <linearGradient id="motion-trail-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#818cf8" stop-opacity="0.85" />
        <stop offset="50%" stop-color="#06b6d4" stop-opacity="0.95" />
        <stop offset="100%" stop-color="#f59e0b" stop-opacity="1" />
      </linearGradient>

      <filter id="glow-trail" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <!-- Motion Sensor Icon (Clear) -->
      <g id="icon-motion-clear">
        <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#64748b" stroke-width="2" />
        <path d="M-6 -4 A8 8 0 0 1 6 -4 M-10 -7 A13 13 0 0 1 10 -7" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" />
        <circle cx="0" cy="4" r="3.5" fill="#94a3b8" />
      </g>

      <!-- Motion Sensor Icon (Active / Detected) -->
      <g id="icon-motion-active">
        <circle cx="0" cy="0" r="18" fill="rgba(239, 68, 68, 0.2)" stroke="#ef4444" stroke-width="2.5" filter="url(#glow-danger)" />
        <circle cx="0" cy="0" r="14" fill="#ef4444" />
        <path d="M-6 -4 A8 8 0 0 1 6 -4 M-10 -7 A13 13 0 0 1 10 -7" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" />
        <circle cx="0" cy="4" r="3.5" fill="#ffffff" />
      </g>

      <!-- Door Sensor Icon (SHUT / Closed) -->
      <g id="icon-door-closed">
        <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#475569" stroke-width="2" />
        <!-- Closed door in jamb -->
        <rect x="-8" y="-11" width="16" height="22" rx="2" fill="#334155" stroke="#94a3b8" stroke-width="1.5" />
        <!-- Door panels / details -->
        <rect x="-6" y="-9" width="12" height="8" rx="1" fill="#1e293b" />
        <rect x="-6" y="1" width="12" height="8" rx="1" fill="#1e293b" />
        <!-- Door knob -->
        <circle cx="4" cy="0" r="1.5" fill="#cbd5e1" />
      </g>

      <!-- Door Sensor Icon (OPEN / Alert) -->
      <g id="icon-door-open">
        <!-- Alert glow circle -->
        <circle cx="0" cy="0" r="19" fill="rgba(245, 158, 11, 0.2)" stroke="#f59e0b" stroke-width="2.5" filter="url(#glow-warning)" />
        <circle cx="0" cy="0" r="15" fill="#d97706" />
        <!-- Swing arc indicating door opening -->
        <path d="M -8 10 A 16 16 0 0 1 8 -6" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-dasharray="2 2" />
        <!-- Open door leaf rotated outward -->
        <line x1="-8" y1="10" x2="-8" y2="-8" stroke="#fef3c7" stroke-width="2" stroke-linecap="round" />
        <line x1="-8" y1="10" x2="6" y2="4" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" />
        <circle cx="3" cy="2" r="1.5" fill="#78350f" />
      </g>

      <!-- Window Sensor Icon (SHUT / Closed) -->
      <g id="icon-window-closed">
        <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#475569" stroke-width="2" />
        <!-- Window frame -->
        <rect x="-9" y="-9" width="18" height="18" rx="2" fill="#334155" stroke="#94a3b8" stroke-width="1.5" />
        <!-- 4 Panes / muntins -->
        <line x1="0" y1="-9" x2="0" y2="9" stroke="#94a3b8" stroke-width="1.5" />
        <line x1="-9" y1="0" x2="9" y2="0" stroke="#94a3b8" stroke-width="1.5" />
      </g>

      <!-- Window Sensor Icon (OPEN / Alert) -->
      <g id="icon-window-open">
        <!-- Alert glow circle -->
        <circle cx="0" cy="0" r="19" fill="rgba(245, 158, 11, 0.2)" stroke="#f59e0b" stroke-width="2.5" filter="url(#glow-warning)" />
        <circle cx="0" cy="0" r="15" fill="#d97706" />
        <!-- Outer window frame -->
        <rect x="-9" y="-9" width="18" height="18" rx="2" fill="none" stroke="#ffffff" stroke-width="1.5" />
        <!-- Bottom sash slid open showing gap -->
        <rect x="-7" y="-7" width="14" height="6" fill="#fef3c7" stroke="#ffffff" stroke-width="1" />
        <!-- Open gap with arrow/wind -->
        <path d="M-4 3 L0 0 L4 3 M-4 6 L0 3 L4 6" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" />
      </g>

      <!-- Camera Icon -->
      <g id="icon-camera">
        <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#6366f1" stroke-width="2" />
        <rect x="-8" y="-6" width="16" height="12" rx="2" fill="#4f46e5" stroke="#818cf8" stroke-width="1.5" />
        <circle cx="0" cy="0" r="3.5" fill="#ffffff" />
        <circle cx="5" cy="-3.5" r="1" fill="#a5b4fc" />
      </g>

      <!-- Generic Sensor Icon -->
      <g id="icon-generic">
        <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#64748b" stroke-width="2" />
        <circle cx="0" cy="0" r="6" fill="#6366f1" />
      </g>

      <!-- Composite / Synthetic Rule Icon (Clear / Inactive) -->
      <g id="icon-composite-clear">
        <circle cx="0" cy="0" r="16" fill="#0f172a" stroke="#8b5cf6" stroke-width="2" />
        <path d="M0 -8 L7 -4 L7 2 C7 6 0 10 0 10 C0 10 -7 6 -7 2 L-7 -4 Z" fill="none" stroke="#a78bfa" stroke-width="1.8" />
        <path d="M1 -5 L-2 -1 L1 -1 L-1 5" fill="none" stroke="#c4b5fd" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </g>

      <!-- Composite / Synthetic Rule Icon (Active / Triggered) -->
      <g id="icon-composite-active">
        <circle cx="0" cy="0" r="19" fill="rgba(239, 68, 68, 0.25)" stroke="#ef4444" stroke-width="2.5" filter="url(#glow-danger)" />
        <circle cx="0" cy="0" r="15" fill="#dc2626" />
        <path d="M0 -8 L7 -4 L7 2 C7 6 0 10 0 10 C0 10 -7 6 -7 2 L-7 -4 Z" fill="#b91c1c" stroke="#ffffff" stroke-width="1.8" />
        <path d="M1 -5 L-2 -1 L1 -1 L-1 5" fill="none" stroke="#fef08a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </g>
    </defs>
  </svg>
</template>
