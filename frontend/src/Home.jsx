import { Link } from "react-router-dom";
import { useSelector } from "react-redux";
function Home({ user, onLogout }) {
  const { items: incidents, status, error } = useSelector((state) => state.incidents);
  return <main className="page"><header className="page-header"><div><h1>Municipal Transit Incidents</h1><p>Logged in as {user.name}</p></div><button onClick={onLogout}>Log out</button></header>
    <section className="card"><div className="section-heading"><h2>Incident Records</h2><Link className="button-link" to="/create">Create incident</Link></div>
      {status === "loading" && <p>Loading incidents...</p>}
      {incidents.length === 0 && status !== "loading" && <p>No incident records are available.</p>}
      {incidents.map((incident) => <article className="incident" key={incident.id}><div><h3>#{incident.id} - {incident.title}</h3><p>{incident.description}</p></div><div className="actions"><Link className="button-link" to={"/update/" + incident.id}>Update</Link><Link className="button-link danger" to={"/delete/" + incident.id}>Delete</Link></div></article>)}
      {error && <p className="error">{error}</p>}
    </section></main>;
}
export default Home;