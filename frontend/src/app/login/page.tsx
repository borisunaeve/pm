"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const router = useRouter();

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (username === "user" && password === "password") {
            // In a real app we'd use true tokens/cookies. For MVP simple localStorage is fine.
            localStorage.setItem("pm_auth", "true");
            router.push("/");
        } else {
            setError("Invalid credentials. Try user / password");
        }
    };

    return (
        <div className="min-h-screen bg-[#032147] flex items-center justify-center p-4 font-body">
            <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-md">
                <h1 className="text-3xl font-display font-bold text-[#032147] mb-6 text-center">
                    Kanban Studio Login
                </h1>

                <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                        <label className="block text-[#888888] mb-1 text-sm font-medium">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:border-[#209dd7] focus:ring-1 focus:ring-[#209dd7]"
                            placeholder="Enter username"
                        />
                    </div>

                    <div>
                        <label className="block text-[#888888] mb-1 text-sm font-medium">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:border-[#209dd7] focus:ring-1 focus:ring-[#209dd7]"
                            placeholder="Enter password"
                        />
                    </div>

                    {error && <p className="text-red-500 text-sm">{error}</p>}

                    <button
                        type="submit"
                        className="w-full bg-[#753991] text-white rounded-lg py-3 font-medium hover:bg-[#5b2a73] transition-colors mt-6"
                    >
                        Sign In
                    </button>
                </form>
            </div>
        </div>
    );
}
