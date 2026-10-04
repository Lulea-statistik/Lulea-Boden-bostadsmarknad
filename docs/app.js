let DATA=null;
const charts={};
const $=id=>document.getElementById(id);
const fmtInt=v=>v===null||v===undefined||v===""?"–":new Intl.NumberFormat("sv-SE",{maximumFractionDigits:0}).format(Number(v));
const fmtMoney=v=>v===null||v===undefined||v===""?"–":new Intl.NumberFormat("sv-SE",{style:"currency",currency:"SEK",maximumFractionDigits:0}).format(Number(v));
const fmtPct=v=>v===null||v===undefined||v===""?"–":new Intl.NumberFormat("sv-SE",{maximumFractionDigits:1,signDisplay:"exceptZero"}).format(Number(v))+" %";
const fmtDate=s=>s?new Intl.DateTimeFormat("sv-SE",{year:"numeric",month:"short",day:"numeric"}).format(new Date(s+"T00:00:00")):"–";
const num=v=>v===""||v===null||v===undefined?null:Number(v);

function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id];}}
function makeChart(id,config){destroyChart(id);charts[id]=new Chart($(id),config);}
function selected(){return{kommun:$("municipality").value,bostadstyp:$("propertyType").value,period:$("period").value};}
function currentRows(){return DATA.maklar_current||[];}
function historyRows(){return DATA.maklar_history||[];}
function weeklyRows(){return DATA.listing_weekly||[];}
function scbRows(){return DATA.scb_newbuild||[];}
function scbHolidayRows(){return DATA.scb_holiday_house||[];}

function tabs(){
  document.querySelectorAll("#tabs button").forEach(btn=>btn.addEventListener("click",()=>{
    document.querySelectorAll("#tabs button").forEach(b=>b.classList.remove("active"));
    document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
    btn.classList.add("active");
    $("page-"+btn.dataset.page).classList.add("active");
    renderAll();
  }));
}

function setUpdated(){
  const dates=currentRows().map(r=>r.source_updated).filter(Boolean).sort();
  $("updated").innerHTML=dates.length?"Mäklarstatistik uppdaterad<br><strong>"+fmtDate(dates.at(-1))+"</strong>":"Ingen marknadsdata";
}

function overview(){
  const s=selected();
  const rows=currentRows().filter(r=>r.kommun===s.kommun&&r.bostadstyp===s.bostadstyp);
  $("overviewCards").innerHTML=rows.map(r=>{
    const change=r.prisutveckling_status==="OK"?fmtPct(r.prisutveckling_pct):(r.prisutveckling_status||"–");
    return '<article class="metric-card"><div class="period-title">'+r.period+'</div><h3>'+s.kommun+' · '+s.bostadstyp+'</h3><div class="metrics">'+
      '<div class="metric"><strong>'+fmtInt(r.pris_per_m2)+'</strong><span>kr/m²</span></div>'+
      '<div class="metric"><strong>'+fmtMoney(r.medelpris)+'</strong><span>medelpris</span></div>'+
      '<div class="metric"><strong>'+fmtInt(r.antal_salda)+'</strong><span>antal sålda</span></div>'+
      '<div class="metric"><strong>'+change+'</strong><span>prisutveckling</span></div></div></article>';
  }).join("");

  const comp=currentRows().filter(r=>r.bostadstyp===s.bostadstyp&&r.period===s.period);
  makeChart("overviewCompare",{type:"bar",data:{labels:comp.map(r=>r.kommun),datasets:[{label:"Kr/m²",data:comp.map(r=>num(r.pris_per_m2)),backgroundColor:["#00528c","#2e8bb7"]}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:false,ticks:{callback:v=>fmtInt(v)}}}}});
  makeChart("overviewSales",{type:"bar",data:{labels:comp.map(r=>r.kommun),datasets:[{label:"Antal sålda",data:comp.map(r=>num(r.antal_salda)),backgroundColor:["#00528c","#2e8bb7"]}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
}

function historyForSelection(){
  const s=selected();
  return historyRows().filter(r=>r.kommun===s.kommun&&r.bostadstyp===s.bostadstyp).sort((a,b)=>a.source_updated.localeCompare(b.source_updated));
}
function uniqueDates(rows){return [...new Set(rows.map(r=>r.source_updated))].sort();}
function valueBy(rows,date,period,field){const r=rows.find(x=>x.source_updated===date&&x.period===period);return r?num(r[field]):null;}

function historyCharts(){
  const rows=historyForSelection(),dates=uniqueDates(rows),labels=dates.map(fmtDate);
  const common={responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false}};
  makeChart("priceChange",{type:"line",data:{labels,datasets:[
    {label:"3 månader",data:dates.map(d=>valueBy(rows,d,"3 månader","prisutveckling_pct")),borderColor:"#00528c",backgroundColor:"#00528c",tension:.2},
    {label:"12 månader",data:dates.map(d=>valueBy(rows,d,"12 månader","prisutveckling_pct")),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.2}
  ]},options:{...common,scales:{y:{ticks:{callback:v=>v+" %"}}}}});
  makeChart("salesHistory",{type:"line",data:{labels,datasets:[
    {label:"3 månader",data:dates.map(d=>valueBy(rows,d,"3 månader","antal_salda")),borderColor:"#00528c",backgroundColor:"#00528c",tension:.2},
    {label:"12 månader",data:dates.map(d=>valueBy(rows,d,"12 månader","antal_salda")),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.2}
  ]},options:common});
  const period=$("period").value;
  makeChart("ppm2History",{type:"line",data:{labels,datasets:[{label:"Kr/m²",data:dates.map(d=>valueBy(rows,d,period,"pris_per_m2")),borderColor:"#00528c",backgroundColor:"#00528c",tension:.2}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>fmtInt(v)}}}}});
  makeChart("meanPriceHistory",{type:"line",data:{labels,datasets:[{label:"Medelpris",data:dates.map(d=>valueBy(rows,d,period,"medelpris")),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.2}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>fmtMoney(v)}}}}});
}

