import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const GAME_URL = import.meta.env.VITE_GAME_SERVICE_URL || "http://localhost:8000";

function App() {
  const [tokens, setTokens] = React.useState([]);
  const [aquarium, setAquarium] = React.useState([]);

  React.useEffect(() => {
    fetch(`${GAME_URL}/leaderboard/tokens`).then((r) => r.json()).then(setTokens);
    fetch(`${GAME_URL}/leaderboard/aquarium`).then((r) => r.json()).then(setAquarium);
  }, []);

  return (
    <main>
      <h1>Leaderboards</h1>
      <section className="grid">
        <article>
          <h2>Tokens</h2>
          {tokens.map((row, index) => (
            <div className="row" key={row.user_id}>
              <span>{index + 1}. {row.user_id}</span>
              <strong>{row.tokens}</strong>
            </div>
          ))}
        </article>
        <article>
          <h2>Aquarium</h2>
          {aquarium.map((row, index) => (
            <div className="row" key={row.user_id}>
              <span>{index + 1}. {row.user_id}</span>
              <strong>{row.collection_percentage}%</strong>
            </div>
          ))}
        </article>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
