"use client";

import { useEffect, useState } from "react";

const API_URL = "http://127.0.0.1:8000";

const DEMO_USERS = [
  "gc.sharma",
  "adv.rao",
  "adv.nair",
  "adv.khan",
  "adv.iyer",
  "comp.deshpande",
  "comp.bose",
  "para.sneha",
];

type User = {
  username: string;
  name: string;
  role: string;
  matters: string[];
};

type Citation = {
  source_document: string;
  doc_id: string;
  chunk_id: string;
  page_numbers: number[];
};

type GroupedCitation = {
  source_document: string;
  doc_id: string;
  page_numbers: number[];
};

type Message = {
  question: string;
  answer: string;
  status: string;
  citations: Citation[];
};

function groupCitations(citations: Citation[]): GroupedCitation[] {
  const grouped = new Map<string, GroupedCitation>();

  for (const citation of citations) {
    const key = citation.doc_id;

    if (!grouped.has(key)) {
      grouped.set(key, {
        source_document: citation.source_document,
        doc_id: citation.doc_id,
        page_numbers: [],
      });
    }

    const existing = grouped.get(key)!;

    existing.page_numbers = [
      ...new Set([
        ...existing.page_numbers,
        ...citation.page_numbers,
      ]),
    ].sort((a, b) => a - b);
  }

  return Array.from(grouped.values());
}

