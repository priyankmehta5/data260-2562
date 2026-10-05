import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import { deleteIncident, fetchIncident } from "./incidentSlice";
function DeleteRecord({ pageTitle }) {
  const { id } = useParams(); const navigate = useNavigate(); const dispatch = useDispatch();
  const [incident, setIncident] = useState(null); const [error, setError] = useState("");
  useEffect(() => { dispatch(fetchIncident(id)).unwrap().then(setIncident).catch(() => setError("Unable to load incident")); }, [dispatch, id]);
  async function handleDelete() { try { await dispatch(deleteIncident(id)).unwrap(); navigate("/"); } catch (requestError) { setError(requestError?.message || "Unable to delete incident"); } }
  return <main className="page"><section className="card"><h1>{pageTitle}</h1>{incident && <><h2>{incident.title}</h2><p>{incident.description}</p><div className="actions"><button className="danger" onClick={handleDelete}>Confirm delete</button><button className="secondary" onClick={() => navigate("/")}>Cancel</button></div></>}{error && <p className="error">{error}</p>}</section></main>;
}
export default DeleteRecord;