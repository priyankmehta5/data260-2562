import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import { fetchIncident, updateIncident } from "./incidentSlice";
function UpdateRecord({ pageTitle }) {
  const { id } = useParams(); const navigate = useNavigate(); const dispatch = useDispatch();
  const [title, setTitle] = useState(""); const [description, setDescription] = useState(""); const [error, setError] = useState("");
  useEffect(() => { dispatch(fetchIncident(id)).unwrap().then((item) => { setTitle(item.title); setDescription(item.description); }).catch(() => setError("Unable to load incident")); }, [dispatch, id]);
  async function handleSubmit(event) { event.preventDefault(); try { await dispatch(updateIncident({ id, changes: { title, description } })).unwrap(); navigate("/"); } catch (requestError) { setError(requestError?.message || "Unable to update incident"); } }
  return <main className="page"><form className="card" onSubmit={handleSubmit}><h1>{pageTitle}</h1><label htmlFor="title">Incident title</label><input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required /><label htmlFor="description">Description</label><textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} required /><div className="actions"><button type="submit">Save changes</button><button type="button" className="secondary" onClick={() => navigate("/")}>Cancel</button></div>{error && <p className="error">{error}</p>}</form></main>;
}
export default UpdateRecord;