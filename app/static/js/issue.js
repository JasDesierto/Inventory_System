const issueDataNode = document.getElementById("issue-data");

if (issueDataNode) {
    const items = JSON.parse(issueDataNode.textContent || "[]");
    const searchInput = document.getElementById("issue-search");
    const quantityInput = document.getElementById("issue-quantity");
    const results = document.getElementById("issue-results");
    const preview = document.getElementById("issue-preview");
    const hiddenInput = document.getElementById("issue-supply-id");
    const submitButton = document.getElementById("issue-submit");
    const currentStockNode = document.getElementById("issue-current-stock");
    const outgoingQuantityNode = document.getElementById("issue-outgoing-quantity");
    const newTotalNode = document.getElementById("issue-new-total");
    const noteNode = document.getElementById("issue-note");
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

    const updateMath = (item) => {
        const quantity = Math.max(0, Number(quantityInput?.value || 0));
        if (!item) {
            currentStockNode.textContent = "-";
            outgoingQuantityNode.textContent = "0";
            newTotalNode.textContent = "-";
            noteNode.textContent = "Select an item and enter an issue quantity to review the remaining balance.";
            submitButton.disabled = true;
            noteNode.dataset.tone = "neutral";
            return;
        }

        const newTotal = item.current_quantity - quantity;
        currentStockNode.textContent = `${item.current_quantity} ${item.unit}`;
        outgoingQuantityNode.textContent = quantity ? `${quantity} ${item.unit}` : "0";
        newTotalNode.textContent = quantity ? `${Math.max(newTotal, 0)} ${item.unit}` : `${item.current_quantity} ${item.unit}`;

        if (!quantity) {
            noteNode.textContent = "Enter the issue quantity to preview the remaining stock before submission.";
            noteNode.dataset.tone = "neutral";
            submitButton.disabled = true;
            return;
        }

        if (quantity > item.current_quantity) {
            noteNode.textContent = "Issue quantity cannot exceed the current stock level.";
            noteNode.dataset.tone = "danger";
            submitButton.disabled = true;
            return;
        }

        if (newTotal === 0) {
            noteNode.textContent = "This issue will deplete the remaining stock to zero.";
            noteNode.dataset.tone = "danger";
        } else if (newTotal <= item.minimum_quantity) {
            noteNode.textContent = "This issue will bring the item into low stock.";
            noteNode.dataset.tone = "warning";
        } else {
            noteNode.textContent = `After issuing, ${item.item_name} will have ${newTotal} ${item.unit} remaining.`;
            noteNode.dataset.tone = "success";
        }
        submitButton.disabled = !hiddenInput.value;
    };

    const renderPreview = (item) => {
        if (!item) {
            preview.className = "detail-panel detail-panel--empty";
            preview.innerHTML = "<p>Select an item to see its preview before issuing.</p>";
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
        updateMath(item);
    };

    const renderResults = (collection) => {
        if (!collection.length) {
            results.innerHTML = '<p class="empty-state">No available stock matches your search.</p>';
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
                            <p class="result-card__stock">${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)} available</p>
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

    document.getElementById("issue-form").addEventListener("submit", (event) => {
        const item = items.find((entry) => entry.id === selectedId);
        const quantity = Number(quantityInput?.value || 0);
        if (!hiddenInput.value || !item || quantity <= 0 || quantity > item.current_quantity) {
            event.preventDefault();
        }
    });

    syncResults();
}
