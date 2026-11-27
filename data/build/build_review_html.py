"""Sinh trang HTML tương tác độc lập để BS RHM duyệt nhanh 3 file CSV trong data/.

Tuân thủ modern-web-guidance (responsive-table, tabs, dark-mode).
Chỉ dùng thư viện chuẩn Python. Chạy từ thư mục gốc repo:
    python3 data/build/build_review_html.py
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUT_HTML = ROOT / "data" / "build" / "review_csv.html"


def _load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames or [])
        rows = [{c: (r.get(c) or "").strip() for c in cols} for r in reader]
        return cols, rows


def build_html() -> Path:
    cr_cols, cr_rows = _load_csv(DATA_DIR / "clinical_risk_rules.csv")
    ddi_cols, ddi_rows = _load_csv(DATA_DIR / "ddi_rules.csv")
    alias_cols, alias_rows = _load_csv(DATA_DIR / "entity_aliases.csv")
    # Thuốc phối hợp có nhiều dòng cùng alias → khoá duyệt phải là alias|canonical_id để không đè nhau.
    for r in alias_rows:
        r["_key"] = f"{r.get('alias', '')}|{r.get('canonical_id', '')}"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tables": {
            "cr": {"title": "Rủi ro lâm sàng (CR)", "cols": cr_cols, "rows": cr_rows, "keyCol": "rule_id"},
            "ddi": {"title": "Tương tác thuốc (DDI)", "cols": ddi_cols, "rows": ddi_rows, "keyCol": "rule_id"},
            "alias": {"title": "Từ điển thực thể (Aliases)", "cols": alias_cols, "rows": alias_rows, "keyCol": "_key"},
        },
    }
    json_safe = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    html = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Duyệt nhanh 3 bảng CSV lâm sàng RHM — Nhóm TDLN</title>
  <style>
    :root {{
      --bg-light: #f6f8fa;
      --bg-dark: #0f1419;
      --surface-light: #ffffff;
      --surface-dark: #182028;
      --surface-alt-light: #f0f4f8;
      --surface-alt-dark: #1f2933;
      --text-light: #17212b;
      --text-dark: #e6edf3;
      --muted-light: #52606d;
      --muted-dark: #9aa5b1;
      --border-light: #d9e2ec;
      --border-dark: #323f4b;
      --accent-light: #0f62fe;
      --accent-dark: #6ea8fe;
      --high-bg-light: #fde8e8;
      --high-bg-dark: #4c1d24;
      --high-fg-light: #9b1c1c;
      --high-fg-dark: #fca5a5;
      --mod-bg-light: #fef3c7;
      --mod-bg-dark: #422c0c;
      --mod-fg-light: #92400e;
      --mod-fg-dark: #fcd34d;
      --ok-bg-light: #def7ec;
      --ok-bg-dark: #123828;
      --ok-fg-light: #03543f;
      --ok-fg-dark: #6ee7b7;

      --bg: var(--bg-light);
      --surface: var(--surface-light);
      --surface-alt: var(--surface-alt-light);
      --text: var(--text-light);
      --muted: var(--muted-light);
      --border: var(--border-light);
      --accent: var(--accent-light);
      --high-bg: var(--high-bg-light);
      --high-fg: var(--high-fg-light);
      --mod-bg: var(--mod-bg-light);
      --mod-fg: var(--mod-fg-light);
      --ok-bg: var(--ok-bg-light);
      --ok-fg: var(--ok-fg-light);

      color-scheme: light dark;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: var(--bg-dark);
        --surface: var(--surface-dark);
        --surface-alt: var(--surface-alt-dark);
        --text: var(--text-dark);
        --muted: var(--muted-dark);
        --border: var(--border-dark);
        --accent: var(--accent-dark);
        --high-bg: var(--high-bg-dark);
        --high-fg: var(--high-fg-dark);
        --mod-bg: var(--mod-bg-dark);
        --mod-fg: var(--mod-fg-dark);
        --ok-bg: var(--ok-bg-dark);
        --ok-fg: var(--ok-fg-dark);
      }}
    }}

    @supports (color: light-dark(white, black)) {{
      :root {{
        --bg: light-dark(var(--bg-light), var(--bg-dark));
        --surface: light-dark(var(--surface-light), var(--surface-dark));
        --surface-alt: light-dark(var(--surface-alt-light), var(--surface-alt-dark));
        --text: light-dark(var(--text-light), var(--text-dark));
        --muted: light-dark(var(--muted-light), var(--muted-dark));
        --border: light-dark(var(--border-light), var(--border-dark));
        --accent: light-dark(var(--accent-light), var(--accent-dark));
        --high-bg: light-dark(var(--high-bg-light), var(--high-bg-dark));
        --high-fg: light-dark(var(--high-fg-light), var(--high-fg-dark));
        --mod-bg: light-dark(var(--mod-bg-light), var(--mod-bg-dark));
        --mod-fg: light-dark(var(--mod-fg-light), var(--mod-fg-dark));
        --ok-bg: light-dark(var(--ok-bg-light), var(--ok-bg-dark));
        --ok-fg: light-dark(var(--ok-fg-light), var(--ok-fg-dark));
      }}
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 1rem 1.25rem 2.5rem;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    .container {{ max-width: 1440px; margin: 0 auto; }}
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-end;
      gap: 1rem;
      margin-bottom: 1rem;
    }}
    h1 {{ font-size: 1.35rem; margin: 0 0 0.25rem; }}
    .subtitle {{ color: var(--muted); font-size: 0.9rem; margin: 0; }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      font-size: 0.85rem;
    }}
    .stat-pill {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 0.3rem 0.75rem;
      font-weight: 600;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.65rem;
      align-items: center;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem;
      margin-bottom: 0.9rem;
    }}
    .toolbar input[type="search"], .toolbar select {{
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.45rem 0.65rem;
      font-size: 0.9rem;
    }}
    .toolbar input[type="search"] {{ flex: 1 1 240px; min-width: 180px; }}
    button {{
      font: inherit;
      cursor: pointer;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: var(--surface-alt);
      color: var(--text);
      padding: 0.45rem 0.75rem;
      font-size: 0.85rem;
    }}
    button.primary {{
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
      font-weight: 600;
    }}
    button:focus-visible, input:focus-visible, select:focus-visible, .table-wrapper:focus-visible {{
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }}

    /* Tabs (modern-web-guidance: single non-wrapping row, underline via border) */
    [role="tablist"] {{
      display: flex;
      overflow-x: auto;
      gap: 0.25rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 0.75rem;
    }}
    [role="tab"] {{
      position: relative;
      flex: none;
      background: transparent;
      border: none;
      border-radius: 6px 6px 0 0;
      padding: 0.65rem 1rem;
      font-size: 0.92rem;
      font-weight: 600;
      color: var(--muted);
    }}
    [role="tab"][aria-selected="true"] {{
      color: var(--accent);
    }}
    [role="tab"][aria-selected="true"]::after {{
      content: "";
      position: absolute;
      inset: auto 0 0;
      border-block-end: 3px solid var(--accent);
    }}

    /* Không đặt padding/border/margin lên chính [role="tabpanel"] để tương thích hidden="until-found" */
    .panel-body {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem;
    }}
    .panel-meta {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.6rem;
      font-size: 0.85rem;
      color: var(--muted);
    }}

    /* Responsive Table (modern-web-guidance: sticky headers + @container stacked cards) */
    .table-wrapper {{
      overflow: auto;
      max-inline-size: 100%;
      max-block-size: min(700px, 70vh);
      container-type: inline-size;
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      font-size: 0.86rem;
    }}
    caption {{
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip-path: inset(50%);
    }}
    thead {{
      position: sticky;
      inset-block-start: 0;
      z-index: 2;
    }}
    thead th {{
      background: var(--surface-alt);
      color: var(--text);
      text-align: left;
      padding: 0.55rem 0.6rem;
      border-bottom: 2px solid var(--border);
      white-space: nowrap;
      font-weight: 700;
    }}
    tbody td, tbody th {{
      padding: 0.55rem 0.6rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    tbody th {{
      position: sticky;
      inset-inline-start: 0;
      z-index: 1;
      background: var(--surface);
      text-align: left;
      font-weight: 700;
      white-space: nowrap;
    }}
    tr.status-ok td, tr.status-ok th {{
      background: var(--ok-bg);
    }}
    tr.status-fix td, tr.status-fix th {{
      background: var(--high-bg);
    }}
    .badge {{
      display: inline-block;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-size: 0.78rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    .badge-HIGH {{ background: var(--high-bg); color: var(--high-fg); }}
    .badge-MODERATE {{ background: var(--mod-bg); color: var(--mod-fg); }}
    .badge-warn {{ background: var(--mod-bg); color: var(--mod-fg); margin-top: 0.25rem; }}
    .review-cell {{ min-width: 195px; }}
    .btn-row {{ display: flex; gap: 0.3rem; margin-bottom: 0.35rem; flex-wrap: wrap; }}
    .btn-mini {{ padding: 0.22rem 0.5rem; font-size: 0.78rem; }}
    .btn-mini.active-ok {{ background: var(--ok-fg); color: #fff; border-color: var(--ok-fg); }}
    .btn-mini.active-fix {{ background: var(--high-fg); color: #fff; border-color: var(--high-fg); }}
    .note-input {{
      width: 100%;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 0.28rem 0.4rem;
      font-size: 0.8rem;
    }}
    .toast {{
      font-size: 0.84rem;
      color: var(--ok-fg);
      font-weight: 600;
      min-height: 1.2em;
    }}

    @container (width < 720px) {{
      table, thead, tbody, tr, th, td {{ display: block; }}
      thead {{ display: none; }}
      tr {{
        margin-block-end: 0.9rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
      }}
      tbody th {{
        position: sticky;
        inset-block-start: 0;
        z-index: 2;
        background: var(--surface-alt);
      }}
      td::before {{
        content: attr(data-label) ": ";
        font-weight: 700;
        color: var(--muted);
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Duyệt nhanh 3 bảng dữ liệu lâm sàng RHM</h1>
        <p class="subtitle">Trạng thái duyệt lưu tự động trong trình duyệt (localStorage). Lọc <strong>"Cần kiểm nguồn"</strong> để ưu tiên kiểm các dòng có ghi chú <code>[cần BS...]</code> / <code>[BS Trung duyệt]</code>.</p>
      </div>
      <div class="stats" id="global-stats"></div>
    </header>

    <div class="toolbar">
      <input type="search" id="search-box" placeholder="Tìm tên thuốc, biệt dược, rule_id, nguồn (không cần gõ dấu)..." aria-label="Tìm kiếm">
      <select id="severity-filter" aria-label="Lọc mức độ">
        <option value="ALL">Mức độ: Tất cả</option>
        <option value="HIGH">Chỉ HIGH</option>
        <option value="MODERATE">Chỉ MODERATE</option>
      </select>
      <select id="status-filter" aria-label="Lọc trạng thái duyệt">
        <option value="ALL">Trạng thái: Tất cả</option>
        <option value="PENDING">Chưa duyệt</option>
        <option value="NEEDS_CHECK">Cần kiểm nguồn</option>
        <option value="OK">Đã duyệt (Đạt)</option>
        <option value="FIX">Cần sửa</option>
      </select>
      <button type="button" id="btn-approve-visible" class="primary">✓ Duyệt các dòng đang lọc</button>
      <button type="button" id="btn-copy-fixes">Copy ghi chú cần sửa</button>
      <button type="button" id="btn-export-json">Tải JSON duyệt</button>
      <button type="button" id="btn-reset">Xoá trạng thái duyệt</button>
    </div>
    <div class="toast" id="toast" role="status" aria-live="polite"></div>

    <div role="tablist" aria-label="Các bảng dữ liệu CSV">
      <button type="button" role="tab" id="tab-cr" aria-selected="true" tabindex="0" data-tab="cr">Rủi ro lâm sàng (CR)</button>
      <button type="button" role="tab" id="tab-ddi" aria-selected="false" tabindex="-1" data-tab="ddi">Tương tác thuốc (DDI)</button>
      <button type="button" role="tab" id="tab-alias" aria-selected="false" tabindex="-1" data-tab="alias">Từ điển thực thể (Aliases)</button>
    </div>

    <div role="tabpanel" id="panel-cr" aria-labelledby="tab-cr" tabindex="0">
      <div class="panel-body">
        <div class="panel-meta"><span id="meta-cr"></span></div>
        <div tabindex="0" role="region" aria-labelledby="cap-cr" class="table-wrapper" id="wrap-cr"></div>
      </div>
    </div>

    <div role="tabpanel" id="panel-ddi" aria-labelledby="tab-ddi" hidden="until-found">
      <div class="panel-body">
        <div class="panel-meta"><span id="meta-ddi"></span></div>
        <div tabindex="0" role="region" aria-labelledby="cap-ddi" class="table-wrapper" id="wrap-ddi"></div>
      </div>
    </div>

    <div role="tabpanel" id="panel-alias" aria-labelledby="tab-alias" hidden="until-found">
      <div class="panel-body">
        <div class="panel-meta"><span id="meta-alias"></span></div>
        <div tabindex="0" role="region" aria-labelledby="cap-alias" class="table-wrapper" id="wrap-alias"></div>
      </div>
    </div>
  </div>

  <script id="csv-data" type="application/json">{json_safe}</script>
  <script>
    (function () {{
      const DATA = JSON.parse(document.getElementById("csv-data").textContent);
      const STORAGE_KEY = "tdln_rhm_csv_review_v1";
      let reviews = {{}};
      try {{
        reviews = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}") || {{}};
      }} catch (_e) {{
        reviews = {{}};
      }}

      const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
      const panels = {{
        cr: document.getElementById("panel-cr"),
        ddi: document.getElementById("panel-ddi"),
        alias: document.getElementById("panel-alias"),
      }};
      let activeTab = "cr";

      function norm(str) {{
        return (str || "")
          .toLowerCase()
          .normalize("NFD")
          .replace(/[\\u0300-\\u036f]/g, "")
          .replace(/đ/g, "d")
          .trim();
      }}

      function rowId(tabKey, row, idx) {{
        if (tabKey === "alias") return `alias:${{row.alias}}`;
        return `${{tabKey}}:${{row[DATA.tables[tabKey].keyCol] || idx}}`;
      }}

      function saveReviews() {{
        try {{
          localStorage.setItem(STORAGE_KEY, JSON.stringify(reviews));
        }} catch (_e) {{}}
        renderStats();
      }}

      function showToast(msg) {{
        const el = document.getElementById("toast");
        el.textContent = msg;
        clearTimeout(showToast._t);
        showToast._t = setTimeout(() => {{ el.textContent = ""; }}, 3000);
      }}

      function selectTab(tabKey, moveFocus) {{
        activeTab = tabKey;
        for (const tab of tabs) {{
          const isSel = tab.dataset.tab === tabKey;
          tab.setAttribute("aria-selected", String(isSel));
          tab.tabIndex = isSel ? 0 : -1;
          if (isSel && moveFocus) tab.focus();
          if (isSel) tab.scrollIntoView({{ block: "nearest", inline: "nearest" }});
        }}
        for (const [k, panel] of Object.entries(panels)) {{
          if (k === tabKey) {{
            panel.removeAttribute("hidden");
            panel.tabIndex = 0;
          }} else {{
            panel.setAttribute("hidden", "until-found");
            panel.removeAttribute("tabindex");
          }}
        }}
      }}

      tabs.forEach((tab, idx) => {{
        tab.addEventListener("click", () => selectTab(tab.dataset.tab, false));
        tab.addEventListener("keydown", (e) => {{
          let next = null;
          if (e.key === "ArrowRight") next = tabs[(idx + 1) % tabs.length];
          else if (e.key === "ArrowLeft") next = tabs[(idx - 1 + tabs.length) % tabs.length];
          else if (e.key === "Home") next = tabs[0];
          else if (e.key === "End") next = tabs[tabs.length - 1];
          if (next) {{
            e.preventDefault();
            selectTab(next.dataset.tab, true);
          }}
        }});
      }});

      for (const [k, panel] of Object.entries(panels)) {{
        panel.addEventListener("beforematch", () => selectTab(k, false));
      }}

      function getFilteredRows(tabKey) {{
        const tbl = DATA.tables[tabKey];
        const q = norm(document.getElementById("search-box").value);
        const sev = document.getElementById("severity-filter").value;
        const st = document.getElementById("status-filter").value;

        return tbl.rows
          .map((row, idx) => ({{ row, idx, id: rowId(tabKey, row, idx) }}))
          .filter(({{ row, id }}) => {{
            if (sev !== "ALL" && row.severity && row.severity !== sev) return false;
            if (sev !== "ALL" && !row.severity) return false;

            const rev = reviews[id] || {{ status: "", note: "" }};
            const needsCheck = /\\[cần BS|\\[BS Trung/i.test(row.source || "");
            if (st === "PENDING" && rev.status) return false;
            if (st === "OK" && rev.status !== "ok") return false;
            if (st === "FIX" && rev.status !== "fix") return false;
            if (st === "NEEDS_CHECK" && !needsCheck) return false;

            if (q) {{
              const hay = norm(Object.values(row).join(" "));
              if (!hay.includes(q)) return false;
            }}
            return true;
          }});
      }}

      function renderTable(tabKey) {{
        const tbl = DATA.tables[tabKey];
        const wrap = document.getElementById(`wrap-${{tabKey}}`);
        const meta = document.getElementById(`meta-${{tabKey}}`);
        const filtered = getFilteredRows(tabKey);

        meta.textContent = `Đang hiển thị ${{filtered.length}} / ${{tbl.rows.length}} dòng`;
        wrap.textContent = "";

        const table = document.createElement("table");
        const caption = document.createElement("caption");
        caption.id = `cap-${{tabKey}}`;
        caption.textContent = tbl.title;
        table.appendChild(caption);

        const thead = document.createElement("thead");
        const headRow = document.createElement("tr");
        const thRev = document.createElement("th");
        thRev.textContent = "Duyệt BS";
        headRow.appendChild(thRev);
        for (const col of tbl.cols) {{
          const th = document.createElement("th");
          th.textContent = col;
          headRow.appendChild(th);
        }}
        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        for (const {{ row, id }} of filtered) {{
          const tr = document.createElement("tr");
          const rev = reviews[id] || {{ status: "", note: "" }};
          if (rev.status === "ok") tr.classList.add("status-ok");
          if (rev.status === "fix") tr.classList.add("status-fix");

          // Sticky first column (Duyệt + mã)
          const thAction = document.createElement("th");
          thAction.scope = "row";
          thAction.className = "review-cell";

          const btnRow = document.createElement("div");
          btnRow.className = "btn-row";

          const bOk = document.createElement("button");
          bOk.type = "button";
          bOk.className = "btn-mini" + (rev.status === "ok" ? " active-ok" : "");
          bOk.textContent = "✓ Đạt";
          bOk.addEventListener("click", () => {{
            const cur = reviews[id] || {{ status: "", note: "" }};
            cur.status = cur.status === "ok" ? "" : "ok";
            reviews[id] = cur;
            saveReviews();
            renderTable(tabKey);
          }});

          const bFix = document.createElement("button");
          bFix.type = "button";
          bFix.className = "btn-mini" + (rev.status === "fix" ? " active-fix" : "");
          bFix.textContent = "✎ Sửa";
          bFix.addEventListener("click", () => {{
            const cur = reviews[id] || {{ status: "", note: "" }};
            cur.status = cur.status === "fix" ? "" : "fix";
            reviews[id] = cur;
            saveReviews();
            renderTable(tabKey);
          }});

          btnRow.appendChild(bOk);
          btnRow.appendChild(bFix);
          thAction.appendChild(btnRow);

          const noteInput = document.createElement("input");
          noteInput.type = "text";
          noteInput.className = "note-input";
          noteInput.placeholder = "Ghi chú sửa...";
          noteInput.value = rev.note || "";
          noteInput.setAttribute("aria-label", `Ghi chú cho ${{id}}`);
          noteInput.addEventListener("input", () => {{
            const cur = reviews[id] || {{ status: "", note: "" }};
            cur.note = noteInput.value;
            if (cur.note.trim() && !cur.status) {{
              cur.status = "fix";
              tr.classList.add("status-fix");
              bFix.classList.add("active-fix");
            }}
            reviews[id] = cur;
            saveReviews();
          }});
          thAction.appendChild(noteInput);
          tr.appendChild(thAction);

          for (const col of tbl.cols) {{
            const td = document.createElement("td");
            td.dataset.label = col;
            const val = row[col] || "";
            if (col === "severity" && val) {{
              const sp = document.createElement("span");
              sp.className = `badge badge-${{val}}`;
              sp.textContent = val;
              td.appendChild(sp);
            }} else if (col === "source" && /\\[cần BS|\\[BS Trung/i.test(val)) {{
              td.appendChild(document.createTextNode(val));
              td.appendChild(document.createElement("br"));
              const warn = document.createElement("span");
              warn.className = "badge badge-warn";
              warn.textContent = "Cần kiểm nguồn";
              td.appendChild(warn);
            }} else {{
              td.textContent = val;
            }}
            tr.appendChild(td);
          }}
          tbody.appendChild(tr);
        }}
        table.appendChild(tbody);
        wrap.appendChild(table);
      }}

      function renderStats() {{
        const statsEl = document.getElementById("global-stats");
        statsEl.textContent = "";
        let total = 0, ok = 0, fix = 0;
        for (const [tabKey, tbl] of Object.entries(DATA.tables)) {{
          tbl.rows.forEach((row, idx) => {{
            total += 1;
            const rev = reviews[rowId(tabKey, row, idx)];
            if (rev?.status === "ok") ok += 1;
            if (rev?.status === "fix") fix += 1;
          }});
        }}
        const items = [
          `CR: ${{DATA.tables.cr.rows.length}}`,
          `DDI: ${{DATA.tables.ddi.rows.length}}`,
          `Alias: ${{DATA.tables.alias.rows.length}}`,
          `Đã duyệt: ${{ok}}/${{total}}`,
          `Cần sửa: ${{fix}}`,
        ];
        for (const text of items) {{
          const s = document.createElement("span");
          s.className = "stat-pill";
          s.textContent = text;
          statsEl.appendChild(s);
        }}
      }}

      function renderAllTables() {{
        renderTable("cr");
        renderTable("ddi");
        renderTable("alias");
        renderStats();
      }}

      document.getElementById("search-box").addEventListener("input", renderAllTables);
      document.getElementById("severity-filter").addEventListener("change", renderAllTables);
      document.getElementById("status-filter").addEventListener("change", renderAllTables);

      document.getElementById("btn-approve-visible").addEventListener("click", () => {{
        const filtered = getFilteredRows(activeTab);
        for (const {{ id }} of filtered) {{
          const cur = reviews[id] || {{ status: "", note: "" }};
          if (cur.status !== "fix") cur.status = "ok";
          reviews[id] = cur;
        }}
        saveReviews();
        renderTable(activeTab);
        showToast(`Đã đánh dấu Đạt cho ${{filtered.length}} dòng ở tab hiện tại.`);
      }});

      document.getElementById("btn-copy-fixes").addEventListener("click", async () => {{
        const lines = [];
        for (const [tabKey, tbl] of Object.entries(DATA.tables)) {{
          tbl.rows.forEach((row, idx) => {{
            const id = rowId(tabKey, row, idx);
            const rev = reviews[id];
            if (rev && (rev.status === "fix" || (rev.note || "").trim())) {{
              const keyLabel = row[tbl.keyCol] || id;
              lines.push(`- [${{tabKey.toUpperCase()}} · ${{keyLabel}}] (${{rev.status || "note"}}): ${{rev.note || "(chưa ghi chi tiết)"}}`);
            }}
          }});
        }}
        const out = lines.length ? lines.join("\\n") : "Không có dòng nào đánh dấu cần sửa.";
        try {{
          await navigator.clipboard.writeText(out);
          showToast(`Đã copy ${{lines.length}} mục cần sửa vào clipboard.`);
        }} catch (_e) {{
          prompt("Copy danh sách cần sửa:", out);
        }}
      }});

      document.getElementById("btn-export-json").addEventListener("click", () => {{
        const blob = new Blob([JSON.stringify(reviews, null, 2)], {{ type: "application/json" }});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "csv_review_notes.json";
        a.click();
        URL.revokeObjectURL(a.href);
      }});

      document.getElementById("btn-reset").addEventListener("click", () => {{
        if (!confirm("Xoá toàn bộ dấu duyệt và ghi chú đã lưu trong trình duyệt?")) return;
        reviews = {{}};
        saveReviews();
        renderAllTables();
        showToast("Đã xoá trạng thái duyệt.");
      }});

      renderAllTables();
    }})();
  </script>
</body>
</html>
"""

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"[OK] {OUT_HTML.relative_to(ROOT)} ({len(html)} bytes)")
    return OUT_HTML


if __name__ == "__main__":
    build_html()
