(() => {
  "use strict";

  const API = "/api";
  const page = document.body.dataset.page || "";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => {
      const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return map[character];
    });
  }

  function setText(selector, value) {
    const element = $(selector);
    if (element) element.textContent = value;
  }

  function money(value, { signed = false } = {}) {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    const formatted = new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Math.abs(number));
    if (signed) return `${number < 0 ? "−" : "+"}${formatted}`;
    return `${number < 0 ? "−" : ""}${formatted}`;
  }

  function compactMoney(value) {
    const number = Number(value) || 0;
    if (number >= 10000000) return `₹${(number / 10000000).toFixed(2)} Cr`;
    if (number >= 100000) return `₹${(number / 100000).toFixed(2)} L`;
    if (number >= 1000) return `₹${(number / 1000).toFixed(1)}k`;
    return money(number);
  }

  function formatDate(value) {
    if (!value) return "—";
    const text = String(value);
    const parsed = new Date(text.length === 10 ? `${text}T00:00:00` : text);
    if (Number.isNaN(parsed.getTime())) return text;
    return parsed.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function formatDateTime(value) {
    if (!value) return "—";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function relativeTime(value) {
    if (!value) return "";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "";
    const seconds = Math.max(1, Math.round((Date.now() - parsed.getTime()) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.round(hours / 24)}d ago`;
  }

  function maskAccount(value) {
    if (!value) return "—";
    const text = String(value);
    if (text.length <= 4) return text;
    return `•••• ${text.slice(-4)}`;
  }

  function initials(value) {
    const text = String(value || "?").trim();
    return text.slice(0, 2).toUpperCase();
  }

  function modeFromDescription(description) {
    const upper = String(description || "").toUpperCase();
    const modes = ["UPI", "NEFT", "IMPS", "RTGS", "ATM", "POS", "ACH", "BILLPAY", "EMI"];
    return modes.find((mode) => upper.includes(mode)) || "TXN";
  }

  function debounce(fn, wait = 220) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), wait);
    };
  }

  async function api(path, options = {}) {
    const response = await fetch(API + path, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
    if (!response.ok) {
      const message =
        (payload && payload.error && payload.error.message) ||
        `Request failed with status ${response.status}`;
      const failure = new Error(message);
      failure.payload = payload;
      failure.status = response.status;
      throw failure;
    }
    return payload;
  }

  function toast(message, kind = "info") {
    let root = $("#toast-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "toast-root";
      root.className = "siq-toast-root";
      document.body.appendChild(root);
    }
    const tones = {
      info: "border-slate-300 bg-white text-slate-800",
      success: "border-emerald-300 bg-emerald-50 text-emerald-900",
      error: "border-red-300 bg-red-50 text-red-900",
    };
    const icons = { info: "info", success: "check_circle", error: "error" };
    const element = document.createElement("div");
    element.className = `siq-toast ${tones[kind] || tones.info}`;
    element.innerHTML = `<span class="material-symbols-outlined text-[18px]">${icons[kind] || "info"}</span><span>${escapeHtml(message)}</span>`;
    root.appendChild(element);
    setTimeout(() => {
      element.classList.add("siq-toast-out");
      setTimeout(() => element.remove(), 260);
    }, 3800);
  }

  function closeMenus() {
    $$(".siq-menu").forEach((menu) => menu.remove());
  }

  function openMenu(anchor, items, onSelect) {
    closeMenus();
    const rect = anchor.getBoundingClientRect();
    const menu = document.createElement("div");
    menu.className = "siq-menu";
    menu.style.left = `${Math.min(rect.left, window.innerWidth - 256)}px`;
    menu.style.top = `${Math.min(rect.bottom + 6, window.innerHeight - 296)}px`;
    menu.innerHTML = items
      .map(
        (item) =>
          `<button type="button" class="siq-menu-item ${item.active ? "siq-menu-item-active" : ""}" data-value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</button>`
      )
      .join("");
    menu.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-value]");
      if (!button) return;
      closeMenus();
      onSelect(button.dataset.value);
    });
    document.body.appendChild(menu);
    setTimeout(() => {
      document.addEventListener("click", closeMenus, { once: true });
    }, 0);
  }

  function wireChrome() {
    const routes = {
      dashboard: "/",
      statements: "/",
      transactions: "/transactions",
      categories: "/categories",
      settings: "/categories",
    };
    $$("aside nav a[data-path]").forEach((link) => {
      const key = link.dataset.path;
      link.href = routes[key] || "#";
      link.classList.remove("bg-primary-container", "text-on-primary-container", "font-headline-sm");
      link.style.borderLeft = "";
      const reviewNav = document.body.dataset.nav || "transactions";
      const active =
        ((page === "dashboard" || page === "upload") && key === "dashboard") ||
        (page === "review" && key === reviewNav) ||
        (page === "categories" && key === "categories");
      if (active) {
        link.classList.add("bg-primary-container", "text-on-primary-container", "font-headline-sm");
        link.style.borderLeft = "3px solid #85f8c4";
      }
    });

    $$("button").forEach((button) => {
      const text = button.textContent.trim();
      if (text.includes("Upload Statement") && button.id !== "btn-upload-top") {
        button.addEventListener("click", () => {
          window.location.href = "/upload";
        });
      }
      if (button.dataset.action === "categories" || text.startsWith("Rules (")) {
        button.addEventListener("click", () => {
          window.location.href = "/categories";
        });
      }
    });

    const uploadButton = $("#btn-upload-top");
    if (uploadButton) {
      uploadButton.addEventListener("click", () => {
        window.location.href = "/upload";
      });
    }

    const globalSearch = $("header input[type=text]");
    if (globalSearch && page === "dashboard") {
      globalSearch.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        const search = $("#statement-search");
        if (search) {
          search.value = globalSearch.value;
          search.dispatchEvent(new Event("input"));
        }
      });
    }
  }

  function badgeStatus(statement) {
    if (statement.status === "failed") {
      return `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm"><span class="material-symbols-outlined text-label-sm">error</span>Failed</span>`;
    }
    if (statement.review_count > 0) {
      return `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm"><span class="material-symbols-outlined text-label-sm">warning</span>Needs Review (${statement.review_count})</span>`;
    }
    return `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-primary-fixed/40 text-on-primary-fixed-variant font-label-sm text-label-sm"><span class="material-symbols-outlined text-label-sm text-primary">check_circle</span>Reconciled</span>`;
  }

  function emptyRow(columnCount, message) {
    return `<tr><td colspan="${columnCount}" class="py-10 px-space-lg text-center text-on-surface-variant font-body-sm text-body-sm">${escapeHtml(message)}</td></tr>`;
  }

  // ---------------------------------------------------------------- dashboard
  async function initDashboard() {
    const state = { statements: [], categories: [], filter: "all", search: "" };
    const tbody = $("#statements-tbody");

    async function load() {
      try {
        const [stats, listing, categoryPayload] = await Promise.all([
          api("/stats"),
          api("/statements?limit=200"),
          api("/categories"),
        ]);
        state.statements = listing.items || [];
        state.categories = categoryPayload.categories || [];
        renderKpis(stats);
        renderTabs();
        renderTable();
        renderCategoryDistribution(stats);
        renderActivity(stats);
      } catch (error) {
        toast(error.message, "error");
      }
    }

    function renderKpis(stats) {
      setText("#kpi-statements", Number(stats.total_statements || 0).toLocaleString("en-IN"));
      setText("#kpi-transactions", Number(stats.total_transactions || 0).toLocaleString("en-IN"));
      setText("#kpi-classification", `${(Number(stats.classification_rate || 0) * 100).toFixed(1)}%`);
      setText("#kpi-review", Number(stats.needs_review || 0).toLocaleString("en-IN"));

      const volume = Number(stats.total_debit || 0) + Number(stats.total_credit || 0);
      setText("#kpi-volume", compactMoney(volume));
      setText(
        "#kpi-avg",
        stats.total_transactions
          ? `Avg ${compactMoney(volume / stats.total_transactions)} / txn`
          : "No transactions yet"
      );
      const processedCount = state.statements.filter((item) => item.status === "processed").length;
      setText("#kpi-statements-sub", `${processedCount} processed statements`);
      const trend = $("#kpi-statements-trend");
      if (trend) {
        trend.innerHTML = `<span class="material-symbols-outlined text-label-sm mr-0.5">trending_up</span>${processedCount} live statement${processedCount === 1 ? "" : "s"}`;
      }
      const statementBar = $("#kpi-statements-bar");
      if (statementBar) {
        statementBar.style.width = `${state.statements.length ? (processedCount / state.statements.length) * 100 : 0}%`;
      }
      const reviewStatements = state.statements.filter((item) => item.review_count > 0).length;
      setText("#kpi-review-sub", `Across ${reviewStatements} file${reviewStatements === 1 ? "" : "s"}`);
      setText(
        "#rule-confidence",
        `${(Number(stats.classification_rate || 0) * 100).toFixed(1)}% Confidence Index`
      );
      setText(
        "#rule-engine-note",
        `Rule engine + TF-IDF ML auto-classified ${Number(stats.total_transactions || 0).toLocaleString("en-IN")} extracted transactions without LLM calls.`
      );

      const counts = stats.source_counts || {};
      const total = Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0) || 1;
      const rulePct = ((Number(counts.rule || 0) / total) * 100);
      const mlPct = ((Number(counts.ml || 0) / total) * 100);
      const manualPct = ((Number(counts.user || 0) + Number(counts.fallback || 0)) / total) * 100;
      setText("#src-rule", `Rules: ${rulePct.toFixed(1)}%`);
      setText("#src-ml", `ML: ${mlPct.toFixed(1)}%`);
      setText("#src-manual", `Manual: ${manualPct.toFixed(1)}%`);
      const barRule = $("#bar-rule");
      const barMl = $("#bar-ml");
      const barManual = $("#bar-manual");
      if (barRule) barRule.style.width = `${rulePct}%`;
      if (barMl) barMl.style.width = `${mlPct}%`;
      if (barManual) barManual.style.width = `${manualPct}%`;
    }

    function filteredStatements() {
      return state.statements.filter((statement) => {
        if (state.filter === "review" && !(statement.review_count > 0)) return false;
        if (state.filter === "failed" && statement.status !== "failed") return false;
        if (state.filter === "processed" && statement.status !== "processed") return false;
        if (state.filter === "image" && statement.pdf_type !== "image") return false;
        if (state.search) {
          const haystack = `${statement.filename} ${statement.bank || ""} ${(statement.account && statement.account.holder) || ""} ${(statement.account && statement.account.account_number) || ""}`.toLowerCase();
          if (!haystack.includes(state.search)) return false;
        }
        return true;
      });
    }

    function renderTabs() {
      const counts = {
        all: state.statements.length,
        review: state.statements.filter((item) => item.review_count > 0).length,
        failed: state.statements.filter((item) => item.status === "failed").length,
        processed: state.statements.filter((item) => item.status === "processed").length,
        image: state.statements.filter((item) => item.pdf_type === "image").length,
      };
      setText("#tab-count-all", counts.all);
      setText("#tab-count-review", counts.review);
      setText("#tab-count-failed", counts.failed);
      setText("#tab-count-processed", counts.processed);
      setText("#tab-count-image", counts.image);

      $$("[data-status-filter]").forEach((button) => {
        const active = button.dataset.statusFilter === state.filter;
        button.classList.toggle("bg-surface-container-highest", active);
        button.classList.toggle("text-on-surface", active);
        button.classList.toggle("shadow-sm", active);
        button.classList.toggle("text-on-surface-variant", !active);
      });
    }

    function renderTable() {
      const items = filteredStatements();
      setText("#statements-footer-text", `Showing ${items.length} of ${state.statements.length} statements`);
      const pagination = $("#statements-pagination");
      if (pagination) pagination.innerHTML = "";

      if (!items.length) {
        tbody.innerHTML = emptyRow(6, "No statements match this filter. Upload a PDF to get started.");
        return;
      }

      tbody.innerHTML = items
        .map((statement) => {
          const isFailed = statement.status === "failed";
          const iconTone = isFailed
            ? "bg-error-container/30 text-error"
            : statement.pdf_type === "image"
              ? "bg-secondary-container text-on-secondary-container"
              : "bg-primary-fixed/40 text-primary";
          const actions = isFailed
            ? `<button class="px-space-sm py-1 rounded bg-primary text-on-primary hover:bg-primary-container font-headline-sm text-label-md shadow-sm transition-colors" data-action="reprocess" data-id="${statement.id}" type="button">Retry</button>`
            : `<button class="px-space-sm py-1 rounded bg-primary text-on-primary hover:bg-primary-container font-headline-sm text-label-md shadow-sm transition-colors" data-action="review" data-id="${statement.id}" type="button">Review</button>
               <button class="px-space-sm py-1 rounded bg-surface-container text-on-surface hover:bg-surface-container-high font-headline-sm text-label-md transition-colors" data-action="export" data-id="${statement.id}" type="button">Export</button>`;
          return `<tr class="hover:bg-surface-container-low/60 transition-colors">
            <td class="py-space-sm px-space-lg">
              <div class="flex items-center gap-space-sm">
                <div class="h-8 w-8 rounded ${iconTone} flex items-center justify-center shrink-0">
                  <span class="material-symbols-outlined text-headline-sm">${statement.pdf_type === "image" ? "document_scanner" : "picture_as_pdf"}</span>
                </div>
                <div class="flex flex-col min-w-0">
                  <span class="font-headline-sm text-body-sm text-on-surface truncate">${escapeHtml(statement.filename)}</span>
                </div>
              </div>
            </td>
            <td class="py-space-sm px-space-md">
              <div class="flex items-center gap-space-xs">
                <span class="h-5 w-5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm flex items-center justify-center font-bold">${escapeHtml(initials(statement.bank))}</span>
                <div class="flex flex-col">
                  <span class="font-headline-sm text-body-sm text-on-surface">${escapeHtml(statement.bank || "Unknown Bank")}</span>
                  <span class="font-label-sm text-label-sm text-on-surface-variant font-mono">A/C ${escapeHtml(maskAccount(statement.account && statement.account.account_number))}</span>
                </div>
              </div>
            </td>
            <td class="py-space-sm px-space-md text-on-surface-variant">
              <span class="text-on-surface">${escapeHtml(formatDateTime(statement.created_at))}</span>
            </td>
            <td class="py-space-sm px-space-md text-right font-financial-numeric text-financial-numeric text-on-surface">${Number(statement.transaction_count || 0).toLocaleString("en-IN")} txns</td>
            <td class="py-space-sm px-space-md">${badgeStatus(statement)}</td>
            <td class="py-space-sm px-space-lg text-right">
              <div class="inline-flex items-center gap-space-xs">${actions}</div>
            </td>
          </tr>`;
        })
        .join("");
    }

    function renderCategoryDistribution(stats) {
      const container = $("#category-distribution");
      if (!container) return;
      const items = (stats.by_category || []).filter((item) => item.category !== "Uncategorized").slice(0, 6);
      if (!items.length) {
        container.innerHTML = `<div class="text-on-surface-variant font-body-sm text-body-sm">No classified transactions yet.</div>`;
        return;
      }
      const colors = new Map(state.categories.map((item) => [item.name, item.color]));
      const max = Math.max(...items.map((item) => Number(item.count || 0)), 1);
      const total = Math.max(Number(stats.total_transactions || 0), 1);
      container.innerHTML = items
        .map((item) => {
          const percentage = (Number(item.count || 0) / total) * 100;
          const width = Math.max(6, (Number(item.count || 0) / max) * 100);
          const color = colors.get(item.category) || "#059669";
          return `<div class="flex flex-col gap-1">
            <div class="flex items-center justify-between text-body-sm">
              <span class="font-headline-sm text-body-sm text-on-surface">${escapeHtml(item.category)}</span>
              <span class="font-financial-numeric text-financial-numeric text-on-surface">${Number(item.count || 0).toLocaleString("en-IN")} txns <span class="text-on-surface-variant font-label-sm text-label-sm font-normal">(${percentage.toFixed(1)}%)</span></span>
            </div>
            <div class="w-full bg-surface-container rounded-full h-2 overflow-hidden">
              <div class="h-2 rounded-full" style="width:${width}%;background-color:${color};"></div>
            </div>
          </div>`;
        })
        .join("");
    }

    function renderActivity(stats) {
      const container = $("#activity-feed");
      if (!container) return;
      const recent = (stats.recent_statements || []).slice(0, 4);
      if (!recent.length) {
        container.innerHTML = `<div class="text-on-surface-variant font-body-sm text-body-sm">No recent activity. Upload a statement to begin.</div>`;
        return;
      }
      container.innerHTML = recent
        .map((statement) => {
          const failed = statement.status === "failed";
          const tone = failed
            ? "bg-error-container text-on-error-container"
            : statement.review_count > 0
              ? "bg-amber-100 text-amber-800"
              : "bg-primary-fixed text-on-primary-fixed";
          const detail = failed
            ? "extraction failed"
            : statement.review_count > 0
              ? `${statement.review_count} flagged for review`
              : `${Number(statement.transaction_count || 0)} transactions classified`;
          return `<div class="flex items-start gap-space-sm">
            <div class="h-7 w-7 rounded-full ${tone} flex items-center justify-center shrink-0 mt-0.5">
              <span class="material-symbols-outlined text-label-sm">${failed ? "error" : statement.review_count > 0 ? "warning" : "smart_toy"}</span>
            </div>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-space-xs flex-wrap">
                <span class="font-headline-sm text-body-sm text-on-surface">${escapeHtml(statement.bank || "Statement")}</span>
                <span class="font-body-sm text-body-sm text-on-surface-variant">${detail}</span>
              </div>
              <span class="font-label-sm text-label-sm text-primary font-mono truncate">${escapeHtml(statement.filename)}</span>
              <span class="font-label-sm text-label-sm text-on-surface-variant mt-0.5">${escapeHtml(relativeTime(statement.created_at))}</span>
            </div>
          </div>`;
        })
        .join("");
    }

    tbody.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const id = button.dataset.id;
      if (button.dataset.action === "review") {
        window.location.href = `/statements/${id}`;
      } else if (button.dataset.action === "export") {
        window.location.href = `${API}/statements/${id}/export?format=xlsx`;
      } else if (button.dataset.action === "reprocess") {
        button.disabled = true;
        button.textContent = "Retrying…";
        try {
          await api(`/statements/${id}/reprocess`, { method: "POST" });
          toast("Statement reprocessed.", "success");
          await load();
        } catch (error) {
          toast(error.message, "error");
          button.disabled = false;
          button.textContent = "Retry";
        }
      }
    });

    $$("[data-status-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        state.filter = button.dataset.statusFilter;
        renderTabs();
        renderTable();
      });
    });

    const search = $("#statement-search");
    if (search) {
      search.addEventListener(
        "input",
        debounce(() => {
          state.search = search.value.trim().toLowerCase();
          renderTable();
        })
      );
    }

    const refresh = $("#btn-refresh-statements");
    if (refresh) refresh.addEventListener("click", load);

    const download = $("#btn-download-log");
    if (download) {
      download.addEventListener("click", () => {
        const latest = state.statements.find((item) => item.status === "processed");
        if (!latest) {
          toast("No processed statement is available to export.", "error");
          return;
        }
        window.location.href = `${API}/statements/${latest.id}/export?format=csv`;
      });
    }

    const reviewQueue = $("#review-queue-link");
    if (reviewQueue) {
      reviewQueue.addEventListener("click", (event) => {
        event.preventDefault();
        state.filter = "review";
        renderTabs();
        renderTable();
      });
    }

    await load();
  }

  // ------------------------------------------------------------------- upload
  function initUpload() {
    const STEPS = [
      "Upload & Hash Integrity",
      "Bank Layout Detection",
      "Extraction & OCR",
      "Balance Equation Validation",
      "Classification Engine",
      "Ready for Review",
    ];
    const state = { items: [], lastStatementId: null, controller: null, timer: null, step: 0 };
    const input = $("#file-dropzone-input");
    const queue = $("#upload-queue");
    const steps = $("#pipeline-steps");
    const log = $("#pipeline-log");
    const openButton = $("#btn-open-review");
    const cancelButton = $("#btn-cancel-upload");
    const clearButton = $("#btn-clear-done");

    if (!input || !queue) return;
    steps.innerHTML = "";
    if (log) log.innerHTML = "";

    function renderSteps(active, allDone = false) {
      if (!steps) return;
      steps.innerHTML = STEPS.map((label, index) => {
        const done = allDone || (active >= 0 && index < active);
        const current = !allDone && index === active;
        const circle = done
          ? "bg-primary text-on-primary"
          : current
            ? "bg-tertiary text-on-tertiary ring-4 ring-tertiary-container/30"
            : "bg-surface-container text-on-surface-variant";
        const icon = done ? "check" : current ? "refresh" : String(index + 1);
        const status = done ? "Pass" : current ? "Active" : "Queued";
        const statusTone = done ? "text-primary" : current ? "text-tertiary font-bold" : "text-outline";
        const rowTone = done || current ? "" : "opacity-60";
        const connector = index < STEPS.length - 1
          ? `<div class="w-0.5 h-3 ${done ? "bg-primary" : "bg-surface-container"} ml-3.5 -my-2.5"></div>`
          : "";
        return `<div class="flex items-center gap-space-md ${rowTone}">
          <div class="h-7 w-7 rounded-full ${circle} flex items-center justify-center shrink-0 font-label-sm shadow-sm">
            <span class="material-symbols-outlined text-[16px] ${current ? "siq-spin" : ""}">${icon}</span>
          </div>
          <div class="flex flex-col min-w-0 flex-1">
            <div class="flex items-center justify-between">
              <span class="text-on-surface font-label-md text-label-md">${index + 1}. ${label}</span>
              <span class="${statusTone} font-label-sm text-label-sm">${status}</span>
            </div>
            <span class="text-outline font-label-sm text-label-sm truncate">${status === "Pass" ? "Completed" : status === "Active" ? "Processing statement…" : "Waiting in queue"}</span>
          </div>
        </div>${connector}`;
      }).join("");
    }

    function logLine(message, tone = "") {
      if (!log) return;
      const line = document.createElement("div");
      line.className = "flex items-start gap-2";
      const time = new Date().toLocaleTimeString("en-GB", { hour12: false });
      line.innerHTML = `<span class="text-surface-container-high/60 shrink-0">[${time}]</span><span class="${tone}">${escapeHtml(message)}</span>`;
      log.appendChild(line);
      log.scrollTop = log.scrollHeight;
    }

    function queueRow(item) {
      const isReady = item.status === "ready";
      const isFailed = item.status === "failed";
      const isUploading = item.status === "uploading";
      const isCanceled = item.status === "canceled";
      const iconTone = isFailed
        ? "bg-error-container/40 text-error"
        : isReady
          ? "bg-primary/10 text-primary"
          : isCanceled
            ? "bg-surface-container text-outline"
            : "bg-tertiary/10 text-tertiary";
      const icon = isFailed ? "error" : isReady ? "check_circle" : isCanceled ? "cancel" : "sync";
      const label = isFailed ? "Failed" : isReady ? "Ready" : isCanceled ? "Canceled" : "Processing";
      const labelTone = isFailed
        ? "bg-error-container text-on-error-container"
        : isReady
          ? "bg-primary-container text-on-primary-container"
          : "bg-tertiary-container text-on-tertiary-container";
      const right = isReady
        ? `<span class="text-primary font-financial-numeric text-financial-numeric">${item.txCount} Txns</span>
           <button class="p-1 rounded text-outline hover:text-on-surface transition-colors" data-open="${item.statementId}" title="Open review" type="button">
             <span class="material-symbols-outlined text-headline-sm">chevron_right</span>
           </button>`
        : `<span class="text-outline font-label-sm text-label-sm">${isFailed ? "Needs attention" : isCanceled ? "Canceled" : "In progress"}</span>`;
      const progress = isReady ? 100 : isFailed ? 100 : isCanceled ? 100 : 45;
      const progressTone = isFailed ? "bg-error" : isCanceled ? "bg-outline" : isReady ? "bg-primary" : "bg-tertiary";
      const detail = item.bank ? `${item.bank} · ${item.message}` : item.message;
      return `<div class="p-space-md rounded-xl ${isUploading ? "bg-surface-container-lowest shadow-md relative overflow-hidden" : "bg-surface-container-low/70"} flex flex-col gap-space-sm">
        ${isUploading ? '<div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-tertiary via-primary to-tertiary animate-pulse"></div>' : ""}
        <div class="flex items-start justify-between gap-space-md ${isUploading ? "pt-1" : ""}">
          <div class="flex items-center gap-space-md min-w-0">
            <div class="h-10 w-10 rounded-lg ${iconTone} flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-headline-sm ${isUploading ? "siq-spin" : ""}">${icon}</span>
            </div>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-2 truncate">
                <span class="text-on-surface font-headline-sm text-headline-sm truncate">${escapeHtml(item.name)}</span>
                <span class="px-2 py-0.5 rounded ${labelTone} font-label-sm text-label-sm shrink-0">${label}</span>
              </div>
              <span class="text-outline font-label-sm text-label-sm truncate">${escapeHtml(detail)}</span>
            </div>
          </div>
          <div class="flex items-center gap-space-sm shrink-0">${right}</div>
        </div>
        <div class="w-full h-1.5 rounded-full bg-surface-container overflow-hidden">
          <div class="h-full ${progressTone} rounded-full transition-all duration-500" style="width:${progress}%"></div>
        </div>
      </div>`;
    }

    function renderQueue() {
      setText("#upload-queue-count", `${state.items.length} Active`);
      const totalBytes = state.items.reduce((sum, item) => sum + Number(item.size || 0), 0);
      setText("#upload-queue-summary", `${state.items.length} Files / ${(totalBytes / 1024 / 1024).toFixed(1)} MB`);
      if (!state.items.length) {
        queue.innerHTML = `<div class="p-space-lg rounded-xl bg-surface-container-low/60 text-center text-on-surface-variant font-body-sm text-body-sm">No files in the queue. Drop a PDF above to begin.</div>`;
        return;
      }
      queue.innerHTML = state.items.map(queueRow).join("");
    }

    function setOpenButton(enabled) {
      if (!openButton) return;
      openButton.classList.toggle("opacity-50", !enabled);
      openButton.classList.toggle("pointer-events-none", !enabled);
    }

    function updateFooter(statement) {
      if (!statement) return;
      setText("#stat-ocr-accuracy", statement.pdf_type === "image" ? "OCR 300 DPI" : "Text layer");
      setText("#stat-throughput", `${statement.summary.transaction_count} txns`);
      setText("#stat-reconciliation", (statement.warnings || []).length ? "Review" : "Exact");
    }

    function matchItem(filename, errors) {
      const normalise = (value) =>
        String(value || "")
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "");
      const wanted = normalise(filename);
      return (
        state.items.find(
          (item) => item.status === "uploading" && normalise(item.name) === wanted
        ) ||
        state.items.find((item) => item.status === "uploading")
      );
    }

    async function uploadFiles(files) {
      if (!files.length) return;
      if (state.timer) clearInterval(state.timer);
      state.items = files.map((file) => ({
        name: file.name,
        size: file.size,
        status: "uploading",
        message: `${(file.size / 1024 / 1024).toFixed(1)} MB · Queued`,
        statementId: null,
        txCount: 0,
        bank: null,
      }));
      state.step = 0;
      renderQueue();
      renderSteps(0);
      setOpenButton(false);
      setText("#pipeline-job", `Extraction job · ${files.length} file${files.length === 1 ? "" : "s"}`);
      if (log) log.innerHTML = "";
      logLine("Upload received. Computing SHA-256 integrity hash…");
      logLine("Detecting PDF type and bank layout templates…");

      state.timer = setInterval(() => {
        state.step = Math.min(state.step + 1, STEPS.length - 1);
        renderSteps(state.step);
      }, 900);

      const form = new FormData();
      files.forEach((file) => form.append("files", file));
      state.controller = new AbortController();

      try {
        const response = await fetch(`${API}/statements`, {
          method: "POST",
          body: form,
          signal: state.controller.signal,
        });
        const payload = await response.json();
        clearInterval(state.timer);
        state.timer = null;

        const successes = payload.statements || [];
        const errors = payload.errors || [];

        successes.forEach((statement) => {
          const item = matchItem(statement.filename, errors);
          if (!item) return;
          item.status = "ready";
          item.statementId = statement.id;
          item.txCount = statement.summary ? statement.summary.transaction_count : statement.transaction_count;
          item.bank = statement.bank;
          item.message = `${statement.pdf_type === "image" ? "OCR" : "Text PDF"} · ${statement.summary ? statement.summary.transaction_count : 0} transactions`;
          if (!state.lastStatementId) state.lastStatementId = statement.id;
          updateFooter(statement);
          logLine(`${statement.filename}: ${statement.bank} · ${item.txCount} transactions extracted.`, "text-primary-fixed");
          (statement.warnings || []).forEach((warning) => logLine(`Notice: ${warning}`, "text-amber-300"));
        });

        errors.forEach((error) => {
          const item = matchItem(error.filename, errors);
          if (!item) return;
          item.status = "failed";
          item.message = error.message;
          logLine(`${error.filename}: ${error.message}`, "text-red-300");
        });

        state.items.forEach((item) => {
          if (item.status === "uploading") {
            item.status = "failed";
            item.message = "The server did not return a result for this file.";
          }
        });

        renderQueue();
        renderSteps(STEPS.length, true);
        setText("#pipeline-job", successes.length ? `Completed · ${successes.length} statement${successes.length === 1 ? "" : "s"}` : "Extraction failed");

        if (successes.length) {
          setOpenButton(true);
          toast(
            successes.length === 1
              ? "Statement processed. Opening review…"
              : `${successes.length} statements processed.`,
            "success"
          );
          if (successes.length === 1 && errors.length === 0) {
            setTimeout(() => {
              window.location.href = `/statements/${successes[0].id}`;
            }, 1600);
          }
        } else if (errors.length) {
          toast(errors[0].message, "error");
        }
      } catch (error) {
        if (state.timer) clearInterval(state.timer);
        state.timer = null;
        if (error.name === "AbortError") {
          state.items.forEach((item) => {
            if (item.status === "uploading") {
              item.status = "canceled";
              item.message = "Canceled by user.";
            }
          });
          renderQueue();
          logLine("Extraction canceled by user.", "text-amber-300");
          toast("Processing canceled.", "info");
        } else {
          state.items.forEach((item) => {
            if (item.status === "uploading") {
              item.status = "failed";
              item.message = error.message;
            }
          });
          renderQueue();
          logLine(`Upload failed: ${error.message}`, "text-red-300");
          toast(error.message, "error");
        }
      } finally {
        state.controller = null;
      }
    }

    input.addEventListener("change", () => {
      uploadFiles(Array.from(input.files || []));
      input.value = "";
    });

    queue.addEventListener("click", (event) => {
      const button = event.target.closest("[data-open]");
      if (button && button.dataset.open) {
        window.location.href = `/statements/${button.dataset.open}`;
      }
    });

    if (openButton) {
      openButton.addEventListener("click", () => {
        if (state.lastStatementId) window.location.href = `/statements/${state.lastStatementId}`;
      });
    }

    if (cancelButton) {
      cancelButton.addEventListener("click", () => {
        if (state.controller) state.controller.abort();
      });
    }

    if (clearButton) {
      clearButton.addEventListener("click", () => {
        state.items = state.items.filter((item) => item.status === "uploading");
        if (!state.items.length) {
          state.lastStatementId = null;
          setOpenButton(false);
          renderSteps(-1);
          if (log) log.innerHTML = "";
          setText("#pipeline-job", "Idle");
        }
        renderQueue();
      });
    }

    renderQueue();
    renderSteps(-1);
    if (log) log.innerHTML = "";
    logLine("Pipeline worker ready. Waiting for statement PDFs…", "text-inverse-primary");
  }

  // ------------------------------------------------------------------- review
  function initReview() {
    const statementId = document.body.dataset.statementId;
    if (!statementId) return;
    if (document.body.dataset.nav === "transactions") {
      document.title = "StatementIQ · Transactions";
    }
    const state = {
      statement: null,
      categories: [],
      rules: [],
      filters: { tab: "all", type: "all", source: "all", category: "all", search: "", page: 1, perPage: 50 },
      selected: new Set(),
      currentItems: [],
    };
    const tbody = $("#review-tbody");

    function computeSummary(transactions) {
      const summary = {
        transaction_count: transactions.length,
        total_debit: 0,
        total_credit: 0,
        needs_review: 0,
        categorized: 0,
        classification_rate: 0,
        category_counts: {},
        source_counts: {},
      };
      transactions.forEach((transaction) => {
        summary.total_debit += Number(transaction.debit || 0);
        summary.total_credit += Number(transaction.credit || 0);
        if (transaction.needs_review) summary.needs_review += 1;
        if (transaction.category && transaction.category !== "Uncategorized") summary.categorized += 1;
        summary.category_counts[transaction.category || "Uncategorized"] =
          (summary.category_counts[transaction.category || "Uncategorized"] || 0) + 1;
        summary.source_counts[transaction.source || "fallback"] =
          (summary.source_counts[transaction.source || "fallback"] || 0) + 1;
      });
      summary.total_debit = Number(summary.total_debit.toFixed(2));
      summary.total_credit = Number(summary.total_credit.toFixed(2));
      summary.classification_rate = transactions.length ? summary.categorized / transactions.length : 0;
      return summary;
    }

    function flaggedTransactions() {
      return state.statement.transactions.filter((transaction) => transaction.needs_review);
    }

    function renderHeader() {
      const statement = state.statement;
      setText("#review-filename", statement.filename);
      setText("#review-parsed-count", `Parsed · ${statement.summary.transaction_count} Transactions`);
      setText("#review-hash", `ID: ${statement.id.slice(0, 10)}`);
      setText("#review-bank", statement.bank || "Unknown Bank");
      setText("#review-holder", statement.account.holder || "Account holder unavailable");
      setText("#review-account", `A/C: ${maskAccount(statement.account.account_number)}`);
      setText("#review-ifsc", statement.account.ifsc || "—");
      setText("#review-branch", "—");
      setText(
        "#review-period",
        statement.period.start || statement.period.end
          ? `${formatDate(statement.period.start)} — ${formatDate(statement.period.end)}`
          : "Period not detected"
      );
      let duration = "Duration unavailable";
      if (statement.period.start && statement.period.end) {
        const start = new Date(`${statement.period.start}T00:00:00`);
        const end = new Date(`${statement.period.end}T00:00:00`);
        if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())) {
          const days = Math.round((end - start) / 86400000) + 1;
          duration = `${days} calendar days · ID ${statement.id.slice(0, 8)}`;
        }
      }
      setText("#review-duration", duration);
      setText(
        "#review-extraction-mode",
        statement.pdf_type === "image" ? "Scanned PDF · OCR 300 DPI" : "Text PDF · Digital Native"
      );
      setText("#review-rules-label", `Category Rules (${state.rules.length})`);
      const reviewed = statement.summary.needs_review;
      const banner = $("#review-banner");
      if (banner) banner.classList.toggle("siq-hidden", reviewed === 0);
      setText(
        "#review-banner-text",
        `${reviewed} low-confidence transaction${reviewed === 1 ? "" : "s"} require human verification`
      );
      setText("#review-step-text", `Step through flagged (0/${flaggedTransactions().length})`);
    }

    function renderSummary() {
      const statement = state.statement;
      const summary = (state.statement.summary = computeSummary(state.statement.transactions));
      const debitCount = statement.transactions.filter((transaction) => transaction.debit).length;
      const creditCount = statement.transactions.filter((transaction) => transaction.credit).length;
      setText("#review-opening", money(statement.opening_balance));
      setText("#review-closing", money(statement.closing_balance));
      setText("#review-debits", money(-summary.total_debit));
      setText("#review-credits", money(summary.total_credit, { signed: true }));
      setText("#review-debits-sub", `${debitCount} Transactions`);
      setText("#review-credits-sub", `${creditCount} Transactions`);
      setText("#review-opening-sub", statement.period.start ? `As of ${formatDate(statement.period.start)}` : "Opening balance");
      setText("#review-closing-sub", statement.period.end ? `As of ${formatDate(statement.period.end)}` : "Closing balance");

      const varianceElement = $("#review-variance");
      const checkLabel = $("#review-check-label");
      if (
        statement.opening_balance !== null &&
        statement.closing_balance !== null
      ) {
        const variance = Number(
          (
            Number(statement.opening_balance) -
            summary.total_debit +
            summary.total_credit -
            Number(statement.closing_balance)
          ).toFixed(2)
        );
        if (varianceElement) {
          varianceElement.textContent = money(variance);
          varianceElement.classList.toggle("text-primary", Math.abs(variance) < 0.02);
          varianceElement.classList.toggle("text-error", Math.abs(variance) >= 0.02);
        }
        if (checkLabel) {
          checkLabel.textContent = Math.abs(variance) < 0.02 ? "Mathematical Check Reconciled" : "Balance mismatch detected";
        }
      } else {
        if (varianceElement) varianceElement.textContent = "—";
        if (checkLabel) checkLabel.textContent = "Balance data incomplete";
      }
    }

    function renderTabs() {
      const total = state.statement.transactions.length;
      const flagged = flaggedTransactions().length;
      $("#review-tab-all").innerHTML = `All (${total})`;
      $("#review-tab-flagged").innerHTML = `<span class="h-2 w-2 rounded-full bg-error"></span><span class="">Flagged / Review (${flagged})</span>`;
      $("#review-tab-auto").innerHTML = `<span class="h-2 w-2 rounded-full bg-primary"></span><span class="">Auto-classified (${total - flagged})</span>`;
      $$("[data-review-filter]").forEach((button) => {
        const active = button.dataset.reviewFilter === state.filters.tab;
        button.classList.toggle("bg-surface-container-lowest", active);
        button.classList.toggle("shadow-sm", active);
        button.classList.toggle("text-on-surface", active);
        button.classList.toggle("font-semibold", active);
        button.classList.toggle("text-on-surface-variant", !active);
      });
    }

    function filteredTransactions() {
      const search = state.filters.search;
      return state.statement.transactions.filter((transaction) => {
        if (state.filters.tab === "flagged" && !transaction.needs_review) return false;
        if (state.filters.tab === "auto" && transaction.needs_review) return false;
        if (state.filters.type !== "all" && transaction.direction !== state.filters.type) return false;
        if (state.filters.source !== "all" && transaction.source !== state.filters.source) return false;
        if (state.filters.category !== "all" && transaction.category !== state.filters.category) return false;
        if (search) {
          const haystack = `${transaction.description} ${transaction.category} ${transaction.raw_text || ""}`.toLowerCase();
          if (!haystack.includes(search)) return false;
        }
        return true;
      });
    }

    function categoryOptions(selected) {
      return state.categories
        .map(
          (category) =>
            `<option value="${escapeHtml(category.name)}" ${category.name === selected ? "selected" : ""}>${escapeHtml(category.name)}</option>`
        )
        .join("");
    }

    function confidenceMarkup(transaction) {
      const percent = Math.round(Number(transaction.confidence || 0) * 100);
      const flagged = transaction.needs_review;
      const tone = flagged ? "text-error" : percent >= 85 ? "text-primary" : "text-amber-700";
      const dot = flagged ? "bg-error" : percent >= 85 ? "bg-primary" : "bg-amber-500";
      return `<div class="flex items-center gap-space-xs font-label-sm text-label-sm">
        <span class="h-2 w-2 rounded-full ${dot}"></span>
        <span class="font-semibold ${tone}">${percent}%</span>
      </div>`;
    }

    function renderTable() {
      const filtered = filteredTransactions();
      const pages = Math.max(1, Math.ceil(filtered.length / state.filters.perPage));
      if (state.filters.page > pages) state.filters.page = pages;
      const start = (state.filters.page - 1) * state.filters.perPage;
      const items = filtered.slice(start, start + state.filters.perPage);
      state.currentItems = items;

      if (!items.length) {
        tbody.innerHTML = emptyRow(9, "No transactions match the current filters.");
      } else {
        tbody.innerHTML = items
          .map((transaction) => {
            const rowTone = transaction.needs_review
              ? "bg-error-container/10 hover:bg-error-container/20 transition-colors group"
              : "hover:bg-surface-container-low transition-colors group";
            const debit = transaction.debit
              ? `<span class="text-error font-semibold">${escapeHtml(money(-transaction.debit))}</span>`
              : `<span class="text-outline">—</span>`;
            const credit = transaction.credit
              ? `<span class="text-primary font-semibold">${escapeHtml(money(transaction.credit, { signed: true }))}</span>`
              : `<span class="text-outline">—</span>`;
            const action = transaction.needs_review
              ? `<button class="px-space-sm py-1 rounded bg-primary text-on-primary hover:bg-primary-container font-label-sm text-label-sm font-semibold transition-colors shadow-sm" data-approve="${transaction.id}" type="button">Approve</button>`
              : `<button class="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors" data-focus-select="${transaction.id}" type="button"><span class="material-symbols-outlined text-body-sm">edit</span></button>`;
            const reasons = transaction.needs_review && (transaction.review_reasons || []).length
              ? `<span class="font-label-sm text-label-sm text-error truncate">${escapeHtml(transaction.review_reasons.map((reason) => reason.replaceAll("_", " ")).join(", "))}</span>`
              : "";
            return `<tr class="${rowTone}" id="tx-row-${transaction.id}">
              <td class="py-space-sm px-space-md text-center"><input class="review-check rounded text-primary focus:ring-0 cursor-pointer" type="checkbox" data-id="${transaction.id}" ${state.selected.has(transaction.id) ? "checked" : ""}></td>
              <td class="py-space-sm px-space-md whitespace-nowrap font-financial-numeric text-on-surface">${escapeHtml(formatDate(transaction.date))}</td>
              <td class="py-space-sm px-space-md">
                <div class="flex flex-col min-w-0">
                  <span class="font-financial-numeric text-on-surface break-words">${escapeHtml(transaction.description)}</span>
                  ${reasons}
                </div>
              </td>
              <td class="py-space-sm px-space-md text-right font-financial-numeric tabular-nums">${debit}</td>
              <td class="py-space-sm px-space-md text-right font-financial-numeric tabular-nums">${credit}</td>
              <td class="py-space-sm px-space-md text-right font-financial-numeric text-on-surface tabular-nums">${escapeHtml(money(transaction.balance))}</td>
              <td class="py-space-sm px-space-md">
                <div class="flex items-center gap-space-xs min-w-[190px]">
                  <select class="siq-table-select" data-category-select="${transaction.id}">
                    ${categoryOptions(transaction.category)}
                  </select>

                </div>
              </td>
              <td class="py-space-sm px-space-md">${confidenceMarkup(transaction)}</td>
              <td class="py-space-sm px-space-md text-right"><div class="flex items-center justify-end gap-space-xs">${action}</div></td>
            </tr>`;
          })
          .join("");
      }

      const range = $("#review-range");
      if (range) {
        const from = filtered.length ? start + 1 : 0;
        const to = start + items.length;
        range.innerHTML = `Showing <strong class="text-on-surface">${from}–${to}</strong> of <strong class="text-on-surface">${filtered.length}</strong> transactions`;
      }
      const pageDebits = items.reduce((sum, transaction) => sum + Number(transaction.debit || 0), 0);
      const pageCredits = items.reduce((sum, transaction) => sum + Number(transaction.credit || 0), 0);
      setText("#review-page-debits", money(pageDebits));
      setText("#review-page-credits", money(pageCredits, { signed: true }));
      setText("#review-page-variance", `Running Variance: ${money(pageCredits - pageDebits)}`);

      renderPagination(pages);
      renderTabs();

      const bulkButton = $("#btn-bulk-categorize");
      if (bulkButton) {
        bulkButton.disabled = state.selected.size === 0;
        bulkButton.classList.toggle("cursor-not-allowed", state.selected.size === 0);
        bulkButton.classList.toggle("text-outline", state.selected.size === 0);
        bulkButton.classList.toggle("bg-surface-container-low", state.selected.size === 0);
        bulkButton.classList.toggle("bg-surface-container", state.selected.size > 0);
        bulkButton.classList.toggle("text-on-surface", state.selected.size > 0);
      }
      setText("#bulk-selected-count", state.selected.size);
      setText("#review-step-text", `Step through flagged (0/${flaggedTransactions().length})`);
      const headerCheck = tbody.closest("table")?.querySelector("thead input[type=checkbox]");
      if (headerCheck) {
        headerCheck.checked = items.length > 0 && items.every((item) => state.selected.has(item.id));
      }
    }

    function renderPagination(pages) {
      const container = $("#review-pagination");
      if (!container) return;
      const current = state.filters.page;
      const buttons = [];
      buttons.push(
        `<button class="px-space-sm py-1 rounded bg-surface-container-lowest ${current <= 1 ? "text-outline cursor-not-allowed" : "text-on-surface hover:bg-surface-container"} shadow-sm" data-page-action="prev" ${current <= 1 ? "disabled" : ""} type="button">Previous</button>`
      );
      const visible = new Set([1, pages, current - 1, current, current + 1]);
      let previous = 0;
      Array.from(visible)
        .filter((value) => value >= 1 && value <= pages)
        .sort((a, b) => a - b)
        .forEach((value) => {
          if (previous && value - previous > 1) {
            buttons.push(`<span class="px-1 text-outline">…</span>`);
          }
          buttons.push(
            value === current
              ? `<button class="w-8 h-8 rounded bg-primary text-on-primary font-semibold flex items-center justify-center shadow-sm" data-page-number="${value}" type="button">${value}</button>`
              : `<button class="w-8 h-8 rounded bg-surface-container-lowest text-on-surface hover:bg-surface-container flex items-center justify-center transition-colors" data-page-number="${value}" type="button">${value}</button>`
          );
          previous = value;
        });
      buttons.push(
        `<button class="px-space-sm py-1 rounded bg-surface-container-lowest ${current >= pages ? "text-outline cursor-not-allowed" : "text-on-surface hover:bg-surface-container"} shadow-sm" data-page-action="next" ${current >= pages ? "disabled" : ""} type="button">Next</button>`
      );
      container.innerHTML = buttons.join("");
    }

    function saveCategory(transactionId, category) {
      api(`/transactions/${transactionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category }),
      })
        .then((payload) => {
          const updated = payload.transaction;
          const index = state.statement.transactions.findIndex((item) => item.id === updated.id);
          if (index >= 0) state.statement.transactions[index] = updated;
          state.selected.delete(updated.id);
          state.statement.summary = computeSummary(state.statement.transactions);
          renderHeader();
          renderSummary();
          renderTable();
          toast("Category updated.", "success");
        })
        .catch((error) => toast(error.message, "error"));
    }

    function openBulkModal() {
      if (!state.selected.size) return;
      const overlay = document.createElement("div");
      overlay.className = "fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/45 p-4";
      overlay.innerHTML = `<div class="w-full max-w-md rounded-xl bg-white shadow-2xl border border-slate-200">
        <div class="p-space-lg border-b border-slate-200">
          <div class="flex items-center gap-2 text-on-surface font-headline-sm text-headline-sm"><span class="material-symbols-outlined text-primary">label</span>Bulk categorize</div>
          <p class="text-on-surface-variant font-body-sm text-body-sm mt-1">${state.selected.size} selected transaction${state.selected.size === 1 ? "" : "s"}</p>
        </div>
        <div class="p-space-lg flex flex-col gap-space-md">
          <label class="text-on-surface font-label-md text-label-md" for="bulk-category-select">Assign category</label>
          <select id="bulk-category-select" class="h-9 px-3 rounded-lg bg-surface-container-low text-on-surface font-body-sm text-body-sm focus:outline-none">
            ${categoryOptions("")}
          </select>
          <div class="flex items-center justify-end gap-space-sm">
            <button class="px-space-md py-space-sm rounded-lg bg-surface-container text-on-surface font-label-md text-label-md" data-close type="button">Cancel</button>
            <button class="px-space-md py-space-sm rounded-lg bg-primary text-on-primary font-label-md text-label-md" id="bulk-apply" type="button">Apply category</button>
          </div>
        </div>
      </div>`;
      document.body.appendChild(overlay);
      overlay.addEventListener("click", (event) => {
        if (event.target === overlay || event.target.closest("[data-close]")) overlay.remove();
      });
      const applyButton = overlay.querySelector("#bulk-apply");
      applyButton.addEventListener("click", async () => {
        const category = overlay.querySelector("#bulk-category-select").value;
        applyButton.disabled = true;
        try {
          const payload = await api("/transactions/bulk-category", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_ids: Array.from(state.selected), category }),
          });
          state.statement.transactions.forEach((transaction) => {
            if (state.selected.has(transaction.id)) {
              transaction.category = category;
              transaction.source = "user";
              transaction.confidence = 1;
              transaction.needs_review = false;
              transaction.review_reasons = [];
            }
          });
          state.selected.clear();
          state.statement.summary = computeSummary(state.statement.transactions);
          overlay.remove();
          renderHeader();
          renderSummary();
          renderTable();
          toast(`${payload.updated} transactions updated.`, "success");
        } catch (error) {
          applyButton.disabled = false;
          toast(error.message, "error");
        }
      });
    }

    function refreshAll() {
      renderHeader();
      renderSummary();
      renderTabs();
      renderTable();
    }

    async function loadStatementSwitcher() {
      const select = $("#statement-switcher");
      if (!select) return;
      try {
        const listing = await api("/statements?limit=200");
        const items = (listing.items || []).filter((item) => item.status === "processed");
        if (items.length <= 1) return;
        select.innerHTML = items
          .map(
            (item) =>
              `<option value="${item.id}" ${item.id === statementId ? "selected" : ""}>${escapeHtml(item.bank || "Bank")} · ${escapeHtml(item.filename)} · ${Number(item.transaction_count || 0)} txns</option>`
          )
          .join("");
        select.classList.remove("hidden");
        select.addEventListener("change", () => {
          const base = document.body.dataset.nav === "transactions" ? "/transactions?statement_id=" : "/statements/";
          window.location.href = `${base}${select.value}`;
        });
      } catch (error) {
        // The switcher is a convenience control; the ledger still works without it.
      }
    }

    async function loadStatement() {
      try {
        const [statement, categoriesPayload, rulesPayload] = await Promise.all([
          api(`/statements/${statementId}`),
          api("/categories"),
          api("/rules"),
          loadStatementSwitcher(),
        ]);
        state.statement = statement;
        state.categories = categoriesPayload.categories || [];
        state.rules = rulesPayload.rules || [];
        state.statement.summary = computeSummary(state.statement.transactions);
        refreshAll();
      } catch (error) {
        toast(error.message, "error");
        tbody.innerHTML = emptyRow(9, "Unable to load this statement.");
      }
    }

    tbody.addEventListener("change", (event) => {
      const select = event.target.closest("select[data-category-select]");
      if (select) {
        saveCategory(select.dataset.categorySelect, select.value);
        return;
      }
      const checkbox = event.target.closest("input.review-check");
      if (checkbox) {
        if (checkbox.checked) state.selected.add(checkbox.dataset.id);
        else state.selected.delete(checkbox.dataset.id);
        renderTable();
      }
    });

    tbody.addEventListener("click", (event) => {
      const approve = event.target.closest("button[data-approve]");
      if (approve) {
        const transaction = state.statement.transactions.find((item) => item.id === approve.dataset.approve);
        if (transaction) saveCategory(transaction.id, transaction.category);
        return;
      }
      const focus = event.target.closest("button[data-focus-select]");
      if (focus) {
        const select = tbody.querySelector(`select[data-category-select="${focus.dataset.focusSelect}"]`);
        if (select) select.focus();
      }
    });

    const headerCheck = tbody.closest("table")?.querySelector("thead input[type=checkbox]");
    if (headerCheck) {
      headerCheck.addEventListener("change", () => {
        if (headerCheck.checked) {
          state.currentItems.forEach((item) => state.selected.add(item.id));
        } else {
          state.currentItems.forEach((item) => state.selected.delete(item.id));
        }
        renderTable();
      });
    }

    $$("[data-review-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        state.filters.tab = button.dataset.reviewFilter;
        state.filters.page = 1;
        renderTabs();
        renderTable();
      });
    });

    $$("[data-type-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        state.filters.type = button.dataset.typeFilter;
        state.filters.page = 1;
        $$("[data-type-filter]").forEach((item) => {
          const active = item.dataset.typeFilter === state.filters.type;
          item.classList.toggle("bg-surface-container-lowest", active);
          item.classList.toggle("text-on-surface", active);
          item.classList.toggle("font-semibold", active);
          item.classList.toggle("shadow-sm", active);
          item.classList.toggle("text-on-surface-variant", !active);
        });
        renderTable();
      });
    });

    const search = $("#review-search");
    if (search) {
      search.addEventListener(
        "input",
        debounce(() => {
          state.filters.search = search.value.trim().toLowerCase();
          state.filters.page = 1;
          renderTable();
        })
      );
    }

    const categoryButton = $("#btn-category-filter");
    if (categoryButton) {
      categoryButton.addEventListener("click", () => {
        const items = [{ value: "all", label: "All categories", active: state.filters.category === "all" }].concat(
          state.categories.map((category) => ({
            value: category.name,
            label: category.name,
            active: state.filters.category === category.name,
          }))
        );
        openMenu(categoryButton, items, (value) => {
          state.filters.category = value;
          state.filters.page = 1;
          setText("#category-filter-label", value === "all" ? "Category: All" : `Category: ${value}`);
          renderTable();
        });
      });
    }

    const sourceButton = $("#btn-source-filter");
    if (sourceButton) {
      sourceButton.addEventListener("click", () => {
        const labels = { all: "All", rule: "Rule engine", ml: "TF-IDF ML", user: "Manual", fallback: "Fallback" };
        const items = Object.entries(labels).map(([value, label]) => ({
          value,
          label,
          active: state.filters.source === value,
        }));
        openMenu(sourceButton, items, (value) => {
          state.filters.source = value;
          state.filters.page = 1;
          setText("#source-filter-label", `Engine: ${labels[value]}`);
          renderTable();
        });
      });
    }

    const perPage = $("#review-per-page");
    if (perPage) {
      perPage.addEventListener("change", () => {
        state.filters.perPage = Number(perPage.value) || 50;
        state.filters.page = 1;
        renderTable();
      });
    }

    const pagination = $("#review-pagination");
    if (pagination) {
      pagination.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (!button) return;
        if (button.dataset.pageAction === "prev") state.filters.page = Math.max(1, state.filters.page - 1);
        else if (button.dataset.pageAction === "next") state.filters.page += 1;
        else if (button.dataset.pageNumber) state.filters.page = Number(button.dataset.pageNumber);
        renderTable();
      });
    }

    const bulkButton = $("#btn-bulk-categorize");
    if (bulkButton) bulkButton.addEventListener("click", openBulkModal);

    const exportCsv = $("#btn-export-csv");
    if (exportCsv) {
      exportCsv.addEventListener("click", () => {
        window.location.href = `${API}/statements/${statementId}/export?format=csv`;
      });
    }
    const exportXlsx = $("#btn-export-xlsx");
    if (exportXlsx) {
      exportXlsx.addEventListener("click", () => {
        window.location.href = `${API}/statements/${statementId}/export?format=xlsx`;
      });
    }

    const reprocess = $("#btn-reprocess");
    if (reprocess) {
      reprocess.addEventListener("click", async () => {
        reprocess.disabled = true;
        try {
          await api(`/statements/${statementId}/reprocess`, { method: "POST" });
          toast("Statement reprocessed with the latest rules.", "success");
          await loadStatement();
        } catch (error) {
          toast(error.message, "error");
        } finally {
          reprocess.disabled = false;
        }
      });
    }

    const complete = $("#btn-complete-review");
    if (complete) {
      complete.addEventListener("click", () => {
        const remaining = flaggedTransactions().length;
        if (remaining) {
          toast(`${remaining} flagged transaction${remaining === 1 ? "" : "s"} still need review.`, "error");
          state.filters.tab = "flagged";
          state.filters.page = 1;
          refreshAll();
        } else {
          toast("Review complete. Ledger is reconciled.", "success");
          setTimeout(() => {
            window.location.href = "/";
          }, 900);
        }
      });
    }

    let flaggedCursor = 0;
    const stepFlagged = $("#btn-step-flagged");
    if (stepFlagged) {
      stepFlagged.addEventListener("click", () => {
        const flagged = flaggedTransactions();
        if (!flagged.length) {
          toast("Every transaction is classified and verified.", "success");
          return;
        }
        const target = flagged[flaggedCursor % flagged.length];
        flaggedCursor += 1;
        state.filters.tab = "flagged";
        state.filters.page = 1;
        state.filters.search = "";
        if (search) search.value = "";
        refreshAll();
        requestAnimationFrame(() => {
          const row = document.getElementById(`tx-row-${target.id}`);
          if (!row) return;
          row.classList.add("siq-row-flash");
          row.scrollIntoView({ behavior: "smooth", block: "center" });
          setTimeout(() => row.classList.remove("siq-row-flash"), 1300);
        });
      });
    }

    loadStatement();
  }

  // --------------------------------------------------------------- categories
  function initCategories() {
    async function load() {
      try {
        const [categoryPayload, rulesPayload, stats] = await Promise.all([
          api("/categories"),
          api("/rules"),
          api("/stats"),
        ]);
        const categories = categoryPayload.categories || [];
        const rules = rulesPayload.rules || [];
        setText("#cat-kpi-total", categories.length);
        setText("#cat-kpi-rules", rules.length);
        setText("#cat-kpi-accuracy", `${(Number(stats.classification_rate || 0) * 100).toFixed(1)}%`);
        setText(
          "#cat-kpi-accuracy-sub",
          `${Number(stats.total_transactions || 0).toLocaleString("en-IN")} transactions analysed`
        );
        const uncategorized =
          (stats.by_category || []).find((item) => item.category === "Uncategorized")?.count || 0;
        setText("#cat-kpi-uncategorized", uncategorized);

        const rulesByCategory = rules.reduce((accumulator, rule) => {
          accumulator[rule.category] = (accumulator[rule.category] || 0) + 1;
          return accumulator;
        }, {});
        const statsByCategory = new Map(
          (stats.by_category || []).map((item) => [item.category, item])
        );

        const tbody = $("#categories-tbody");
        if (!categories.length) {
          tbody.innerHTML = emptyRow(4, "No categories configured.");
        } else {
          tbody.innerHTML = categories
            .map((category) => {
              const statsItem = statsByCategory.get(category.name) || { count: 0, debit_total: 0, credit_total: 0 };
              return `<tr class="hover:bg-surface-container-low transition-colors" data-category-name="${escapeHtml(category.name)}">
                <td class="py-3 px-space-md">
                  <div class="flex items-center gap-space-sm">
                    <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background-color:${escapeHtml(category.color || "#059669")}"></span>
                    <span class="font-headline-sm text-body-md text-on-surface font-semibold">${escapeHtml(category.name)}</span>
                  </div>
                </td>
                <td class="py-3 px-space-md text-right font-financial-numeric text-financial-numeric text-on-surface">${Number(statsItem.count || 0).toLocaleString("en-IN")}</td>
                <td class="py-3 px-space-md text-right text-on-surface-variant font-label-md">${rulesByCategory[category.name] || 0}</td>
                <td class="py-3 px-space-md text-right font-financial-numeric text-financial-numeric text-on-surface">${escapeHtml(money(Number(statsItem.debit_total || 0)))}</td>
              </tr>`;
            })
            .join("");
        }

        const rulesBody = $("#rules-tbody");
        if (!rules.length) {
          rulesBody.innerHTML = emptyRow(4, "No rules configured.");
        } else {
          rulesBody.innerHTML = rules
            .map((rule) => {
              const patterns = (rule.patterns || []).slice(0, 2).join(" | ");
              return `<tr class="hover:bg-surface-container-low transition-colors">
                <td class="py-3 px-space-md">
                  <div class="flex flex-col">
                    <span class="font-headline-sm text-body-md text-on-surface font-semibold">${escapeHtml(rule.id)}</span>
                    <span class="font-label-sm text-label-sm text-outline capitalize">${escapeHtml(rule.direction)} match</span>
                  </div>
                </td>
                <td class="py-3 px-space-md"><code class="px-2 py-1 rounded bg-surface-container font-mono text-label-sm text-tertiary select-all">${escapeHtml(patterns)}</code></td>
                <td class="py-3 px-space-md"><span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-fixed text-label-sm">${escapeHtml(rule.category)}</span></td>
                <td class="py-3 px-space-md"><span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-primary-fixed text-on-primary-fixed font-label-sm text-label-sm font-semibold">${Math.round(Number(rule.confidence || 0) * 100)}%</span></td>
              </tr>`;
            })
            .join("");
        }

        const filter = $("#category-filter");
        if (filter) {
          filter.addEventListener(
            "input",
            debounce(() => {
              const term = filter.value.trim().toLowerCase();
              $$("#categories-tbody tr[data-category-name]").forEach((row) => {
                row.classList.toggle("siq-hidden", term && !row.dataset.categoryName.toLowerCase().includes(term));
              });
            })
          );
        }
      } catch (error) {
        toast(error.message, "error");
      }
    }

    load();
  }

  function boot() {
    wireChrome();
    if (page === "dashboard") initDashboard();
    else if (page === "upload") initUpload();
    else if (page === "review") initReview();
    else if (page === "categories") initCategories();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
