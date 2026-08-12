<script setup lang="ts">
import { RouterLink } from 'vue-router'

const shortcuts = [
  { keys: ['Space'], action: 'Play / Stop', hint: 'Toggles playback of the current pattern' },
  { keys: ['R'], action: 'Loop', hint: 'Turns looping on or off' },
  { keys: ['C'], action: 'Click', hint: 'Toggles the metronome click over the pattern' },
  { keys: ['Enter'], action: 'Generate', hint: 'Generates a new pattern' },
]
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Keyboard Shortcuts</span>
        </div>
        <div class="brand__meta">
          <RouterLink to="/" class="nav-link">&larr; Back</RouterLink>
        </div>
      </header>

      <section class="sheet" aria-label="Keyboard shortcuts">
        <p class="sheet__lead">Work the studio without leaving the keyboard.</p>
        <ul class="rows">
          <li v-for="s in shortcuts" :key="s.action" class="row">
            <span class="row__keys">
              <kbd v-for="k in s.keys" :key="k">{{ k }}</kbd>
            </span>
            <span class="row__body">
              <span class="row__action">{{ s.action }}</span>
              <span class="row__hint">{{ s.hint }}</span>
            </span>
          </li>
        </ul>
        <p class="sheet__note">
          Shortcuts are ignored while you’re typing in a field, and pair with the same
          buttons in the transport — hover any of them to see its key.
        </p>
      </section>
    </div>
  </main>
</template>

<style scoped>
.sheet {
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), inset 0 1px 0 rgba(239, 231, 216, 0.04);
  padding: clamp(18px, 3vw, 28px);
}

.sheet__lead {
  margin: 0 0 18px;
  color: var(--text-dim);
  font-size: 0.95rem;
}

.rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 18px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge-soft, var(--edge));
  background: #100e0c;
  box-shadow: var(--inset);
  transition:
    border-color 0.16s ease,
    transform 0.16s cubic-bezier(0.2, 0.7, 0.3, 1),
    box-shadow 0.16s ease;
}

.row:hover {
  border-color: var(--amber-dim);
  transform: translateX(3px);
  box-shadow: var(--inset), inset 3px 0 0 var(--amber);
}

.row__keys {
  display: inline-flex;
  gap: 6px;
  flex: 0 0 96px;
}

kbd {
  display: inline-grid;
  place-items: center;
  min-width: 42px;
  padding: 8px 12px;
  border-radius: var(--r-sm);
  border: 1px solid var(--amber-dim);
  border-bottom-width: 3px;
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  color: var(--amber-bright);
  font-family: var(--font-mono);
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  box-shadow: var(--shadow-1);
}

.row__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.row__action {
  font-family: var(--font-display, var(--font-ui));
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.row__hint {
  font-size: 0.82rem;
  color: var(--text-dim);
}

.sheet__note {
  margin: 18px 0 0;
  font-size: 0.8rem;
  color: var(--text-faint);
}

@media (max-width: 480px) {
  .row {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .row__keys {
    flex-basis: auto;
  }
}
</style>
