/** LetsLearn learning quiz API — Python Agent (8000) proxies to Java for DB, quiz gen directly */
const AGENT = 'http://localhost:8000';

function getUserId(): string {
  const token = localStorage.getItem('LetsLearn_token') || '';
  try { return JSON.parse(atob(token.split('.')[1])).userId || ''; } catch { return ''; }
}
function hdrs(extra?: Record<string,string>): Record<string,string> {
  const uid = getUserId();
  return { 'Content-Type': 'application/json', ...(extra || {}), ...(uid ? { 'X-User-Id': uid } : {}) };
}

export interface QuizOption { label: string; text: string; isCorrect: boolean; feedback: string; }
export interface QuizCard { title: string; aiExplanation: string; question: string; options: QuizOption[]; }
export interface QuizGenerateResponse { fileMd5: string; key_points: string[]; cards: QuizCard[]; }
export interface QuizAnswer { cardIndex: number; selectedLabel: string; isCorrect: boolean; }

// ── Quiz generation (Python Agent directly) ──
export async function fetchGenerateQuiz(fileMd5: string): Promise<QuizGenerateResponse> {
  const resp = await fetch(`${AGENT}/api/quiz/generate`, { method: 'POST', headers: hdrs(), body: JSON.stringify({ fileMd5 }) });
  if (!resp.ok) throw new Error(`Quiz generation failed (${resp.status})`); return resp.json();
}

export type ProgressEvent = { type: string; done?: number; total?: number; cards?: QuizCard[]; message?: string };
export async function fetchGenerateQuizStream(fileMd5: string, onProgress: (e: ProgressEvent) => void): Promise<QuizCard[]> {
  const uid = getUserId();
  const resp = await fetch(`${AGENT}/api/quiz/generate/stream?fileMd5=${encodeURIComponent(fileMd5)}`, { headers: uid ? { 'X-User-Id': uid } : {} });
  if (!resp.ok) throw new Error(`Stream failed (${resp.status})`);
  const reader = resp.body!.getReader(); const decoder = new TextDecoder(); let buffer = '';
  return new Promise((resolve, reject) => {
    function pump() { reader.read().then(({ done, value }) => {
      if (done) { reject(new Error('Stream ended without complete')); return; }
      buffer += decoder.decode(value, { stream: true }); const lines = buffer.split('\n'); buffer = lines.pop() || '';
      for (const line of lines) { if (line.startsWith('data: ')) { try { const e = JSON.parse(line.slice(6));
        onProgress(e); if (e.type === 'complete') { resolve(e.cards || []); return; } if (e.type === 'error') { reject(new Error(e.message)); return; }
      } catch { /* skip */ } } } pump();
    }).catch(reject); }
    pump();
  });
}

// ── Quiz persistence (Python Agent proxies to Java with admin JWT + X-User-Id) ──
export async function completeQuiz(fileMd5: string, fileName: string, cards: QuizCard[], answers: QuizAnswer[]) {
  const resp = await fetch(`${AGENT}/api/quiz/complete`, { method: 'POST', headers: hdrs(), body: JSON.stringify({ fileMd5, fileName, cards, userAnswers: answers }) });
  if (!resp.ok) throw new Error(`Save failed (${resp.status})`); return resp.json();
}
export async function fetchLatestQuiz(fileMd5: string): Promise<any> {
  try {
    const resp = await fetch(`${AGENT}/api/quiz/latest?fileMd5=${encodeURIComponent(fileMd5)}`, { headers: hdrs() });
    if (!resp.ok) return { hasQuiz: false }; return resp.json();
  } catch { return { hasQuiz: false }; }
}
export async function checkQuizExists(fileMd5: string): Promise<boolean> {
  try {
    const resp = await fetch(`${AGENT}/api/quiz/check?fileMd5=${encodeURIComponent(fileMd5)}`, { headers: hdrs() });
    if (!resp.ok) return false; const data = await resp.json(); return data?.hasQuiz === true;
  } catch { return false; }
}
export interface QuizHistoryItem { quizId: number; correctCount: number; totalCount: number; accuracy: number; createdAt: string; }
export async function fetchQuizHistory(fileMd5: string): Promise<QuizHistoryItem[]> {
  const resp = await fetch(`${AGENT}/api/quiz/history?fileMd5=${encodeURIComponent(fileMd5)}`, { headers: hdrs() });
  if (!resp.ok) throw new Error(`History failed (${resp.status})`); return resp.json();
}
export async function fetchQuizDetail(quizId: number): Promise<any> {
  const resp = await fetch(`${AGENT}/api/quiz/detail?quizId=${quizId}`, { headers: hdrs() });
  if (!resp.ok) throw new Error(`Detail failed (${resp.status})`); return resp.json();
}
