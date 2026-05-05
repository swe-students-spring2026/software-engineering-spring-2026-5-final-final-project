import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import type { ProblemSummary, Problem } from '../types';
import { listProblems, getProblem, submitCode } from '../api/client';

export default function Quiz() {
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [code, setCode] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listProblems()
      .then(setProblems)
      .catch((err: Error) => alert(`Failed to load problems: ${err.message}`));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    getProblem(selectedId)
      .then((p) => {
        setProblem(p);
        setCode(p.starter_code);
      })
      .catch((err: Error) => alert(`Failed to load problem: ${err.message}`));
  }, [selectedId]);

  const handleSubmit = async () => {
    if (!problem) return;
    setSubmitting(true);
    try {
      const result = await submitCode(problem.id, code);
      if (result.passed) {
        alert(`✓ Passed!\n${result.tests_passed}/${result.tests_run} tests.`);
      } else {
        const detail =
          result.failed_test
            ? `Failed at: ${result.failed_test}`
            : result.error_message || 'Unknown error';
        alert(
          `✗ Failed.\n${result.tests_passed}/${result.tests_run} tests passed.\n${detail}`,
        );
      }
    } catch (err) {
      alert(`Error: ${(err as Error).message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Fish_Likes_Cat — Quiz</h1>
      </header>
      <div className="layout">
        <aside className="sidebar">
          <h2>Problems</h2>
          <ul className="problem-list">
            {problems.map((p) => (
              <li
                key={p.id}
                className={p.id === selectedId ? 'active' : ''}
                onClick={() => setSelectedId(p.id)}
              >
                <div className="problem-title">{p.title}</div>
                <div className="problem-meta">
                  <span className="difficulty">{p.difficulty}</span>
                  <span className="reward">🎣 ×{p.fishing_reward}</span>
                </div>
              </li>
            ))}
          </ul>
        </aside>

        <main className="main">
          {!problem ? (
            <div className="empty">Select a problem on the left to start.</div>
          ) : (
            <>
              <section className="problem-detail">
                <h2>{problem.title}</h2>
                <pre className="instructions">{problem.instructions}</pre>
                <div className="meta">
                  <span>
                    Function: <code>{problem.function_name}</code>
                  </span>
                  <span>Reward: 🎣 ×{problem.fishing_reward}</span>
                </div>
              </section>
              <section className="editor-section">
                <Editor
                  height="100%"
                  defaultLanguage="python"
                  value={code}
                  onChange={(v) => setCode(v ?? '')}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    automaticLayout: true,
                  }}
                />
                <button
                  className="submit-btn"
                  onClick={handleSubmit}
                  disabled={submitting}
                >
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
