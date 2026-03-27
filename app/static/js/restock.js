const restockDataNode = document.getElementById("restock-data");

if (restockDataNode) {
    const items = JSON.parse(restockDataNode.textContent || "[]");
    const categoryFilter = document.getElementById("restock-category-filter");
    const categorySelect = document.getElementById("restock-category");
    const searchInput = document.getElementById("restock-search");
    const quantityInput = document.getElementById("restock-quantity");
    const results = document.getElementById("restock-results");
    const preview = document.getElementById("restock-preview");
    const hiddenInput = document.getElementById("restock-supply-id");
    const submitButton = document.getElementById("restock-submit");
    const currentStockNode = document.getElementById("restock-current-stock");
    const addQuantityNode = document.getElementById("restock-add-quantity");
    const newTotalNode = document.getElementById("restock-new-total");
    const noteNode = document.getElementById("restock-note");
    let selectedId = hiddenInput.value ? Number(hiddenInput.value) : (items[0] ? items[0].id : null);
    let lastPreviewSupplyId = categorySelect?.value && selectedId ? selectedId : null;

    const escapeHtml = (value) =>
        String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");

    const filterItems = (query, category) => {
        const normalized = query.toLowerCase();
        return items.filter((item) => {
            const matchesCategory = !category || item.category === category;
            const matchesQuery = !query || [item.item_name, item.description, item.category, item.location]
                .join(" ")
                .toLowerCase()
                .includes(normalized);
            return matchesCategory && matchesQuery;
        });
    };

    const updateMath = (item) => {
        const quantity = Math.max(0, Number(quantityInput?.value || 0));
        if (!item) {
            currentStockNode.textContent = "-";
            addQuantityNode.textContent = "0";
            newTotalNode.textContent = "-";
            noteNode.textContent = "Select an item and enter a quantity to preview the updated stock total.";
            submitButton.disabled = true;
            return;
        }

        const newTotal = item.current_quantity + quantity;
        currentStockNode.textContent = `${item.current_quantity} ${item.unit}`;
        addQuantityNode.textContent = quantity ? `${quantity} ${item.unit}` : "0";
        newTotalNode.textContent = quantity ? `${newTotal} ${item.unit}` : `${item.current_quantity} ${item.unit}`;
        noteNode.textContent = quantity
            ? `This restock will increase ${item.item_name} from ${item.current_quantity} to ${newTotal} ${item.unit}.`
            : "Enter the incoming quantity to review the new stock total before submission.";
        submitButton.disabled = !(hiddenInput.value && categorySelect?.value && quantity > 0);
    };

    const renderPreview = (item) => {
        if (!item) {
            preview.className = "detail-panel detail-panel--empty";
            preview.innerHTML = "<p>Select an item to preview it before restocking.</p>";
            hiddenInput.value = "";
            updateMath(null);
            return;
        }

        preview.className = "detail-panel detail-panel--transaction";
        preview.innerHTML = `
            <div class="transaction-preview">
                <div class="transaction-preview__hero">
                    <img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.item_name)}">
                    <div>
                        <div class="badge-row">
                            <span class="badge badge--${item.status_tone}">${escapeHtml(item.status_label)}</span>
                            <span class="badge badge--neutral">${escapeHtml(item.location)}</span>
                        </div>
                        <h3>${escapeHtml(item.item_name)}</h3>
                        <p>${escapeHtml(item.description)}</p>
                    </div>
                </div>
                <dl class="transaction-preview__metrics">
                    <div><dt>Category</dt><dd>${escapeHtml(item.category)}</dd></div>
                    <div><dt>Current stock</dt><dd>${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Minimum stock</dt><dd>${escapeHtml(item.minimum_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Updated</dt><dd>${escapeHtml(item.updated_at)}</dd></div>
                </dl>
            </div>
        `;
        hiddenInput.value = item.id;
        if (item.id !== lastPreviewSupplyId && categorySelect) {
            categorySelect.value = item.category;
            lastPreviewSupplyId = item.id;
        }
        updateMath(item);
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
                            <p class="result-card__context">${escapeHtml(item.category)} &middot; ${escapeHtml(item.location)}</p>
                            <p class="result-card__stock">${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)} on hand</p>
                        </div>
                        <span class="badge badge--${item.status_tone}">${escapeHtml(item.status_label)}</span>
                    </button>
                `
            )
            .join("");

        renderPreview(collection.find((item) => item.id === selectedId));
    };

    const syncResults = () => renderResults(filterItems(searchInput.value.trim(), categoryFilter?.value || ""));

    searchInput.addEventListener("input", syncResults);
    categoryFilter?.addEventListener("change", syncResults);
    quantityInput?.addEventListener("input", () => {
        const item = items.find((entry) => entry.id === selectedId);
        updateMath(item || null);
    });

    results.addEventListener("click", (event) => {
        const card = event.target.closest("[data-supply-id]");
        if (!card) {
            return;
        }
        selectedId = Number(card.dataset.supplyId);
        syncResults();
    });

    document.getElementById("restock-form").addEventListener("submit", (event) => {
        if (!hiddenInput.value || !categorySelect?.value || Number(quantityInput?.value || 0) <= 0) {
            event.preventDefault();
        }
    });

    if (categoryFilter && items.some((item) => item.id === selectedId)) {
        categoryFilter.value = items.find((item) => item.id === selectedId)?.category || "";
    }
    syncResults();
}
