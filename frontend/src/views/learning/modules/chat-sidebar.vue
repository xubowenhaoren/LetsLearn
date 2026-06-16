<script setup lang="ts">
import { NButton, NInput, NScrollbar, NTag } from 'naive-ui';
import ChatMessage from '@/views/chat/modules/chat-message.vue';

const props = defineProps<{ fileName: string }>();
const chatStore = useChatStore();
const inputText = ref('');
let previousSessionId: string | null = null;
let pendingAssistantIndex = -1;

// ── Session isolation ──
onMounted(async () => {
  previousSessionId = chatStore.conversationId;
  const now = new Date();
  const dateStr = `${now.getFullYear()}/${String(now.getMonth() + 1).padStart(2, '0')}/${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  await chatStore.createNewSession(`学习: ${props.fileName} ${dateStr}`);
});

// ── Find pending assistant message by generationId ──
function findAssistantMessage(generationId?: string) {
  if (!generationId) return null;
  for (let i = chatStore.list.length - 1; i >= 0; i--) {
    const msg = chatStore.list[i];
    if (msg.role === 'assistant' && (msg as any).generationId === generationId) {
      return msg;
    }
  }
  // Fallback: find any pending assistant
  for (let i = chatStore.list.length - 1; i >= 0; i--) {
    const msg = chatStore.list[i];
    if (msg.role === 'assistant' && (msg.status === 'pending' || msg.status === 'streaming')) {
      return msg;
    }
  }
  return null;
}

// ── WebSocket message handler (same logic as input-box.vue) ──
watch(() => chatStore.wsData, (val) => {
  if (!val) return;
  let payload: Record<string, any>;
  try {
    payload = JSON.parse(val as string);
  } catch {
    return;
  }
  // Use tracked index instead of searching (avoids matching wrong pending message)
  const assistant = (pendingAssistantIndex >= 0 && pendingAssistantIndex < chatStore.list.length)
    ? chatStore.list[pendingAssistantIndex]
    : findAssistantMessage(payload.generationId);
  if (!assistant || assistant.role !== 'assistant') return;

  if (payload.type === 'start') {
    (assistant as any).generationId = payload.generationId;
    (assistant as any).conversationId = payload.conversationId;
    (assistant as any).status = 'streaming';
    return;
  }
  if (payload.type === 'completion') {
    assistant.status = payload.status === 'finished' ? 'completed' : 'failed';
    if (payload.referenceMappings) {
      (assistant as any).referenceMappings = payload.referenceMappings;
    }
    pendingAssistantIndex = -1;
    return;
  }
  if (payload.type === 'error' || Number(payload.code) >= 400) {
    assistant.status = 'failed';
    assistant.content = payload.message || '请求失败';
    return;
  }
  if (payload.chunk) {
    assistant.content = (assistant.content || '') + payload.chunk;
    (assistant as any).status = 'streaming';
  }
});

// ── Send message ──
function handleSend() {
  const text = inputText.value.trim();
  if (!text) return;
  chatStore.list.push({ content: text, role: 'user' } as any);
  chatStore.list.push({ content: '', role: 'assistant', status: 'pending' } as any);
  pendingAssistantIndex = chatStore.list.length - 1;
  chatStore.wsSend(text);
  inputText.value = '';
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

// ── Exposed for select-to-search ──
function setInput(text: string) {
  inputText.value = text;
}
defineExpose({ setInput });
</script>

<template>
  <div class="chat-sidebar">
    <div class="sidebar-header">
      <NTag type="info" size="small">AI 助手</NTag>
      <span class="sidebar-title">{{ props.fileName }}</span>
    </div>

    <NScrollbar class="sidebar-messages">
      <div class="messages-list">
        <ChatMessage
          v-for="(msg, i) in chatStore.list"
          :key="i"
          :msg="msg"
          :session-id="chatStore.sessionId"
        />
        <div v-if="chatStore.list.length === 0" class="empty-hint">
          <p>选中左侧精讲文字，点击"问问Agent"即可提问</p>
          <p>也可以直接在下方输入框中提问</p>
        </div>
      </div>
    </NScrollbar>

    <div class="sidebar-input">
      <NInput
        v-model:value="inputText"
        type="textarea"
        placeholder="输入问题，基于知识库回答..."
        :autosize="{ minRows: 2, maxRows: 4 }"
        @keydown="handleKeydown"
      />
      <NButton type="primary" size="small" @click="handleSend" class="send-btn">
        发送
      </NButton>
    </div>
  </div>
</template>

<style scoped>
.chat-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 50%;
  min-width: 380px;
  max-width: 600px;
  flex-shrink: 0;
  background: #fafbfc;
  border-left: 1px solid #e8e8e8;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 13px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-messages {
  flex: 1;
  min-height: 0;
}

.messages-list {
  padding: 12px 16px;
}

.empty-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 40px 16px;
  line-height: 1.8;
}

.sidebar-input {
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
  flex-shrink: 0;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.send-btn {
  flex-shrink: 0;
}
</style>
