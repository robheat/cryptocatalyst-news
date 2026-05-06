"use client";

import { useState, FormEvent } from "react";

export default function NewsletterSignup({ compact = false }: { compact?: boolean }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("loading");

    try {
      const res = await fetch("/api/newsletter/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();

      if (res.ok) {
        setStatus("success");
        setMessage("You're in! We sent a welcome email — check your inbox.");
        setEmail("");
      } else {
        setStatus("error");
        setMessage(data.error ?? "Something went wrong.");
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Please try again.");
    }
  }

  if (status === "success") {
    return (
      <div className={compact ? "" : "border border-neutral-800 rounded-xl p-6 bg-neutral-900 text-center"}>
        <p className="text-violet-400 font-medium">✓ Subscribed!</p>
        <p className="text-sm text-neutral-400 mt-1">{message}</p>
      </div>
    );
  }

  return (
    <div className={compact ? "" : "border border-neutral-800 rounded-xl p-6 bg-neutral-900 text-center"}>
      {!compact && (
        <>
          <p className="text-neutral-400 text-sm mb-1">Stay in the loop</p>
          <h3 className="text-lg font-semibold text-neutral-100 mb-1">
            Weekly AI Digest
          </h3>
          <p className="text-sm text-neutral-500 mb-4">
            The top AI stories of the week, delivered every Sunday.
          </p>
        </>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-md mx-auto">
        <input
          type="email"
          required
          placeholder="you@email.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (status === "error") setStatus("idle");
          }}
          className="flex-1 bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          {status === "loading" ? "..." : "Subscribe"}
        </button>
      </form>
      {status === "error" && (
        <p className="text-red-400 text-xs mt-2">{message}</p>
      )}
      <p className="text-xs text-neutral-600 mt-3">
        No spam. Unsubscribe anytime.
      </p>
    </div>
  );
}
