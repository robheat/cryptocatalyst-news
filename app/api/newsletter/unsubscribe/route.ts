import { NextRequest, NextResponse } from "next/server";
import { getResend } from "@/lib/resend";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id") ?? "";

  if (!id) {
    return new NextResponse(unsubPage("Invalid unsubscribe link."), {
      status: 400,
      headers: { "Content-Type": "text/html" },
    });
  }

  try {
    const resend = getResend();
    await resend.contacts.update({
      id,
      unsubscribed: true,
    });

    return new NextResponse(
      unsubPage("You have been unsubscribed. You won't receive any more emails from CryptoCatalyst."),
      { status: 200, headers: { "Content-Type": "text/html" } }
    );
  } catch (err) {
    console.error("Unsubscribe error:", err);
    return new NextResponse(
      unsubPage("Something went wrong. Please try again or email us."),
      { status: 500, headers: { "Content-Type": "text/html" } }
    );
  }
}

function unsubPage(message: string) {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unsubscribe — CryptoCatalyst</title>
<style>body{font-family:system-ui,sans-serif;background:#0a0a0a;color:#ededed;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{max-width:420px;text-align:center;padding:2rem}.card h1{font-size:1.25rem;margin-bottom:1rem}.card p{color:#9ca3af;font-size:.875rem}
a{color:#f59e0b;text-decoration:none}</style></head>
<body><div class="card"><h1>CryptoCatalyst</h1><p>${message}</p><p style="margin-top:1.5rem"><a href="https://cryptocatalyst.news">← Back to CryptoCatalyst</a></p></div></body></html>`;
}
