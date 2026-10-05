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
import "./App.css";
function App() {
  const dispatch = useDispatch();
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  useEffect(() => {
    dispatch(fetchIncidents());
    async function checkSession() {
      try { setUser((await api.get("/api/session")).data); }
      catch { setUser(null); } finally { setCheckingSession(false); }
    }
    checkSession();
  }, [dispatch]);
  async function handleLogout() { await api.post("/api/logout"); setUser(null); }
  if (checkingSession) return <p className="status">Checking session...</p>;
  if (!user) return <Login onLogin={setUser} />;
  return <BrowserRouter><Routes>
    <Route path="/" element={<Home user={user} onLogout={handleLogout} />} />
    <Route path="/create" element={<CreateRecord pageTitle="Create Incident" />} />
    <Route path="/update/:id" element={<UpdateRecord pageTitle="Update Incident" />} />
    <Route path="/delete/:id" element={<DeleteRecord pageTitle="Delete Incident" />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></BrowserRouter>;
}
export default App;