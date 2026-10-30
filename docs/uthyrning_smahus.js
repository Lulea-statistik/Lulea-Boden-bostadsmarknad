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


// Webbplatsöverlappningen bygger enbart på offentlig, aggregerad JSON.
// Inga object_id, listing_id eller adresser ska skickas till webbläsaren.
(function () {
  "use strict";
  const E = (name, css, textValue) => {
    const el = document.createElement(name);
    if (css) el.className = css;
    if (textValue !== undefined) el.textContent = textValue;
    return el;
  };
  const S = (name, attributes) => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes || {})) el.setAttribute(key, String(value));
    return el;
  };
  const fmt = n => new Intl.NumberFormat("sv-SE").format(n);
  const pct = n => new Intl.NumberFormat("sv-SE", {maximumFractionDigits:1}).format(n * 100) + " %";
  const byName = new Map();
  const pairByName = new Map();
  let OVERLAP = null;

  const pairKey = (a, b) => [a,b].sort().join("\u0000");
  const shared = (a,b) => a===b ? byName.get(a).unique_objects : (pairByName.get(pairKey(a,b)) || 0);
  const union = (a,b) => byName.get(a).unique_objects + byName.get(b).unique_objects - shared(a,b);
  const jaccard = (a,b) => union(a,b) ? shared(a,b)/union(a,b) : 0;

  function validate(data) {
    const c = data.coverage || {};
    if (!Array.isArray(data.sites) || !data.sites.length || !Array.isArray(data.overlap_pairs) ||
        !Array.isArray(data.site_count_distribution)) throw new Error("Felaktigt format på aggregerat underlag.");
    if (!Number.isInteger(c.objects_with_listing_links) || c.objects_with_listing_links <= 0) throw new Error("Felaktig täckningsuppgift.");
    for (const site of data.sites) {
      if (!site.name || byName.has(site.name) || !Number.isInteger(site.unique_objects) || site.unique_objects < 0)
        throw new Error("Felaktiga webbplatsuppgifter.");
      byName.set(site.name, site);
    }
    for (const pair of data.overlap_pairs) {
      if (!byName.has(pair.site_a) || !byName.has(pair.site_b) || pair.site_a === pair.site_b ||
          !Number.isInteger(pair.shared_unique_objects) || pair.shared_unique_objects <= 0 ||
          pair.shared_unique_objects > Math.min(byName.get(pair.site_a).unique_objects,byName.get(pair.site_b).unique_objects) ||
          pairByName.has(pairKey(pair.site_a,pair.site_b))) throw new Error("Felaktigt webbplatspar i underlaget.");
      pairByName.set(pairKey(pair.site_a,pair.site_b),pair.shared_unique_objects);
    }
    const sumObjects = data.site_count_distribution.reduce((n,x)=>n+x.object_count,0);
    const sumLinked = data.site_count_distribution.reduce((n,x)=>n+x.site_count*x.object_count,0);
    if (sumObjects !== c.objects_with_listing_links || sumLinked !== c.distinct_site_object_links ||
        data.sites.reduce((n,x)=>n+x.unique_objects,0)!==sumLinked) throw new Error("Aggregaten går inte ihop.");
  }

  function matrix() {
    const sites=OVERLAP.sites, selected=byId("overlapSiteFilter").value;
    const isPercent=byId("overlapMatrixMode").value==="jaccard";
    const tbl=E("table","overlap-matrix");
    const thead=E("thead"), hrow=E("tr");
    hrow.append(E("th","","Webbplats"));
    for (const site of sites) {
      const th=E("th","overlap-column-head",site.name);
      th.scope="col";hrow.append(th);
    }
    thead.append(hrow); tbl.append(thead);
    const tbody=E("tbody");
    for(const siteA of sites) {
      const tr=E("tr"), header=E("th","overlap-row-head",siteA.name);header.scope="row";tr.append(header);
      for(const siteB of sites) {
        const n=shared(siteA.name,siteB.name);
        const percent=jaccard(siteA.name,siteB.name);
        const diagonal=siteA.name===siteB.name;
        const td=E("td",diagonal?"overlap-diagonal":"overlap-cell",isPercent?pct(percent):fmt(n));
        if (selected && siteA.name!==selected && siteB.name!==selected) td.classList.add("overlap-muted");
        if (!diagonal && n>0) td.style.setProperty("--cell-strength", String(0.08 + 0.36*percent));
        td.title = diagonal
          ? siteA.name + ": " + fmt(n) + " dokumenterade unika objekt"
          : siteA.name + " + " + siteB.name + ": " + fmt(n) + " gemensamma objekt; " + pct(percent) + " av unionen ("+fmt(union(siteA.name,siteB.name))+" objekt)";
        tr.append(td);
      }
      tbody.append(tr);
    }
    tbl.append(tbody);const host=byId("overlapMatrixWrap");host.replaceChildren(tbl);
  }

  function pairsTable() {
    const tbody=byId("overlapPairsBody");tbody.replaceChildren();
    const pairs=[...OVERLAP.overlap_pairs].sort((a,b)=>b.shared_unique_objects-a.shared_unique_objects || a.site_a.localeCompare(b.site_a,"sv"));
    for(const p of pairs) {
      const tr=E("tr");
      for(const value of [p.site_a,p.site_b,fmt(p.shared_unique_objects),pct(jaccard(p.site_a,p.site_b))])
        tr.append(E("td","",value));
      tbody.append(tr);
    }
  }

  function distribution() {
    const host=byId("overlapDistribution");host.replaceChildren();
    const rows=[...OVERLAP.site_count_distribution].sort((a,b)=>a.site_count-b.site_count);
    const max=Math.max(...rows.map(x=>x.object_count),1);
    for (const entry of rows) {
      const row=E("div","overlap-bar-row");
      const label=E("span","",entry.site_count+" "+(entry.site_count===1?"webbplats":"webbplatser"));
      const track=E("div","overlap-bar-track");
      const fill=E("div","overlap-bar-fill");
      fill.style.width=(100*entry.object_count/max)+"%";
      track.append(fill);
      row.append(label,track,E("strong","",fmt(entry.object_count)));
      host.append(row);
    }
  }

  function network() {
    const host=byId("overlapNetwork");host.replaceChildren();
    const sites=OVERLAP.sites, selected=byId("overlapSiteFilter").value;
    const svg=S("svg",{viewBox:"0 0 1020 510",role:"img","aria-label":"Nätverk över dokumenterade objekt som delas mellan webbplatser"});
    const title=S("title");title.textContent="Webbplatsöverlapppning – kantens tjocklek visar gemensamma objekt";svg.append(title);
    const positions=new Map(),cx=510,cy=252,rx=346,ry=174;
    sites.forEach((site,i)=>{
      const angle=(-Math.PI/2)+2*Math.PI*i/sites.length;
      positions.set(site.name,{x:cx+rx*Math.cos(angle),y:cy+ry*Math.sin(angle)});
    });
    const maxOverlap=Math.max(...OVERLAP.overlap_pairs.map(p=>p.shared_unique_objects),1);
    for(const pair of OVERLAP.overlap_pairs) {
      const a=positions.get(pair.site_a),b=positions.get(pair.site_b);
      const active=!selected || pair.site_a===selected || pair.site_b===selected;
      const line=S("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:active?"#2e8bb7":"#aab5c4",
        "stroke-width":(1.7+5*pair.shared_unique_objects/maxOverlap).toFixed(2),
        "stroke-linecap":"round",opacity:active?0.71:0.11});
      const tip=S("title");tip.textContent=pair.site_a+" / "+pair.site_b+": "+pair.shared_unique_objects+" gemensamma objekt ("+pct(jaccard(pair.site_a,pair.site_b))+")";line.append(tip);svg.append(line);
    }
    sites.forEach(site=>{
      const p=positions.get(site.name);
      const active=!selected || site.name===selected;
      const group=S("g",{class:"overlap-node",tabindex:"0",role:"button","aria-label":"Markera "+site.name});
      const circle=S("circle",{cx:p.x,cy:p.y,r:27,fill:site.name===selected?"#00528c":"#d8ecf8",
        stroke:"#00528c","stroke-width":active?3:1.4,opacity:active?1:0.45});
      const count=S("text",{x:p.x,y:p.y+5,"text-anchor":"middle",fill:site.name===selected?"#fff":"#00528c","font-size":"16","font-weight":"700"});
      count.textContent=String(site.unique_objects);
      const lab=S("text",{x:p.x,y:p.y+(p.y<cy?-43:51),"text-anchor":"middle","font-size":"14","font-weight":"600",fill:"#233449"});
      lab.textContent=site.name;
      const tip=S("title");tip.textContent=site.name+": "+site.unique_objects+" unika objekt; "+site.recorded_listings+" registrerade annonser";
      group.append(circle,count,lab,tip);
      const choose=()=>{byId("overlapSiteFilter").value=selected===site.name?"":site.name;refresh();};
      group.addEventListener("click",choose);
      group.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();choose();}});
      svg.append(group);
    });
    host.append(svg);
  }

  function refresh() {matrix();network();}

  async function load() {
    const response=await fetch("villa_site_overlap.json?v=1",{cache:"no-store"});
    if(!response.ok)throw new Error("Kunde inte läsa data för webbplatsöverlappning.");
    const data=await response.json();
    validate(data);OVERLAP=data;
    byId("overlapUnique").textContent=fmt(data.coverage.objects_with_listing_links);
    byId("overlapListings").textContent=fmt(data.coverage.recorded_listing_rows);
    byId("overlapSingle").textContent=fmt(data.coverage.unique_objects_single_site);
    byId("overlapMulti").textContent=fmt(data.coverage.unique_objects_multi_site);
    byId("overlapCoverage").textContent=
      "Täckning: "+fmt(data.coverage.objects_with_listing_links)+" objekt med annonskopplingar av "+
      fmt(data.coverage.reviewed_objects_in_master)+" särskilt granskade objekt och "+
      fmt(data.coverage.identified_objects_in_surveillance)+" identifierade i bevakningen (senaste sammanställning "+data.snapshot_date+"). "+
      fmt(data.coverage.recorded_listing_rows)+" registrerade annonser ger "+
      fmt(data.coverage.distinct_site_object_links)+" unika kombinationer av webbplats och objekt.";
    const select=byId("overlapSiteFilter");
    for(const s of data.sites){const opt=E("option","",s.name);opt.value=s.name;select.append(opt);}
    byId("overlapMatrixMode").addEventListener("change",refresh);
    select.addEventListener("change",refresh);
    pairsTable();distribution();refresh();
  }
  load().catch(err=>{console.error(err);const box=byId("overlapError");box.textContent=err.message;box.hidden=false;});
})();
