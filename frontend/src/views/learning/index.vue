<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';
import { NCard, NButton, NProgress, NTag } from 'naive-ui';
import { fetchGenerateQuizStream, completeQuiz } from '@/service/api/learning';
import type { QuizCard, QuizAnswer } from '@/service/api/learning';
import ChatSidebar from './modules/chat-sidebar.vue';

const route = useRoute();
const router = useRouter();
const chatSidebarRef = ref<InstanceType<typeof ChatSidebar> | null>(null);

const fileMd5 = (route.query.fileMd5 as string) || '';
const fileName = (route.query.name as string) || fileMd5;

// ── Select-to-search ──
const showSelectPopup = ref(false);
const selectPopupStyle = ref<Record<string, string>>({});

function onQuizMouseUp() {
  const sel = window.getSelection();
  const text = sel?.toString().trim();
  if (!text || text.length < 2) {
    showSelectPopup.value = false;
    return;
  }
  const range = sel!.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  selectPopupStyle.value = {
    position: 'fixed',
    left: `${rect.left + rect.width / 2 - 50}px`,
    top: `${rect.top - 40}px`,
  };
  showSelectPopup.value = true;
}

function askAgent() {
  const sel = window.getSelection();
  const text = sel?.toString().trim();
  if (!text) return;
  const title = currentCard.value?.title || '';
  chatSidebarRef.value?.setInput(`主题: ${title}\n解释一下：${text}`);
  showSelectPopup.value = false;
  window.getSelection()?.removeAllRanges();
}

// ── State ──
type PageState = 'loading' | 'quiz' | 'result' | 'error';
const pageState = ref<PageState>('loading');
const errorMsg = ref('');

// Debug logging
console.log('[LetsLearn] Learning page mounted', { fileMd5, fileName, fullPath: route.fullPath, query: route.query });

// Loading animation
const loadingText = ref('正在初始化...');
const progressDone = ref(0);
const progressTotal = ref(0);

// Quiz state
const cards = ref<QuizCard[]>([]);
const currentCardIndex = ref(0);
const selectedOption = ref<string | null>(null);
const submitted = ref(false);
const correctCount = ref(0);
const userAnswers = ref<QuizAnswer[]>([]);
const isSaving = ref(false);
const saveError = ref('');

// ── Computed ──
const currentCard = computed(() => cards.value[currentCardIndex.value] || null);
const isLastCard = computed(() => currentCardIndex.value >= cards.value.length - 1);
const totalCards = computed(() => cards.value.length);
const accuracy = computed(() => totalCards.value > 0 ? Math.round((correctCount.value / totalCards.value) * 100) : 0);

// Computed: selected option's full data for the current card
const selectedOptionData = computed(() => {
  if (!selectedOption.value || !currentCard.value) return null;
  return currentCard.value.options.find(o => o.label === selectedOption.value) || null;
});
const correctOptionData = computed(() => {
  if (!currentCard.value) return null;
  return currentCard.value.options.find(o => o.isCorrect) || null;
});

// ── Lifecycle ──
onMounted(async () => {
  try {
    console.log('[LetsLearn] Streaming quiz generation for fileMd5:', fileMd5);
    const result = await fetchGenerateQuizStream(fileMd5, (event) => {
      console.log('[LetsLearn SSE]', event.type, event);
      if (event.type === 'start') {
        progressTotal.value = event.total || 0;
        loadingText.value = '正在分析章节知识点...';
      } else if (event.type === 'progress') {
        progressDone.value = event.done || 0;
        progressTotal.value = event.total || progressTotal.value;
        loadingText.value = `已生成 ${progressDone.value} / ${progressTotal.value} 张卡片...`;
      }
    });
    console.log('[LetsLearn] Quiz complete:', result.length, 'cards');
    cards.value = result;
    pageState.value = 'quiz';
  } catch (e: any) {
    console.error('[LetsLearn] Quiz generation failed:', e);
    errorMsg.value = e.message || '生成失败';
    pageState.value = 'error';
  }
});

// ── Card actions ──
function selectOption(label: string) {
  if (submitted.value) return;
  selectedOption.value = label;
}

function submitAnswer() {
  if (!selectedOption.value || !currentCard.value) {
    console.warn('[LetsLearn] submitAnswer blocked:', { selected: selectedOption.value, hasCard: !!currentCard.value });
    return;
  }
  submitted.value = true;
  const opt = currentCard.value.options.find(o => o.label === selectedOption.value);
  const isCorrect = !!opt?.isCorrect;
  if (isCorrect) correctCount.value++;
  userAnswers.value.push({
    cardIndex: currentCardIndex.value,
    selectedLabel: selectedOption.value,
    isCorrect
  });
}

