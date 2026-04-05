"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, changePassword, clearAuth, isLoggedIn, type UserProfile } from "@/lib/api";

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    getMe().then(setProfile).finally(() => setLoading(false));
  }, [router]);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError("");
    setPwSuccess(false);

    if (newPw !== confirmPw) { setPwError("New passwords do not match"); return; }
    if (newPw.length < 6) { setPwError("New password must be at least 6 characters"); return; }

    setPwSaving(true);
    try {
      await changePassword(currentPw, newPw);
      setPwSuccess(true);
      setCurrentPw(""); setNewPw(""); setConfirmPw("");
    } catch (err: unknown) {
      setPwError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setPwSaving(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-[#032147] flex items-center justify-center text-white">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-[#032147] font-body">
      <header className="bg-[#032147] border-b border-white/10 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/boards")}
            className="text-white/60 hover:text-white text-sm transition-colors flex items-center gap-1"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 18-6-6 6-6" />
            </svg>
            Boards
          </button>
          <h1 className="text-white font-display text-lg font-bold">Project Studio</h1>
        </div>
        <button
          onClick={() => { clearAuth(); router.push("/login"); }}
          className="text-white/60 hover:text-white text-sm transition-colors"
        >
          Sign Out
        </button>
      </header>

      <main className="max-w-lg mx-auto px-6 py-10 space-y-8">
        <h2 className="text-white font-display text-3xl font-semibold">Profile</h2>

        {/* Profile info */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-4">
          <h3 className="text-white font-display font-semibold">Account Details</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center py-2 border-b border-white/10">
              <span className="text-white/50 text-sm">Username</span>
              <span className="text-white font-medium">{profile?.username}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/10">
              <span className="text-white/50 text-sm">User ID</span>
              <span className="text-white/70 text-xs font-mono">{profile?.id}</span>
            </div>
            {profile?.created_at && (
              <div className="flex justify-between items-center py-2">
                <span className="text-white/50 text-sm">Member since</span>
                <span className="text-white/70 text-sm">
                  {new Date(profile.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Change password */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          <h3 className="text-white font-display font-semibold mb-4">Change Password</h3>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="text-white/50 text-xs uppercase tracking-wide block mb-1">Current Password</label>
              <input
                type="password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                className="w-full rounded-xl bg-white/10 border border-white/20 text-white px-4 py-2.5 text-sm focus:outline-none focus:border-[#209dd7]"
                required
              />
            </div>
            <div>
              <label className="text-white/50 text-xs uppercase tracking-wide block mb-1">New Password</label>
              <input
                type="password"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                minLength={6}
                className="w-full rounded-xl bg-white/10 border border-white/20 text-white px-4 py-2.5 text-sm focus:outline-none focus:border-[#209dd7]"
                required
              />
            </div>
            <div>
              <label className="text-white/50 text-xs uppercase tracking-wide block mb-1">Confirm New Password</label>
              <input
                type="password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                className="w-full rounded-xl bg-white/10 border border-white/20 text-white px-4 py-2.5 text-sm focus:outline-none focus:border-[#209dd7]"
                required
              />
            </div>

            {pwError && <p className="text-red-400 text-sm">{pwError}</p>}
            {pwSuccess && <p className="text-green-400 text-sm">Password changed successfully.</p>}

            <button
              type="submit"
              disabled={pwSaving}
              className="w-full bg-[#753991] text-white rounded-xl py-2.5 text-sm font-semibold hover:bg-[#5b2a73] transition-colors disabled:opacity-60"
            >
              {pwSaving ? "Saving..." : "Change Password"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
