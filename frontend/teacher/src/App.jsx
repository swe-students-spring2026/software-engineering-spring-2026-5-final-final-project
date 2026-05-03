import { useMemo, useState } from "react";

const TEACHER_ACTIONS = [
  "Create public fish pond",
  "Create private fish pond",
  "Add coding problems",
  "Send room code invitations",
  "Create assignments",
];

const CAT_RULES = [
  "No Cat Can Token balance",
  "No marketplace participation",
  "No fishing chance loop",
  "No token leaderboard",
  "No aquarium leaderboard",
];

export default function App() {
  const [visibility, setVisibility] = useState("private");
  const [pondName, setPondName] = useState("Intro Python Pond");
  const roomCode = useMemo(() => (visibility === "private" ? "CATCH7" : "Public"), [visibility]);

  return (
    <main className="teacher-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Cat workspace</p>
          <h1>Teacher Fish Ponds</h1>
        </div>
        <span className="role-pill">Cat role · tokens off</span>
      </section>

      <section className="layout">
        <form className="panel">
          <h2>Create Pond</h2>
          <label>
            Pond name
            <input value={pondName} onChange={(event) => setPondName(event.target.value)} />
          </label>
          <label>
            Visibility
            <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
              <option value="private">Private fish pond</option>
              <option value="public">Public fish pond</option>
            </select>
          </label>
          <div className="room-code">
            <span>Room code</span>
            <strong>{roomCode}</strong>
          </div>
          <button type="button">Save Template</button>
        </form>

        <section className="panel">
          <h2>Cat Actions</h2>
          <ul>
            {TEACHER_ACTIONS.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </section>

        <section className="panel quiet">
          <h2>Economy Boundary</h2>
          <ul>
            {CAT_RULES.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </section>
      </section>

      <section className="pond-preview">
        <h2>{pondName}</h2>
        <p>
          Cats can add up to 100 problems, send assignments, and invite kittens by room code.
          Public ponds can receive support or not-support feedback from kittens.
        </p>
      </section>
    </main>
  );
}
