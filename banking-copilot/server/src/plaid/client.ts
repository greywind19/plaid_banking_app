import { Configuration, PlaidApi, PlaidEnvironments } from "plaid";
import "dotenv/config";

const clientId = process.env.PLAID_CLIENT_ID;
const secret = process.env.PLAID_SECRET;
const env = (process.env.PLAID_ENV ?? "sandbox") as keyof typeof PlaidEnvironments;

if (!clientId || !secret) {
  console.warn(
    "[plaid] PLAID_CLIENT_ID / PLAID_SECRET are not set. Copy .env.example to .env and fill in your sandbox credentials."
  );
}

const configuration = new Configuration({
  basePath: PlaidEnvironments[env] ?? PlaidEnvironments.sandbox,
  baseOptions: {
    headers: {
      "PLAID-CLIENT-ID": clientId ?? "",
      "PLAID-SECRET": secret ?? "",
    },
  },
});

export const plaid = new PlaidApi(configuration);
export const SANDBOX_INSTITUTION_ID =
  process.env.SANDBOX_INSTITUTION_ID ?? "ins_109508";
