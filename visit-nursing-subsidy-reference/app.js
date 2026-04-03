(function () {
  "use strict";

  const data = window.SUBSIDY_REFERENCE_DATA;
  if (!data) {
    console.error("SUBSIDY_REFERENCE_DATA が読み込まれていません");
    return;
  }

  const LEVEL_LABEL = {
    national: "国",
    prefecture: "都道府県",
    municipality: "市区町村",
  };

  const form = document.getElementById("region-form");
  const prefSelect = document.getElementById("prefecture");
  const citySelect = document.getElementById("municipality");
  const cityFilter = document.getElementById("municipality-filter");
  const resetBtn = document.getElementById("reset-btn");
  const resultsSection = document.getElementById("results-section");
  const resultsSummary = document.getElementById("results-summary");
  const resultsList = document.getElementById("results-list");
  const resultsEmpty = document.getElementById("results-empty");
  const cardTemplate = document.getElementById("card-template");
  let resultsEverShown = false;
  /** @type {{ code: string, name: string }[]} */
  let fullCitiesForPref = [];
  let filterDebounce = null;

  function fillPrefectures() {
    const frag = document.createDocumentFragment();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "選択してください";
    frag.appendChild(placeholder);
    data.prefectures.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.code;
      opt.textContent = p.name;
      frag.appendChild(opt);
    });
    prefSelect.innerHTML = "";
    prefSelect.appendChild(frag);
  }

  function rebuildCityOptions(filterText, preferredCode) {
    const q = filterText.trim().toLowerCase();
    const frag = document.createDocumentFragment();
    const anyOpt = document.createElement("option");
    anyOpt.value = "";
    anyOpt.textContent = "指定しない（県レベルまでで表示）";
    frag.appendChild(anyOpt);

    const list = !q
      ? fullCitiesForPref
      : fullCitiesForPref.filter((c) => c.name.toLowerCase().includes(q));

    if (list.length === 0 && q) {
      const empty = document.createElement("option");
      empty.value = "";
      empty.disabled = true;
      empty.textContent = "（該当なし。キーワードを変えてください）";
      frag.appendChild(empty);
    } else {
      list.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.code;
        opt.textContent = c.name;
        frag.appendChild(opt);
      });
    }

    citySelect.innerHTML = "";
    citySelect.appendChild(frag);

    if (preferredCode && list.some((c) => c.code === preferredCode)) {
      citySelect.value = preferredCode;
    } else {
      citySelect.value = "";
    }
  }

  function fillCities(prefCode) {
    cityFilter.value = "";
    fullCitiesForPref = [];
    if (!prefCode) {
      cityFilter.hidden = true;
      citySelect.innerHTML = "";
      citySelect.disabled = true;
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "都道府県を先に選択";
      citySelect.appendChild(opt);
      return;
    }
    fullCitiesForPref = data.municipalities[prefCode] || [];
    cityFilter.hidden = fullCitiesForPref.length === 0;
    citySelect.disabled = false;
    rebuildCityOptions("", "");
  }

  /**
   * 候補判定:
   * - 国: 常に表示
   * - 県: 選択県と一致
   * - 市: 選択市が cityCodes に含まれる、または市未選択なら同県の市町村条項は「県全体向け」としては出さない（市データは特定市のみ）
   */
  function filterPrograms(prefCode, cityCode) {
    return data.programs.filter((prog) => {
      if (prog.level === "national") return true;
      if (prog.level === "prefecture") {
        return prog.prefectureCode === prefCode;
      }
      if (prog.level === "municipality") {
        if (prog.prefectureCode !== prefCode) return false;
        if (!cityCode) return false;
        return Array.isArray(prog.cityCodes) && prog.cityCodes.includes(cityCode);
      }
      return false;
    });
  }

  function sortPrograms(list) {
    const order = { national: 0, prefecture: 1, municipality: 2 };
    return [...list].sort((a, b) => {
      const d = order[a.level] - order[b.level];
      if (d !== 0) return d;
      return a.title.localeCompare(b.title, "ja");
    });
  }

  /**
   * official-meta.js の旧形式（1URL分がフラット）と新形式 { sources: [] } の両対応
   */
  function normalizePageMeta(raw) {
    if (!raw || typeof raw !== "object") return null;
    if (Array.isArray(raw.sources)) return raw;
    if ("requestedUrl" in raw || "pageTitle" in raw || "ok" in raw) {
      return {
        fetchedAt: raw.fetchedAt,
        sources: [
          {
            requestedUrl: raw.requestedUrl,
            finalUrl: raw.finalUrl,
            pageTitle: raw.pageTitle,
            description: raw.description,
            ok: raw.ok,
            error: raw.error,
          },
        ],
      };
    }
    return null;
  }

  function renderCard(prog) {
    const node = cardTemplate.content.cloneNode(true);
    const levelPill = node.querySelector(".pill--level");
    const tagsPill = node.querySelector(".pill--tags");
    const title = node.querySelector(".card__title");
    const summary = node.querySelector(".card__summary");
    const note = node.querySelector(".card__note");
    const link = node.querySelector(".card__link");
    const verified = node.querySelector(".card__verified");
    const live = node.querySelector(".card__live");
    const staticWrap = node.querySelector(".card__static-urls-wrap");
    const staticUl = node.querySelector(".card__static-urls");
    const liveSources = node.querySelector(".card__live-sources");

    levelPill.textContent = LEVEL_LABEL[prog.level] || prog.level;
    tagsPill.textContent = (prog.tags || []).join(" · ");
    title.textContent = prog.title;
    summary.textContent = prog.summary;
    note.textContent = prog.note || "";
    note.hidden = !prog.note;
    link.href = prog.officialUrl;
    link.setAttribute("aria-label", `${prog.title}の公式情報を新しいタブで開く`);
    verified.textContent = `最終確認日（参考）: ${prog.lastVerified}`;

    const regUrls = [];
    if (prog.officialUrl) regUrls.push(prog.officialUrl);
    (prog.sourceUrls || []).forEach((u) => {
      if (u && !regUrls.includes(u)) regUrls.push(u);
    });

    if (regUrls.length) {
      staticWrap.hidden = false;
      staticUl.innerHTML = "";
      regUrls.forEach((u) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = u;
        a.textContent = u;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        li.appendChild(a);
        staticUl.appendChild(li);
      });
    } else {
      staticWrap.hidden = true;
    }

    const rawMeta =
      typeof window.OFFICIAL_PAGE_META !== "undefined"
        ? window.OFFICIAL_PAGE_META[prog.id]
        : null;
    const pageMeta = normalizePageMeta(rawMeta);

    liveSources.innerHTML = "";
    if (pageMeta && pageMeta.sources && pageMeta.sources.length) {
      pageMeta.sources.forEach((src, idx) => {
        const art = document.createElement("article");
        art.className = "card__live-source";
        const h = document.createElement("h4");
        h.className = "card__live-source-heading";
        h.textContent = `取得サイト ${idx + 1}`;
        art.appendChild(h);

        const req = src.requestedUrl || "";
        const fin = src.finalUrl || req;
        const urlP = document.createElement("p");
        urlP.className = "card__live-source-url";
        const open = document.createElement("a");
        open.href = fin || "#";
        open.textContent = req || fin;
        open.target = "_blank";
        open.rel = "noopener noreferrer";
        urlP.appendChild(open);
        art.appendChild(urlP);

        if (src.ok) {
          if (src.pageTitle) {
            const tp = document.createElement("p");
            tp.className = "card__live-source-title";
            tp.textContent = `ページタイトル: ${src.pageTitle}`;
            art.appendChild(tp);
          }
          if (src.description) {
            const dp = document.createElement("p");
            dp.className = "card__live-source-desc";
            dp.textContent = src.description;
            art.appendChild(dp);
          }
          const mp = document.createElement("p");
          mp.className = "card__live-source-meta";
          let metaTxt = pageMeta.fetchedAt ? `取得日時: ${pageMeta.fetchedAt}` : "";
          if (fin && fin !== req) {
            metaTxt += `${metaTxt ? " ・ " : ""}リダイレクト先: ${fin}`;
          }
          mp.textContent = metaTxt;
          art.appendChild(mp);
        } else {
          const ep = document.createElement("p");
          ep.className = "card__live-source-err";
          ep.textContent = src.error
            ? `取得失敗: ${src.error}（リンクから直接開いて確認してください）`
            : "取得に失敗しました。";
          art.appendChild(ep);
        }
        liveSources.appendChild(art);
      });
    }

    const hasFetched =
      pageMeta && pageMeta.sources && pageMeta.sources.length > 0;
    live.hidden = regUrls.length === 0 && !hasFetched;

    return node;
  }

  function showResults(prefCode, cityCode, opts) {
    const scroll = !opts || opts.scroll !== false;
    const pref = data.prefectures.find((p) => p.code === prefCode);
    const prefName = pref ? pref.name : "";
    let cityName = "";
    if (cityCode && data.municipalities[prefCode]) {
      const c = data.municipalities[prefCode].find((x) => x.code === cityCode);
      cityName = c ? c.name : "";
    }

    const matched = sortPrograms(filterPrograms(prefCode, cityCode));
    resultsList.innerHTML = "";

    const loc =
      cityName ? `${prefName} ${cityName}` : `${prefName}（市区町村は指定なし）`;
    const hint = cityCode
      ? ""
      : " 区市町村独自の制度は、市区町村を選ぶと追加で表示されます。";
    resultsSummary.textContent = `${loc} の条件で、データ上 ${matched.length} 件の候補があります。${hint}`;

    if (matched.length === 0) {
      resultsEmpty.hidden = false;
    } else {
      resultsEmpty.hidden = true;
      matched.forEach((p) => {
        resultsList.appendChild(renderCard(p));
      });
    }

    resultsSection.hidden = false;
    resultsEverShown = true;
    if (scroll) {
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function refreshIfVisible() {
    if (!resultsEverShown || resultsSection.hidden) return;
    const pref = prefSelect.value;
    if (!pref) return;
    showResults(pref, citySelect.value || "", { scroll: false });
  }

  prefSelect.addEventListener("change", () => {
    fillCities(prefSelect.value);
    refreshIfVisible();
  });

  citySelect.addEventListener("change", () => {
    refreshIfVisible();
  });

  cityFilter.addEventListener("input", () => {
    window.clearTimeout(filterDebounce);
    filterDebounce = window.setTimeout(() => {
      const keep = citySelect.value;
      rebuildCityOptions(cityFilter.value, keep);
      refreshIfVisible();
    }, 120);
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const pref = prefSelect.value;
    if (!pref) {
      prefSelect.focus();
      return;
    }
    const city = citySelect.value || "";
    showResults(pref, city, { scroll: true });
  });

  resetBtn.addEventListener("click", () => {
    setTimeout(() => {
      cityFilter.value = "";
      cityFilter.hidden = true;
      fillCities("");
      resultsSection.hidden = true;
      resultsEverShown = false;
      resultsList.innerHTML = "";
      resultsEmpty.hidden = true;
    }, 0);
  });

  fillPrefectures();
  fillCities("");
})();
