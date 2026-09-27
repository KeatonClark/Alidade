function severityLabel(severity, counters) {
  if (severity === "error") {
    counters.errors++;
    return "Error";
  }
  if (severity === "warning") {
    counters.warnings++;
    return "Warning";
  }
  return "Unknown";
}

function statusFromCounts(error_count, warning_count) {
  if (error_count > 0)
    return "Errors Found";

  if (warning_count > 0)
    return "Warnings Only";

  return "Clean";
}

function renderStatusLine(container, error_count, warning_count) {
  const status = statusFromCounts(error_count, warning_count);
  const p = document.createElement("p");
  p.classList.add("kicad-status");
  p.textContent = `${status} — ${error_count} error(s), ${warning_count} warning(s)`;
  container.appendChild(p);
  return p;
}

function makeTable(container, data, options = {}) {
  const el = document.createElement("div");
  container.appendChild(el);
  return new Tabulator(el, {
    data: data,
    autoColumns: true,
    movableColumns: true,
    resizableColumns: true,
    layout: "fitColumns",
    ...options,
  });
}

function makeHeading(container, level, text) {
  const h = document.createElement(`h${level}`);
  h.textContent = text;
  container.appendChild(h);
  return h;
}

class DRCTable extends HTMLElement {
  async connectedCallback() {
    const src = this.dataset.src;

    const container = document.createElement("div");
    this.appendChild(container);

    const response = await fetch(src);

    if (!response.ok) {
      container.innerHTML = "Error Loading DRC";
      throw new Error(`Failed to load ${src}: ${response.status}`);
    }

    const drc = await response.json();

    if (drc["$schema"] !== "https://schemas.kicad.org/drc.v1.json") {
      container.innerHTML = "Error parsing DRC";
      throw new Error(`Schema is of unknown type ${drc["$schema"]}`);
    }

    const counters = {
      errors: 0,
      warnings: 0,
    };

    const data = [];

    const violations = [
      ...(drc.schematic_parity || []),
      ...(drc.unconnected_items || []),
      ...(drc.violations || [])
    ];

    for (const violation of violations) {
      const severity = severityLabel(violation.severity, counters);
      const details = (violation.items || [])
        .map(item =>
          `${item.description} @ (${item.pos.x}, ${item.pos.y})`
        ).join(", ");

      data.push({
        Severity: severity,
        Description: violation.description,
        Details: details
      });
    }

    renderStatusLine(container, counters.errors, counters.warnings);

    if (counters.errors || counters.warnings) {
      this.table = makeTable(container, data, {
        rowFormatter: (row) => {
          const rowData = row.getData();
          const el = row.getElement();
          if (rowData.Severity === "Warning") {
            el.classList.add("drc-warning")
          } else if (rowData.Severity === "Error") {
            el.classList.add("drc-error")
          }
        },
      });
    }
  }
}
customElements.define("drc-table", DRCTable);

class ERCTable extends HTMLElement {
  async connectedCallback() {
    const src = this.dataset.src;

    const container = document.createElement("div");
    this.appendChild(container);

    const response = await fetch(src);

    if (!response.ok) {
      container.innerHTML = "Error Loading ERC";
      throw new Error(`Failed to load ${src}: ${response.status}`);
    }

    const erc = await response.json();

    if (erc["$schema"] !== "https://schemas.kicad.org/erc.v1.json") {
      container.innerHTML = "Error parsing ERC";
      throw new Error(`Schema is of unknown type ${erc["$schema"]}`);
    }

    const counters = {
      errors: 0,
      warnings: 0,
    };

    const data = [];

    for (const sheet of erc.sheets || []) {
      const sheetName = sheet.path;
      for (const violation of sheet.violations || []) {
        const severity = severityLabel(violation.severity, counters);
        const details = (violation.items || [])
          .map(item =>
            `${item.description} @ (${item.pos.x}, ${item.pos.y})`
          ).join(", ");

        data.push({
          Severity: severity,
          Sheet: sheetName,
          Description: violation.description,
          Details: details
        });
      }
    }

    renderStatusLine(container, counters.errors, counters.warnings);

    if (counters.errors || counters.warnings) {
      this.table = makeTable(container, data, {
        rowFormatter: (row) => {
          const rowData = row.getData();
          const el = row.getElement();
          if (rowData.Severity === "Warning") {
            el.classList.add("erc-warning")
          } else if (rowData.Severity === "Error") {
            el.classList.add("erc-error")
          }
        },
      });
    }
  }
}
customElements.define("erc-table", ERCTable);

