import type { AccountBase, Transaction } from "plaid";

/**
 * Plaid amount sign convention (same across account types):
 *   amount > 0  => money leaving the account   (spend / charge)
 *   amount < 0  => money entering the account   (deposit / payment / refund)
 *
 * We normalize every transaction to an explicit shape so the rest of the app
 * (and later, the LLM agent) never has to reason about Plaid's sign rules.
 */

export type Direction = "outflow" | "inflow";

export interface NormalizedTxn {
  id: string;
  accountId: string;
  date: string;
  name: string;
  merchant: string | null;
  amount: number; // always positive magnitude
  direction: Direction; // outflow = spend, inflow = money in
  category: string; // PFC primary, human-friendly
  detailedCategory: string | null;
  isTransfer: boolean; // internal movement (transfer / card payment) — exclude from spend
  currency: string | null;
}

const TRANSFER_PRIMARIES = new Set(["TRANSFER_IN", "TRANSFER_OUT"]);

function prettyCategory(primary: string | undefined): string {
  if (!primary) return "Uncategorized";
  return primary
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function normalizeTransaction(t: Transaction): NormalizedTxn {
  const pfc = t.personal_finance_category;
  const primary = pfc?.primary;
  const detailed = pfc?.detailed ?? null;

  const isTransfer =
    (primary != null && TRANSFER_PRIMARIES.has(primary)) ||
    detailed === "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT";

  return {
    id: t.transaction_id,
    accountId: t.account_id,
    date: t.date,
    name: t.name,
    merchant: t.merchant_name ?? null,
    amount: Math.abs(t.amount),
    direction: t.amount > 0 ? "outflow" : "inflow",
    category: prettyCategory(primary),
    detailedCategory: detailed,
    isTransfer,
    currency: t.iso_currency_code ?? t.unofficial_currency_code ?? null,
  };
}

export interface NormalizedAccount {
  accountId: string;
  name: string;
  officialName: string | null;
  mask: string | null; // last 4 only — never expose full numbers
  type: string; // depository | credit | ...
  subtype: string | null; // checking | savings | credit card | ...
  currentBalance: number | null;
  availableBalance: number | null;
  creditLimit: number | null;
  currency: string | null;
}

export function normalizeAccount(a: AccountBase): NormalizedAccount {
  return {
    accountId: a.account_id,
    name: a.name,
    officialName: a.official_name ?? null,
    mask: a.mask ?? null,
    type: String(a.type),
    subtype: a.subtype ? String(a.subtype) : null,
    currentBalance: a.balances.current ?? null,
    availableBalance: a.balances.available ?? null,
    creditLimit: a.balances.limit ?? null,
    currency:
      a.balances.iso_currency_code ??
      a.balances.unofficial_currency_code ??
      null,
  };
}
