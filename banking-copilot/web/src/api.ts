// Thin typed client for the Banking Copilot REST API (proxied via Vite to :8787).

export interface Account {
  accountId: string;
  name: string;
  officialName: string | null;
  mask: string | null;
  type: string;
  subtype: string | null;
  currentBalance: number | null;
  availableBalance: number | null;
  creditLimit: number | null;
  currency: string | null;
}

export interface Txn {
  id: string;
  accountId: string;
  date: string;
  name: string;
  merchant: string | null;
  amount: number;
  direction: "outflow" | "inflow";
  category: string;
  detailedCategory: string | null;
  isTransfer: boolean;
  currency: string | null;
}

export interface CategorySpend {
  category: string;
  total: number;
  count: number;
}

export interface NetWorth {
  assets: number;
  liabilities: number;
  netWorth: number;
  breakdown: {
    accountId: string;
    name: string;
    type: string;
    balance: number;
    sign: "asset" | "liability";
  }[];
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.error ?? `Request failed: ${res.status}`);
  }
  return body as T;
}

export const api = {
  health: () => req<{ ok: boolean; linked: boolean }>("/api/health"),
  connect: () =>
    req<{ itemId: string; accounts: Account[]; transactionCount: number }>(
      "/api/connect",
      { method: "POST" }
    ),
  accounts: () => req<{ accounts: Account[] }>("/api/accounts"),
  transactions: (params: { start?: string; end?: string; count?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.start) qs.set("start", params.start);
    if (params.end) qs.set("end", params.end);
    if (params.count) qs.set("count", String(params.count));
    return req<{ transactions: Txn[] }>(`/api/transactions?${qs.toString()}`);
  },
  spending: (params: { start?: string; end?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.start) qs.set("start", params.start);
    if (params.end) qs.set("end", params.end);
    return req<{ totalSpend: number; categories: CategorySpend[] }>(
      `/api/spending?${qs.toString()}`
    );
  },
  netWorth: () => req<NetWorth>("/api/net-worth"),
};

export function money(n: number | null, currency = "USD"): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(n);
}
