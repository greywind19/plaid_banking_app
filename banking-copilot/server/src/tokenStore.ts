/**
 * In-memory store for the Plaid access_token (and a cached copy of synced
 * transactions). This is intentionally ephemeral — storage/persistence is a
 * later phase. The access_token and secret NEVER leave the server.
 */
import type { NormalizedTxn } from "./plaid/normalize.js";

interface Store {
  accessToken: string | null;
  itemId: string | null;
  cursor: string | null;
  transactions: NormalizedTxn[];
}

const store: Store = {
  accessToken: null,
  itemId: null,
  cursor: null,
  transactions: [],
};

export const tokenStore = {
  isLinked(): boolean {
    return store.accessToken !== null;
  },
  get(): Store {
    return store;
  },
  setItem(accessToken: string, itemId: string) {
    store.accessToken = accessToken;
    store.itemId = itemId;
    store.cursor = null;
    store.transactions = [];
  },
  setCursor(cursor: string) {
    store.cursor = cursor;
  },
  setTransactions(txns: NormalizedTxn[]) {
    store.transactions = txns;
  },
  requireToken(): string {
    if (!store.accessToken) {
      throw new Error(
        "No linked account. Call the connect/init endpoint first to bootstrap the Plaid sandbox Item."
      );
    }
    return store.accessToken;
  },
  reset() {
    store.accessToken = null;
    store.itemId = null;
    store.cursor = null;
    store.transactions = [];
  },
};
