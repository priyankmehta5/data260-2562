import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "./api";

function UpdateRecord({ pageTitle }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadIncident() {
      try {
        const response = await api.get(`/api/incidents/${id}`);
        setTitle(response.data.title);
        setDescription(response.data.description);
      } catch {
        setError("Unable to load incident");
      }
    }

    loadIncident();
  }, [id]);

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      await api.put(`/api/incidents/${id}`, {
        title,
        description,
      });

      navigate("/");
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to update incident"
      );
    }
  }

  return (
    <main className="page">
      <form className="card" onSubmit={handleSubmit}>
        <h1>{pageTitle}</h1>

        <label htmlFor="title">Incident title</label>
        <input
          id="title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          required
        />

        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(event) =>
            setDescription(event.target.value)
          }
          required
        />

        <div className="actions">
          <button type="submit">Save changes</button>
          <button
            type="button"
            className="secondary"
            onClick={() => navigate("/")}
          >
            Cancel
          </button>
        </div>

        {error && <p className="error">{error}</p>}
      </form>
    </main>
  );
}

export default UpdateRecord;