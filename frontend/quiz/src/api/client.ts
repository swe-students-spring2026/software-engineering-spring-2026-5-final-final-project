import type { ProblemSummary, Problem, SubmitResponse } from '../types';

const BASE_URL =
  (import.meta.env.VITE_GAME_SERVICE_URL as string | undefined) ||
  'http://localhost:8000';

export async function listProblems(): Promise<ProblemSummary[]> {
  const r = await fetch(`${BASE_URL}/quiz/problems`);
  if (!r.ok) throw new Error(`failed to list problems: ${r.status}`);
  return r.json();
}

export async function getProblem(id: string): Promise<Problem> {
  const r = await fetch(`${BASE_URL}/quiz/problems/${id}`);
  if (!r.ok) throw new Error(`failed to get problem ${id}: ${r.status}`);
  return r.json();
}

export async function submitCode(
  problemId: string,
  code: string,
  userId = 'celia',
): Promise<SubmitResponse> {
  const r = await fetch(`${BASE_URL}/quiz/problems/${problemId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, user_id: userId }),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`submit failed (${r.status}): ${text}`);
  }
  return r.json();
}
