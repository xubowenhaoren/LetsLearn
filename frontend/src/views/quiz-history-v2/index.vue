<script setup lang="ts">
import { NCard, NButton, NTag, NScrollbar } from 'naive-ui';
import { fetchQuizHistory, fetchQuizDetail } from '@/service/api/learning';
import type { QuizHistoryItem, QuizCard, QuizOption } from '@/service/api/learning';
import { request } from '@/service/request';

const router = useRouter();
const route = useRoute();
const preselectedMd5 = (route.query.fileMd5 as string) || '';

// ── File list (reuse Java accessible API) ──
interface FileInfo { fileMd5: string; fileName: string; }
const files = ref<FileInfo[]>([]);
const selectedFileMd5 = ref('');

// ── Quiz list ──
const quizList = ref<QuizHistoryItem[]>([]);
const selectedQuizId = ref<number | null>(null);
const quizLoading = ref(false);

// ── Preview ──
interface PreviewState { cards: QuizCard[]; userAnswers: Record<number, { selectedLabel: string; isCorrect: boolean }>; correctCount: number; totalCount: number; accuracy: number; }
const preview = ref<PreviewState | null>(null);
const previewLoading = ref(false);
const noQuizYet = ref(false); // This file has no quiz records

onMounted(async () => {
  // Load files from Java accessible API
  try {
    const { error, data } = await request<any>({ url: '/documents/accessible' });
    if (!error) {
      const arr = data?.data || data || [];
      files.value = (Array.isArray(arr) ? arr : []).map((f: any) => ({
        fileMd5: f.fileMd5 || f.fileMd5,
        fileName: f.fileName || f.fileName || 'unknown'
      }));
      if (preselectedMd5 && files.value.some(f => f.fileMd5 === preselectedMd5)) {
        selectFile(preselectedMd5);
      } else if (files.value.length > 0) {
        selectFile(files.value[0].fileMd5);
      }
    }
  } catch (e) { console.warn('Failed to load files', e); }
});

async function selectFile(fileMd5: string) {
  selectedFileMd5.value = fileMd5;
  selectedQuizId.value = null;
  preview.value = null;
  noQuizYet.value = false;
  quizLoading.value = true;

  try {
    const list = await fetchQuizHistory(fileMd5);
    quizList.value = list;
    if (list.length > 0) {
      selectQuiz(list[0].quizId);
    } else {
      noQuizYet.value = true;
    }
  } catch (e) {
    quizList.value = [];
    noQuizYet.value = true;
  } finally {
    quizLoading.value = false;
  }
}

async function selectQuiz(quizId: number) {
  selectedQuizId.value = quizId;
  previewLoading.value = true;
  try {
    const data = await fetchQuizDetail(quizId);
    const cards: QuizCard[] = JSON.parse(data.cardsJson);
    const rawAnswers = data.userAnswersJson ? JSON.parse(data.userAnswersJson) : [];
    const answerMap: Record<number, { selectedLabel: string; isCorrect: boolean }> = {};
    for (const a of rawAnswers) answerMap[a.cardIndex] = { selectedLabel: a.selectedLabel, isCorrect: a.isCorrect };
    preview.value = {
      cards, userAnswers: answerMap,
      correctCount: data.correctCount, totalCount: data.totalCount, accuracy: data.accuracy
    };
  } catch (e) { console.error('Failed to load quiz detail', e); }
  finally { previewLoading.value = false; }
}

function optionClass(cardIndex: number, opt: QuizOption) {
  const ua = preview.value?.userAnswers[cardIndex];
  if (!ua) return 'option-dimmed';
  if (opt.isCorrect) return 'option-correct';
  if (ua.selectedLabel === opt.label && !ua.isCorrect) return 'option-wrong';
  return 'option-dimmed';
}

function goLearn() { router.push({ name: 'knowledge-base' }); }
</script>

