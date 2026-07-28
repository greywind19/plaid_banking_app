import { CountryCode, Products } from "plaid";
import { plaid, SANDBOX_INSTITUTION_ID } from "./client.js";
import {
  normalizeAccount,
  normalizeTransaction,
  type NormalizedAccount,
  type NormalizedTxn,
} from "./normalize.js";
import { tokenStore } from "../tokenStore.js";

/**
 * Core banking service. Every capability the UI (and later the agent) needs is
 * a plain async function here. The REST and MCP layers are thin wrappers.
 */

/** Bootstrap a Plaid sandbox Item and sync its transactions. */
export async function connectSandbox(): Promise<{
  itemId: string;
  accounts: NormalizedAccount[];
  transactionCount: number;
}> {
  // 1. Create a sandbox public_token for the test institution.
  const publicTokenRes = await plaid.sandboxPublicTokenCreate({
    institution_id: SANDBOX_INSTITUTION_ID,
    initial_products: [Products.Transactions],
  });

  // 2. Exchange it for a durable access_token.
  const exchangeRes = await plaid.itemPublicTokenExchange({
    public_token: publicTokenRes.data.public_token,
  });

  const accessToken = exchangeRes.data.access_token;
  const itemId = exchangeRes.data.item_id;
  tokenStore.setItem(accessToken, itemId);

  // 3. Sync transactions into the in-memory cache.
  const transactionCount = await syncTransactions();

  const accounts = await listAccounts();
  return { itemId, accounts, transactionCount };
}

/** Pull all transactions via /transactions/sync, retrying while data is prepping. */
export async function syncTransactions(): Promise<number> {
  const accessToken = tokenStore.requireToken();
  const collected: NormalizedTxn[] = [];
  let cursor: string | undefined = undefined;
  let hasMore = true;
  let attempts = 0;

  while (hasMore) {
    try {
      const res = await plaid.transactionsSync({
        access_token: accessToken,
        cursor,
        count: 500,
      });
      const data = res.data;
      for (const t of data.added) collected.push(normalizeTransaction(t));
      cursor = data.next_cursor;
      hasMore = data.has_more;
    } catch (err: any) {
      // Sandbox data may not be ready yet (PRODUCT_NOT_READY) — back off and retry.
      const code = err?.response?.data?.error_code;
      if (code === "PRODUCT_NOT_READY" && attempts < 8) {
        attempts++;
        await new Promise((r) => setTimeout(r, 1500));
        continue;
      }
      throw err;
    }
  }

  if (cursor) tokenStore.setCursor(cursor);
  tokenStore.setTransactions(collected);
  return collected.length;
}

export async function listAccounts(): Promise<NormalizedAccount[]> {
  const accessToken = tokenStore.requireToken();
  const res = await plaid.accountsGet({ access_token: accessToken });
  return res.data.accounts.map(normalizeAccount);
}

export async function getBalances(
  accountIds?: string[]
): Promise<NormalizedAccount[]> {
  const accessToken = tokenStore.requireToken();
  const res = await plaid.accountsBalanceGet({ access_token: accessToken });
  let accounts = res.data.accounts.map(normalizeAccount);
  if (accountIds?.length) {
    const set = new Set(accountIds);
    accounts = accounts.filter((a) => set.has(a.accountId));
  }
  return accounts;
}

function inRange(dateStr: string, start?: string, end?: string): boolean {
  if (start && dateStr < start) return false;
  if (end && dateStr > end) return false;
  return true;
}

export interface TransactionQuery {
  start?: string;
  end?: string;
  accountIds?: string[];
  count?: number;
}

export function getTransactions(q: TransactionQuery = {}): NormalizedTxn[] {
  const { transactions } = tokenStore.get();
  const accountSet = q.accountIds?.length ? new Set(q.accountIds) : null;
  let result = transactions.filter(
    (t) =>
      inRange(t.date, q.start, q.end) &&
      (!accountSet || accountSet.has(t.accountId))
  );
  result = result.sort((a, b) => (a.date < b.date ? 1 : -1)); // newest first
  if (q.count && q.count > 0) result = result.slice(0, q.count);
  return result;
}

export interface CategorySpend {
  category: string;
  total: number;
  count: number;
}

/** Sum outflows by category, excluding internal transfers/card payments by default. */
export function spendingByCategory(q: TransactionQuery & {
  excludeTransfers?: boolean;
} = {}): { totalSpend: number; categories: CategorySpend[] } {
  const excludeTransfers = q.excludeTransfers ?? true;
  const txns = getTransactions({ ...q, count: undefined }).filter(
    (t) =>
      t.direction === "outflow" && (!excludeTransfers || !t.isTransfer)
  );

  const byCat = new Map<string, CategorySpend>();
  let totalSpend = 0;
  for (const t of txns) {
    totalSpend += t.amount;
    const existing = byCat.get(t.category) ?? {
      category: t.category,
      total: 0,
      count: 0,
    };
    existing.total = round2(existing.total + t.amount);
    existing.count += 1;
    byCat.set(t.category, existing);
  }

  const categories = [...byCat.values()].sort((a, b) => b.total - a.total);
  return { totalSpend: round2(totalSpend), categories };
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

/** assets (depository) minus liabilities (credit) across all linked accounts. */
export async function netWorth(): Promise<NetWorth> {
  const accounts = await getBalances();
  let assets = 0;
  let liabilities = 0;
  const breakdown = accounts.map((a) => {
    const bal = a.currentBalance ?? 0;
    const isCredit = a.type === "credit";
    if (isCredit) liabilities += bal;
    else assets += bal;
    return {
      accountId: a.accountId,
      name: a.name,
      type: a.type,
      balance: bal,
      sign: isCredit ? ("liability" as const) : ("asset" as const),
    };
  });
  return {
    assets: round2(assets),
    liabilities: round2(liabilities),
    netWorth: round2(assets - liabilities),
    breakdown,
  };
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