function nextCard() {
  if (isLastCard.value) {
    pageState.value = 'result';
  } else {
    currentCardIndex.value++;
    selectedOption.value = null;
    submitted.value = false;
  }
}

async function saveAndReturn() {
  isSaving.value = true;
  saveError.value = '';
  try {
    await completeQuiz(fileMd5, fileName, cards.value, userAnswers.value);
    router.push({ name: 'knowledge-base' });
  } catch (e: any) {
    saveError.value = e.message || '保存失败';
    isSaving.value = false;
  }
}

function backToKnowledge() {
  router.push({ name: 'knowledge-base' });
}

// ── Helpers ──
function optionClass(label: string) {
  if (!submitted.value) {
    return selectedOption.value === label ? 'option-selected' : '';
  }
  const opt = currentCard.value?.options.find(o => o.label === label);
  if (opt?.isCorrect) return 'option-correct';
  if (selectedOption.value === label && !opt?.isCorrect) return 'option-wrong';
  return 'option-dimmed';
}
</script>

<template>
  <div class="learning-page" @mouseup="onQuizMouseUp">
    <!-- ── Loading State ── -->
    <div v-if="pageState === 'loading'" class="loading-container">
      <NCard :bordered="false" class="loading-card">
        <div class="loading-content">
          <div class="spinner"></div>
          <h2 class="loading-title">AI 正在为你生成学习卡片</h2>
          <p class="loading-filename">{{ fileName }}</p>
          <div class="loading-text">{{ loadingText }}</div>
          <NProgress
            v-if="progressTotal > 0"
            type="line"
            :percentage="Math.round((progressDone / progressTotal) * 100)"
            :indicator-placement="'inside'"
            :height="20"
            class="loading-progress"
          />
          <p class="loading-hint" v-else>首次生成需要 15-30 秒，请耐心等待</p>
        </div>
      </NCard>
    </div>

    <!-- ── Error State ── -->
    <div v-else-if="pageState === 'error'" class="loading-container">
      <NCard :bordered="false" class="loading-card">
        <div class="loading-content">
          <h2 class="error-title">生成失败</h2>
          <p class="error-msg">{{ errorMsg }}</p>
          <NButton type="primary" @click="backToKnowledge">返回知识库</NButton>
        </div>
      </NCard>
    </div>

    <!-- ── Quiz State ── -->
    <div v-else-if="pageState === 'quiz' && currentCard" class="quiz-split-layout">
      <div class="quiz-left">
        <div class="quiz-container">
      <NCard :bordered="false" class="quiz-card">
        <!-- Header -->
        <div class="quiz-header">
          <NTag type="info" size="small">Card {{ currentCardIndex + 1 }} / {{ totalCards }}</NTag>
          <span class="quiz-filename">{{ fileName }}</span>
        </div>

        <!-- AI Explanation -->
        <div class="quiz-explanation">
          <h3 class="section-title">
            <NTag v-if="(currentCard as any).isMistake" type="warning" size="small" style="margin-right:8px">⚠️ 复习错题</NTag>
            {{ currentCard.title }}
          </h3>
          <p class="explanation-text">{{ currentCard.aiExplanation }}</p>
        </div>

        <div class="quiz-divider"></div>

        <!-- Question + Options -->
        <div class="quiz-question-area">
          <h3 class="question-text">{{ currentCard.question }}</h3>

          <div class="options-list">
            <div
              v-for="opt in currentCard.options"
              :key="opt.label"
              :class="['option-item', optionClass(opt.label)]"
              @click="selectOption(opt.label)"
            >
              <span class="option-label">{{ opt.label }}</span>
              <span class="option-text">{{ opt.text }}</span>
            </div>
          </div>

          <!-- Submit button (before submission) -->
          <div v-if="!submitted" class="submit-area">
            <NButton
              type="primary"
              size="large"
              :disabled="!selectedOption"
              @click="submitAnswer"
            >
              提交
            </NButton>
          </div>

          <!-- Result panel (after submission, Duolingo-style) -->
          <div v-else class="result-panel">
            <div :class="['result-header', selectedOptionData?.isCorrect ? 'correct' : 'wrong']">
              <span v-if="selectedOptionData?.isCorrect">✅ 回答正确!</span>
              <span v-else>❌ 回答错误 <span class="correct-answer-hint">(正确答案: {{ correctOptionData?.label }})</span></span>
            </div>
            <p class="feedback-text">
              {{ selectedOptionData?.feedback || '(无反馈内容)' }}
            </p>
            <div class="next-area">
              <NButton type="primary" size="large" @click="nextCard">
                {{ isLastCard ? '查看结果' : '下一题 →' }}
              </NButton>
            </div>
          </div>
        </div>
      </NCard>
        </div><!-- .quiz-container -->
      </div><!-- .quiz-left -->

      <ChatSidebar ref="chatSidebarRef" :file-name="fileName" />

      <!-- Select-to-search popup -->
      <div v-if="showSelectPopup" class="select-popup" :style="selectPopupStyle">
        <NButton size="tiny" type="info" @click="askAgent">问问Agent</NButton>
      </div>
    </div><!-- .quiz-split-layout -->

    <!-- ── Result State ── -->
    <div v-else-if="pageState === 'result'" class="loading-container">
      <NCard :bordered="false" class="loading-card">
        <div class="loading-content">
          <div v-if="isSaving" class="spinner"></div>
          <div v-else class="result-icon-large">{{ accuracy >= 80 ? '🎉' : accuracy >= 50 ? '👍' : '💪' }}</div>
          <h2 v-if="isSaving" class="result-title">正在保存quiz结果...</h2>
          <h2 v-else class="result-title">学习完成!</h2>
          <p class="result-stats">
            正确率: {{ correctCount }} / {{ totalCards }} ({{ accuracy }}%)
          </p>
          <p v-if="isSaving" class="loading-hint">请勿关闭窗口</p>
          <p v-if="saveError" class="error-msg">{{ saveError }}</p>
          <NButton v-if="!isSaving" type="primary" size="large" @click="saveAndReturn">
            保存并返回
          </NButton>
        </div>
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.learning-page {
  min-height: 80vh;
  display: flex;
  justify-content: center;
  padding: 24px 16px;
}

