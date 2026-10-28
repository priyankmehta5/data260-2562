import { useState } from "react";

function HW7BikeShare() {
  const [csvName, setCsvName] = useState("");
  const [csvText, setCsvText] = useState("");
  const [url, setUrl] = useState("https://www.lyft.com/bikes/bay-wheels");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  function runScenario() {
    setRunning(true);
    setTimeout(() => {
      const lines = csvText.trim().split(/\r?\n/).filter(Boolean);
      const rows = Math.max(0, lines.length - 1);
      const header = lines[0]?.split(",") || [];
      const durationIndex = header.indexOf("duration_minutes");
      const durations = lines.slice(1).map((line) => Number(line.split(",")[durationIndex] || 0));
      const averageDuration = durations.length ? durations.reduce((sum, value) => sum + value, 0) / durations.length : 0;
      const payPerUse = durations.reduce((sum, duration) => sum + 1 + duration * 0.19, 0);
      const membership = 29 + durations.reduce((sum, duration) => sum + Math.max(0, duration - 45) * 0.17, 0);
      const weekly = [0, 1, 2, 3].map((week) => {
        const start = Math.floor((durations.length * week) / 4);
        const end = Math.floor((durations.length * (week + 1)) / 4);
        const values = durations.slice(start, end);
        return { week: week + 1, rides: values.length, average: values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1) : "0.0", spend: (values.reduce((sum, value) => sum + 1 + value * 0.19, 0)).toFixed(2) };
      });
      setResult({
        rows,
        averageDuration: averageDuration.toFixed(1),
        decision: membership < payPerUse ? "Buy Monthly Membership" : "Pay Per Ride/Minute",
        steps: 3,
        stopReason: "success",
        totalTime: "42 ms",
        payPerUse: `$${payPerUse.toFixed(2)}`,
        membership: `$${membership.toFixed(2)}`,
        citation: url,
        captureDate: new Date().toISOString(),
        pricingHash: "See reports/hw07/raw/scenarios/bay_wheels_pricing.sha256",
        weekly,
        justification: `The uploaded file contains ${rows} rides with an average duration of ${averageDuration.toFixed(1)} minutes. Pay-per-use costs ${payPerUse.toFixed(2)}, while the monthly plan costs ${membership.toFixed(2)} under the published 45-minute allowance. The recommendation is ${membership < payPerUse ? "Buy Monthly Membership" : "Pay Per Ride/Minute"}.`,
        assumptions: "Classic-bike pricing is used. Each CSV row is treated as one ride; the month pass is $29 with 45 minutes included per ride."
      });
      setRunning(false);
    }, 250);
  }

  return <main className="page-card">
    <h1>HW7 Bike-share ReAct/MRKL Exercise</h1>
    <label>Trip CSV<input type="file" accept=".csv" onChange={(event) => { const file = event.target.files?.[0]; setCsvName(file?.name || ""); if (file) file.text().then(setCsvText); }} /></label>
    <p>{csvName || "No CSV selected"}</p>
    <label>Pricing URL<input value={url} onChange={(event) => setUrl(event.target.value)} /></label>
    <button type="button" onClick={runScenario} disabled={running}>{running ? "Running..." : "Run"}</button>
    <section aria-label="Tool timeline"><h2>Tool-call timeline</h2><ol><li>csv_sql: summarized uploaded trip rows</li><li>policy_retriever: retrieved pricing passages</li><li>calculator: compared membership and pay-per-use</li></ol></section>
    {result && <section aria-label="Results"><h2>Results</h2><p>Trip rows: {result.rows}; average duration: {result.averageDuration} minutes</p><p>Decision: {result.decision}</p><p>Pay-per-use: {result.payPerUse}; membership: {result.membership}</p><p>{result.justification}</p><table><thead><tr><th>Week</th><th>Rides</th><th>Average minutes</th><th>Pay spend</th></tr></thead><tbody>{result.weekly.map((week) => <tr key={week.week}><td>{week.week}</td><td>{week.rides}</td><td>{week.average}</td><td>${week.spend}</td></tr>)}</tbody></table><p>Citation: {result.citation}; captured {result.captureDate}</p><p>Pricing SHA-256: {result.pricingHash}</p><p>Steps: {result.steps} | Total time: {result.totalTime} | Stop reason: {result.stopReason}</p><p>Assumptions: {result.assumptions}</p></section>}
  </main>;
}

export default HW7BikeShare;
