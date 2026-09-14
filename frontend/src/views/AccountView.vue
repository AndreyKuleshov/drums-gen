<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import GrooveScore from '../components/GrooveScore.vue'
import ScoreView from '../components/ScoreView.vue'
import SocialGlyph from '../components/SocialGlyph.vue'
import { ApiError } from '../lib/api'
import { normalizeUrl, socialIcon } from '../lib/social'

// The cropper (+ its cropping/compression deps) only loads once the user picks a
// photo — most account visits never crop.
const AvatarCropper = defineAsyncComponent(() => import('../components/AvatarCropper.vue'))
import { useAuth } from '../lib/auth'
import { setPendingGroove, setPendingPhrase } from '../lib/loadedPattern'
import { listLiked, unlikePattern, updateProfile, uploadAvatar } from '../lib/patterns'
import type { LikedPattern } from '../lib/patterns'
import type { Groove, Phrase } from '../types'

const isPattern = (fave: LikedPattern): boolean => fave.meta.kind === 'pattern'

const router = useRouter()
const { user, setUser } = useAuth()

// --- Profile editor ---------------------------------------------------------
const displayName = ref(user.value?.display_name ?? '')
const bio = ref(user.value?.bio ?? '')
// Editable social links. Each row carries a STABLE id so v-for keys survive
// removal/reorder (index keys mis-associate inputs). Backend normalises + drops blanks.
interface LinkRow {
  id: number
  url: string
}
let nextLinkId = 0
const toRows = (urls: string[]): LinkRow[] => urls.map((url) => ({ id: nextLinkId++, url }))
const links = ref<LinkRow[]>(toRows(user.value?.social_links ?? []))
const saving = ref(false)
const saveMsg = ref<'' | 'saved' | 'error'>('')

function addLink(): void {
  links.value.push({ id: nextLinkId++, url: '' })
}
function removeLink(i: number): void {
  links.value.splice(i, 1)
}
// A non-empty entry that isn't a usable URL — shown as an inline hint.
function linkInvalid(url: string): boolean {
  return url.trim() !== '' && normalizeUrl(url) === null
}
// Saved links (from the account) that resolve to an icon — shown under the avatar.
const savedLinks = computed(() =>
  (user.value?.social_links ?? [])
    .map((url) => ({ url, href: normalizeUrl(url), icon: socialIcon(url) }))
    .filter((s): s is { url: string; href: string; icon: NonNullable<typeof s.icon> } =>
      Boolean(s.href && s.icon),
    ),
)
const avatarBusy = ref(false)
const avatarError = ref('')
const avatarOk = ref('') // announced confirmation after an avatar change
const fileInput = ref<HTMLInputElement | null>(null)
// Object URL of the picked-and-compressed image, shown in the crop modal.
const cropSrc = ref<string | null>(null)

async function saveProfile(): Promise<void> {
  saving.value = true
  saveMsg.value = ''
  try {
    const updated = await updateProfile(
      displayName.value.trim(),
      bio.value,
      links.value.map((r) => r.url),
    )
    setUser(updated)
    // Reflect the normalised list (https:// added, blanks dropped) back into the editor.
    links.value = toRows(updated.social_links)
    saveMsg.value = 'saved'
  } catch {
    saveMsg.value = 'error'
  } finally {
    saving.value = false
  }
}

async function onAvatarPicked(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // let the same file be re-picked later
  if (!file) return
  avatarError.value = ''
  avatarOk.value = ''
  avatarBusy.value = true
  try {
    // Compress before cropping: keeps big phone photos under ~1MB and makes the
    // cropper snappy. The lib is imported on demand so it isn't in the base load.
    const { default: imageCompression } = await import('browser-image-compression')
    const compressed = await imageCompression(file, {
      maxSizeMB: 1,
      maxWidthOrHeight: 1600,
      useWebWorker: true,
    })
    closeCrop()
    cropSrc.value = URL.createObjectURL(compressed)
  } catch {
    avatarError.value = 'Couldn’t read that image. Try another one.'
  } finally {
    avatarBusy.value = false
  }
}

