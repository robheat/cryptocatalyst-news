import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get("title") ?? "CryptoCatalyst — Daily Crypto News";
  const category = searchParams.get("category") ?? "";
  const date =
    searchParams.get("date") ?? new Date().toISOString().slice(0, 10);

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          width: "100%",
          height: "100%",
          background: "linear-gradient(135deg, #0a0a0a 0%, #111827 100%)",
          padding: "60px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center" }}>
          <span
            style={{
              color: "#ffffff",
              fontSize: "28px",
              fontWeight: 700,
              letterSpacing: "-0.5px",
            }}
          >
            AI
          </span>
          <span
            style={{
              color: "#a78bfa",
              fontSize: "28px",
              fontWeight: 700,
            }}
          >
            nformed
          </span>
          <span
            style={{
              color: "#6b7280",
              fontSize: "18px",
              marginLeft: "2px",
            }}
          >
            .dev
          </span>
          {category ? (
            <span
              style={{
                background: "rgba(245,158,11,0.15)",
                border: "1px solid rgba(245,158,11,0.4)",
                color: "#f59e0b",
                fontSize: "13px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "1px",
                padding: "4px 12px",
                borderRadius: "999px",
                marginLeft: "16px",
              }}
            >
              {category}
            </span>
          ) : null}
        </div>

        <div
          style={{
            display: "flex",
            color: "#f9fafb",
            fontSize: title.length > 70 ? 36 : 44,
            fontWeight: 800,
            lineHeight: 1.2,
            letterSpacing: "-1px",
            maxWidth: "900px",
          }}
        >
          {title}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            color: "#6b7280",
            fontSize: "15px",
            width: "100%",
          }}
        >
          <span>{date}</span>
          <span>Daily Crypto News — Curated by AI</span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
