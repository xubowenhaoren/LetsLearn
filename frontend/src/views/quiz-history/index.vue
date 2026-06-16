<script setup lang="ts">
import { NCard, NButton, NTag } from 'naive-ui';
import { fetchLatestQuiz } from '@/service/api/learning';
import type { QuizCard, QuizOption } from '@/service/api/learning';

const route = useRoute();
const router = useRouter();
const fileMd5 = (route.query.fileMd5 as string) || '';

interface QuizState {
  cards: QuizCard[];
  userAnswers: Record<number, { selectedLabel: string; isCorrect: boolean }>;
  correctCount: number;
  totalCount: number;
  accuracy: number;
  fileName: string;
  createdAt: string;
}

const quiz = ref<QuizState | null>(null);
const loading = ref(true);
const error = ref('');

onMounted(async () => {
  try {
    const data = await fetchLatestQuiz(fileMd5);
    if (!data.hasQuiz || !data.cardsJson) {
      error.value = '暂无quiz记录';
      return;
    }
    const cards: QuizCard[] = JSON.parse(data.cardsJson);
    const userAnswers: QuizAnswer[] = data.userAnswersJson ? JSON.parse(data.userAnswersJson) : [];
    const answerMap: Record<number, { selectedLabel: string; isCorrect: boolean }> = {};
    for (const a of userAnswers) {
      answerMap[a.cardIndex] = { selectedLabel: a.selectedLabel, isCorrect: a.isCorrect };
    }
    quiz.value = {
      cards,
      userAnswers: answerMap,
      correctCount: data.correctCount || 0,
      totalCount: data.totalCount || cards.length,
      accuracy: data.accuracy || 0,
      fileName: '',
      createdAt: data.createdAt || '',
    };
  } catch (e: any) {
    error.value = e.message || '加载失败';
  } finally {
    loading.value = false;
  }
});

function optionClass(cardIndex: number, opt: QuizOption) {
  const ua = quiz.value?.userAnswers[cardIndex];
  if (!ua) return 'option-dimmed';
  if (opt.isCorrect) return 'option-correct';
  if (ua.selectedLabel === opt.label && !ua.isCorrect) return 'option-wrong';
  return 'option-dimmed';
}

function backToKnowledge() {
  router.push({ name: 'knowledge-base' });
}
</script>

<template>
  <div class="quiz-history-page">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <h2>{{ error }}</h2>
      <NButton type="primary" @click="backToKnowledge">返回知识库</NButton>
    </div>

    <div v-else-if="quiz" class="history-content">
      <div class="history-header">
        <h2>Quiz 历史</h2>
        <NTag type="info">正确率: {{ quiz.correctCount }}/{{ quiz.totalCount }} ({{ quiz.accuracy }}%)</NTag>
        <span v-if="quiz.createdAt" class="history-time">{{ quiz.createdAt.replace('T', ' ').replace(/\.\d+/, '') }}</span>
      </div>

      <div v-for="(card, ci) in quiz.cards" :key="ci" class="history-card-wrapper">
        <NCard :bordered="false" class="history-card">
          <h3 class="card-title"><NTag v-if="card.isMistake" type="warning" size="small" style="margin-right:8px">⚠️ 复习错题</NTag> {{ card.title }}</h3>
          <p class="card-explanation">{{ card.aiExplanation }}</p>
          <div class="quiz-divider"></div>
          <h4 class="card-question">{{ card.question }}</h4>

          <div class="options-list">
            <div
              v-for="opt in card.options"
              :key="opt.label"
              :class="['option-item', optionClass(ci, opt)]"
            >
              <span class="option-label">{{ opt.label }}</span>
              <span class="option-text">{{ opt.text }}</span>
            </div>
          </div>

          <div class="card-feedback">
            <p v-if="quiz.userAnswers[ci]">
              💬 {{ card.options.find(o => o.label === quiz.userAnswers[ci].selectedLabel)?.feedback || '无反馈' }}
            </p>
          </div>
        </NCard>
      </div>

      <div class="history-footer">
        <NButton type="primary" size="large" @click="backToKnowledge">返回知识库</NButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quiz-history-page {
  min-height: 80vh;
  padding: 24px 16px;
  max-width: 860px;
  margin: 0 auto;
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
}

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

.history-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.history-header h2 {
  margin: 0;
  font-size: 22px;
}

.history-time {
  color: #999;
  font-size: 13px;
}

.history-card-wrapper {
  margin-bottom: 24px;
}

.history-card {
  width: 100%;
}

.card-title {
  font-size: 17px;
  font-weight: 600;
  color: #2080f0;
  margin: 0 0 12px 0;
}

.card-explanation {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
}

.quiz-divider {
  height: 1px;
  background: #eee;
  margin: 16px 0;
}

.card-question {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
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
  opacity: 0.45;
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

.card-feedback {
  margin-top: 12px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.card-feedback p {
  margin: 0;
  font-size: 14px;
  color: #555;
  line-height: 1.6;
}

.history-footer {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}
</style>
