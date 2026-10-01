import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "./api";

function DeleteRecord({ pageTitle }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [incident, setIncident] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadIncident() {
      try {
        const response = await api.get(`/api/incidents/${id}`);
        setIncident(response.data);
      } catch {
        setError("Unable to load incident");
      }
    }

    loadIncident();
  }, [id]);

  async function handleDelete() {
    try {
      await api.delete(`/api/incidents/${id}`);
      navigate("/");
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to delete incident"
      );
    }
  }

  return (
    <main className="page">
      <section className="card">
        <h1>{pageTitle}</h1>

        {incident && (
          <>
            <h2>{incident.title}</h2>
            <p>{incident.description}</p>

            <div className="actions">
              <button
                className="danger"
                onClick={handleDelete}
              >
                Confirm delete
              </button>

              <button
                className="secondary"
                onClick={() => navigate("/")}
              >
                Cancel
              </button>
            </div>
          </>
        )}

        {error && <p className="error">{error}</p>}
      </section>
    </main>
  );
}

export default DeleteRecord;