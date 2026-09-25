// widget/cluster-view.js
(function () {
  let plotDivId = null;
  let layoutData = null;

  window.__immunolitHighlightPmids = function (pmids) {
    if (!plotDivId || !layoutData) return;
    const pmidSet = new Set(pmids);
    const colors = Object.keys(layoutData).map((pmid) =>
      pmidSet.has(pmid) ? "#ff5722" : "#888"
    );
    const sizes = Object.keys(layoutData).map((pmid) => (pmidSet.has(pmid) ? 14 : 6));
    Plotly.restyle(plotDivId, { "marker.color": [colors], "marker.size": [sizes] });
  };

  window.initImmunolitClusterView = async function (containerId, apiBaseUrl) {
    const root = document.getElementById(containerId);
    root.className = "immunolit-cluster-view";
    plotDivId = containerId;

    try {
      const resp = await fetch(`${apiBaseUrl}/api/graph/summary`);
      if (!resp.ok) throw new Error("no graph summary yet");
      const data = await resp.json();
      layoutData = data.layout;

      const pmids = Object.keys(layoutData);
      const trace = {
        x: pmids.map((p) => layoutData[p].x),
        y: pmids.map((p) => layoutData[p].y),
        text: pmids.map((p) => `${layoutData[p].title} (PMID ${p})`),
        mode: "markers",
        type: "scatter",
        marker: { size: 6, color: "#888" },
      };
      Plotly.newPlot(containerId, [trace], {
        title: "Corpus map (colored points = papers cited in your last answer)",
        height: 400,
      });
    } catch (err) {
      root.textContent = "Cluster view unavailable.";
    }
  };
})();
