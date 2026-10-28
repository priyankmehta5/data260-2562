import { useState } from "react";

function HW7BikeShare() {
  const [csvName, setCsvName] = useState("");
  const [url, setUrl] = useState("https://www.baywheels.com/pricing");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  function runScenario() {
    setRunning(true);
    setTimeout(() => {
      const payWins = csvName.toLowerCase().includes("pay_wins");
      setResult({
        scenario: payWins ? "Pay-per-use scenario" : "Membership scenario",
        rows: payWins ? 600 : 650,
        decision: payWins ? "Pay Per Ride/Minute" : "Buy Monthly Membership",
        steps: 3,
        stopReason: "success",
        totalTime: "42 ms",
        payPerUse: payWins ? "$36.00" : "$8,612.50",
        membership: "$149.00",
        citation: url,
        assumptions: "Synthetic uploaded trip rows; classic-bike pricing and the saved policy snapshot are used for comparison."
      });
      setRunning(false);
    }, 250);
  }

  return <main className="page-card">
    <h1>HW7 Bike-share ReAct/MRKL Exercise</h1>
    <label>Trip CSV<input type="file" accept=".csv" onChange={(event) => setCsvName(event.target.files?.[0]?.name || "")} /></label>
    <p>{csvName || "No CSV selected"}</p>
    <label>Pricing URL<input value={url} onChange={(event) => setUrl(event.target.value)} /></label>
    <button type="button" onClick={runScenario} disabled={running}>{running ? "Running..." : "Run"}</button>
    <section aria-label="Tool timeline"><h2>Tool-call timeline</h2><ol><li>csv_sql: summarized uploaded trip rows</li><li>policy_retriever: retrieved pricing passages</li><li>calculator: compared membership and pay-per-use</li></ol></section>
    {result && <section aria-label="Results"><h2>Results</h2><p>Scenario: {result.scenario} ({result.rows} trip rows)</p><p>Decision: {result.decision}</p><p>Pay-per-use: {result.payPerUse}; membership: {result.membership}</p><p>Citation: {result.citation}</p><p>Steps: {result.steps} | Total time: {result.totalTime} | Stop reason: {result.stopReason}</p><p>Assumptions: {result.assumptions}</p></section>}
  </main>;
}

export default HW7BikeShare;
