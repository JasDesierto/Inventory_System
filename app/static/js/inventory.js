const inventoryScript = document.getElementById("inventory-data");
const inventoryRoot = document.querySelector("[data-inventory-browser]");

if (inventoryRoot && inventoryScript) {
    const endpoint = inventoryRoot.dataset.endpoint;
    const form = document.getElementById("inventory-filter-form");
    const resultsContainer = document.getElementById("inventory-results");
    const previewContainer = document.getElementById("inventory-preview");
    const resultCount = document.getElementById("inventory-result-count");
    const drawer = document.getElementById("inventory-drawer");
    const drawerContent = document.getElementById("inventory-drawer-content");
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
    let items = JSON.parse(inventoryScript.textContent || "[]");
    let selectedId = items[0] ? items[0].id : null;
    let debounceTimer = null;

    const badgeClass = (tone) => `badge badge--${tone || "neutral"}`;
    const escapeHtml = (value) =>
        String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");

    const renderPreviewMarkup = (item) => {
        if (!item) {
            return `<div class="detail-panel detail-panel--empty"><p>Select an item to preview its full details.</p></div>`;
        }

        const deleteAction = item.delete_url
            ? `
                <form method="post" action="${escapeHtml(item.delete_url)}" data-confirm="Delete this stock item and its transaction history? This cannot be undone.">
                    <input type="hidden" name="_csrf_token" value="${escapeHtml(csrfToken)}">
                    <button class="button button--danger" type="submit">Delete</button>
                </form>
            `
            : "";

        // Inventory values come from the database, so escape them before inserting any HTML string.
        return `
            <div class="preview-shell">
                <img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.item_name)}">
                <div>
                    <div class="badge-row">
                        <span class="${badgeClass(item.status_tone)}">${escapeHtml(item.status_label)}</span>
                        <span class="badge badge--neutral">${escapeHtml(item.category)}</span>
                    </div>
                    <h3>${escapeHtml(item.item_name)}</h3>
                    <p>${escapeHtml(item.description)}</p>
                </div>
                <dl>
                    <div><dt>Current stock</dt><dd>${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Minimum stock</dt><dd>${escapeHtml(item.minimum_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Location</dt><dd>${escapeHtml(item.location)}</dd></div>
                    <div><dt>Last updated</dt><dd>${escapeHtml(item.updated_at)}</dd></div>
                </dl>
                <div class="action-row">
                    <a class="button button--primary" href="${escapeHtml(item.issue_url)}">Issue</a>
                    <a class="button" href="${escapeHtml(item.restock_url)}">Restock</a>
                    ${deleteAction}
                    <a class="button button--ghost" href="${escapeHtml(item.detail_url)}">Open details</a>
                </div>
            </div>
        `;
    };

    const setPreview = (item, mobile = false) => {
        previewContainer.innerHTML = renderPreviewMarkup(item);
        if (mobile && drawer && drawerContent) {
            drawerContent.innerHTML = renderPreviewMarkup(item);
            drawer.classList.add("is-open");
            drawer.setAttribute("aria-hidden", "false");
        }
    };

    const renderResults = () => {
        resultCount.textContent = `${items.length} item${items.length === 1 ? "" : "s"}`;
        if (!items.length) {
            resultsContainer.innerHTML = `<p class="empty-state">No supplies match the current filters.</p>`;
            setPreview(null);
            return;
        }

        if (!items.some((item) => item.id === selectedId)) {
            selectedId = items[0].id;
        }

        resultsContainer.innerHTML = items
            .map(
                (item) => `
                    <button class="result-card ${item.id === selectedId ? "is-selected" : ""}" type="button" data-supply-id="${escapeHtml(item.id)}">
                        <img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.item_name)}">
                        <div class="result-card__meta">
                            <strong>${escapeHtml(item.item_name)}</strong>
                            <p>${escapeHtml(item.category)} · ${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}</p>
                        </div>
                        <span class="${badgeClass(item.status_tone)}">${escapeHtml(item.status_label)}</span>
                    </button>
                `
            )
            .join("");

        const selectedItem = items.find((item) => item.id === selectedId) || items[0];
        setPreview(selectedItem);
    };

    const fetchItems = () => {
        const params = new URLSearchParams();
        new FormData(form).forEach((value, key) => {
            if (value) {
                params.append(key, value);
            }
        });

        fetch(`${endpoint}?${params.toString()}`)
            .then((response) => response.json())
            .then((data) => {
                items = data;
                renderResults();
            });
    };

    form.addEventListener("input", () => {
        window.clearTimeout(debounceTimer);
        debounceTimer = window.setTimeout(fetchItems, 180);
    });
    form.addEventListener("change", fetchItems);

    resultsContainer.addEventListener("click", (event) => {
        const button = event.target.closest("[data-supply-id]");
        if (!button) {
            return;
        }
        selectedId = Number(button.dataset.supplyId);
        const item = items.find((entry) => entry.id === selectedId);
        renderResults();
        setPreview(item, window.matchMedia("(max-width: 960px)").matches);
    });

    drawer?.querySelectorAll("[data-drawer-close]").forEach((element) => {
        element.addEventListener("click", () => {
            drawer.classList.remove("is-open");
            drawer.setAttribute("aria-hidden", "true");
        });
    });

    renderResults();
}