function compareChart(){
  const s=selected(),metric=$("compareMetric").value;
  const rows=currentRows().filter(r=>r.bostadstyp===s.bostadstyp&&r.period===s.period);
  const labels={pris_per_m2:"Kr/m²",medelpris:"Medelpris",antal_salda:"Antal sålda",prisutveckling_pct:"Prisutveckling"};
  makeChart("municipalityCompare",{type:"bar",data:{labels:rows.map(r=>r.kommun),datasets:[{label:labels[metric],data:rows.map(r=>num(r[metric])),backgroundColor:["#00528c","#2e8bb7"]}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:metric==="antal_salda",ticks:{callback:v=>metric==="prisutveckling_pct"?v+" %":metric==="medelpris"?fmtMoney(v):fmtInt(v)}}}}});
}

function weeklyFiltered(){
  const s=selected();
  return weeklyRows().filter(r=>r.kommun===s.kommun&&r.bostadstyp===s.bostadstyp).sort((a,b)=>a.snapshot_date.localeCompare(b.snapshot_date));
}
function weeklyCharts(){
  const rows=weeklyFiltered(),has=rows.length>0;
  document.querySelectorAll(".weekly-card").forEach(el=>el.style.display=has?"block":"none");
  const msg="Veckosnapshot-funktionen är klar, men ingen tillåten annonskälla är ännu ansluten. När data börjar komma in fylls diagrammen automatiskt.";
  $("weeklySupplyEmpty").textContent=has?"":msg;
  $("weeklyFlowsEmpty").textContent=has?"":msg;
  $("weeklySupplyEmpty").style.display=has?"none":"block";
  $("weeklyFlowsEmpty").style.display=has?"none":"block";
  if(!has)return;
  const labels=rows.map(r=>r.year_week||r.snapshot_date);
  const common={responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false}};
  makeChart("weeklySupply",{type:"line",data:{labels,datasets:[{label:"Aktiva objekt",data:rows.map(r=>num(r.active_objects)),borderColor:"#00528c",backgroundColor:"#00528c",tension:.15}]},options:{...common,plugins:{legend:{display:false}}}});
  makeChart("weeklyPrice",{type:"line",data:{labels,datasets:[{label:"Median utgångspris",data:rows.map(r=>num(r.median_asking_price)),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.15}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>fmtMoney(v)}}}}});
  makeChart("weeklyDays",{type:"line",data:{labels,datasets:[{label:"Median dagar",data:rows.map(r=>num(r.median_days_on_market)),borderColor:"#00528c",backgroundColor:"#00528c",tension:.15}]},options:{...common,plugins:{legend:{display:false}}}});
  makeChart("weeklyFlows",{type:"bar",data:{labels,datasets:[
    {label:"Nya objekt",data:rows.map(r=>num(r.new_objects)),backgroundColor:"#2e8bb7"},
    {label:"Försvunna objekt",data:rows.map(r=>num(r.removed_objects)),backgroundColor:"#6b7280"}
  ]},options:common});
  makeChart("weeklyNet",{type:"bar",data:{labels,datasets:[{label:"Nettoförändring",data:rows.map(r=>num(r.net_change)),backgroundColor:"#00528c"}]},options:{...common,plugins:{legend:{display:false}}}});
  makeChart("weeklyReductions",{type:"bar",data:{labels,datasets:[{label:"Prissänkningar",data:rows.map(r=>num(r.price_reductions)),backgroundColor:"#2e8bb7"}]},options:{...common,plugins:{legend:{display:false}}}});
}


