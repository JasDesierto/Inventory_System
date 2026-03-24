const restockDataNode = document.getElementById("restock-data");

if (restockDataNode) {
    const items = JSON.parse(restockDataNode.textContent || "[]");
    const searchInput = document.getElementById("restock-search");
    const results = document.getElementById("restock-results");
    const preview = document.getElementById("restock-preview");
    const hiddenInput = document.getElementById("restock-supply-id");
    const submitButton = document.getElementById("restock-submit");
    let selectedId = hiddenInput.value ? Number(hiddenInput.value) : (items[0] ? items[0].id : null);

    const escapeHtml = (value) =>
        String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");

    const filterItems = (query) => {
        if (!query) {
            return items;
        }
        const normalized = query.toLowerCase();
        return items.filter((item) =>
            [item.item_name, item.description, item.category, item.location]
                .join(" ")
                .toLowerCase()
                .includes(normalized)
        );
    };

    const renderPreview = (item) => {
        if (!item) {
            preview.className = "detail-panel detail-panel--empty";
            preview.innerHTML = "<p>Select an item to preview it before restocking.</p>";
            hiddenInput.value = "";
            submitButton.disabled = true;
            return;
        }

        // Inventory values can contain user-managed text, so escape before rendering.
        preview.className = "detail-panel";
        preview.innerHTML = `
            <img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.item_name)}">
            <div class="badge-row">
                <span class="badge badge--${item.status_tone}">${escapeHtml(item.status_label)}</span>
                <span class="badge badge--neutral">${escapeHtml(item.location)}</span>
            </div>
            <h3>${escapeHtml(item.item_name)}</h3>
            <p>${escapeHtml(item.description)}</p>
            <div class="preview-shell">
                <dl>
                    <div><dt>Category</dt><dd>${escapeHtml(item.category)}</dd></div>
                    <div><dt>Current stock</dt><dd>${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Minimum stock</dt><dd>${escapeHtml(item.minimum_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Updated</dt><dd>${escapeHtml(item.updated_at)}</dd></div>
                </dl>
            </div>
        `;
        hiddenInput.value = item.id;
        submitButton.disabled = false;
    };

    const renderResults = (collection) => {
        if (!collection.length) {
            results.innerHTML = '<p class="empty-state">No supplies match your search.</p>';
            renderPreview(null);
            return;
        }

        if (!collection.some((item) => item.id === selectedId)) {
            selectedId = collection[0].id;
        }

        results.innerHTML = collection
            .map(
                (item) => `
                    <button class="result-card ${item.id === selectedId ? "is-selected" : ""}" type="button" data-supply-id="${escapeHtml(item.id)}">
                        <img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.item_name)}">
                        <div class="result-card__meta">
                            <strong>${escapeHtml(item.item_name)}</strong>
                            <p>${escapeHtml(item.category)} - ${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}</p>
                        </div>
                        <span class="badge badge--${item.status_tone}">${escapeHtml(item.status_label)}</span>
                    </button>
                `
            )
            .join("");

        renderPreview(collection.find((item) => item.id === selectedId));
    };

    const syncResults = () => renderResults(filterItems(searchInput.value.trim()));

    searchInput.addEventListener("input", syncResults);
    results.addEventListener("click", (event) => {
        const card = event.target.closest("[data-supply-id]");
        if (!card) {
            return;
        }
        selectedId = Number(card.dataset.supplyId);
        syncResults();
    });

    document.getElementById("restock-form").addEventListener("submit", (event) => {
        if (!hiddenInput.value) {
            event.preventDefault();
        }
    });

    syncResults();
}
