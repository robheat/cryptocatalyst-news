import { NextRequest, NextResponse } from "next/server";
import { getResend } from "@/lib/resend";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json(
        { error: "Please enter a valid email address." },
        { status: 400 }
      );
    }

    const resend = getResend();
    await resend.contacts.create({
      email,
      unsubscribed: false,
    });

    // Send welcome email (fire-and-forget — don't block the response)
    resend.emails.send({
      from: "CryptoCatalyst <digest@cryptocatalyst.news>",
      to: [email],
      subject: "Welcome to CryptoCatalyst — Weekly Crypto Digest",
      html: welcomeEmail(),
    }).catch((err) => console.error("Welcome email failed:", err));

    return NextResponse.json({ ok: true });
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Something went wrong.";

    // Resend returns 409 if contact already exists — treat as success
    if (message.includes("already exists")) {
      return NextResponse.json({ ok: true });
    }

    console.error("Subscribe error:", message);
    return NextResponse.json(
      { error: "Something went wrong. Please try again." },
      { status: 500 }
    );
  }
}

function welcomeEmail(): string {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"></head>
<body style="margin:0;padding:0;background:#0a0a0a;color:#ededed;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
  <div style="max-width:560px;margin:0 auto;padding:40px 20px">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1f2937">
      <h1 style="margin:0;font-size:24px;font-weight:700">
        <span style="color:#ffffff">Crypto</span><span style="color:#f59e0b">Catalyst</span><span style="color:#6b7280;font-size:14px">.news</span>
      </h1>
    </div>
    <div style="padding:32px 0">
      <h2 style="margin:0 0 16px;font-size:20px;color:#f9fafb">Welcome aboard!</h2>
      <p style="margin:0 0 16px;color:#d1d5db;font-size:15px;line-height:1.6">
        You're now subscribed to the <strong>CryptoCatalyst Weekly Digest</strong>. Every Sunday, you'll receive a curated email with the most important crypto and blockchain stories of the week.
      </p>
      <p style="margin:0 0 16px;color:#d1d5db;font-size:15px;line-height:1.6">
        In the meantime, check out today's latest stories:
      </p>
      <div style="text-align:center;padding:16px 0">
        <a href="https://cryptocatalyst.news" style="display:inline-block;background:#d97706;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:12px 24px;border-radius:8px">
          Visit CryptoCatalyst →
        </a>
      </div>
    </div>
    <div style="border-top:1px solid #1f2937;padding-top:20px;text-align:center">
      <p style="margin:0;color:#6b7280;font-size:12px">
        <a href="https://cryptocatalyst.news" style="color:#f59e0b;text-decoration:none">CryptoCatalyst.news</a> · <a href="https://twitter.com/CryptoCatalystN" style="color:#f59e0b;text-decoration:none">@CryptoCatalystN</a>
      </p>
    </div>
  </div>
</body>
</html>`;
}
