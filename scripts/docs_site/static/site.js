/**
 * nWave docs-site client navigation.
 *
 * Fetches /versions.json (written by build_site.py) and drives three pieces:
 *   - #version-select: switch versions, staying on the same page when it
 *     exists at the target version, else falling back to that version's home.
 *   - #site-nav: the hierarchical left sidebar for the current version, with
 *     the branch containing the current page expanded and highlighted.
 *   - #page-toc: an "on this page" list built from the rendered <h2>/<h3>,
 *     with scrollspy highlighting.
 *
 * Reads the current version + url from <meta> tags injected by the template.
 */
(function () {
  "use strict";

  var VERSIONS_URL = "/versions.json";

  function meta(name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? el.getAttribute("content") : "";
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function loadVersions() {
    return fetch(VERSIONS_URL, { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("status " + r.status);
        return r.json();
      })
      .catch(function (err) {
        console.warn("docs-site: failed to load versions.json", err);
        return null;
      });
  }

  var PINNED = { latest: 0, dev: 1 };

  function sortVersions(versions) {
    return versions.slice().sort(function (a, b) {
      // 'latest' then 'dev' pinned to the top; otherwise newest date first.
      var ap = a.version in PINNED, bp = b.version in PINNED;
      if (ap || bp) {
        if (ap && bp) return PINNED[a.version] - PINNED[b.version];
        return ap ? -1 : 1;
      }
      var ad = a.date || "", bd = b.date || "";
      if (ad !== bd) return bd.localeCompare(ad);
      return (b.version || "").localeCompare(a.version || "");
    });
  }

  // Semver "vX.Y" key for grouping patch releases under their minor line.
  function minorKey(v) {
    var m = /^v(\d+)\.(\d+)\./.exec(v);
    return m ? "v" + m[1] + "." + m[2] : v;
  }

  // ---- version selector ----

  function flattenUrls(nav, version, acc) {
    nav.forEach(function (node) {
      if (node.url) acc.add(node.url.replace("{V}", version));
      if (node.children) flattenUrls(node.children, version, acc);
    });
    return acc;
  }

  function gotoVersion(chosen) {
    var currentUrl = meta("docs-url");
    var currentVersion = meta("docs-version");
    var rel = currentUrl.replace(
      "/" + currentVersion + "/", "/" + chosen.version + "/"
    );
    var urls = flattenUrls(chosen.nav || [], chosen.version, new Set());
    urls.add("/" + chosen.version + "/");
    window.location.href = urls.has(rel) ? rel : "/" + chosen.version + "/";
  }

  // A searchable, grouped version picker. Pinned entries (Latest, dev) sit at
  // the top; released versions collapse to the newest patch per minor line,
  // with a "show all" toggle and a live filter box for jumping to any version.
  function buildVersionPicker(versions, current) {
    var root = document.getElementById("version-picker");
    var button = document.getElementById("version-picker-button");
    if (!root || !button) return;

    var curObj = versions.find(function (v) { return v.version === current; });
    var label =
      current === "latest"
        ? "Latest" + (curObj && curObj.alias_of ? " (" + curObj.alias_of + ")" : "")
        : current === "dev" ? "dev"
          : current;
    root.querySelector(".version-picker__current").textContent = label;

    var pinned = versions.filter(function (v) { return v.version in PINNED; });
    var released = versions.filter(function (v) { return !(v.version in PINNED); });
    // The newest release is already represented by the pinned "Latest (vX.Y.Z)"
    // entry, so drop its standalone row to avoid a duplicate.
    var latestObj = versions.find(function (v) { return v.version === "latest"; });
    var aliasOf = latestObj && latestObj.alias_of;
    if (aliasOf) {
      released = released.filter(function (v) { return v.version !== aliasOf; });
    }
    var curEntry = released.find(function (v) { return v.version === current; });

    // newest patch per minor line (released is already sorted newest-first).
    var seenMinor = {};
    var latestPerMinor = released.filter(function (v) {
      var k = minorKey(v.version);
      if (seenMinor[k]) return false;
      seenMinor[k] = true;
      return true;
    });

    var pop = document.createElement("div");
    pop.className = "version-picker__pop";
    pop.hidden = true;
    pop.innerHTML =
      '<input class="version-picker__search" type="search" ' +
      'placeholder="Filter versions…" aria-label="Filter versions">' +
      '<ul class="version-picker__list" role="listbox"></ul>' +
      '<button type="button" class="version-picker__more"></button>';
    root.appendChild(pop);

    var list = pop.querySelector(".version-picker__list");
    var search = pop.querySelector(".version-picker__search");
    var moreBtn = pop.querySelector(".version-picker__more");
    var showAll = false;

    function label2(v) {
      if (v.version === "latest") {
        return "Latest" +
          (v.alias_of ? " (" + v.alias_of + ")" : "") +
          (v.date ? " · " + v.date : "");
      }
      if (v.version === "dev") return "dev (unreleased)";
      return v.version + (v.date ? " · " + v.date : "");
    }

    function render(filter) {
      filter = (filter || "").trim().toLowerCase();
      var rows = [];
      function add(v, group) {
        // Match the version string AND the aliased tag, so filtering by a
        // version number (e.g. "3.15") still surfaces "Latest (v3.15.1)".
        var hay = (v.version + " " + (v.alias_of || "")).toLowerCase();
        if (filter && hay.indexOf(filter) === -1) return;
        var isCurrent =
          v.version === current ||
          (v.version === "latest" && current === aliasOf);
        rows.push(
          '<li role="option"><button type="button" class="version-picker__opt' +
          (isCurrent ? " current" : "") +
          (group ? " version-picker__opt--grouped" : "") +
          '" data-version="' + esc(v.version) + '">' +
          esc(label2(v)) + "</button></li>"
        );
      }
      pinned.forEach(function (v) { add(v, false); });
      var pool = filter || showAll ? released : latestPerMinor;
      // Always surface the version you're currently viewing, even if it's an
      // older patch hidden by the collapsed (newest-per-minor) view.
      if (!filter && !showAll && pool.indexOf(curEntry) === -1 && curEntry) {
        pool = pool.concat([curEntry]).sort(function (a, b) {
          return (b.version || "").localeCompare(a.version || "", undefined, {
            numeric: true,
          });
        });
      }
      pool.forEach(function (v) { add(v, true); });
      list.innerHTML = rows.join("") ||
        '<li class="version-picker__empty">No match</li>';
      // The "show all" toggle is irrelevant while filtering.
      if (filter) {
        moreBtn.hidden = true;
      } else {
        moreBtn.hidden = released.length === latestPerMinor.length;
        moreBtn.textContent = showAll
          ? "Show latest per release line"
          : "Show all " + released.length + " versions";
      }
    }

    function open() {
      pop.hidden = false;
      button.setAttribute("aria-expanded", "true");
      search.value = "";
      render("");
      search.focus();
    }
    function close() {
      pop.hidden = true;
      button.setAttribute("aria-expanded", "false");
    }
    function toggle() { pop.hidden ? open() : close(); }

    button.addEventListener("click", function (e) {
      e.stopPropagation();
      toggle();
    });
    search.addEventListener("input", function () { render(search.value); });
    moreBtn.addEventListener("click", function () {
      showAll = !showAll;
      render(search.value);
    });
    list.addEventListener("click", function (e) {
      var opt = e.target.closest(".version-picker__opt");
      if (!opt) return;
      var chosen = versions.find(function (v) {
        return v.version === opt.getAttribute("data-version");
      });
      if (chosen) gotoVersion(chosen);
    });
    document.addEventListener("click", function (e) {
      if (!root.contains(e.target)) close();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });
  }

  // ---- sidebar nav ----

  function renderTree(nodes, version, currentUrl) {
    var html = '<ul class="nav-tree">';
    nodes.forEach(function (node) {
      var url = node.url ? node.url.replace("{V}", version) : null;
      var hasChildren = node.children && node.children.length;
      var isCurrent = url && url === currentUrl;
      var cls = hasChildren ? ' class="nav-tree__branch"' : "";
      html += "<li" + cls + ">";
      if (url) {
        html +=
          '<a href="' + esc(url) + '"' +
          (isCurrent ? ' class="current"' : "") + ">" + esc(node.title) + "</a>";
      } else {
        html += '<a href="' +
          (firstUrl(node, version) || "/" + version + "/") +
          '">' + esc(node.title) + "</a>";
      }
      if (hasChildren) html += renderTree(node.children, version, currentUrl);
      html += "</li>";
    });
    return html + "</ul>";
  }

  function firstUrl(node, version) {
    if (node.url) return node.url.replace("{V}", version);
    if (node.children) {
      for (var i = 0; i < node.children.length; i++) {
        var u = firstUrl(node.children[i], version);
        if (u) return u;
      }
    }
    return null;
  }

  function sectionContains(section, version, currentUrl) {
    var found = false;
    (function walk(nodes) {
      nodes.forEach(function (n) {
        if (n.url && n.url.replace("{V}", version) === currentUrl) found = true;
        if (n.children) walk(n.children);
      });
    })(section.children || []);
    return found;
  }

  function populateSidebar(nav, version, currentUrl) {
    var host = document.getElementById("site-nav");
    var sidebar = document.getElementById("doc-sidebar");
    if (!host || !nav) return;
    // Show ONLY the category (Divio section) that contains the current page.
    // The top header carries the cross-category links; the left rail stays
    // focused on where you are. On the landing page (no active category) the
    // rail collapses entirely.
    var active = nav.find(function (s) {
      return sectionContains(s, version, currentUrl);
    });
    if (!active) {
      host.innerHTML = "";
      if (sidebar) sidebar.classList.add("is-empty");
      return;
    }
    host.innerHTML =
      '<div class="nav-section">' +
      '<p class="nav-section__title">' + esc(active.title) + "</p>" +
      renderTree(active.children || [], version, currentUrl) +
      "</div>";
    var cur = host.querySelector("a.current");
    if (cur) cur.scrollIntoView({ block: "nearest" });
  }

  // ---- on-this-page toc + scrollspy ----

  function buildPageToc() {
    var host = document.getElementById("page-toc");
    var main = document.querySelector(".doc");
    if (!host || !main) return;
    var heads = main.querySelectorAll("h2, h3");
    if (!heads.length) return;
    var items = [];
    heads.forEach(function (h) {
      var sec = h.closest("section[id]");
      var id = h.id || (sec && sec.id);
      if (!id) return;
      if (!h.id) h.id = id;
      items.push({ id: id, text: h.textContent.trim(), level: h.tagName === "H3" ? 3 : 2 });
    });
    if (!items.length) return;
    var html = '<p class="page-toc__heading">On this page</p><ul>';
    items.forEach(function (it) {
      html += '<li class="lvl-' + it.level + '"><a href="#' +
        encodeURIComponent(it.id) + '">' + esc(it.text) + "</a></li>";
    });
    host.innerHTML = html + "</ul>";
    wireScrollspy(items, host);
  }

  function wireScrollspy(items, host) {
    var links = {};
    host.querySelectorAll("a").forEach(function (a) {
      links[decodeURIComponent(a.getAttribute("href").slice(1))] = a;
    });
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          Object.keys(links).forEach(function (k) {
            links[k].classList.remove("active");
          });
          var id = e.target.id;
          if (links[id]) links[id].classList.add("active");
        });
      },
      { rootMargin: "-10% 0px -80% 0px", threshold: 0 }
    );
    items.forEach(function (it) {
      var el = document.getElementById(it.id);
      if (el) observer.observe(el);
    });
  }

  // ---- mobile sidebar toggle ----

  function wireSidebarToggle() {
    var btn = document.getElementById("sidebar-toggle");
    var sidebar = document.getElementById("doc-sidebar");
    if (!btn || !sidebar) return;
    btn.addEventListener("click", function () {
      var open = sidebar.classList.toggle("open");
      btn.setAttribute("aria-expanded", String(open));
    });
  }

  function init() {
    buildPageToc();
    wireSidebarToggle();
    wireSearch();
    loadVersions().then(function (data) {
      if (!data || !data.versions || !data.versions.length) return;
      var versions = sortVersions(data.versions);
      var current = meta("docs-version");
      var currentUrl = meta("docs-url");
      buildVersionPicker(versions, current);
      var entry = versions.find(function (v) { return v.version === current; });
      if (entry) populateSidebar(entry.nav, current, currentUrl);
    });
  }

  // ---- search (Pagefind, loaded on demand) ----

  function wireSearch() {
    var trigger = document.getElementById("search-trigger");
    var overlay = document.getElementById("search-overlay");
    if (!trigger || !overlay) return;
    var loaded = false;

    function loadPagefind() {
      if (loaded) return Promise.resolve();
      loaded = true;
      var css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = "/pagefind/pagefind-ui.css";
      document.head.appendChild(css);
      return import("/pagefind/pagefind-ui.js")
        .then(function () {
          /* global PagefindUI */
          new PagefindUI({
            element: "#search-box",
            showSubResults: true,
            showImages: false,
          });
        })
        .catch(function (err) {
          console.warn("docs-site: search index not available", err);
          document.getElementById("search-box").innerHTML =
            '<p class="search-unavailable">Search isn’t available in this ' +
            "build. It is generated at deploy time.</p>";
        });
    }

    function open() {
      overlay.hidden = false;
      document.body.classList.add("search-open");
      loadPagefind().then(function () {
        var input = overlay.querySelector("input");
        if (input) input.focus();
      });
    }
    function close() {
      overlay.hidden = true;
      document.body.classList.remove("search-open");
    }

    trigger.addEventListener("click", open);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });
    document.addEventListener("keydown", function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      var typing = tag === "input" || tag === "textarea";
      if (e.key === "/" && !typing && overlay.hidden) {
        e.preventDefault();
        open();
      } else if (e.key === "Escape" && !overlay.hidden) {
        close();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
