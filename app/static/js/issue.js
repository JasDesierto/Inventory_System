const issueDataNode = document.getElementById("issue-data");

if (issueDataNode) {
    const items = JSON.parse(issueDataNode.textContent || "[]");
    const searchInput = document.getElementById("issue-search");
    const results = document.getElementById("issue-results");
    const preview = document.getElementById("issue-preview");
    const hiddenInput = document.getElementById("issue-supply-id");
    const submitButton = document.getElementById("issue-submit");
    let selectedId = hiddenInput.value ? Number(hiddenInput.value) : (items[0] ? items[0].id : null);

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
            preview.innerHTML = "<p>Select an item to see its preview before issuing.</p>";
            hiddenInput.value = "";
            submitButton.disabled = true;
            return;
        }

        preview.className = "detail-panel";
        preview.innerHTML = `
            <img src="${item.photo_url}" alt="${item.item_name}">
            <div class="badge-row">
                <span class="badge badge--${item.status_tone}">${item.status_label}</span>
                <span class="badge badge--neutral">${item.location}</span>
            </div>
            <h3>${item.item_name}</h3>
            <p>${item.description}</p>
            <div class="preview-shell">
                <dl>
                    <div><dt>Category</dt><dd>${item.category}</dd></div>
                    <div><dt>Current stock</dt><dd>${item.current_quantity} ${item.unit}</dd></div>
                    <div><dt>Minimum stock</dt><dd>${item.minimum_quantity} ${item.unit}</dd></div>
                    <div><dt>Updated</dt><dd>${item.updated_at}</dd></div>
                </dl>
            </div>
        `;
        hiddenInput.value = item.id;
        submitButton.disabled = false;
    };

    const renderResults = (collection) => {
        if (!collection.length) {
            results.innerHTML = `<p class="empty-state">No available stock matches your search.</p>`;
            renderPreview(null);
            return;
        }

        if (!collection.some((item) => item.id === selectedId)) {
            selectedId = collection[0].id;
        }

        results.innerHTML = collection
            .map(
                (item) => `
                    <button class="result-card ${item.id === selectedId ? "is-selected" : ""}" type="button" data-supply-id="${item.id}">
                        <img src="${item.photo_url}" alt="${item.item_name}">
                        <div class="result-card__meta">
                            <strong>${item.item_name}</strong>
                            <p>${item.category} · ${item.current_quantity} ${item.unit}</p>
                        </div>
                        <span class="badge badge--${item.status_tone}">${item.status_label}</span>
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

    document.getElementById("issue-form").addEventListener("submit", (event) => {
        if (!hiddenInput.value) {
            event.preventDefault();
        }
    });

    syncResults();
}
