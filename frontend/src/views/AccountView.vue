<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import ScoreView from '../components/ScoreView.vue'
import { ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { setPendingPhrase } from '../lib/loadedPattern'
import { listLiked, unlikePattern, updateProfile, uploadAvatar } from '../lib/patterns'
import type { LikedPattern } from '../lib/patterns'

const router = useRouter()
const { user, setUser } = useAuth()

// --- Profile editor ---------------------------------------------------------
const displayName = ref(user.value?.display_name ?? '')
const bio = ref(user.value?.bio ?? '')
const saving = ref(false)
const saveMsg = ref<'' | 'saved' | 'error'>('')
const avatarBusy = ref(false)
const avatarError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

async function saveProfile(): Promise<void> {
  saving.value = true
  saveMsg.value = ''
  try {
    const updated = await updateProfile(displayName.value.trim(), bio.value)
    setUser(updated)
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
  if (!file) return
  avatarBusy.value = true
  avatarError.value = ''
  try {
    const updated = await uploadAvatar(file)
    setUser(updated)
  } catch (err) {
    avatarError.value =
      err instanceof ApiError && (err.status === 400 || err.status === 413)
        ? err.message
        : 'Upload failed. Please try again.'
  } finally {
    avatarBusy.value = false
    input.value = ''
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
  setPendingPhrase(fave.phrase)
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

      <section v-if="user" class="account">
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
                {{ avatarBusy ? 'Uploading…' : 'Change photo' }}
              </button>
              <input
                ref="fileInput"
                class="visually-hidden"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                @change="onAvatarPicked"
              />
              <p v-if="avatarError" class="profile__avatar-error">{{ avatarError }}</p>
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
              <div class="profile__actions">
                <button class="btn-primary" type="submit" :disabled="saving">
                  {{ saving ? 'Saving…' : 'Save profile' }}
                </button>
                <span v-if="saveMsg === 'saved'" class="profile__ok">Saved</span>
                <span v-else-if="saveMsg === 'error'" class="profile__err">Couldn't save</span>
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
                <ScoreView :phrase="fave.phrase" />
              </div>
              <div class="fave__meta">
                <span v-for="k in ['level', 'meter', 'feel', 'bars', 'tempo']" :key="k">
                  <template v-if="chip(fave, k)">
                    <span class="fave__chip">{{ chip(fave, k) }}{{ k === 'tempo' ? ' bpm' : '' }}</span>
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
  flex: none;
}

.profile__avatar {
  display: grid;
  place-items: center;
  width: 96px;
  height: 96px;
  border-radius: 999px;
  overflow: hidden;
  background: linear-gradient(160deg, var(--amber), var(--amber-dim));
  color: #1a1206;
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
  padding: 6px 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.64rem;
  letter-spacing: 0.08em;
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

.profile__fields {
  flex: 1 1 260px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.profile__ok {
  color: #9fd68a;
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
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

.fave {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, #171310, var(--chassis));
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
</style>
