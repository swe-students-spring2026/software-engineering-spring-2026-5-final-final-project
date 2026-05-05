// Mirrors game-service Pydantic models. Keep in sync if backend changes.

export type ProblemSummary = {
  id: string;
  title: string;
  difficulty: string;
  fishing_reward: number;
};

export type Problem = {
  id: string;
  title: string;
  function_name: string;
  instructions: string;
  starter_code: string;
  difficulty: string;
  fishing_reward: number;
  source: string;
  source_url: string;
};

export type SubmitResponse = {
  passed: boolean;
  tests_run: number;
  tests_passed: number;
  failed_test: string | null;
  error_message: string | null;
  fishing_reward_granted: number;
  new_fishing_chances: number | null;
};
