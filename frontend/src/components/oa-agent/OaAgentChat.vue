<template>
  <section class="agent-shell">
    <div class="agent-header">
      <div>
        <h2>{{ title }}</h2>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <el-button text size="small" @click="resetSession">{{ t.clear }}</el-button>
    </div>

    <div ref="messageListRef" class="agent-messages">
      <div v-for="(item, index) in messages" :key="index" :class="['message-row', item.role]">
        <div class="message-bubble">
          <p v-for="(line, lineIndex) in renderMessageContent(item.content)" :key="lineIndex" class="message-line">
            <template v-for="(part, partIndex) in line" :key="partIndex">
              <router-link v-if="part.href" class="agent-link" :to="part.href">{{ part.text }}</router-link>
              <span v-else>{{ part.text }}</span>
            </template>
          </p>
        </div>
      </div>
      <el-empty v-if="messages.length === 0" :description="emptyText" />
    </div>

    <div v-if="candidates.length" class="candidate-list">
      <button
        v-for="candidate in candidates"
        :key="candidate.id"
        type="button"
        class="candidate-item"
        @click="chooseCandidate(candidate)"
      >
        <strong>{{ candidate.project_name }}</strong>
        <span>{{ candidate.project_code }} · {{ candidate.client_name }}</span>
        <em>{{ candidate.current_step || '-' }}</em>
      </button>
    </div>

    <form class="agent-input" @submit.prevent="submitMessage">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="submitMessage"
      />
      <el-button type="primary" :loading="sending" native-type="submit">{{ t.send }}</el-button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  clearAgentSession,
  clearLocalAgentSessionId,
  getAgentSession,
  readLocalAgentSessionId,
  saveLocalAgentSessionId,
  sendAgentMessage,
  setAgentProjectContext,
  type OaAgentProjectCandidate,
} from '@/api/oaAgent'

const props = defineProps<{
  projectId?: number
  title?: string
  subtitle?: string
  placeholder?: string
  emptyText?: string
}>()

const t = {
  clear: '\u6e05\u9664\u4f1a\u8bdd',
  send: '\u53d1\u9001',
  loadContextFailed: '\u9879\u76ee\u4e0a\u4e0b\u6587\u8bbe\u7f6e\u5931\u8d25',
  sendFailed: '\u53d1\u9001\u5931\u8d25',
}

const title = props.title || '\u004f\u0041 \u667a\u80fd\u5ba2\u670d'
const subtitle = props.subtitle || ''
const placeholder = props.placeholder || '\u8bf7\u8f93\u5165\u9879\u76ee\u540d\u79f0\u3001\u9879\u76ee\u7f16\u53f7\u3001\u5ba2\u6237\u540d\u79f0\u6216\u4f60\u60f3\u4e86\u89e3\u7684\u64cd\u4f5c'
const emptyText = props.emptyText || '\u53ef\u4ee5\u76f4\u63a5\u8be2\u95ee\u9879\u76ee\u8fdb\u5ea6\u6216\u4e0b\u4e00\u6b65\u64cd\u4f5c'
const draft = ref('')
const sending = ref(false)
const sessionId = ref<string>()
const messages = ref<Array<{ role: string; content: string }>>([])
const candidates = ref<OaAgentProjectCandidate[]>([])
const messageListRef = ref<HTMLElement | null>(null)

async function restoreSession() {
  const savedSessionId = readLocalAgentSessionId()
  if (!savedSessionId) return
  try {
    const session = await getAgentSession(savedSessionId)
    sessionId.value = session.session_id
    saveLocalAgentSessionId(session.session_id)
    messages.value = session.messages.map(item => ({
      role: item.role,
      content: item.content,
    }))
    await scrollToBottom()
  } catch {
    clearLocalAgentSessionId()
    sessionId.value = undefined
    messages.value = []
  }
}

async function initializeContext() {
  if (!props.projectId) return
  try {
    const session = await setAgentProjectContext({ project_id: props.projectId, session_id: sessionId.value })
    sessionId.value = session.session_id
    saveLocalAgentSessionId(session.session_id)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t.loadContextFailed)
  }
}

