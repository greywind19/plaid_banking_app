import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import "dotenv/config";
import {
  connectSandbox,
  getBalances,
  getTransactions,
  listAccounts,
  netWorth,
  spendingByCategory,
} from "./plaid/service.js";

/**
 * MCP server exposing the Plaid-backed banking tools. This is the surface the
 * future Foundry hosted agent will call. All tools are READ-ONLY.
 */
const server = new McpServer({
  name: "banking-copilot",
  version: "0.1.0",
});

const json = (data: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
});

const accountIds = z
  .array(z.string())
  .optional()
  .describe("Optional list of account IDs to filter by. Omit for all accounts.");

server.tool(
  "connect_sandbox",
  "Bootstrap the Plaid sandbox: create a test bank Item, exchange the token, and sync transactions. Call this once before other tools.",
  {},
  async () => json(await connectSandbox())
);

server.tool(
  "list_accounts",
  "List all linked accounts with type, subtype, masked number, and balances.",
  {},
  async () => json({ accounts: await listAccounts() })
);

server.tool(
  "get_balances",
  "Get current/available balances (and credit limits) for accounts.",
  { accountIds },
  async ({ accountIds }) => json({ accounts: await getBalances(accountIds) })
);

server.tool(
  "get_transactions",
  "Get normalized transactions in a date range (YYYY-MM-DD). direction=outflow means spend.",
  {
    start: z.string().optional().describe("Start date YYYY-MM-DD (inclusive)."),
    end: z.string().optional().describe("End date YYYY-MM-DD (inclusive)."),
    accountIds,
    count: z.number().int().positive().optional().describe("Max transactions to return."),
  },
  async (args) => json({ transactions: getTransactions(args) })
);

server.tool(
  "spending_by_category",
  "Aggregate spending (outflows) by category over a date range. Excludes internal transfers and credit-card payments by default so totals are not double-counted.",
  {
    start: z.string().optional(),
    end: z.string().optional(),
    accountIds,
    excludeTransfers: z.boolean().optional().default(true),
  },
  async (args) => json(spendingByCategory(args))
);

server.tool(
  "net_worth",
  "Compute net worth: assets (depository accounts) minus liabilities (credit accounts).",
  {},
  async () => json(await netWorth())
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[mcp] banking-copilot MCP server running on stdio");
