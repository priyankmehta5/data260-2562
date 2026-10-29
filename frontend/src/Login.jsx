import { useState } from "react";
import api from "./api";

function Login({ onLogin }) {
  const [email, setEmail] = useState("writer@example.com");
  const [password, setPassword] = useState("Transit2562!");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    try {
      try {
        const response = await api.post("/auth/login", { username: email, password });
        localStorage.setItem("hw7_access_token", response.data.access_token);
        api.defaults.headers.common.Authorization = `Bearer ${response.data.access_token}`;
        const currentUser = await api.get("/auth/me");
        onLogin(currentUser.data);
      } catch {
        const response = await api.post("/api/login", { email, password });
        onLogin(response.data);
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Login failed"
      );
    }
  }

  return (
    <main className="login-page">
      <form className="card login-form" onSubmit={handleSubmit}>
        <h1>Transit Incident Login</h1>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <button type="submit">Log in</button>

        {error && <p className="error">{error}</p>}
      </form>
    </main>
  );
}

export default Login;
