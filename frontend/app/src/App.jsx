import React, { useEffect, useMemo, useState } from "react";

const GAME_URL = import.meta.env.VITE_GAME_SERVICE_URL || "http://localhost:8000";
const AUTH_URL = import.meta.env.VITE_AUTH_SERVICE_URL || "http://localhost:8002";
const TEACHER_URL =
  import.meta.env.VITE_TEACHER_SERVICE_URL || "http://localhost:8003";
const INTEGRATION_URL =
  import.meta.env.VITE_INTEGRATION_SERVICE_URL || "http://localhost:8004";

const kittenTabs = [
  ["quiz", "Quiz"],
  ["fishing", "Fish"],
  ["aquarium", "Aquarium"],
  ["market", "Market"],
  ["leaderboard", "Leaderboard"],
];

const catTabs = [["teacher", "Teacher"]];
const SESSION_VERSION = "2";

function emptyInventory(userId) {
  return {
    user_id: userId,
    fish: [],
    total_count: 0,
    tokens: 0,
    fishing_chances: 0,
  };
}

function loadStoredSession() {
  const version = localStorage.getItem("catch_session_version");
  const token = localStorage.getItem("catch_token");
  const userId = localStorage.getItem("catch_user_id");
  const role = localStorage.getItem("catch_role");
  const username = localStorage.getItem("catch_username");
  if (version !== SESSION_VERSION) return null;
  if (!token || !userId || !role) return null;
  return { token, user_id: userId, role, username: username || userId };
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function imageUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${GAME_URL}${path}`;
}

function Status({ error, message }) {
  if (!error && !message) return null;
  return <p className={error ? "status error" : "status"}>{error || message}</p>;
}

function AuthPanel({ session, setSession }) {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("kitten");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);

  async function sendCode() {
    setError("");
    setMessage("");
    setSending(true);
    try {
      const data = await request(`${AUTH_URL}/auth/send-verification-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, username, role }),
      });
      setMessage(
        data.email_sent
          ? "Code sent. Check your email."
          : "Email was not sent. Check SMTP settings in .env.",
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function verifyCode() {
    setError("");
    setMessage("");
    setVerifying(true);
    try {
      const data = await request(`${AUTH_URL}/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code, username, role }),
      });
      localStorage.setItem("catch_user_id", data.user_id);
      localStorage.setItem("catch_role", data.role);
      localStorage.setItem("catch_token", data.token);
      localStorage.setItem("catch_username", data.username);
      localStorage.setItem("catch_session_version", SESSION_VERSION);
      setSession(data);
      setMessage("Signed in.");
    } catch (err) {
      setError(err.message);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <section className="panel auth-panel">
      <div className="panel-head">
        <h2>Sign In</h2>
        <span>{session ? session.role : "choose your role"}</span>
      </div>
      <div className="role-choice">
        <button
          className={role === "kitten" ? "role-card active" : "role-card"}
          onClick={() => setRole("kitten")}
          type="button"
        >
          <strong>Kitten</strong>
          <span>Solve problems, fish, collect, trade, and rank.</span>
        </button>
        <button
          className={role === "cat" ? "role-card active" : "role-card"}
          onClick={() => setRole("cat")}
          type="button"
        >
          <strong>Cat</strong>
          <span>Create fish ponds and coding problems for kittens.</span>
        </button>
      </div>
      <div className="form-grid two-cols">
        <label>
          Username
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Email
          <input
            value={email}
            type="email"
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Verification code
          <input
            value={code}
            maxLength={6}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>
      </div>
      <div className="button-row">
        <button disabled={!email || !username || sending} onClick={sendCode}>
          {sending ? "Sending..." : "Send Code"}
        </button>
        <button disabled={!email || !username || !code || verifying} onClick={verifyCode}>
          {verifying ? "Verifying..." : "Enter CatCh"}
        </button>
      </div>
      <Status error={error} message={message} />
    </section>
  );
}

function LoginScreen({ session, setSession }) {
  return (
    <main className="login-screen">
      <section className="login-copy">
        <strong>CatCh</strong>
        <h1>Code, fish, and learn.</h1>
        <p>
          Kittens play the coding game economy. Cats create ponds and problems
          without joining the token system.
        </p>
      </section>
      <AuthPanel session={session} setSession={setSession} />
    </main>
  );
}

function QuizPanel({ userId, refreshInventory }) {
  const [channels, setChannels] = useState({ public: [], private: [] });
  const [problem, setProblem] = useState(null);
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const allProblems = [
    ...channels.public.flatMap((channel) => channel.problems || []),
    ...channels.private.flatMap((channel) => channel.problems || []),
  ];

  async function refreshChannels() {
    const data = await request(`${GAME_URL}/quiz/channels/${userId}`);
    setChannels(data);
    return [
      ...data.public.flatMap((channel) => channel.problems || []),
      ...data.private.flatMap((channel) => channel.problems || []),
    ];
  }

  useEffect(() => {
    refreshChannels().catch((err) => setError(err.message));
  }, [userId]);

  async function selectProblem(problemId) {
    setResult(null);
    setError("");
    try {
      const data = await request(`${GAME_URL}/quiz/problems/${problemId}`);
      setProblem(data);
      setCode(data.starter_code);
    } catch (err) {
      setError(err.message);
    }
  }

  async function submitCode() {
    if (!problem) return;
    setError("");
    setSubmitting(true);
    try {
      const data = await request(`${GAME_URL}/quiz/problems/${problem.id}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, code, language: "python" }),
      });
      setResult(data);
      await refreshInventory();
      const refreshedProblems = await refreshChannels();
      if (data.passed) {
        const nextProblem = refreshedProblems.find(
          (item) => !item.completed && item.id !== problem.id,
        );
        if (nextProblem) {
          await selectProblem(nextProblem.id);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="workbench">
      <aside className="list-pane">
        <strong className="channel-title">Public</strong>
        {channels.public.map((channel) => (
          <div key={channel.pond_id}>
            <div className="pond-label">{channel.name}</div>
            {(channel.problems || []).map((item) => (
              <button
                className={
                  problem?.id === item.id ? "list-item active" : "list-item"
                }
                key={item.id}
                onClick={() => selectProblem(item.id)}
              >
                <strong>
                  {item.completed ? "✓ " : ""}
                  {item.title}
                </strong>
                <span>
                  {item.difficulty} · reward {item.fishing_reward} · attempts{" "}
                  {item.attempts_used}
                </span>
              </button>
            ))}
          </div>
        ))}
        <strong className="channel-title">Private</strong>
        {channels.private.length === 0 ? (
          <span className="muted">No private ponds assigned yet.</span>
        ) : null}
        {channels.private.map((channel) => (
          <div key={channel.pond_id}>
            <div className="pond-label">{channel.name}</div>
            {(channel.problems || []).map((item) => (
              <button
                className={
                  problem?.id === item.id ? "list-item active" : "list-item"
                }
                key={item.id}
                onClick={() => selectProblem(item.id)}
              >
                <strong>
                  {item.completed ? "✓ " : ""}
                  {item.title}
                </strong>
                <span>{item.difficulty}</span>
              </button>
            ))}
          </div>
        ))}
      </aside>
      <section className="panel">
        {problem ? (
          <>
            <div className="panel-head">
              <h2>{problem.title}</h2>
              <span>
                {result
                  ? `${result.attempts_remaining} attempts left`
                  : `${problem.max_attempts} attempts`}
              </span>
            </div>
            <pre className="instructions">{problem.instructions}</pre>
            <textarea
              className="code-box"
              spellCheck="false"
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
            <button disabled={submitting} onClick={submitCode}>
              {submitting ? "Checking..." : "Submit"}
            </button>
            {result ? (
              <div className={result.passed ? "result pass" : "result"}>
                <strong>{result.passed ? "Passed" : "Not passed"}</strong>
                <span>
                  {result.tests_passed}/{result.tests_run} tests · fishing reward{" "}
                  {result.fishing_reward_granted}
                </span>
                {result.tokens_lost ? (
                  <span>Lost {result.tokens_lost} Cat Can Token.</span>
                ) : null}
                {result.solution_revealed ? (
                  <pre className="solution">{result.solution_code}</pre>
                ) : null}
              </div>
            ) : null}
          </>
        ) : (
          <div className="empty">
            {allProblems.length ? "Select a problem to start." : "No quizzes yet."}
          </div>
        )}
        <Status error={error} />
      </section>
    </section>
  );
}

