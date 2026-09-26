// widget/cluster-view.js
(function () {
  let plotDivId = null;
  let layoutData = null;
  let clusterInfo = null; // { [clusterId]: { count, topConcepts: [...] } }

  const CLUSTER_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"];
  const NOISE_COLOR = "#ccc";
  const NOISE_LABEL = "Uncategorized";

  function clusterColor(cluster) {
    if (cluster === -1 || cluster === undefined || cluster === null) return NOISE_COLOR;
    return CLUSTER_PALETTE[cluster % CLUSTER_PALETTE.length];
  }

  // Aggregate each cluster's per-paper `concepts` lists into a small set of
  // representative top terms, by simple frequency count across papers in
  // that cluster (no new dependency — this mirrors the TF-IDF top-k idea
  // server-side, just done client-side over already-fetched data).
  function computeClusterInfo(layout) {
    const byCluster = {};
    Object.values(layout).forEach((entry) => {
      const cid = entry.cluster;
      if (!byCluster[cid]) byCluster[cid] = { count: 0, termCounts: {} };
      byCluster[cid].count += 1;
      (entry.concepts || []).forEach((term) => {
        byCluster[cid].termCounts[term] = (byCluster[cid].termCounts[term] || 0) + 1;
      });
    });
    const info = {};
    Object.keys(byCluster).forEach((cid) => {
      const { count, termCounts } = byCluster[cid];
      const topConcepts = Object.entries(termCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([term]) => term);
      info[cid] = { count, topConcepts };
    });
    return info;
  }

  // Plotly hover labels don't wrap long single-line text on their own, so a
  // long title near the plot's edge runs off-screen. Break it into short
  // lines instead.
  function wrapText(text, maxLineLen) {
    const words = String(text).split(" ");
    const lines = [];
    let current = "";
    words.forEach((word) => {
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length > maxLineLen && current) {
        lines.push(current);
        current = word;
      } else {
        current = candidate;
      }
    });
    if (current) lines.push(current);
    return lines.join("<br>");
  }

  function clusterLabelText(cluster) {
    if (cluster === -1 || cluster === undefined || cluster === null) return NOISE_LABEL;
    const info = clusterInfo && clusterInfo[cluster];
    if (!info || !info.topConcepts.length) return `Cluster ${cluster}`;
    return info.topConcepts.join(", ");
  }

  function renderLegend(legendEl) {
    if (!clusterInfo) return;
    legendEl.innerHTML = "";
    const clusterIds = Object.keys(clusterInfo)
      .map(Number)
      .sort((a, b) => (a === -1 ? 1 : b === -1 ? -1 : a - b));
    clusterIds.forEach((cid) => {
      const info = clusterInfo[cid];
      const row = document.createElement("div");
      row.className = "immunolit-cluster-view__legend-item";
      const swatch = document.createElement("span");
      swatch.className = "immunolit-cluster-view__swatch";
      swatch.style.backgroundColor = clusterColor(cid);
      const label = document.createElement("span");
      label.textContent = `${clusterLabelText(cid)} (${info.count})`;
      row.appendChild(swatch);
      row.appendChild(label);
      legendEl.appendChild(row);
    });
  }

  window.__immunolitHighlightPmids = function (pmids) {
    if (!plotDivId || !layoutData) return;
    const pmidSet = new Set(pmids);
    const colors = Object.keys(layoutData).map((pmid) =>
      pmidSet.has(pmid) ? "#ff5722" : clusterColor(layoutData[pmid].cluster)
    );
    const sizes = Object.keys(layoutData).map((pmid) => (pmidSet.has(pmid) ? 14 : 6));
    Plotly.restyle(plotDivId, { "marker.color": [colors], "marker.size": [sizes] });
  };

  window.initImmunolitClusterView = async function (containerId, apiBaseUrl, themeColors) {
    const theme = themeColors || {};
    const plotBg = theme.plotBg || "#ffffff";
    const paperBg = theme.paperBg || "#ffffff";
    const fontColor = theme.fontColor || "#333333";
    const gridColor = theme.gridColor || "#e5e5e5";

    const root = document.getElementById(containerId);
    root.className = "immunolit-cluster-view";
    root.innerHTML = "";

    const plotEl = document.createElement("div");
    plotEl.id = `${containerId}-plot`;
    const legendEl = document.createElement("div");
    legendEl.className = "immunolit-cluster-view__legend";
    root.appendChild(plotEl);
    root.appendChild(legendEl);

    plotDivId = plotEl.id;

    try {
      const resp = await fetch(`${apiBaseUrl}/api/graph/summary`);
      if (!resp.ok) throw new Error("no graph summary yet");
      const data = await resp.json();
      layoutData = data.layout;
      clusterInfo = computeClusterInfo(layoutData);

      const pmids = Object.keys(layoutData);
      const trace = {
        x: pmids.map((p) => layoutData[p].x),
        y: pmids.map((p) => layoutData[p].y),
        text: pmids.map(
          (p) =>
            `${wrapText(layoutData[p].title, 42)}<br>PMID ${p}<br>Topic: ${wrapText(
              clusterLabelText(layoutData[p].cluster),
              42
            )}`
        ),
        hoverinfo: "text",
        mode: "markers",
        type: "scatter",
        marker: { size: 6, color: pmids.map((p) => clusterColor(layoutData[p].cluster)) },
      };
      Plotly.newPlot(plotEl.id, [trace], {
        title: { text: "Corpus map — colored by topic cluster (highlighted after a chat answer)", font: { color: fontColor } },
        height: 400,
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        font: { color: fontColor },
        xaxis: { gridcolor: gridColor, zerolinecolor: gridColor },
        yaxis: { gridcolor: gridColor, zerolinecolor: gridColor },
        hoverlabel: { align: "left", font: { size: 11 } },
        margin: { l: 40, r: 40, t: 40, b: 40 },
      });
      renderLegend(legendEl);
    } catch (err) {
      root.textContent = "Cluster view unavailable.";
    }
  };
})();
