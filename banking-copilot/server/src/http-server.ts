import express from "express";
import cors from "cors";
import "dotenv/config";
import {
  connectSandbox,
  getBalances,
  getTransactions,
  listAccounts,
  netWorth,
  spendingByCategory,
  syncTransactions,
} from "./plaid/service.js";
import { tokenStore } from "./tokenStore.js";

const app = express();
app.use(cors());
app.use(express.json());

function parseAccountIds(v: unknown): string[] | undefined {
  if (typeof v !== "string" || v.trim() === "") return undefined;
  return v.split(",").map((s) => s.trim()).filter(Boolean);
}

const wrap =
  (fn: (req: express.Request, res: express.Response) => Promise<void>) =>
  (req: express.Request, res: express.Response) => {
    fn(req, res).catch((err) => {
      const plaidErr = err?.response?.data;
      console.error("[api] error:", plaidErr ?? err?.message ?? err);
      res.status(500).json({
        error: plaidErr?.error_message ?? err?.message ?? "Unknown error",
        code: plaidErr?.error_code,
      });
    });
  };

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, linked: tokenStore.isLinked() });
});

// Bootstrap the Plaid sandbox Item (creates + exchanges token, syncs txns).
app.post(
  "/api/connect",
  wrap(async (_req, res) => {
    const result = await connectSandbox();
    res.json(result);
  })
);

app.post(
  "/api/sync",
  wrap(async (_req, res) => {
    const count = await syncTransactions();
    res.json({ transactionCount: count });
  })
);

app.get(
  "/api/accounts",
  wrap(async (_req, res) => {
    res.json({ accounts: await listAccounts() });
  })
);

app.get(
  "/api/balances",
  wrap(async (req, res) => {
    const accountIds = parseAccountIds(req.query.accountIds);
    res.json({ accounts: await getBalances(accountIds) });
  })
);

app.get(
  "/api/transactions",
  wrap(async (req, res) => {
    const txns = getTransactions({
      start: req.query.start as string | undefined,
      end: req.query.end as string | undefined,
      accountIds: parseAccountIds(req.query.accountIds),
      count: req.query.count ? Number(req.query.count) : undefined,
    });
    res.json({ transactions: txns });
  })
);

app.get(
  "/api/spending",
  wrap(async (req, res) => {
    const result = spendingByCategory({
      start: req.query.start as string | undefined,
      end: req.query.end as string | undefined,
      accountIds: parseAccountIds(req.query.accountIds),
      excludeTransfers: req.query.includeTransfers !== "true",
    });
    res.json(result);
  })
);

app.get(
  "/api/net-worth",
  wrap(async (_req, res) => {
    res.json(await netWorth());
  })
);

const port = Number(process.env.PORT ?? 8787);
app.listen(port, () => {
  console.log(`[api] Banking Copilot REST API listening on http://localhost:${port}`);
  console.log(`[api] POST /api/connect to bootstrap the Plaid sandbox.`);
});
