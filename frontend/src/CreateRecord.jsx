import { useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { createIncident } from "./incidentSlice";
function CreateRecord({ pageTitle }) {
  const navigate = useNavigate(); const dispatch = useDispatch();
  const [title, setTitle] = useState(""); const [description, setDescription] = useState(""); const [error, setError] = useState("");
  async function handleSubmit(event) {
    event.preventDefault();
    try { await dispatch(createIncident({ title, description, incident_code: "WEB-" + Date.now(), severity: 1, agency_id: 1 })).unwrap(); navigate("/"); }
    catch (requestError) { setError(requestError?.message || "Unable to create incident"); }
  }
  return <main className="page"><form className="card" onSubmit={handleSubmit}><h1>{pageTitle}</h1><label htmlFor="title">Incident title</label><input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required /><label htmlFor="description">Description</label><textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} required /><div className="actions"><button type="submit">Create</button><button type="button" className="secondary" onClick={() => navigate("/")}>Cancel</button></div>{error && <p className="error">{error}</p>}</form></main>;
}
export default CreateRecord;