function closeCrop(): void {
  if (cropSrc.value) URL.revokeObjectURL(cropSrc.value)
  cropSrc.value = null
}

async function onCropConfirm(blob: Blob): Promise<void> {
  const file = new File([blob], 'avatar.webp', { type: 'image/webp' })
  closeCrop()
  avatarBusy.value = true
  avatarError.value = ''
  avatarOk.value = ''
  try {
    const updated = await uploadAvatar(file)
    setUser(updated)
    avatarOk.value = 'Photo updated' // the avatar saves on its own — confirm it
  } catch (err) {
    avatarError.value =
      err instanceof ApiError && (err.status === 400 || err.status === 413)
        ? err.message
        : 'Upload failed. Please try again.'
  } finally {
    avatarBusy.value = false
  }
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2)
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || '?'
}

// --- Favorites --------------------------------------------------------------
const favorites = ref<LikedPattern[]>([])
const loadingFaves = ref(true)
const favesError = ref('')

onMounted(async () => {
  document.title = 'My Account · Drum Pattern Generator'
  try {
    favorites.value = await listLiked()
  } catch {
    favesError.value = 'Could not load your favorites.'
  } finally {
    loadingFaves.value = false
  }
})

async function remove(id: string): Promise<void> {
  const before = favorites.value
  favorites.value = favorites.value.filter((f) => f.id !== id)
  try {
    await unlikePattern(id)
  } catch {
    favorites.value = before // restore on failure
  }
}

async function openInGenerator(fave: LikedPattern): Promise<void> {
  // One page decides its mode from whichever pending pattern is set.
  if (isPattern(fave)) {
    setPendingGroove(fave.phrase as Groove)
  } else {
    setPendingPhrase(fave.phrase as Phrase)
  }
  await router.push('/')
}

