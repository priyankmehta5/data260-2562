import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import api from "./api";
import { fetchIncidents } from "./incidentSlice";
import CreateRecord from "./CreateRecord";
import DeleteRecord from "./DeleteRecord";
import Home from "./Home";
import Login from "./Login";
import UpdateRecord from "./UpdateRecord";
import HW7BikeShare from "./HW7BikeShare";
import "./App.css";
function App() {
  const dispatch = useDispatch();
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  useEffect(() => {
    const token = localStorage.getItem("hw7_access_token");
    if (!token) dispatch(fetchIncidents());
    async function checkSession() {
      try { setUser((await api.get("/api/session")).data); }
      catch { setUser(null); } finally { setCheckingSession(false); }
    }
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`;
      api.get("/auth/me")
        .then((response) => setUser(response.data))
        .catch(() => { localStorage.removeItem("hw7_access_token"); delete api.defaults.headers.common.Authorization; setUser(null); })
        .finally(() => setCheckingSession(false));
      return;
    }
    checkSession();
  }, [dispatch]);
  async function handleLogout() {
    if (localStorage.getItem("hw7_access_token")) {
      localStorage.removeItem("hw7_access_token");
      delete api.defaults.headers.common.Authorization;
    } else {
      await api.post("/api/logout");
    }
    setUser(null);
  }
  if (checkingSession) return <p className="status">Checking session...</p>;
  if (!user) return <Login onLogin={setUser} />;
  return <BrowserRouter><Routes>
    <Route path="/" element={<Home user={user} onLogout={handleLogout} />} />
    <Route path="/create" element={<CreateRecord pageTitle="Create Incident" />} />
    <Route path="/update/:id" element={<UpdateRecord pageTitle="Update Incident" />} />
    <Route path="/delete/:id" element={<DeleteRecord pageTitle="Delete Incident" />} />
    <Route path="/hw7/bikeshare" element={<HW7BikeShare />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></BrowserRouter>;
}
export default App;
