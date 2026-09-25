// widget/cluster-view.js
(function () {
  let plotDivId = null;
  let layoutData = null;

  const CLUSTER_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"];
  const NOISE_COLOR = "#ccc";

  function clusterColor(cluster) {
    if (cluster === -1 || cluster === undefined || cluster === null) return NOISE_COLOR;
    return CLUSTER_PALETTE[cluster % CLUSTER_PALETTE.length];
  }

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
        marker: { size: 6, color: pmids.map((p) => clusterColor(layoutData[p].cluster)) },
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
