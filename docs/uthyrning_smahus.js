"use strict";

const byId = id => document.getElementById(id);
const numberText = value => value === null || value === undefined ? "–" : new Intl.NumberFormat("sv-SE").format(value);
const dateText = iso => iso ? new Intl.DateTimeFormat("sv-SE", {day:"numeric",month:"short",year:"numeric"}).format(new Date(iso + "T12:00:00")) : "–";

function populateRentalTable(snapshots) {
  const tbody = byId("rentalTableBody");
  tbody.replaceChildren();
  const columns = [
    row => dateText(row.snapshot),
    row => numberText(row.identified_unique_objects),
    row => numberText(row.ordinary_rental_objects),
    row => numberText(row.short_term_objects),
    row => numberText(row.full_address_objects),
    row => row.comparability_note || "–"
  ];
  for (const row of snapshots) {
    const tr = document.createElement("tr");
    for (const value of columns) {
      const td = document.createElement("td");
      td.textContent = value(row);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

function renderRental(data) {
  if (!Array.isArray(data.snapshots) || !data.snapshots.length) throw new Error("Inga aggregerade uppgifter finns tillgängliga.");
  const rows = [...data.snapshots].sort((a,b) => a.snapshot.localeCompare(b.snapshot));
  const last = rows[rows.length-1];

  byId("rentalUpdated").textContent = dateText(last.snapshot);
  byId("rentalTotal").textContent = numberText(last.identified_unique_objects);
  byId("rentalOrdinary").textContent = numberText(last.ordinary_rental_objects);
  byId("rentalShort").textContent = numberText(last.short_term_objects);
  byId("rentalFullAddress").textContent = numberText(last.full_address_objects);
  byId("rentalReviewed").textContent = numberText(data.reviewed_objects_in_master);
  populateRentalTable(rows);

  if (typeof Chart === "undefined") throw new Error("Diagramfunktionen kunde inte laddas. Tabellen ovan visar fortfarande uppgifterna.");
  const labels = rows.map(row => dateText(row.snapshot));
  const chartOptions = {
    responsive: true, maintainAspectRatio: false,
    interaction: {mode:"index", intersect:false},
    plugins: {legend: {position:"bottom"}},
    scales: {y: {beginAtZero:true, ticks: {precision:0}, title: {display:true,text:"Antal objekt"}}}
  };
  new Chart(byId("rentalTrend"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {label:"Identifierade unika objekt",data:rows.map(r=>r.identified_unique_objects),borderColor:"#00528c",backgroundColor:"#00528c",borderWidth:3,tension:0.16},
        {label:"Fullständig adress",data:rows.map(r=>r.full_address_objects),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",borderWidth:2,tension:0.16}
      ]
    },
    options: chartOptions
  });

  const split = rows.filter(r => r.ordinary_rental_objects !== null && r.short_term_objects !== null);
  new Chart(byId("rentalTypes"), {
    type: "bar",
    data: {
      labels: split.map(row => dateText(row.snapshot)),
      datasets: [
        {label:"Ordinarie uthyrning",data:split.map(r=>r.ordinary_rental_objects),backgroundColor:"#00528c",stack:"usage"},
        {label:"Korttidsuthyrning",data:split.map(r=>r.short_term_objects),backgroundColor:"#2e8bb7",stack:"usage"}
      ]
    },
    options: {...chartOptions,scales: {x:{stacked:true},y:{stacked:true,beginAtZero:true,ticks:{precision:0},title:{display:true,text:"Antal objekt"}}}}
  });
}

fetch("villa_rental_aggregates.json?v=1", {cache:"no-store"})
  .then(response => {if(!response.ok) throw new Error("Kunde inte hämta sammanställningen."); return response.json();})
  .then(renderRental)
  .catch(error => {
    console.error(error);
    const box = byId("rentalError");
    box.textContent = error.message;
    box.hidden = false;
  });
