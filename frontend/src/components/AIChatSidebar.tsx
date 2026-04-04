"use client";

import { useState, useRef, useEffect } from "react";
import clsx from "clsx";

type Message = {
    role: "user" | "assistant";
    content: string;
};

type AIChatSidebarProps = {
    onRefreshBoard: () => void;
};

export const AIChatSidebar = ({ onRefreshBoard }: AIChatSidebarProps) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        { role: "assistant", content: "Hi! I am the PM AI. I can create, move, delete cards or rename columns for you. How can I help?" }
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (isOpen) {
            bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = { role: "user", content: input };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        try {
            const response = await fetch("/api/ai/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    messages: [...messages, userMessage].map((m) => ({
                        role: m.role,
                        content: m.content,
                    })),
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to communicate with AI");
            }

            const data = await response.json();

            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: data.message || "Done." },
            ]);

            // If the AI took any board actions, refresh so the changes appear.
            if (data.actions?.length > 0) {
                onRefreshBoard();
            }

        } catch (error) {
            console.error(error);
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Sorry, I ran into an error processing that request." },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            {/* Floating Toggle Button */}
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--primary-blue)] text-white shadow-lg transition hover:scale-105 active:scale-95"
                aria-label="Toggle AI Chat"
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
                </svg>
            </button>

            {/* Sidebar Panel */}
            <div
                className={clsx(
                    "fixed bottom-24 right-6 z-40 flex h-[600px] w-80 max-w-[calc(100vw-48px)] flex-col overflow-hidden rounded-[24px] border border-[var(--stroke)] bg-white/90 shadow-2xl backdrop-blur transition-all duration-300",
                    isOpen
                        ? "translate-y-0 opacity-100"
                        : "pointer-events-none translate-y-8 opacity-0"
                )}
            >
                <header className="flex items-center justify-between border-b border-[var(--stroke)] bg-[var(--surface)] px-4 py-3">
                    <h3 className="font-display font-semibold text-[var(--navy-dark)]">AI Assistant</h3>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </header>

                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((m, idx) => (
                        <div
                            key={idx}
                            className={clsx(
                                "w-full flex",
                                m.role === "user" ? "justify-end" : "justify-start"
                            )}
                        >
                            <div
                                className={clsx(
                                    "max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-6",
                                    m.role === "user"
                                        ? "bg-[var(--primary-blue)] text-white"
                                        : "bg-[var(--surface-strong)] text-[var(--navy-dark)]"
                                )}
                            >
                                {m.content}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex w-full justify-start">
                            <div className="max-w-[85%] rounded-2xl bg-[var(--surface-strong)] px-4 py-2 text-sm leading-6 text-[var(--gray-text)]">
                                Thinking...
                            </div>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                <form onSubmit={handleSubmit} className="border-t border-[var(--stroke)] p-4 bg-white">
                    <div className="relative flex items-center">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="e.g. Add a card 'Fix tests' to Done"
                            className="w-full rounded-full border border-[var(--stroke)] bg-[var(--surface)] pl-4 pr-12 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-1 focus:ring-[var(--primary-blue)]"
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className="absolute right-2 flex h-8 w-8 items-center justify-center rounded-full bg-[var(--primary-blue)] text-white disabled:opacity-50"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </div>
                </form>
            </div>
        </>
    );
};
