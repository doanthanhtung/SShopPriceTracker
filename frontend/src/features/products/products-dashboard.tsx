"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Search, ShoppingCart, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";

import { formatVnd } from "@/lib/utils";
import { listProducts, syncSamsungProducts, type Product } from "./api";

const statusLabels: Record<string, string> = {
  in_stock: "Còn hàng",
  out_of_stock: "Hết hàng",
  pre_order: "Đặt trước",
  unknown: "Không rõ",
};

export function ProductsDashboard() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");

  const productsQuery = useQuery({
    queryKey: ["products", "samsung"],
    queryFn: () => listProducts("samsung"),
  });

  const syncMutation = useMutation({
    mutationFn: syncSamsungProducts,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["products"] }),
  });

  const products = productsQuery.data ?? [];
  const filteredProducts = useMemo(
    () =>
      products.filter((product) => {
        const matchesSearch = product.name.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = status === "all" || product.status === status;
        return matchesSearch && matchesStatus;
      }),
    [products, search, status],
  );

  const availableCount = products.filter((product) => product.is_available).length;

  return (
    <main className="min-h-screen">
      <section className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">SShop Price Tracker</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Samsung product monitoring dashboard
              </p>
            </div>
            <button
              type="button"
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={syncMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              Sync Samsung
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="Products" value={products.length.toString()} />
            <Metric label="Available" value={availableCount.toString()} />
            <Metric label="Tracked Store" value="Samsung" />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-5">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
          <label className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search products"
              className="h-10 w-full rounded-md border border-border bg-white pl-9 pr-3 text-sm outline-none focus:border-primary"
            />
          </label>
          <label className="relative md:w-56">
            <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="h-10 w-full appearance-none rounded-md border border-border bg-white pl-9 pr-3 text-sm outline-none focus:border-primary"
            >
              <option value="all">All statuses</option>
              <option value="in_stock">Còn hàng</option>
              <option value="pre_order">Đặt trước</option>
              <option value="out_of_stock">Hết hàng</option>
              <option value="unknown">Không rõ</option>
            </select>
          </label>
        </div>

        {productsQuery.isLoading ? (
          <StateMessage title="Loading products" />
        ) : productsQuery.isError ? (
          <StateMessage title="Cannot load products" />
        ) : (
          <ProductsTable products={filteredProducts} />
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-white px-4 py-3">
      <div className="text-xs font-medium uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}

function StateMessage({ title }: { title: string }) {
  return (
    <div className="rounded-md border border-border bg-white px-4 py-10 text-center text-sm text-muted-foreground">
      {title}
    </div>
  );
}

function ProductsTable({ products }: { products: Product[] }) {
  if (products.length === 0) {
    return <StateMessage title="No products found" />;
  }

  return (
    <div className="overflow-hidden rounded-md border border-border bg-white">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[920px] border-collapse text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Product</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Current Price</th>
              <th className="px-4 py-3 text-right font-medium">Original Price</th>
              <th className="px-4 py-3 text-right font-medium">Discount</th>
              <th className="px-4 py-3 text-right font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={`${product.provider}-${product.external_id}`} className="border-t border-border">
                <td className="px-4 py-3">
                  <div className="font-medium">{product.name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{product.external_id}</div>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{product.category ?? "-"}</td>
                <td className="px-4 py-3">
                  <span className="rounded-md border border-border px-2 py-1 text-xs">
                    {statusLabels[product.status] ?? product.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  {formatVnd(product.current_price)}
                </td>
                <td className="px-4 py-3 text-right text-muted-foreground">
                  {formatVnd(product.original_price)}
                </td>
                <td className="px-4 py-3 text-right">{product.discount_percentage}%</td>
                <td className="px-4 py-3 text-right">
                  {product.product_url ? (
                    <a
                      href={product.product_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-border px-3 text-xs font-medium"
                    >
                      <ShoppingCart className="h-3.5 w-3.5" />
                      Open
                    </a>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

