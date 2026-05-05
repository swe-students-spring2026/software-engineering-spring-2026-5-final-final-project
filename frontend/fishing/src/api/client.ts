import type {
  CastResponse,
  FishSpecies,
  InventoryResponse,
  SellSmallResponse,
} from '../types';

export const BASE_URL =
  (import.meta.env.VITE_GAME_SERVICE_URL as string | undefined) ||
  'http://localhost:8000';

export async function listSpecies(): Promise<FishSpecies[]> {
  const r = await fetch(`${BASE_URL}/fishing/species`);
  if (!r.ok) throw new Error(`failed to list species: ${r.status}`);
  return r.json();
}

export async function castFish(userId: string): Promise<CastResponse> {
  const r = await fetch(
    `${BASE_URL}/fishing/cast?user_id=${encodeURIComponent(userId)}`,
    { method: 'POST' },
  );
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`cast failed (${r.status}): ${text}`);
  }
  return r.json();
}

export async function getInventory(userId: string): Promise<InventoryResponse> {
  const r = await fetch(
    `${BASE_URL}/fishing/inventory/${encodeURIComponent(userId)}`,
  );
  if (!r.ok) throw new Error(`failed to get inventory: ${r.status}`);
  return r.json();
}

export async function sellSmall(
  fishId: string,
  userId: string,
): Promise<SellSmallResponse> {
  const r = await fetch(
    `${BASE_URL}/fishing/sell-small/${encodeURIComponent(fishId)}?user_id=${encodeURIComponent(userId)}`,
    { method: 'POST' },
  );
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`sell failed (${r.status}): ${text}`);
  }
  return r.json();
}
