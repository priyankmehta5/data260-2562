import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "./api";

function CreateRecord({ pageTitle }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      await api.post("/api/incidents", {
        title,
        description,
      });

      navigate("/");
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to create incident"
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
          <button type="submit">Create</button>
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

export default CreateRecord;