async function submitMessage() {
  const message = draft.value.trim()
  if (!message || sending.value) return
  draft.value = ''
  candidates.value = []
  messages.value.push({ role: 'user', content: message })
  sending.value = true
  try {
    const response = await sendAgentMessage({
      message,
      session_id: sessionId.value,
      project_id: props.projectId,
    })
    sessionId.value = response.session_id
    saveLocalAgentSessionId(response.session_id)
    if (response.answer) {
      messages.value.push({ role: 'assistant', content: response.answer })
    }
    candidates.value = response.candidates || []
    await scrollToBottom()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t.sendFailed)
  } finally {
    sending.value = false
  }
}

async function chooseCandidate(candidate: OaAgentProjectCandidate) {
  candidates.value = []
  messages.value.push({ role: 'user', content: `选择项目：${candidate.project_name}` })
  sending.value = true
  try {
    const response = await sendAgentMessage({
      message: '\u8bf7\u544a\u8bc9\u6211\u8fd9\u4e2a\u9879\u76ee\u5f53\u524d\u8fdb\u5ea6\u548c\u4e0b\u4e00\u6b65\u64cd\u4f5c',
      session_id: sessionId.value,
      project_id: candidate.id,
    })
    sessionId.value = response.session_id
    saveLocalAgentSessionId(response.session_id)
    if (response.answer) {
      messages.value.push({ role: 'assistant', content: response.answer })
    }
    await scrollToBottom()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t.sendFailed)
  } finally {
    sending.value = false
  }
}

async function resetSession() {
  await clearAgentSession()
  clearLocalAgentSessionId()
  sessionId.value = undefined
  messages.value = []
  candidates.value = []
  await initializeContext()
}

async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

function renderMessageContent(content: string) {
  const pathPattern = /(\/projects\/\d+\/flow\?todoPanel=[A-Za-z]+)/g
  return content.split(/\r?\n/).map((line) => {
    const parts: Array<{ text: string; href?: string }> = []
    let cursor = 0
    for (const match of line.matchAll(pathPattern)) {
      const value = match[0]
      const index = match.index ?? 0
      if (index > cursor) {
        parts.push({ text: line.slice(cursor, index) })
      }
      parts.push({ text: value, href: value })
      cursor = index + value.length
    }
    if (cursor < line.length || parts.length === 0) {
      parts.push({ text: line.slice(cursor) })
    }
    return parts
  })
}

onMounted(async () => {
  await restoreSession()
  await initializeContext()
})
</script>

<style scoped>
.agent-shell {
  display: flex;
  min-height: 420px;
  flex-direction: column;
  border: 1px solid var(--zq-border-soft);
  border-radius: 8px;
  background: #fff;
}

.agent-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--zq-border-soft);
}

.agent-header h2 {
  margin: 0;
  color: var(--zq-text);
  font-size: 16px;
}

.agent-header p {
  margin: 4px 0 0;
  color: var(--zq-muted);
  font-size: 12px;
}

.agent-messages {
  flex: 1;
  min-height: 260px;
  max-height: 520px;
  overflow: auto;
  padding: 16px;
  background: #f8fafc;
}

.message-row {
  display: flex;
  margin-bottom: 10px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: min(680px, 86%);
  word-break: break-word;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  color: #1f2937;
  line-height: 1.6;
  box-shadow: 0 1px 2px rgb(15 23 42 / 8%);
}

.message-line {
  min-height: 1.6em;
  margin: 0;
  white-space: pre-wrap;
}

.agent-link {
  color: var(--zq-primary);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.message-row.user .message-bubble {
  background: var(--zq-primary);
  color: #fff;
}

.message-row.user .agent-link {
  color: #fff;
}

.candidate-list {
  display: grid;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--zq-border-soft);
  background: #fff;
}

.candidate-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  width: 100%;
  border: 1px solid var(--zq-border-soft);
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.candidate-item:hover {
  border-color: var(--zq-primary);
}

.candidate-item strong {
  font-size: 14px;
}

.candidate-item span {
  color: #64748b;
  font-size: 12px;
}

.candidate-item em {
  grid-row: 1 / span 2;
  grid-column: 2;
  align-self: center;
  color: var(--zq-primary);
  font-size: 12px;
  font-style: normal;
}

.agent-input {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: end;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--zq-border-soft);
}

@media (max-width: 720px) {
  .agent-input {
    grid-template-columns: 1fr;
  }
}
</style>
