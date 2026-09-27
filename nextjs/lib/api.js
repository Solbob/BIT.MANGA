import { useEffect, useState } from "react";
import { useRouter } from "next/router";

export function getToken() {
  return typeof window === "undefined" ? null : localStorage.getItem("token");
}

function responseMessage(detail) {
  if (Array.isArray(detail)) {
    return detail.map((issue) => issue.msg).filter(Boolean).join("; ");
  }
  return detail;
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(responseMessage(body.detail) || `Request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function useAuth(requiredRole) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      router.replace("/login");
      return null;
    }
    try {
      const profile = await apiFetch("/users/me");
      setUser(profile);
      setLoading(false);
      if (requiredRole && profile.role !== requiredRole && profile.role !== "admin") {
        router.replace("/reader");
      }
      return profile;
    } catch {
      localStorage.removeItem("token");
      localStorage.removeItem("email");
      setUser(null);
      setLoading(false);
      router.replace("/login");
      return null;
    }
  }

  useEffect(() => {
    refresh();
  }, [requiredRole, router]);

  return { user, setUser, loading, refresh };
}

export function signOut() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("token");
    localStorage.removeItem("email");
  }
}