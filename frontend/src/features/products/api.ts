import { apiRequest } from "@/lib/api-client";

export type Product = {
  provider: string;
  external_id: string;
  name: string;
  status: string;
  is_available: boolean;
  product_url: string | null;
  category: string | null;
  original_price: string | null;
  current_price: string | null;
  discount_percentage: string;
};

export type SyncProductsResponse = {
  fetched_count: number;
  persisted_count: number;
  snapshot_count: number;
};

export function listProducts(provider?: string) {
  const query = provider ? `?provider=${provider}` : "";
  return apiRequest<Product[]>(`/products${query}`);
}

export function syncSamsungProducts() {
  return apiRequest<SyncProductsResponse>("/sync/samsung", {
    method: "POST",
  });
}