function scbSetup(){
  const rows=scbRows();
  const has=rows.length>0;
  document.querySelectorAll(".scb-card").forEach(el=>el.style.display=has?"block":"none");
  $("scbEmpty").style.display=has?"none":"block";
  $("scbEmpty").textContent=has?"":"SCB-data är ännu inte hämtad. Kör workflowet Update SCB new-build prices.";
  if(!has)return;

  const regions=[...new Set(rows.map(r=>r.region).filter(Boolean))].sort();
  const priceTypes=[...new Set(rows.map(r=>r.price_type).filter(Boolean))].sort();

  const currentRegion=$("scbRegion").value;
  const currentPrice=$("scbPriceType").value;

  $("scbRegion").innerHTML=regions.map(v=>'<option>'+v+'</option>').join("");
  $("scbPriceType").innerHTML=priceTypes.map(v=>'<option>'+v+'</option>').join("");

  const preferred=regions.find(v=>/övre norrland/i.test(v)) || regions.find(v=>/norra/i.test(v)) || regions[0];
  $("scbRegion").value=regions.includes(currentRegion)?currentRegion:preferred;
  $("scbPriceType").value=priceTypes.includes(currentPrice)?currentPrice:(priceTypes[0]||"");

  scbCharts();
}

function scbSeries(measureNeedle){
  const region=$("scbRegion").value,priceType=$("scbPriceType").value;
  return scbRows()
    .filter(r=>r.region===region&&r.price_type===priceType&&r.measure.toLowerCase().includes(measureNeedle.toLowerCase()))
    .sort((a,b)=>Number(a.year)-Number(b.year));
}