function chip(fave: LikedPattern, key: string): string | null {
  const v = fave.meta[key]
  return v === undefined || v === null ? null : String(v)
}
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">My Account</span>
        </div>
        <div class="brand__meta">
          <span class="brand__model">RG&#8209;40 · RUDIMENT ENGINE</span>
          <RouterLink to="/" class="nav-link">&larr; Generator</RouterLink>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <p v-if="!user" class="muted account__loading">Loading your account…</p>

      <section v-else class="account">
        <h1 class="visually-hidden">My Account</h1>
        <!-- Profile editor -->
        <div class="card">
          <h2 class="card__title">Profile</h2>
          <div class="profile">
            <div class="profile__avatarcol">
              <span v-if="user.avatar_url" class="profile__avatar">
                <img :src="user.avatar_url" alt="Your avatar" />
              </span>
              <span v-else class="profile__avatar profile__avatar--initials" aria-hidden="true">
                {{ initials(user.display_name) }}
              </span>
              <button
                class="profile__upload"
                type="button"
                :disabled="avatarBusy"
                @click="fileInput?.click()"
              >
                {{ avatarBusy ? 'Working…' : 'Change photo' }}
              </button>
              <input
                ref="fileInput"
                class="visually-hidden"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                aria-label="Upload profile photo"
                tabindex="-1"
                @change="onAvatarPicked"
              />
              <p v-if="avatarError" class="profile__avatar-error" role="alert">{{ avatarError }}</p>
              <p v-if="avatarOk" class="profile__avatar-ok" role="status">{{ avatarOk }}</p>
              <AvatarCropper
                v-if="cropSrc"
                :src="cropSrc"
                @confirm="onCropConfirm"
                @cancel="closeCrop"
              />
              <div v-if="savedLinks.length" class="socials">
                <a
                  v-for="s in savedLinks"
                  :key="s.url"
                  class="socials__link"
                  :href="s.href"
                  target="_blank"
                  rel="noopener noreferrer"
                  :title="s.icon.label"
                  :aria-label="s.icon.label"
                >
                  <SocialGlyph :url="s.url" :size="20" />
                </a>
              </div>
            </div>

            <form class="profile__fields" @submit.prevent="saveProfile">
              <div class="field">
                <label class="field__label" for="dn">Display name</label>
                <input
                  id="dn"
                  v-model="displayName"
                  class="field__input"
                  type="text"
                  maxlength="80"
                  required
                />
              </div>
              <div class="field">
                <label class="field__label" for="bio">Bio</label>
                <textarea
                  id="bio"
                  v-model="bio"
                  class="field__input"
                  maxlength="2000"
                  placeholder="Tell other drummers a little about yourself."
                />
              </div>
              <div class="field">
                <span class="field__label">Links</span>
                <div v-for="(row, i) in links" :key="row.id" class="linkitem">
                  <div class="linkrow">
                    <span
                      class="linkrow__icon"
                      :class="{ 'is-empty': !socialIcon(row.url) }"
                      aria-hidden="true"
                    >
                      <SocialGlyph :url="row.url" :size="18" />
                    </span>
                    <input
                      v-model="row.url"
                      class="field__input linkrow__input"
                      :class="{ 'is-invalid': linkInvalid(row.url) }"
                      type="text"
                      inputmode="url"
                      maxlength="200"
                      :aria-label="`Social link ${i + 1} URL`"
                      :aria-invalid="linkInvalid(row.url) || undefined"
                      placeholder="https://instagram.com/you"
                    />
                    <button
                      class="linkrow__remove"
                      type="button"
                      :aria-label="`Remove link ${i + 1}`"
                      @click="removeLink(i)"
                    >
                      ×
                    </button>
                  </div>
                  <p v-if="linkInvalid(row.url)" class="linkrow__hint" role="alert">
                    That doesn’t look like a link — use a full address, e.g. https://…
                  </p>
                </div>
                <button
                  v-if="links.length < 10"
                  class="linkrow__add"
                  type="button"
                  @click="addLink"
                >
                  + Add link
                </button>
              </div>
              <div class="profile__actions">
                <button class="btn-primary" type="submit" :disabled="saving">
                  {{ saving ? 'Saving…' : 'Save profile' }}
                </button>
                <span class="profile__status" role="status" aria-live="polite">
                  <span v-if="saveMsg === 'saved'" class="profile__ok">✓ Saved</span>
                  <span v-else-if="saveMsg === 'error'" class="profile__err"
                    >Couldn’t save — try again</span
                  >
                </span>
              </div>
            </form>
          </div>
        </div>

        <!-- Favorites -->
        <div class="card">
          <h2 class="card__title">
            Favorites
            <span v-if="!loadingFaves" class="card__count">{{ favorites.length }}</span>
          </h2>

          <p v-if="loadingFaves" class="muted">Loading…</p>
          <p v-else-if="favesError" class="muted" role="alert">{{ favesError }}</p>
          <p v-else-if="favorites.length === 0" class="muted">
            No saved patterns yet. Hit the heart on a generated pattern to save it here.
          </p>

          <ul v-else class="faves">
            <li v-for="fave in favorites" :key="fave.id" class="fave">
              <div class="fave__screen">
                <GrooveScore v-if="isPattern(fave)" :groove="(fave.phrase as Groove)" />
                <ScoreView v-else :phrase="(fave.phrase as Phrase)" />
              </div>
              <div class="fave__meta">
                <span v-for="k in ['level', 'meter', 'feel', 'bars', 'tempo']" :key="k">
                  <template v-if="chip(fave, k)">
                    <span class="fave__chip"
                      >{{ chip(fave, k)
                      }}{{ k === 'tempo' ? ' bpm' : k === 'bars' ? ' bars' : '' }}</span
                    >
                  </template>
                </span>
              </div>
              <div class="fave__actions">
                <button class="fave__btn" type="button" @click="openInGenerator(fave)">
                  Open in generator
                </button>
                <button class="fave__btn fave__btn--danger" type="button" @click="remove(fave.id)">
                  Remove
                </button>
              </div>
            </li>
          </ul>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.account {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  padding: 20px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), var(--inset);
}

.card__title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text);
}

.card__count {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--amber-bright);
  border: 1px solid var(--edge);
  border-radius: 999px;
  padding: 1px 8px;
}

.muted {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.9rem;
}

.account__loading {
  padding: 24px 4px;
}

.profile {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
}

