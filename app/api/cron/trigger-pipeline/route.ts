import { NextRequest, NextResponse } from "next/server";

const CRON_SECRET = process.env.CRON_SECRET;
const GITHUB_PAT = process.env.GITHUB_PAT;
const REPO = "robheat/cryptocatalyst-news";
const WORKFLOW_FILE = "daily-pipeline.yml";
const BRANCH = "master";

export async function POST(req: NextRequest) {
  // Verify shared secret
  const auth = req.headers.get("authorization");
  if (!CRON_SECRET || auth !== `Bearer ${CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!GITHUB_PAT) {
    return NextResponse.json(
      { error: "GITHUB_PAT not configured" },
      { status: 500 }
    );
  }

  // Trigger GitHub Actions workflow_dispatch
  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${GITHUB_PAT}`,
        Accept: "application/vnd.github+v3+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: BRANCH }),
    }
  );

  if (resp.status === 204) {
    return NextResponse.json({
      ok: true,
      triggered: new Date().toISOString(),
    });
  }

  const body = await resp.text();
  return NextResponse.json(
    { error: `GitHub API ${resp.status}: ${body}` },
    { status: resp.status }
  );
}
