(function () {
  function initAmbientBackground() {
    const root = document.documentElement;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      return;
    }

    let targetX = window.innerWidth * 0.5;
    let targetY = window.innerHeight * 0.35;
    let currentX = targetX;
    let currentY = targetY;
    let rafId = 0;

    function render() {
      currentX += (targetX - currentX) * 0.1;
      currentY += (targetY - currentY) * 0.1;
      root.style.setProperty("--mx", currentX.toFixed(1) + "px");
      root.style.setProperty("--my", currentY.toFixed(1) + "px");

      if (Math.abs(targetX - currentX) > 0.4 || Math.abs(targetY - currentY) > 0.4) {
        rafId = window.requestAnimationFrame(render);
      } else {
        rafId = 0;
      }
    }

    function onPointerMove(event) {
      targetX = event.clientX;
      targetY = event.clientY;
      if (!rafId) {
        rafId = window.requestAnimationFrame(render);
      }
    }

    function onResize() {
      if (!rafId) {
        root.style.setProperty("--mx", Math.round(targetX) + "px");
        root.style.setProperty("--my", Math.round(targetY) + "px");
      }
    }

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerdown", onPointerMove, { passive: true });
    window.addEventListener("resize", onResize, { passive: true });
    root.style.setProperty("--mx", Math.round(targetX) + "px");
    root.style.setProperty("--my", Math.round(targetY) + "px");
  }

  function normalizeSectionTitle(rawTitle) {
    const title = rawTitle.trim();
    const lower = title.toLowerCase();
    if (lower === "generated concept" || lower === "концепт") {
      return "Концепт";
    }
    if (lower === "suggested execution" || lower === "рекомендации по исполнению") {
      return "Рекомендации по исполнению";
    }
    if (lower === "trend" || lower === "тренд") {
      return "Тренд";
    }
    if (lower === "result") {
      return "Результат";
    }
    return title;
  }

  function stripBackticks(value) {
    return value.replace(/^`+|`+$/g, "");
  }

  function localizeType(value) {
    const lower = value.trim().toLowerCase();
    if (lower === "video" || lower === "видео") {
      return "видео";
    }
    if (lower === "photo" || lower === "фото") {
      return "фото";
    }
    return value;
  }

  function parseResultText(rawText, fallbackTrendTitle) {
    const parsed = {
      trend: fallbackTrendTitle || "",
      type: "",
      fingerprint: "",
      sections: [],
    };

    const lines = rawText
      .split(/\r?\n/)
      .map(function (line) {
        return line.trim();
      })
      .filter(Boolean);

    let currentSection = null;

    function upsertSection(title) {
      const normalized = normalizeSectionTitle(title);
      const section = {
        title: normalized,
        paragraphs: [],
        list: [],
      };
      parsed.sections.push(section);
      return section;
    }

    function parseMetaLine(line) {
      const match = line.match(/^([A-Za-z][A-Za-z\s_-]+):\s*(.+)$/);
      if (!match) {
        return false;
      }
      const key = match[1].trim().toLowerCase();
      const value = stripBackticks(match[2].trim());
      if (key === "trend" || key === "тренд") {
        parsed.trend = value;
        return true;
      }
      if (key === "type" || key === "тип") {
        parsed.type = value;
        return true;
      }
      if (key === "fingerprint" || key === "отпечаток") {
        parsed.fingerprint = value;
        return true;
      }
      return false;
    }

    lines.forEach(function (line) {
      const headingMatch = line.match(/^#{1,6}\s*(.+)$/);
      if (headingMatch) {
        const headingText = headingMatch[1].trim();
        if (parseMetaLine(headingText)) {
          currentSection = null;
          return;
        }
        currentSection = upsertSection(headingText);
        return;
      }

      if (parseMetaLine(line)) {
        return;
      }

      const listMatch = line.match(/^(?:\d+\.|[-*])\s+(.+)$/);
      if (listMatch) {
        if (!currentSection) {
          currentSection = upsertSection("Рекомендации по исполнению");
        }
        currentSection.list.push(stripBackticks(listMatch[1].trim()));
        return;
      }

      if (!currentSection) {
        currentSection = upsertSection("Концепт");
      }
      currentSection.paragraphs.push(stripBackticks(line));
    });

    return parsed;
  }

  function createResultBlock(title, paragraphs, listItems) {
    const block = document.createElement("article");
    block.className = "result-block";

    const heading = document.createElement("h3");
    heading.textContent = title;
    block.appendChild(heading);

    paragraphs.forEach(function (text) {
      const p = document.createElement("p");
      p.textContent = text;
      block.appendChild(p);
    });

    if (listItems.length > 0) {
      const ul = document.createElement("ul");
      listItems.forEach(function (text) {
        const li = document.createElement("li");
        li.textContent = text;
        ul.appendChild(li);
      });
      block.appendChild(ul);
    }

    return block;
  }

  function renderParsedResult(container, parsed, fallbackTrendTitle) {
    container.innerHTML = "";

    const trendTitle = parsed.trend || fallbackTrendTitle || "";
    if (trendTitle) {
      const trendParagraphs = [trendTitle];
      if (parsed.type) {
        trendParagraphs.push("Тип: " + localizeType(parsed.type));
      }
      container.appendChild(createResultBlock("Тренд", trendParagraphs, []));
    }

    let hasRenderableSection = false;
    parsed.sections.forEach(function (section) {
      const lowerTitle = section.title.toLowerCase();
      if (lowerTitle === "trend" || lowerTitle === "тренд" || lowerTitle === "fingerprint" || lowerTitle === "отпечаток") {
        return;
      }
      if (section.paragraphs.length === 0 && section.list.length === 0) {
        return;
      }
      hasRenderableSection = true;
      container.appendChild(createResultBlock(section.title, section.paragraphs, section.list));
    });

    if (!hasRenderableSection && !trendTitle) {
      container.appendChild(
        createResultBlock(
          "Результат",
          ["Результат пока недоступен. Дождитесь завершения генерации."],
          []
        )
      );
    }
  }

  function renderTechnicalDetails(target, parsed, root) {
    if (!target) {
      return;
    }
    target.innerHTML = "";

    const rows = [];
    const id = root.getAttribute("data-generation-id") || "";
    const provider = root.getAttribute("data-provider") || "";
    const model = root.getAttribute("data-model") || "";

    if (parsed.fingerprint) {
      rows.push(["Отпечаток", parsed.fingerprint]);
    }
    if (provider) {
      rows.push(["Провайдер", provider]);
    }
    if (model) {
      rows.push(["Модель", model]);
    }
    if (id) {
      rows.push(["ID генерации", id]);
    }

    if (rows.length === 0) {
      target.textContent = "Технические детали недоступны.";
      return;
    }

    const dl = document.createElement("dl");
    rows.forEach(function (row) {
      const dt = document.createElement("dt");
      dt.textContent = row[0];
      const dd = document.createElement("dd");
      const code = document.createElement("code");
      code.textContent = row[1];
      dd.appendChild(code);
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
    target.appendChild(dl);
  }

  function initCopyButton(copyButton, rawNode) {
    if (!copyButton || !rawNode) {
      return;
    }

    copyButton.addEventListener("click", function () {
      const text = rawNode.textContent.trim();
      if (!text) {
        return;
      }

      function markCopied() {
        const original = copyButton.textContent;
        copyButton.textContent = "Скопировано";
        window.setTimeout(function () {
          copyButton.textContent = original;
        }, 1200);
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(markCopied).catch(function () {});
        return;
      }

      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      try {
        document.execCommand("copy");
        markCopied();
      } catch (err) {
        void err;
      } finally {
        document.body.removeChild(area);
      }
    });
  }

  function initGenerationStatusSSE() {
    const root = document.getElementById("generation-status");
    if (!root) {
      return;
    }

    const url = root.getAttribute("data-events-url");
    if (!url) {
      return;
    }

    const statusNode = document.getElementById("status-value");
    const resultContentNode = document.getElementById("result-content");
    const resultRawNode = document.getElementById("result-raw");
    const technicalContentNode = document.getElementById("technical-content");
    const errorNode = document.getElementById("error-text");
    const copyButton = document.getElementById("copy-result-btn");
    const fallbackTrendTitle = root.getAttribute("data-trend-title") || "";

    const statusLabels = {
      queued: "\u0412 \u043e\u0447\u0435\u0440\u0435\u0434\u0438",
      running: "\u0412 \u0440\u0430\u0431\u043e\u0442\u0435",
      done: "\u0413\u043e\u0442\u043e\u0432\u043e",
      failed: "\u041e\u0448\u0438\u0431\u043a\u0430",
    };

    function renderFromRaw(rawText) {
      const parsed = parseResultText(rawText || "", fallbackTrendTitle);
      renderParsedResult(resultContentNode, parsed, fallbackTrendTitle);
      renderTechnicalDetails(technicalContentNode, parsed, root);
    }

    function applyPayload(payload) {
      if (statusNode) {
        statusNode.dataset.status = payload.status;
        statusNode.textContent = statusLabels[payload.status] || payload.status;
      }

      if (payload.result_text !== undefined && payload.result_text !== null && resultRawNode) {
        resultRawNode.textContent = payload.result_text;
      }

      if (resultRawNode) {
        renderFromRaw(resultRawNode.textContent.trim());
      }

      if (payload.error_message && errorNode) {
        errorNode.textContent = payload.error_message;
        errorNode.classList.remove("hidden");
      }

      if (payload.status === "done" || payload.status === "failed") {
        source.close();
      }
    }

    if (resultRawNode) {
      renderFromRaw(resultRawNode.textContent.trim());
    }
    initCopyButton(copyButton, resultRawNode);

    const source = new EventSource(url);

    source.addEventListener("status", function (event) {
      applyPayload(JSON.parse(event.data));
    });

    source.addEventListener("done", function (event) {
      applyPayload(JSON.parse(event.data));
    });

    source.addEventListener("failed", function (event) {
      applyPayload(JSON.parse(event.data));
    });

    source.onerror = function () {
      source.close();
    };
  }

  function initUploadDropzone() {
    const dropzones = document.querySelectorAll("[data-dropzone]");
    if (!dropzones.length) {
      return;
    }

    const maxFileSizeBytes = 10 * 1024 * 1024;
    const allowedExtensions = [".jpg", ".jpeg", ".png", ".mp4"];
    const allowedMimePrefixes = ["image/jpeg", "image/png", "video/mp4"];

    function isAllowedFile(file) {
      const name = (file.name || "").toLowerCase();
      const hasAllowedExt = allowedExtensions.some(function (ext) {
        return name.endsWith(ext);
      });
      const mime = (file.type || "").toLowerCase();
      const hasAllowedMime = allowedMimePrefixes.some(function (prefix) {
        return mime === prefix;
      });
      return hasAllowedExt || hasAllowedMime;
    }

    function renderStatus(statusNode, text) {
      if (statusNode) {
        statusNode.textContent = text;
      }
    }

    function describeSelectedFiles(files) {
      if (!files.length) {
        return "Файлы не выбраны";
      }
      if (files.length === 1) {
        return "Выбран файл: " + files[0].name;
      }
      const first = files[0].name;
      const second = files[1] ? ", " + files[1].name : "";
      const suffix = files.length > 2 ? " и ещё " + (files.length - 2) : "";
      return "Выбрано файлов: " + files.length + " (" + first + second + suffix + ")";
    }

    dropzones.forEach(function (zone) {
      const input = zone.querySelector("input[type='file']");
      const statusNode = zone.querySelector("[data-dropzone-status]");
      if (!input) {
        return;
      }

      function applyFiles(rawFiles) {
        const selected = [];
        let skippedCount = 0;

        rawFiles.forEach(function (file) {
          if (!isAllowedFile(file) || file.size > maxFileSizeBytes) {
            skippedCount += 1;
            return;
          }
          selected.push(file);
        });

        if (!selected.length) {
          input.value = "";
          zone.classList.remove("has-files");
          zone.classList.add("is-error");
          renderStatus(
            statusNode,
            skippedCount
              ? "Файлы не добавлены: допустимы только JPG, PNG, MP4 до 10MB"
              : "Файлы не выбраны"
          );
          return;
        }

        const transfer = new DataTransfer();
        selected.forEach(function (file) {
          transfer.items.add(file);
        });
        input.files = transfer.files;
        zone.classList.remove("is-error");
        zone.classList.add("has-files");

        const baseStatus = describeSelectedFiles(selected);
        const suffix = skippedCount ? " • Пропущено: " + skippedCount : "";
        renderStatus(statusNode, baseStatus + suffix);
      }

      input.addEventListener("change", function () {
        const files = Array.from(input.files || []);
        applyFiles(files);
      });

      ["dragenter", "dragover"].forEach(function (eventName) {
        zone.addEventListener(eventName, function (event) {
          event.preventDefault();
          zone.classList.add("is-dragover");
        });
      });

      ["dragleave", "dragend"].forEach(function (eventName) {
        zone.addEventListener(eventName, function () {
          zone.classList.remove("is-dragover");
        });
      });

      zone.addEventListener("drop", function (event) {
        event.preventDefault();
        zone.classList.remove("is-dragover");
        const files = Array.from((event.dataTransfer && event.dataTransfer.files) || []);
        applyFiles(files);
      });
    });
  }

  function initAdminTrendsPage() {
    const table = document.querySelector("[data-admin-trends-table]");
    if (!table) {
      return;
    }

    const rows = Array.from(table.querySelectorAll("[data-trend-row]"));
    const searchInput = document.getElementById("admin-trend-search");
    const typeSelect = document.getElementById("admin-trend-type");
    const statusSelect = document.getElementById("admin-trend-status");
    const emptyNote = document.querySelector("[data-admin-trends-empty]");
    const counterNode = document.querySelector("[data-admin-trends-count]");

    function normalize(value) {
      return (value || "").toString().trim().toLowerCase();
    }

    function applyFilters() {
      const query = normalize(searchInput && searchInput.value);
      const selectedType = normalize(typeSelect && typeSelect.value);
      const selectedStatus = normalize(statusSelect && statusSelect.value);
      let visibleCount = 0;

      rows.forEach(function (row) {
        const rowName = normalize(row.getAttribute("data-name"));
        const rowType = normalize(row.getAttribute("data-type"));
        const rowStatus = normalize(row.getAttribute("data-active"));

        const matchesQuery = !query || rowName.indexOf(query) !== -1;
        const matchesType = selectedType === "all" || !selectedType || rowType === selectedType;
        const matchesStatus = selectedStatus === "all" || !selectedStatus || rowStatus === selectedStatus;
        const visible = matchesQuery && matchesType && matchesStatus;

        row.hidden = !visible;
        if (visible) {
          visibleCount += 1;
        }
      });

      if (counterNode) {
        counterNode.textContent = "Показано: " + visibleCount;
      }

      if (emptyNote) {
        emptyNote.hidden = visibleCount > 0;
      }
    }

    if (searchInput) {
      searchInput.addEventListener("input", applyFilters);
    }
    if (typeSelect) {
      typeSelect.addEventListener("change", applyFilters);
    }
    if (statusSelect) {
      statusSelect.addEventListener("change", applyFilters);
    }

    table.querySelectorAll(".admin-toggle-input").forEach(function (input) {
      input.addEventListener("change", function () {
        const form = input.closest("form");
        if (form) {
          form.submit();
        }
      });
    });

    applyFilters();
  }

  initAmbientBackground();
  initGenerationStatusSSE();
  initUploadDropzone();
  initAdminTrendsPage();
})();