.profile__avatarcol {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  /* Pinned width so a long list of social links wraps to more rows instead of
     stretching the column and shoving the fields sideways. */
  flex: none;
  width: 128px;
}

.profile__avatar {
  display: grid;
  place-items: center;
  width: 96px;
  height: 96px;
  border-radius: 999px;
  overflow: hidden;
  background: linear-gradient(160deg, var(--amber), var(--amber-dim));
  color: var(--on-amber);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 2rem;
  box-shadow: 0 0 22px -6px var(--amber-glow);
}

.profile__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile__upload {
  /* Pinned width (fits the longest label) + centred text so swapping to
     "Working…" doesn't resize the button and nudge the column. */
  min-width: 112px;
  padding: 6px 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.64rem;
  letter-spacing: 0.08em;
  text-align: center;
  text-transform: uppercase;
  cursor: pointer;
}

.profile__upload:hover:not(:disabled) {
  color: var(--amber-bright);
}

.profile__avatar-error {
  margin: 0;
  max-width: 120px;
  text-align: center;
  color: var(--danger);
  font-size: 0.72rem;
}

.profile__avatar-ok {
  margin: 0;
  max-width: 120px;
  text-align: center;
  color: var(--amber-bright);
  font-size: 0.72rem;
}

/* Social icons under the avatar (saved links). */
.socials {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 12px;
  margin-top: 12px;
  max-width: 100%;
}

.socials__link {
  display: inline-flex;
  color: var(--text-dim);
  line-height: 0;
  transition: color 0.15s ease;
}

.socials__link:hover {
  color: var(--amber-bright);
}

.profile__fields {
  flex: 1 1 260px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Links editor: one row per link — detected icon + URL input + remove. */
.linkitem {
  margin-bottom: 10px;
}

.linkrow {
  display: flex;
  align-items: center;
  gap: 8px;
}

.linkrow__input.is-invalid {
  box-shadow: inset 0 0 0 1px var(--danger);
}

.linkrow__hint {
  /* Indent past the 20px icon + 8px gap so it aligns under the input. */
  margin: 4px 0 0 28px;
  color: var(--danger);
  font-size: 0.72rem;
  line-height: 1.35;
}

.linkrow__icon {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  color: var(--text-dim);
}

.linkrow__icon.is-empty {
  opacity: 0.3;
}

.linkrow__input {
  flex: 1 1 auto;
  min-width: 0;
}

.linkrow__remove {
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: transparent;
  color: var(--text-faint);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.15s ease;
}

.linkrow__remove:hover {
  color: var(--danger);
}

.linkrow__add {
  align-self: flex-start;
  padding: 5px 10px;
  border: 1px dashed var(--edge);
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.linkrow__add:hover {
  color: var(--amber-bright);
  border-color: var(--amber-dim);
}

.profile__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.profile__status {
  /* Reserve room so the row height is stable whether or not a message shows. */
  min-height: 1.2em;
}

.profile__ok {
  color: var(--amber-bright);
  font-size: 0.85rem;
}

.profile__err {
  color: var(--danger);
  font-size: 0.85rem;
}

.faves {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
  gap: 14px;
}

.fave {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--field-ink), var(--chassis));
}

.fave__screen {
  border-radius: var(--r-sm);
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  overflow: hidden;
}

.fave__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.fave__chip {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  border: 1px solid var(--edge);
  border-radius: var(--r-sm);
  padding: 2px 7px;
}

.fave__actions {
  display: flex;
  gap: 8px;
  margin-top: 2px;
}

.fave__btn {
  flex: 1;
  padding: 7px 10px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
  transition: color 0.15s ease;
}

.fave__btn:hover {
  color: var(--amber-bright);
}

.fave__btn--danger:hover {
  color: var(--danger);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

/* Touch devices: grow the small controls to a comfortable ≥44px target. */
@media (pointer: coarse) {
  .profile__upload {
    min-height: 44px;
  }

  .linkrow__remove {
    width: 44px;
    height: 44px;
  }

  .linkrow__add {
    min-height: 44px;
  }

  .socials__link {
    padding: 10px;
  }
}
</style>
