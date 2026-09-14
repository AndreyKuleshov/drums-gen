<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { CircleStencil, Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'

const props = defineProps<{ src: string }>()
const emit = defineEmits<{
  (e: 'confirm', blob: Blob): void
  (e: 'cancel'): void
}>()

// Focus management: trap Tab inside the dialog while open, then restore focus
// to whatever opened it (the "Change photo" button) on close.
const dialog = ref<HTMLElement | null>(null)
let opener: HTMLElement | null = null

function focusable(): HTMLElement[] {
  if (!dialog.value) return []
  return Array.from(
    dialog.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input, [tabindex]:not([tabindex="-1"])',
    ),
  )
}

// The library exposes these instance methods via defineExpose; we only need two.
interface CropperApi {
  getResult: () => { canvas?: HTMLCanvasElement | null }
  zoom: (factor: number) => void
}
const cropper = ref<CropperApi | null>(null)
const working = ref(false)

const OUT = 512 // exported square side; the backend downsamples further to 256

// Fix the circular stencil to the largest circle that fits the stage; the image
// is what moves and zooms under it (Instagram/Telegram-style avatar crop).
function stencilSize({ boundaries }: { boundaries: { width: number; height: number } }): {
  width: number
  height: number
} {
  const side = Math.min(boundaries.width, boundaries.height) - 24
  return { width: side, height: side }
}

function zoom(factor: number): void {
  cropper.value?.zoom(factor)
}

async function confirm(): Promise<void> {
  const canvas = cropper.value?.getResult().canvas
  if (!canvas) return
  working.value = true
  // Redraw the crop onto a fixed square so uploads are a predictable, small WebP.
  const out = document.createElement('canvas')
  out.width = OUT
  out.height = OUT
  const ctx = out.getContext('2d')
  if (ctx === null) {
    working.value = false
    return
  }
  ctx.drawImage(canvas, 0, 0, OUT, OUT)
  const blob = await new Promise<Blob | null>((resolve) =>
    out.toBlob((b) => resolve(b), 'image/webp', 0.9),
  )
  working.value = false
  if (blob) emit('confirm', blob)
}

function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    emit('cancel')
    return
  }
  if (e.key !== 'Tab') return
  const items = focusable()
  if (items.length === 0) return
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement as HTMLElement | null
  // Wrap around the ends, and pull focus back in if it has escaped the dialog.
  if (e.shiftKey && (active === first || !dialog.value?.contains(active))) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && (active === last || !dialog.value?.contains(active))) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  opener = document.activeElement as HTMLElement | null
  window.addEventListener('keydown', onKey)
  await nextTick()
  focusable()[0]?.focus()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  opener?.focus()
})
</script>

<template>
  <Teleport to="body">
    <div class="cropmodal__backdrop" @click="emit('cancel')" />
    <div
      ref="dialog"
      class="cropmodal"
      role="dialog"
      aria-modal="true"
      aria-label="Crop your photo"
    >
      <h3 class="cropmodal__title">Position your photo</h3>
      <div class="cropmodal__stage">
        <Cropper
          ref="cropper"
          class="cropmodal__cropper"
          :src="props.src"
          :stencil-component="CircleStencil"
          :stencil-size="stencilSize"
          :stencil-props="{ aspectRatio: 1, handlers: {}, movable: false, resizable: false }"
          image-restriction="stencil"
          :resize-image="{ wheel: { ratio: 0.12 }, touch: true }"
          :move-image="true"
          :canvas="{ minWidth: 256, maxWidth: 1024 }"
        />
      </div>
      <div class="cropmodal__zoom" role="group" aria-label="Zoom">
        <button type="button" class="cropmodal__zoombtn" aria-label="Zoom out" @click="zoom(0.84)">
          −
        </button>
        <span class="cropmodal__hint">Drag to move · scroll or ± to zoom</span>
        <button type="button" class="cropmodal__zoombtn" aria-label="Zoom in" @click="zoom(1.19)">
          +
        </button>
      </div>
      <div class="cropmodal__actions">
        <button type="button" class="cropmodal__cancel" @click="emit('cancel')">Cancel</button>
        <button type="button" class="cropmodal__save" :disabled="working" @click="confirm">
          {{ working ? 'Saving…' : 'Save photo' }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.cropmodal__backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(8, 6, 4, 0.72);
  backdrop-filter: blur(2px);
}

.cropmodal {
  position: fixed;
  z-index: 81;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(92vw, 420px);
  padding: 18px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  box-shadow: var(--shadow-3), 0 0 40px -12px var(--amber-glow);
}

.cropmodal__title {
  margin: 0 0 14px;
  font-family: var(--font-display, var(--font-ui));
  font-size: 1.05rem;
  color: var(--text);
}

.cropmodal__stage {
  border-radius: var(--r-md);
  overflow: hidden;
  background: var(--field-ink);
  border: 1px solid var(--edge);
}

.cropmodal__cropper {
  height: min(60vh, 340px);
  background: var(--field-ink);
}

.cropmodal__zoom {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin: 12px 0 4px;
}

.cropmodal__zoombtn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.15s ease, box-shadow 0.18s ease;
}

.cropmodal__zoombtn:hover {
  color: var(--amber-bright);
  box-shadow: inset 0 0 0 1px rgba(255, 157, 60, 0.28);
}

.cropmodal__hint {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  color: var(--text-dim);
}

.cropmodal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.cropmodal__cancel {
  padding: 9px 16px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.05em;
  cursor: pointer;
}

.cropmodal__cancel:hover {
  color: var(--text);
}

.cropmodal__save {
  padding: 9px 18px;
  border-radius: var(--r-md);
  border: 1px solid var(--amber-dim);
  background: linear-gradient(180deg, var(--amber), var(--amber-dim));
  color: var(--on-amber);
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: 0.86rem;
  cursor: pointer;
}

.cropmodal__save:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
