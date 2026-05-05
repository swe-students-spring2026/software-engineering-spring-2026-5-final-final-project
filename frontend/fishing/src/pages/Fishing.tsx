import { useEffect, useState } from 'react';
import type { InventoryFish, InventoryResponse } from '../types';
import {
  BASE_URL,
  castFish,
  getInventory,
  sellSmall,
} from '../api/client';

const USER_ID = 'demo_user';

function imageSrc(url: string): string {
  if (url.startsWith('http')) return url;
  if (url.startsWith('/fish_images/')) return `${BASE_URL}${url}`;
  return url;
}

function rarityBadgeClass(rarity: string): string {
  return `badge badge-${rarity}`;
}

export default function Fishing() {
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [casting, setCasting] = useState(false);
  const [lastCast, setLastCast] = useState<InventoryFish | null>(null);
  const [castAnimKey, setCastAnimKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const refreshInventory = async () => {
    try {
      const inv = await getInventory(USER_ID);
      setInventory(inv);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    refreshInventory();
  }, []);

  const handleCast = async () => {
    if (casting) return;
    setError(null);
    setCasting(true);
    try {
      const result = await castFish(USER_ID);
      setLastCast(result.fish);
      setCastAnimKey((k) => k + 1);
      await refreshInventory();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCasting(false);
    }
  };

  const handleSell = async (fishId: string) => {
    setError(null);
    try {
      await sellSmall(fishId, USER_ID);
      await refreshInventory();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const chances = inventory?.fishing_chances ?? 0;
  const tokens = inventory?.tokens ?? 0;
  const fish = inventory?.fish ?? [];

  return (
    <div className="app">
      <header className="header">
        <h1>Fish_Likes_Cat — Fishing</h1>
        <div className="stats">
          <span>🎣 chances: <b>{chances}</b></span>
          <span>🪙 tokens: <b>{tokens}</b></span>
          <span>🐟 caught: <b>{inventory?.total_count ?? 0}</b></span>
        </div>
      </header>

      <section className="cast-section">
        <button
          className="cast-btn"
          onClick={handleCast}
          disabled={casting || chances <= 0}
          title={chances <= 0 ? 'No chances. Solve quiz problems to earn more.' : ''}
        >
          {casting ? 'Casting...' : chances > 0 ? 'Cast Line 🎣' : 'No chances'}
        </button>

        {lastCast && (
          <div key={castAnimKey} className="last-cast pop-in">
            <img
              className={`fish-img quality-${lastCast.quality}`}
              src={imageSrc(lastCast.image_url)}
              alt={lastCast.species_name}
            />
            <div className="last-cast-info">
              <div className="last-cast-name">
                You caught a <b>{lastCast.species_name}</b>!
              </div>
              <div>
                <span className={rarityBadgeClass(lastCast.rarity)}>
                  {lastCast.rarity}
                </span>{' '}
                <span className={`badge badge-quality-${lastCast.quality}`}>
                  {lastCast.quality}
                </span>
              </div>
              <div className="dim">
                {lastCast.size_cm} cm · {lastCast.weight_g} g · suggested{' '}
                🪙 {lastCast.suggested_price}
              </div>
              <div className="dim">{lastCast.description}</div>
            </div>
          </div>
        )}
      </section>

      {error && <div className="error">{error}</div>}

      <section className="inventory">
        <h2>Inventory ({fish.length})</h2>
        {fish.length === 0 ? (
          <div className="empty">
            Empty net. Cast your line above to catch your first fish.
          </div>
        ) : (
          <div className="fish-grid">
            {fish.map((f) => (
              <div className="fish-card" key={f.fish_id}>
                <img
                  className={`fish-img quality-${f.quality}`}
                  src={imageSrc(f.image_url)}
                  alt={f.species_name}
                />
                <div className="fish-name">{f.species_name}</div>
                <div className="fish-row">
                  <span className={rarityBadgeClass(f.rarity)}>{f.rarity}</span>
                  <span className={`badge badge-quality-${f.quality}`}>
                    {f.quality}
                  </span>
                </div>
                <div className="dim">
                  {f.size_cm} cm · {f.weight_g} g
                </div>
                <div className="fish-description">{f.description}</div>
                <div className="fish-row">
                  <span>🪙 {f.suggested_price}</span>
                  {f.is_small && !f.marketplace_eligible ? (
                    <button
                      className="sell-btn"
                      onClick={() => handleSell(f.fish_id)}
                    >
                      Sell small
                    </button>
                  ) : f.marketplace_eligible ? (
                    <span className="dim small">→ marketplace</span>
                  ) : (
                    <span className="dim small">keep or sell</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
