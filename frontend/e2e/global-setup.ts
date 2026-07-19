import { execSync } from "child_process";
import * as path from "path";

export default async function globalSetup() {
  const seedScript = path.resolve(__dirname, "../../scripts/e2e_seed.py");
  try {
    const out = execSync(`python3 "${seedScript}"`, {
      timeout: 30_000,
      env: { ...process.env },
    });
    console.log("[e2e global-setup]", out.toString().trim());
  } catch (err: any) {
    console.warn("[e2e global-setup] seed skipped:", err.message?.split("\n")[0]);
  }
}