function FishingPanel({ userId, inventory, refreshInventory }) {
  const [lastFish, setLastFish] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [casting, setCasting] = useState(false);

  async function cast() {
    setError("");
    setMessage("");
    setCasting(true);
    try {
      const data = await request(`${GAME_URL}/fishing/cast?user_id=${userId}`, {
        method: "POST",
      });
      setLastFish(data.fish);
      setMessage(`Cast complete. ${data.remaining_chances} chances left.`);
      await refreshInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setCasting(false);
    }
  }

  async function sellSmall(fishId) {
    setError("");
    setMessage("");
    try {
      const data = await request(
        `${GAME_URL}/fishing/sell-small/${fishId}?user_id=${userId}`,
        { method: "POST" },
      );
      setMessage(`Sold small fish for ${data.tokens_earned} tokens.`);
      await refreshInventory();
    } catch (err) {
      setError(err.message);
    }
  }

  const canCast = inventory.fishing_chances > 0 && !casting;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Fish</h2>
        <span>{inventory.fishing_chances} chances</span>
      </div>
      <div className="cast-strip">
        <button onClick={cast} disabled={!canCast}>
          {casting ? "Casting..." : "Cast"}
        </button>
        <span>
          {inventory.fishing_chances > 0
            ? "Each cast consumes 1 fishing chance and uses the fish dataset."
            : "Solve a quiz problem correctly to earn a fishing chance."}
        </span>
      </div>
      {lastFish ? (
        <div className="fish-highlight">
          <img src={imageUrl(lastFish.image_url)} alt={lastFish.species_name} />
          <div>
            <strong>{lastFish.species_name}</strong>
            <span>
              {lastFish.rarity} · {lastFish.quality} · {lastFish.size_cm} cm
            </span>
            <p>{lastFish.description}</p>
          </div>
        </div>
      ) : null}
      <Status error={error} message={message} />
      <div className="card-grid">
        {inventory.fish.map((fish) => (
          <article className="fish-card" key={fish.fish_id}>
            <img src={imageUrl(fish.image_url)} alt={fish.species_name} />
            <strong>{fish.species_name}</strong>
            <span>
              {fish.rarity} · {fish.quality} · {fish.size_cm} cm
            </span>
            {fish.is_small && !fish.marketplace_eligible ? (
              <button onClick={() => sellSmall(fish.fish_id)}>Sell Small</button>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function AquariumPanel({ userId }) {
  const [aquarium, setAquarium] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    request(`${GAME_URL}/aquarium/${userId}`)
      .then(setAquarium)
      .catch((err) => setError(err.message));
  }, [userId]);

  if (!aquarium) {
    return (
      <section className="panel">
        <div className="panel-head">
          <h2>Aquarium Collection</h2>
          <span>Loading collection...</span>
        </div>
        <Status error={error} />
      </section>
    );
  }

  const collected = aquarium.collected_species || 0;
  const total = aquarium.total_species || 50;
  const percentage = aquarium.collection_percentage || 0;

  return (
    <section className="panel aquarium-panel">
      <div className="panel-head">
        <div>
          <h2>Aquarium Collection</h2>
          <p className="subtle-text">
            Your medal wall: collect unique fish species to grow your aquarium.
          </p>
        </div>
        <span>{percentage}% collected</span>
      </div>

      <div className="collection-summary">
        <div>
          <strong>{collected}</strong>
          <span>Species collected</span>
        </div>
        <div>
          <strong>{total - collected}</strong>
          <span>Species left</span>
        </div>
        <div>
          <strong>{aquarium.fish.length}</strong>
          <span>Unique fish shown</span>
        </div>
      </div>

      <div className="progress-track labeled">
        <div style={{ width: `${percentage}%` }} />
      </div>

      {aquarium.fish.length === 0 ? (
        <div className="aquarium-empty">
          <strong>No fish collected yet.</strong>
          <span>Solve quiz problems to earn fishing chances, then start collecting.</span>
        </div>
      ) : (
        <div className="aquarium-stage">
          {aquarium.fish.map((fish, index) => (
            <button
              className="swimmer"
              key={fish.species_id}
              style={{
                top: `${14 + (index % 6) * 12}%`,
                animationDelay: `${index * -1.25}s`,
              }}
              title={`${fish.species_name}, quantity ${fish.quantity}`}
              type="button"
            >
              <img src={imageUrl(fish.image_url)} alt={fish.species_name} />
              <span>x{fish.quantity}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function MarketPanel({ inventory, userId, refreshInventory }) {
  const [listings, setListings] = useState([]);
  const [priceByFish, setPriceByFish] = useState({});
  const [error, setError] = useState("");

  async function refreshListings() {
    try {
      setListings(await request(`${GAME_URL}/market/listings`));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refreshListings();
  }, []);

  async function listFish(fishId) {
    setError("");
    try {
      await request(`${GAME_URL}/market/list`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          fish_id: fishId,
          price: Number(priceByFish[fishId] || 1),
        }),
      });
      refreshListings();
    } catch (err) {
      setError(err.message);
    }
  }

  async function buy(listingId) {
    setError("");
    try {
      await request(`${GAME_URL}/market/buy/${listingId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ buyer_id: userId }),
      });
      refreshListings();
      refreshInventory();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="workbench two">
      <section className="panel">
        <h2>Your Market Fish</h2>
        {inventory.fish.filter((fish) => fish.marketplace_eligible).map((fish) => (
          <div className="market-row" key={fish.fish_id}>
            <span>{fish.species_name}</span>
            <input
              type="number"
              min="1"
              value={priceByFish[fish.fish_id] || fish.suggested_price}
              onChange={(event) =>
                setPriceByFish({ ...priceByFish, [fish.fish_id]: event.target.value })
              }
            />
            <button onClick={() => listFish(fish.fish_id)}>List</button>
          </div>
        ))}
      </section>
      <section className="panel">
        <h2>Listings</h2>
        {listings.map((listing) => (
          <div className="market-row" key={listing.listing_id}>
            <span>{listing.fish.species_name}</span>
            <strong>{listing.price} tokens</strong>
            <button onClick={() => buy(listing.listing_id)}>Buy</button>
          </div>
        ))}
        <Status error={error} />
      </section>
    </section>
  );
}

function LeaderboardPanel() {
  const [tokens, setTokens] = useState([]);
  const [aquarium, setAquarium] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");

    Promise.all([
      request(`${GAME_URL}/leaderboard/tokens`),
      request(`${GAME_URL}/leaderboard/aquarium`),
    ])
      .then(([tokenRows, aquariumRows]) => {
        setTokens(tokenRows);
        setAquarium(aquariumRows);
      })
      .catch((err) => setError(err.message));
  }, []);

  function rankBadge(index) {
    if (index === 0) return "🥇";
    if (index === 1) return "🥈";
    if (index === 2) return "🥉";
    return `#${index + 1}`;
  }

  return (
    <section className="workbench two leaderboard-page">
      <section className="panel leaderboard-card">
        <div className="panel-head">
          <div>
            <h2>Token Leaderboard</h2>
            <p className="subtle-text">Ranks kittens by total earned tokens.</p>
          </div>
        </div>

        {tokens.length === 0 ? (
          <p className="empty">No token rankings yet.</p>
        ) : (
          <div className="rank-list">
            {tokens.map((row, index) => (
              <div className="rank-row enhanced" key={row.user_id}>
                <span className="rank-medal">{rankBadge(index)}</span>
                <span className="rank-name">{row.username || row.user_id}</span>
                <strong className="rank-value">{row.tokens} tokens</strong>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel leaderboard-card">
        <div className="panel-head">
          <div>
            <h2>Aquarium Leaderboard</h2>
            <p className="subtle-text">Ranks kittens by fish species collection progress.</p>
          </div>
        </div>

        {aquarium.length === 0 ? (
          <p className="empty">No aquarium rankings yet.</p>
        ) : (
          <div className="rank-list">
            {aquarium.map((row, index) => (
              <div className="rank-row enhanced" key={row.user_id}>
                <span className="rank-medal">{rankBadge(index)}</span>
                <span className="rank-name">
                  {row.username || row.user_id}
                  <small>
                    {row.collected_species || 0}/{row.total_species || 50} species
                  </small>
                </span>
                <strong className="rank-value">{row.collection_percentage}%</strong>
              </div>
            ))}
          </div>
        )}

        <Status error={error} />
      </section>
    </section>
  );
}

function TeacherPanel({ userId }) {
  const [name, setName] = useState("CS Pond");
  const [visibility, setVisibility] = useState("private");
  const [pond, setPond] = useState(null);
  const [rules, setRules] = useState(null);
  const [problem, setProblem] = useState({
    title: "Return the larger number",
    prompt: "Write a function solve(a, b) that returns the larger number.",
    starter_code: "def solve(a, b):\n    pass\n",
    reference_solution: "def solve(a, b):\n    return max(a, b)\n",
    test_code:
      "assert solve(1, 2) == 2\nassert solve(7, 3) == 7\nassert solve(-1, -5) == -1\n",
    topic: "conditionals",
  });
  const [problemResult, setProblemResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    request(`${TEACHER_URL}/teacher/rules`).then(setRules).catch(() => {});
  }, []);

  async function createPond() {
    setError("");
    setProblemResult(null);
    try {
      const data = await request(`${TEACHER_URL}/teacher/ponds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cat_id: userId,
          name,
          visibility,
          description: "Teacher-created fish pond",
        }),
      });
      setPond(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function createProblem() {
    if (!pond?.pond_id) {
      setError("Create a fish pond before adding a problem.");
      return;
    }
    setError("");
    try {
      const payload = {
        cat_id: userId,
        pond_id: pond.pond_id,
        ...problem,
      };
      const data = await request(`${TEACHER_URL}/teacher/ponds/${pond.pond_id}/problems`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setProblemResult(data);
    } catch (err) {
      setError(err.message);
    }
  }

  function updateProblem(field, value) {
    setProblem((current) => ({ ...current, [field]: value }));
  }

  return (
    <section className="workbench two">
      <section className="panel">
        <div className="panel-head">
          <h2>Create Fish Pond</h2>
          <span>{rules?.token_system_enabled === false ? "no token system" : ""}</span>
        </div>
        <div className="form-grid two-cols">
          <label>
            Pond name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Visibility
            <select
              value={visibility}
              onChange={(event) => setVisibility(event.target.value)}
            >
              <option value="public">Public</option>
              <option value="private">Private</option>
            </select>
          </label>
        </div>
        <button onClick={createPond}>Create Room</button>
        {pond ? (
          <div className="result pass">
            <strong>{pond.name}</strong>
            <span>
              {pond.visibility} · room code {pond.room_code || "none"}
            </span>
          </div>
        ) : null}
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Create Problem</h2>
          <span>{pond?.pond_id || "create room first"}</span>
        </div>
        <div className="form-grid two-cols">
          <label>
            Title
            <input
              value={problem.title}
              onChange={(event) => updateProblem("title", event.target.value)}
            />
          </label>
          <label>
            Topic
            <input
              value={problem.topic}
              onChange={(event) => updateProblem("topic", event.target.value)}
            />
          </label>
        </div>
        <label>
          Prompt
          <textarea
            value={problem.prompt}
            onChange={(event) => updateProblem("prompt", event.target.value)}
          />
        </label>
        <label>
          Starter code
          <textarea
            className="code-box small"
            value={problem.starter_code}
            onChange={(event) => updateProblem("starter_code", event.target.value)}
          />
        </label>
        <label>
          Reference solution
          <textarea
            className="code-box small"
            value={problem.reference_solution}
            onChange={(event) =>
              updateProblem("reference_solution", event.target.value)
            }
          />
        </label>
        <label>
          Test code
          <textarea
            className="code-box small"
            value={problem.test_code}
            onChange={(event) => updateProblem("test_code", event.target.value)}
          />
        </label>
        <button onClick={createProblem}>Create Problem</button>
        {problemResult ? (
          <div className="result pass">
            <strong>{problem.title}</strong>
            <span>{problemResult.status || "created"}</span>
          </div>
        ) : null}
        <Status error={error} />
      </section>
    </section>
  );
}

export default function App() {
  const [session, setSession] = useState(loadStoredSession);
  const [activeTab, setActiveTab] = useState("quiz");
  const [inventory, setInventory] = useState(emptyInventory("demo_user"));
  const [rules, setRules] = useState(null);

  const role = session?.role;
  const userId = session?.user_id || "";
  const tabs = role === "cat" ? catTabs : kittenTabs;
  const activeLabel = tabs.find(([id]) => id === activeTab)?.[1] || tabs[0][1];

  function logout() {
    localStorage.removeItem("catch_user_id");
    localStorage.removeItem("catch_role");
    localStorage.removeItem("catch_token");
    localStorage.removeItem("catch_username");
    localStorage.removeItem("catch_session_version");
    setSession(null);
    setActiveTab("quiz");
    setInventory(emptyInventory("demo_user"));
  }

  async function refreshInventory() {
    if (!userId || role !== "kitten") return;
    const data = await request(`${GAME_URL}/fishing/inventory/${userId}`);
    setInventory(data);
  }

  useEffect(() => {
    if (!session) return;
    setActiveTab(session.role === "cat" ? "teacher" : "quiz");
  }, [session?.role]);

  useEffect(() => {
    if (!session) return;
    if (role === "kitten") {
      refreshInventory().catch(() => {});
    } else {
      setInventory(emptyInventory(userId));
    }
    request(`${INTEGRATION_URL}/integration/product-rules`)
      .then(setRules)
      .catch(() => {});
  }, [userId, role]);

  const tabContent = useMemo(() => {
    if (role === "cat") {
      return <TeacherPanel userId={userId} />;
    }
    if (activeTab === "quiz") {
      return <QuizPanel userId={userId} refreshInventory={refreshInventory} />;
    }
    if (activeTab === "fishing") {
      return (
        <FishingPanel
          userId={userId}
          inventory={inventory}
          refreshInventory={refreshInventory}
        />
      );
    }
    if (activeTab === "aquarium") return <AquariumPanel userId={userId} />;
    if (activeTab === "market") {
      return (
        <MarketPanel
          inventory={inventory}
          userId={userId}
          refreshInventory={refreshInventory}
        />
      );
    }
    return <LeaderboardPanel />;
  }, [activeTab, inventory, role, userId]);

  if (!session) {
    return <LoginScreen session={session} setSession={setSession} />;
  }

  return (
    <main className="app-shell">
      <aside className="nav">
        <div className="brand">
          <strong>CatCh</strong>
          <span>{role === "cat" ? "Cat teacher" : "Kitten programmer"}</span>
          <span>{session.username || userId}</span>
        </div>
        {tabs.map(([id, label]) => (
          <button
            className={activeTab === id ? "nav-button active" : "nav-button"}
            key={id}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
        <button className="nav-button logout" onClick={logout}>
          Log out
        </button>
      </aside>
      <section className="content">
        <header className="topbar">
          <div>
            <h1>{activeLabel}</h1>
            <p>{rules?.name || "CatCh: Code, Fish, and Learn"}</p>
          </div>
          {role === "kitten" ? (
            <div className="quick-stats">
              <span>Chances {inventory.fishing_chances}</span>
              <span>Tokens {inventory.tokens}</span>
              <span>Fish {inventory.total_count}</span>
            </div>
          ) : (
            <div className="quick-stats">
              <span>Teacher mode</span>
              <span>No tokens</span>
            </div>
          )}
        </header>
        {tabContent}
      </section>
    </main>
  );
}
