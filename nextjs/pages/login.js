import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Toast } from "@/components/toast";

function responseMessage(detail) {
  if (Array.isArray(detail)) {
    return detail.map((issue) => issue.msg).filter(Boolean).join("; ");
  }
  return detail;
}

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(responseMessage(data.detail) || "Login failed");
      }

      const data = await response.json();
      localStorage.setItem("token", data.token);
      localStorage.setItem("email", data.email);
      router.push("/reader");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <div className="auth-side">
        <Link href="/" className="brand-lockup"><span className="brand-mark">B.</span><span>BIT<span className="brand-light">.MANGA</span></span></Link>
        <div className="auth-quote"><p>“A story can take you<br />somewhere new.”</p><span>YOUR NEXT CHAPTER IS WAITING</span></div>
        <div className="auth-side-art"><img src="https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1200&q=85" alt="Clouds parting over a mountain landscape" /></div>
      </div>
      <div className="auth-main">
        <div className="auth-mobile-brand"><Link href="/" className="brand-lockup"><span className="brand-mark">B.</span><span>BIT<span className="brand-light">.MANGA</span></span></Link></div>
        <Card className="auth-card">
        <CardHeader className="px-0 pt-0">
          <p className="eyebrow">A SHELF FULL OF WORLDS</p>
          <CardTitle className="auth-title">{mode === "login" ? "Welcome back." : "Find your people."}</CardTitle>
          <CardDescription>{mode === "login" ? "Sign in to pick up where your story left off." : "Create a free account. Your reading list comes with you."}</CardDescription>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                required
              />
            </div>

            {error && <p className="form-error" role="alert">{error}</p>}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
            </Button>
          </form>
          <p className="auth-switch">{mode === "login" ? "New to BIT.MANGA?" : "Already have an account?"}{" "}
            <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
              {mode === "login" ? "Create an account" : "Log in"}
            </button>
          </p>
          <p className="demo-note">Demo reader: demo@example.com · password<br />Admin: admin@example.com · admin123</p>
        </CardContent>
        </Card>
      </div>
      <Toast message={error} kind="error" />
    </main>
  );
}
