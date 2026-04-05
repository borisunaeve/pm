"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, saveAuth } from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const payload = mode === "login"
        ? await login(username, password)
        : await register(username, password);

      saveAuth(payload);
      router.push("/boards");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#032147] flex items-center justify-center p-4 font-body">
      <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-md">
        <h1 className="text-3xl font-display font-bold text-[#032147] mb-2 text-center">
          Project Studio
        </h1>
        <p className="text-center text-[#888888] text-sm mb-6">
          Manage your projects with AI
        </p>

        {/* Mode toggle */}
        <div className="flex rounded-lg border border-gray-200 p-1 mb-6">
          {(["login", "register"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setError(""); }}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === m
                  ? "bg-[#032147] text-white"
                  : "text-[#888888] hover:text-[#032147]"
              }`}
            >
              {m === "login" ? "Sign In" : "Create Account"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[#888888] mb-1 text-sm font-medium">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:border-[#209dd7] focus:ring-1 focus:ring-[#209dd7]"
              placeholder={mode === "register" ? "Min 3 characters" : "Enter username"}
              minLength={mode === "register" ? 3 : undefined}
              required
            />
          </div>

          <div>
            <label className="block text-[#888888] mb-1 text-sm font-medium">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:border-[#209dd7] focus:ring-1 focus:ring-[#209dd7]"
              placeholder={mode === "register" ? "Min 6 characters" : "Enter password"}
              minLength={mode === "register" ? 6 : undefined}
              required
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#753991] text-white rounded-lg py-3 font-medium hover:bg-[#5b2a73] transition-colors mt-6 disabled:opacity-60"
          >
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        {mode === "login" && (
          <p className="text-center text-xs text-[#888888] mt-4">
            Demo: <strong>user</strong> / <strong>password</strong>
          </p>
        )}
      </div>
    </div>
  );
}
