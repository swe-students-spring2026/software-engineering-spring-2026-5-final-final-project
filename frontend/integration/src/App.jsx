const SERVICES = [
  {
    name: "auth-service",
    port: "8002",
    owns: "Email verification, JWT, cat/kitten role claims",
  },
  {
    name: "teacher-service",
    port: "8003",
    owns: "Cat pond management, problem creation, room code invitations",
  },
  {
    name: "game-service",
    port: "8000",
    owns: "Kitten gameplay, tokens, marketplace, fishing, aquarium",
  },
  {
    name: "grader-service",
    port: "8001",
    owns: "Judge0-style code checking and verdicts",
  },
];

const RULES = [
  "Aquarium replaces medal wall.",
  "Cats do not participate in the token system.",
  "Token and aquarium leaderboards include kittens only.",
  "Public pond ranking is support votes minus not-support votes.",
  "CatCh Fish Pond is the pinned default public pond.",
];

export default function App() {
  return (
    <main className="integration-shell">
      <header>
        <p className="eyebrow">Integration contracts</p>
        <h1>CatCh Service Map</h1>
      </header>

      <section className="service-grid">
        {SERVICES.map((service) => (
          <article className="service-card" key={service.name}>
            <div className="card-heading">
              <h2>{service.name}</h2>
              <span>:{service.port}</span>
            </div>
            <p>{service.owns}</p>
          </article>
        ))}
      </section>

      <section className="rules">
        <h2>Shared Rules</h2>
        <ul>
          {RULES.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </section>

      <section className="aquarium">
        <h2>Aquarium Contract</h2>
        <p>
          Collection progress is based on unique fish species collected divided by the
          current fish dataset size. Quantity is tracked separately for repeated catches.
        </p>
      </section>
    </main>
  );
}
