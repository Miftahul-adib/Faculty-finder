import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiPost } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("sl_token") || "");
  const [studentId, setStudentId] = useState(() => {
    const raw = localStorage.getItem("sl_student_id");
    return raw ? Number(raw) : null;
  });
  const [studentName, setStudentName] = useState(() => localStorage.getItem("sl_student_name") || "");

  useEffect(() => {
    if (token) localStorage.setItem("sl_token", token);
    else localStorage.removeItem("sl_token");
  }, [token]);

  useEffect(() => {
    if (studentId != null) localStorage.setItem("sl_student_id", String(studentId));
    else localStorage.removeItem("sl_student_id");
  }, [studentId]);

  useEffect(() => {
    if (studentName) localStorage.setItem("sl_student_name", studentName);
    else localStorage.removeItem("sl_student_name");
  }, [studentName]);

  const login = (data) => {
    setToken(data.token);
    setStudentId(data.student_id);
    setStudentName(data.name);
  };

  const logout = async () => {
    try {
      await apiPost("/auth/logout");
    } catch {
      /* best effort */
    }
    setToken("");
    setStudentId(null);
    setStudentName("");
  };

  const value = useMemo(
    () => ({ token, studentId, studentName, isLoggedIn: Boolean(token), login, logout }),
    [token, studentId, studentName]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