function scbCharts(){
  if(!scbRows().length)return;
  const common={responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false}};
  const total=scbSeries("Totalt produktionspris");
  makeChart("scbTotalPrice",{type:"line",data:{labels:total.map(r=>r.year),datasets:[{label:"Totalt produktionspris, kr/m²",data:total.map(r=>num(r.value)),borderColor:"#00528c",backgroundColor:"#00528c",tension:.15}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>fmtInt(v)}}}}});

  const build=scbSeries("Byggnadspris");
  const land=scbSeries("Markpris");
  const years=[...new Set([...build.map(r=>r.year),...land.map(r=>r.year)])].sort((a,b)=>Number(a)-Number(b));
  const lookup=(rows,y)=>{const r=rows.find(x=>x.year===y);return r?num(r.value):null;};
  makeChart("scbCostParts",{type:"line",data:{labels:years,datasets:[
    {label:"Byggnadspris",data:years.map(y=>lookup(build,y)),borderColor:"#00528c",backgroundColor:"#00528c",tension:.15},
    {label:"Markpris",data:years.map(y=>lookup(land,y)),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.15}
  ]},options:{...common,scales:{y:{ticks:{callback:v=>fmtInt(v)}}}}});

  const area=scbSeries("Bostadsarea/lägenhet");
  makeChart("scbArea",{type:"line",data:{labels:area.map(r=>r.year),datasets:[{label:"m² per lägenhet",data:area.map(r=>num(r.value)),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.15}]},options:{...common,plugins:{legend:{display:false}}}});

  const dwell=scbSeries("Lägenheter, antal");
  makeChart("scbDwellings",{type:"bar",data:{labels:dwell.map(r=>r.year),datasets:[{label:"Antal lägenheter",data:dwell.map(r=>num(r.value)),backgroundColor:"#00528c"}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
}


function scbHolidaySetup(){
  const rows=scbHolidayRows();
  const has=rows.length>0;
  document.querySelectorAll(".scbholiday-card").forEach(el=>el.style.display=has?"block":"none");
  $("scbHolidayEmpty").style.display=has?"none":"block";
  $("scbHolidayEmpty").textContent=has?"":"SCB:s fritidshusdata är ännu inte hämtad. Kör workflowet Update SCB housing prices.";
  if(!has)return;

  const regions=[...new Set(rows.map(r=>r.region).filter(Boolean))].sort();
  const current=$("scbHolidayRegion").value;
  $("scbHolidayRegion").innerHTML=regions.map(v=>'<option>'+v+'</option>').join("");
  const preferred=regions.find(v=>/övre norrland/i.test(v)) || regions.find(v=>/norrland/i.test(v)) || regions[0];
  $("scbHolidayRegion").value=regions.includes(current)?current:preferred;
  scbHolidayCharts();
}

function scbHolidaySeries(measureNeedle){
  const region=$("scbHolidayRegion").value;
  return scbHolidayRows()
    .filter(r=>r.region===region&&r.measure.toLowerCase().includes(measureNeedle.toLowerCase()))
    .sort((a,b)=>a.quarter.localeCompare(b.quarter));
}

function scbHolidayCharts(){
  if(!scbHolidayRows().length)return;
  const common={responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false}};
  const price=scbHolidaySeries("Köpeskilling, medelvärde");
  const sales=scbHolidaySeries("Antal");
  const kt=scbHolidaySeries("Köpeskillingskoefficient");
  const tax=scbHolidaySeries("Bas-/taxeringsvärde");

  makeChart("scbHolidayPrice",{type:"line",data:{labels:price.map(r=>r.quarter),datasets:[{label:"Köpeskilling, tkr",data:price.map(r=>num(r.value)),borderColor:"#00528c",backgroundColor:"#00528c",tension:.15}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>fmtInt(v)}}}}});
  makeChart("scbHolidaySales",{type:"bar",data:{labels:sales.map(r=>r.quarter),datasets:[{label:"Antal",data:sales.map(r=>num(r.value)),backgroundColor:"#2e8bb7"}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
  makeChart("scbHolidayKT",{type:"line",data:{labels:kt.map(r=>r.quarter),datasets:[{label:"K/T-tal",data:kt.map(r=>num(r.value)),borderColor:"#2e8bb7",backgroundColor:"#2e8bb7",tension:.15}]},options:{...common,plugins:{legend:{display:false}}}});
  makeChart("scbHolidayTax",{type:"line",data:{labels:tax.map(r=>r.quarter),datasets:[{label:"Bas-/taxeringsvärde, tkr",data:tax.map(r=>num(r.value)),borderColor:"#00528c",backgroundColor:"#00528c",tension:.15}]},options:{...common,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>fmtInt(v)}}}}});
}

function coverage(){
  const h=historyRows(),w=weeklyRows(),dates=[...new Set(h.map(r=>r.source_updated).filter(Boolean))].sort();
  $("coverage").innerHTML='<table><tbody>'+
    '<tr><th>Mäklarstatistik – publiceringar</th><td>'+dates.length+'</td><td>'+(dates.length?fmtDate(dates[0])+" – "+fmtDate(dates.at(-1)):"–")+'</td></tr>'+
    '<tr><th>Mäklarstatistik – rader</th><td>'+h.length+'</td><td>Luleå + Boden</td></tr>'+
    '<tr><th>Veckosnapshots – indikatorrader</th><td>'+w.length+'</td><td>'+(w.length?"Aktiv":"Väntar på tillåten datakälla")+'</td></tr></tbody></table>';
  $("dataTable").innerHTML='<table><thead><tr><th>Kommun</th><th>Bostadstyp</th><th>Period</th><th>Kr/m²</th><th>Medelpris</th><th>Sålda</th><th>Prisutv.</th><th>Källdatum</th></tr></thead><tbody>'+
    currentRows().map(r=>'<tr><td>'+r.kommun+'</td><td>'+r.bostadstyp+'</td><td>'+r.period+'</td><td>'+fmtInt(r.pris_per_m2)+'</td><td>'+fmtMoney(r.medelpris)+'</td><td>'+fmtInt(r.antal_salda)+'</td><td>'+(r.prisutveckling_status==="OK"?fmtPct(r.prisutveckling_pct):r.prisutveckling_status)+'</td><td>'+fmtDate(r.source_updated)+'</td></tr>').join("")+
    '</tbody></table>';
}

function renderAll(){overview();historyCharts();compareChart();weeklyCharts();scbSetup();scbHolidaySetup();coverage();}
async function init(){
  DATA=await fetch("dashboard_data.json?v="+Date.now()).then(r=>{if(!r.ok)throw new Error("Kunde inte läsa dashboard_data.json");return r.json();});
  tabs();setUpdated();
  ["municipality","propertyType","period","compareMetric"].forEach(id=>$(id).addEventListener("change",renderAll));
  $("scbRegion").addEventListener("change",scbCharts);
  $("scbPriceType").addEventListener("change",scbCharts);
  $("scbHolidayRegion").addEventListener("change",scbHolidayCharts);
  $("resetFilters").addEventListener("click",()=>{$("municipality").value="Luleå";$("propertyType").value="Bostadsrätter";$("period").value="3 månader";$("compareMetric").value="pris_per_m2";renderAll();});
  renderAll();
}
init().catch(err=>{document.querySelector("main").innerHTML='<div class="empty-state">'+err.message+'</div>';console.error(err);});
