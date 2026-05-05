import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const GAME_URL = import.meta.env.VITE_GAME_SERVICE_URL || "http://localhost:8000";

function imageUrl(path) {
  return path?.startsWith("http") ? path : `${GAME_URL}${path}`;
}

function App() {
  const [userId, setUserId] = React.useState("demo_user");
  const [aquarium, setAquarium] = React.useState(null);

  React.useEffect(() => {
    fetch(`${GAME_URL}/aquarium/${userId}`)
      .then((response) => response.json())
      .then(setAquarium)
      .catch(() => setAquarium(null));
  }, [userId]);

  return (
    <main>
      <header>
        <h1>Aquarium</h1>
        <input value={userId} onChange={(event) => setUserId(event.target.value)} />
      </header>
      <section className="panel">
        <div className="summary">
          <strong>{aquarium?.collection_percentage ?? 0}%</strong>
          <span>
            {aquarium?.collected_species ?? 0}/{aquarium?.total_species ?? 0} species
          </span>
        </div>
        <div className="tank">
          {(aquarium?.fish ?? []).map((fish, index) => (
            <button
              className="fish"
              key={fish.species_id}
              style={{ top: `${20 + (index % 5) * 12}%` }}
              title={`${fish.species_name} x${fish.quantity}`}
            >
              <img src={imageUrl(fish.image_url)} alt={fish.species_name} />
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
