// Mirrors game-service Pydantic models.

export type Rarity = 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
export type Quality = 'normal' | 'shiny' | 'perfect';

export type FishSpecies = {
  id: string;
  species_id: string;
  name: string;
  species: string;
  rarity: Rarity;
  catch_probability: number;
  image_url: string;
  image_path: string;
  animation_url: string | null;
  description: string;
  sell_value: number;
  sell_value_tokens: number;
  marketplace_eligible: boolean;
  base_price: number;
  typical_size_cm: number;
  image_pool: string[];
};

export type InventoryFish = {
  fish_id: string;
  species_id: string;
  species_name: string;
  species: string;
  rarity: Rarity;
  quality: Quality;
  size_cm: number;
  weight_g: number;
  image_url: string;
  image_path: string;
  description: string;
  caught_at: string;
  suggested_price: number;
  sell_value: number;
  sell_value_tokens: number;
  marketplace_eligible: boolean;
  is_small: boolean;
};

export type CastResponse = {
  fish: InventoryFish;
  remaining_chances: number;
};

export type InventoryResponse = {
  user_id: string;
  fish: InventoryFish[];
  total_count: number;
  tokens: number;
  fishing_chances: number;
};

export type SellSmallResponse = {
  fish_id: string;
  species_id: string;
  tokens_earned: number;
  new_token_balance: number;
};