export default function Home() {
  const [username, setUsername] = useState("gc.sharma");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState("");
  const [chatError, setChatError] = useState("");

  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [collections, setCollections] = useState<string[]>([]);

  const [queryType, setQueryType] = useState<"document" | "sql">("document");
  const [collectionName, setCollectionName] = useState("general");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  async function loadAuthenticatedUser(accessToken: string) {
    const headers = {
      Authorization: `Bearer ${accessToken}`,
    };

    const meResponse = await fetch(`${API_URL}/me`, { headers });

    if (!meResponse.ok) {
      throw new Error("Your session is invalid. Please sign in again.");
    }

    const meData = await meResponse.json();
    const authenticatedUser: User = meData.user;

    const collectionsResponse = await fetch(
      `${API_URL}/collections/${encodeURIComponent(authenticatedUser.role)}`,
      { headers }
    );

    if (!collectionsResponse.ok) {
      throw new Error("Unable to load your permitted collections.");
    }

    const collectionsData = await collectionsResponse.json();
    const permittedCollections: string[] = collectionsData.collections || [];

    setToken(accessToken);
    setUser(authenticatedUser);
    setCollections(permittedCollections);

    if (permittedCollections.length > 0) {
      setCollectionName(permittedCollections[0]);
    }
  }

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const savedToken = sessionStorage.getItem("counselbot_token");

      if (!savedToken) return;

      try {
        const headers = {
          Authorization: `Bearer ${savedToken}`,
        };

        const meResponse = await fetch(`${API_URL}/me`, { headers });

        if (!meResponse.ok) {
          throw new Error("Invalid session");
        }

        const meData = await meResponse.json();
        const authenticatedUser: User = meData.user;

        const collectionsResponse = await fetch(
          `${API_URL}/collections/${encodeURIComponent(authenticatedUser.role)}`,
          { headers }
        );

        if (!collectionsResponse.ok) {
          throw new Error("Unable to load collections");
        }

        const collectionsData = await collectionsResponse.json();

        if (!active) return;

        const permittedCollections: string[] =
          collectionsData.collections || [];

        setToken(savedToken);
        setUser(authenticatedUser);
        setCollections(permittedCollections);

        if (permittedCollections.length > 0) {
          setCollectionName(permittedCollections[0]);
        }
      } catch {
        sessionStorage.removeItem("counselbot_token");
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, []);

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }

      sessionStorage.setItem("counselbot_token", data.access_token);

      await loadAuthenticatedUser(data.access_token);
      setPassword("");
      setMessages([]);
    } catch (err) {
      sessionStorage.removeItem("counselbot_token");
      setToken("");
      setUser(null);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to CounselBot"
      );
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    sessionStorage.removeItem("counselbot_token");

    setToken("");
    setUser(null);
    setCollections([]);
    setMessages([]);
    setQuestion("");
    setPassword("");
    setError("");
    setChatError("");
  }

  async function handleAskQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!question.trim() || !token) return;

    setChatLoading(true);
    setChatError("");

    const submittedQuestion = question.trim();

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: submittedQuestion,
          collection_name: collectionName,
          query_type: queryType,
        }),
      });

      const data = await response.json();

      if (response.status === 401) {
        handleLogout();
        throw new Error("Your session expired. Please sign in again.");
      }

      if (!response.ok) {
        throw new Error(data.detail || "Unable to process your question");
      }

      setMessages((previous) => [
        ...previous,
        {
          question: submittedQuestion,
          answer: data.answer,
          status: data.status,
          citations: data.citations || [],
        },
      ]);

      setQuestion("");
    } catch (err) {
      setChatError(
        err instanceof Error
          ? err.message
          : "Unable to connect to CounselBot"
      );
    } finally {
      setChatLoading(false);
    }
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <section className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-white p-8 shadow-lg">
          <div className="mb-8">
            <p className="text-sm font-semibold tracking-widest text-blue-800">
              VERIDIAN LEGAL HUB
            </p>

            <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-900">
              CounselBot
            </h1>

            <p className="mt-2 text-slate-500">
              Secure internal legal document assistant
            </p>
          </div>

          <div className="mb-6 rounded-lg border border-blue-100 bg-blue-50 p-4">
            <p className="text-sm font-medium text-blue-900">
              Restricted access
            </p>
            <p className="mt-1 text-sm text-blue-800">
              Sign in with your assigned demo account to continue.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label
                htmlFor="username"
                className="mb-2 block text-sm font-semibold text-slate-700"
              >
                Demo user
              </label>

              <select
                id="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
              >
                {DEMO_USERS.map((demoUser) => (
                  <option key={demoUser} value={demoUser}>
                    {demoUser}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-semibold text-slate-700"
              >
                Password
              </label>

              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                required
                className="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-900 px-5 py-3 font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="mt-8 text-center text-xs text-slate-400">
            Demo environment · Access controlled by CounselBot API
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-4 md:p-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm">
          <div>
            <p className="text-xs font-semibold tracking-widest text-blue-800">
              VERIDIAN LEGAL HUB
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              CounselBot
            </h1>
            <p className="text-sm text-slate-500">
              Secure legal document assistant
            </p>
          </div>

          <button
            onClick={handleLogout}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Sign out
          </button>
        </header>

        <section className="mb-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-[var(--border)] bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Signed-in user
            </p>
            <p className="mt-2 font-semibold text-slate-900">{user.name}</p>
            <p className="mt-1 text-sm text-slate-500">{user.username}</p>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Role
            </p>
            <p className="mt-2 font-semibold text-slate-900">{user.role}</p>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Assigned matters
            </p>
            <p className="mt-2 font-semibold text-slate-900">
              {user.matters.length > 0
                ? user.matters.join(", ")
                : "No assigned matters"}
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">
              Ask CounselBot
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Your access is controlled by your authenticated role and matter assignments.
            </p>
          </div>

          <div className="mb-6">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Your permitted collections
            </p>

            <div className="flex flex-wrap gap-2">
              {collections.map((collection) => (
                <span
                  key={collection}
                  className="rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-900"
                >
                  {collection}
                </span>
              ))}
            </div>
          </div>

          <form onSubmit={handleAskQuestion} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label
                  htmlFor="queryType"
                  className="mb-2 block text-sm font-semibold text-slate-700"
                >
                  Query mode
                </label>

                <select
                  id="queryType"
                  value={queryType}
                  onChange={(event) =>
                    setQueryType(event.target.value as "document" | "sql")
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900"
                >
                  <option value="document">Document RAG</option>
                  <option value="sql">SQL RAG</option>
                </select>
              </div>

              {queryType === "document" && (
                <div>
                  <label
                    htmlFor="collection"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                  >
                    Document collection
                  </label>

                  <select
                    id="collection"
                    value={collectionName}
                    onChange={(event) => setCollectionName(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900"
                  >
                    {collections.map((collection) => (
                      <option key={collection} value={collection}>
                        {collection}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {queryType === "sql" && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                SQL access depends on your role. Matter-scoped database views
                enforce the permissions on the backend.
              </p>
            )}

            <div>
              <label
                htmlFor="question"
                className="mb-2 block text-sm font-semibold text-slate-700"
              >
                Your question
              </label>

              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a question about an accessible legal document or database..."
                rows={4}
                required
                className="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            {chatError && (
              <p role="alert" className="text-sm text-red-700">
                {chatError}
              </p>
            )}

            <button
              type="submit"
              disabled={chatLoading || !question.trim()}
              className="rounded-lg bg-blue-900 px-6 py-3 font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {chatLoading ? "Processing..." : "Ask CounselBot"}
            </button>
          </form>
        </section>

        {messages.length > 0 && (
          <section className="mt-6 space-y-5">
            <h2 className="text-xl font-bold text-slate-900">
              Conversation
            </h2>

            {messages.map((message, index) => {
              const grouped = groupCitations(message.citations);

              return (
                <article
                  key={`${index}-${message.question}`}
                  className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Your question
                  </p>
                  <p className="mt-2 font-medium text-slate-900">
                    {message.question}
                  </p>

                  <div className="my-5 border-t border-slate-100" />

                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      CounselBot answer
                    </p>

                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        message.status === "ok"
                          ? "bg-green-50 text-green-800"
                          : message.status === "role_restricted"
                            ? "bg-amber-50 text-amber-800"
                            : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {message.status}
                    </span>
                  </div>

                  <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-700">
                    {message.answer}
                  </p>

                  {grouped.length > 0 && (
                    <div className="mt-6 border-t border-slate-100 pt-4">
                      <h3 className="text-sm font-semibold text-slate-800">
                        Sources and citations
                      </h3>

                      <ul className="mt-3 space-y-2">
                        {grouped.map((citation) => (
                          <li
                            key={citation.doc_id}
                            className="rounded-lg bg-slate-50 p-3 text-sm"
                          >
                            <p className="font-medium text-slate-800">
                              {citation.source_document}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              Document ID: {citation.doc_id}
                            </p>
                            <p className="text-xs text-slate-500">
                              Pages:{" "}
                              {citation.page_numbers.length > 0
                                ? citation.page_numbers.join(", ")
                                : "Not available"}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </article>
              );
            })}
          </section>
        )}
      </div>
    </main>
  );
}