<template>
  <div class="history-v2">
    <!-- Left: File list -->
    <div class="panel panel-files">
      <h3>文件列表</h3>
      <NScrollbar>
        <div v-for="f in files" :key="f.fileMd5"
             :class="['file-item', { active: f.fileMd5 === selectedFileMd5 }]"
             @click="selectFile(f.fileMd5)">
          {{ f.fileName }}
        </div>
        <div v-if="files.length === 0" class="empty-text">暂无文件</div>
      </NScrollbar>
    </div>

    <!-- Middle: Quiz list -->
    <div class="panel panel-quiz-list">
      <h3>Quiz 记录</h3>
      <NScrollbar>
        <div v-if="quizLoading" class="empty-text">加载中...</div>
        <div v-else-if="quizList.length === 0" class="empty-text">
          {{ noQuizYet ? '暂无记录' : '请选择文件' }}
        </div>
        <div v-for="q in quizList" :key="q.quizId"
             :class="['quiz-item', { active: q.quizId === selectedQuizId }]"
             @click="selectQuiz(q.quizId)">
          <div class="quiz-item-time">{{ q.createdAt?.replace('T',' ').replace(/\.\d+/,'') }}</div>
          <div class="quiz-item-row">
            <NTag type="info" size="small">{{ q.accuracy }}% ({{ q.correctCount }}/{{ q.totalCount }})</NTag>
            <span style="color: #2080f0; font-size:13px; cursor:pointer">查看详情</span>
          </div>
        </div>
      </NScrollbar>
    </div>

    <!-- Right: Preview -->
    <div class="panel panel-preview">
      <h3>预览</h3>
      <NScrollbar>
        <div v-if="previewLoading" class="empty-text">加载中...</div>
        <div v-else-if="!preview && !noQuizYet" class="empty-text">请选择 quiz 记录</div>
        <div v-else-if="noQuizYet" class="placeholder">
          <div class="placeholder-icon">📋</div>
          <h3>暂无 Quiz 记录</h3>
          <p>完成第一个 quiz 后，可以在这里预览 quiz 详情</p>
          <NButton type="primary" size="small" @click="goLearn">去学习 →</NButton>
        </div>
        <div v-else class="preview-content">
          <div class="preview-header">
            <NTag type="info">{{ preview!.accuracy }}% ({{ preview!.correctCount }}/{{ preview!.totalCount }})</NTag>
          </div>
          <div v-for="(card, ci) in preview!.cards" :key="ci" class="history-card-wrapper">
            <NCard :bordered="false" class="history-card">
              <h3 class="card-title"><NTag v-if="card.isMistake" type="warning" size="small" style="margin-right:8px">⚠️ 复习错题</NTag> {{ card.title }}</h3>
              <p class="card-explanation">{{ card.aiExplanation }}</p>
              <div class="quiz-divider"></div>
              <h4 class="card-question">{{ card.question }}</h4>
              <div class="options-list">
                <div v-for="opt in card.options" :key="opt.label"
                     :class="['option-item', optionClass(ci, opt)]">
                  <span class="option-label">{{ opt.label }}</span>
                  <span class="option-text">{{ opt.text }}</span>
                </div>
              </div>
              <div class="card-feedback">
                <p v-if="preview!.userAnswers[ci]">
                  💬 {{ card.options.find(o => o.label === preview!.userAnswers[ci].selectedLabel)?.feedback || '无反馈' }}
                </p>
              </div>
            </NCard>
          </div>
        </div>
      </NScrollbar>
    </div>
  </div>
</template>

<style scoped>
.history-v2 {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e8e8e8;
  padding: 16px;
}

.panel h3 {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  flex-shrink: 0;
}

.panel-files { width: 18%; min-width: 140px; }
.panel-quiz-list { width: 25%; min-width: 200px; }
.panel-preview { flex: 1; border-right: none; }

.file-item, .quiz-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  font-size: 13px;
}
.file-item:hover, .quiz-item:hover { background: #f0f4ff; }
.file-item.active, .quiz-item.active { background: #e0e8ff; font-weight: 600; }

.quiz-item-time { font-size: 12px; color: #999; margin-bottom: 4px; }
.quiz-item-row { display: flex; align-items: center; justify-content: space-between; }

.empty-text { color: #999; font-size: 13px; padding: 20px 0; text-align: center; }

.placeholder { text-align: center; padding: 60px 20px; color: #666; }
.placeholder-icon { font-size: 48px; margin-bottom: 16px; }
.placeholder h3 { margin: 8px 0; font-size: 18px; }
.placeholder p { margin: 8px 0 16px; font-size: 14px; }

.preview-content { padding-bottom: 20px; }
.preview-header { margin-bottom: 16px; }

.history-card-wrapper { margin-bottom: 24px; }
.history-card { width: 100%; }

.card-title { font-size: 17px; font-weight: 600; color: #2080f0; margin: 0 0 12px 0; }
.card-explanation { font-size: 15px; line-height: 1.8; color: #333; white-space: pre-wrap; }
.quiz-divider { height: 1px; background: #eee; margin: 16px 0; }
.card-question { font-size: 16px; font-weight: 600; margin: 0 0 16px 0; }

.options-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.option-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px; border: 2px solid #e5e7eb; border-radius: 10px; }
.option-item.option-correct { border-color: #18a058; background: #e8f8ee; }
.option-item.option-wrong { border-color: #d03050; background: #fde8ec; }
.option-item.option-dimmed { opacity: 0.45; }
.option-label { font-weight: 700; font-size: 15px; color: #666; min-width: 24px; }
.option-text { font-size: 15px; line-height: 1.5; color: #333; }

.card-feedback { margin-top: 12px; padding: 12px 16px; background: #f8f9fa; border-radius: 8px; }
.card-feedback p { margin: 0; font-size: 14px; color: #555; line-height: 1.6; }
</style>