/* ── Split layout ── */
.quiz-split-layout {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
  width: 100%;
  padding: 0;
}

.quiz-left {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 24px 16px;
}

/* ── Select-to-search popup ── */
.select-popup {
  z-index: 1000;
}

.select-popup button {
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* ── Loading / Error / Result ── */
.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 560px;
}

.loading-card {
  width: 100%;
  text-align: center;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px 24px;
}

/* Spinning animation */
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #2080f0;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.loading-filename {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.loading-text {
  color: #2080f0;
  font-size: 15px;
  font-weight: 500;
  min-height: 24px;
}

.loading-progress {
  width: 80%;
  max-width: 400px;
}

.loading-hint {
  color: #999;
  font-size: 13px;
  margin: 0;
}

.error-title {
  color: #d03050;
  font-size: 20px;
  margin: 0;
}

.error-msg {
  color: #666;
  font-size: 14px;
}

/* ── Quiz ── */
.quiz-container {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
}

.quiz-card {
  width: 100%;
}

.quiz-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.quiz-filename {
  color: #999;
  font-size: 13px;
}

.quiz-explanation {
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #2080f0;
  margin: 0 0 8px 0;
}

.explanation-text {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
}

.quiz-divider {
  height: 1px;
  background: #eee;
  margin: 20px 0;
}

.quiz-question-area {
  /* question + options area */
}

.question-text {
  font-size: 17px;
  font-weight: 600;
  margin: 0 0 20px 0;
  line-height: 1.6;
}

/* ── Options ── */
.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-item:hover {
  border-color: #a0c4ff;
  background: #f8faff;
}

.option-item.option-selected {
  border-color: #2080f0;
  background: #e8f0fe;
}

.option-item.option-correct {
  border-color: #18a058;
  background: #e8f8ee;
}

.option-item.option-wrong {
  border-color: #d03050;
  background: #fde8ec;
}

.option-item.option-dimmed {
  opacity: 0.5;
}

.option-label {
  font-weight: 700;
  font-size: 15px;
  color: #666;
  min-width: 24px;
}

.option-text {
  font-size: 15px;
  line-height: 1.5;
  color: #333;
}

/* ── Submit / Result ── */
.submit-area {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.result-panel {
  margin-top: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-header {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
}

.result-header.correct {
  color: #18a058;
}

.result-header.wrong {
  color: #d03050;
}

.correct-answer-hint {
  font-size: 14px;
  font-weight: 400;
  color: #18a058;
  margin-left: 8px;
}

.feedback-text {
  font-size: 15px;
  line-height: 1.7;
  color: #444;
  margin: 0 0 16px 0;
}

.next-area {
  display: flex;
  justify-content: flex-end;
}

/* ── Result ── */
.result-icon-large {
  font-size: 56px;
}

.result-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.result-stats {
  font-size: 18px;
  color: #333;
  margin: 8px 0 16px 0;
}
</style>