class PCBStats extends HTMLElement {
  async connectedCallback() {
    const src = this.dataset.src;

    const container = document.createElement("div");
    this.appendChild(container);

    const response = await fetch(src);

    if (!response.ok) {
      container.innerHTML = "Error Loading Stats";
      throw new Error(`Failed to load ${src}: ${response.status}`);
    }

    const stats = await response.json();

    const meta = stats.metadata || {};
    const board = stats.board || {};
    const pads = stats.pads || {};
    const vias = stats.vias || {};
    const components = stats.components || {};
    const drillHoles = stats.drill_holes || [];

    const metaP = document.createElement("p");
    metaP.innerHTML = `Board: <strong>${meta.board_name || "unknown"}</strong><br>Generator: ${meta.generator || "unknown"}`;
    container.appendChild(metaP);

    // Board
    makeHeading(container, 3, "Board");
    const boardRows = [
      { Metric: "Outline present", Value: board.has_outline },
      { Metric: "Dimensions", Value: `${board.width ?? "?"} x ${board.height ?? "?"}` },
      { Metric: "Thickness", Value: board.board_thickness ?? "?" },
      { Metric: "Min track width", Value: board.min_track_width ?? "?" },
      { Metric: "Min track clearance", Value: board.min_track_clearance ?? "?" },
      { Metric: "Min drill diameter", Value: board.min_drill_diameter ?? "?" },
      { Metric: "Front component density", Value: board.front_component_density ?? "?" },
      { Metric: "Back component density", Value: board.back_component_density ?? "?" },
    ];
    makeTable(container, boardRows);

    makeHeading(container, 3, "Components");
    const componentRows = [];
    for (const kind of ["tht", "smd", "unspecified", "total"]) {
      const c = components[kind] || {};
      const label = kind === "total" ? "Total" : kind.toUpperCase();
      componentRows.push({
        Type: label,
        Front: c.front ?? 0,
        Back: c.back ?? 0,
        Total: c.total ?? 0,
      });
    }
    makeTable(container, componentRows);

    makeHeading(container, 3, "Pads & Vias");
    const padViaRows = [
      { Metric: "Through-hole pads", Count: pads.through_hole ?? 0 },
      { Metric: "SMD pads", Count: pads.smd ?? 0 },
      { Metric: "Connector pads", Count: pads.connector ?? 0 },
      { Metric: "NPTH pads", Count: pads.npth ?? 0 },
      { Metric: "Castellated pads", Count: pads.castellated ?? 0 },
      { Metric: "Press-fit pads", Count: pads.press_fit ?? 0 },
      { Metric: "Through vias", Count: vias.through ?? 0 },
      { Metric: "Blind vias", Count: vias.blind ?? 0 },
      { Metric: "Buried vias", Count: vias.buried ?? 0 },
      { Metric: "Micro vias", Count: vias.micro ?? 0 },
    ];
    makeTable(container, padViaRows);

    makeHeading(container, 3, "Drill Holes");
    if (drillHoles.length) {
      const sorted = [...drillHoles].sort((a, b) => (b.count ?? 0) - (a.count ?? 0));
      let totalHoles = 0;
      const drillRows = sorted.map(hole => {
        const count = hole.count ?? 0;
        totalHoles += count;
        const isSquareRound = hole.shape === "Round" && hole.x_size === hole.y_size;
        const size = isSquareRound
          ? hole.x_size ?? "?"
          : `${hole.x_size ?? "?"} x ${hole.y_size ?? "?"}`;
        return {
          Count: count,
          Shape: hole.shape ?? "?",
          Size: size,
          Plated: hole.plated ? "Yes" : "No",
          Source: hole.source ?? "?",
          Layers: `${hole.start_layer ?? "?"} - ${hole.stop_layer ?? "?"}`,
        };
      });
      makeTable(container, drillRows);

      const totalP = document.createElement("p");
      totalP.innerHTML = `<strong>Total drill holes:</strong> ${totalHoles}`;
      container.appendChild(totalP);
    } else {
      const noneP = document.createElement("p");
      noneP.textContent = "No drill hole data found.";
      container.appendChild(noneP);
    }
  }
}
customElements.define("pcb-stats", PCBStats);

class BomElement extends HTMLElement {
  async connectedCallback() {
    const src = this.dataset.src;

    const container = document.createElement("div");
    this.appendChild(container);

    const response = await fetch(src);

    if (!response.ok) {
      throw new Error(`Failed to load ${src}: ${response.status}`);
    }

    const csv = await response.text();

    this.table = new Tabulator(container, {
      data: csv,
      importFormat: "csv",
      autoColumns: true,
      movableColumns: true,
      resizableColumns: true,
      layout: "fitColumns",

      autoColumnsDefinitions: {
        "LCSC Part #": {
          formatter: "link",
          formatterParams: {
            url: function(cell) {
              return "https://lcsc.com/product-detail/" +
                encodeURIComponent(cell.getValue()) + ".html";
            },
            target: "_blank",
          },
        },
      },
    });
  }
}

customElements.define("bom-table", BomElement);
