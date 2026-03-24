const stockCardDataNode = document.getElementById("stock-card-data");
const stockCardRoot = document.querySelector("[data-stock-card-browser]");

if (stockCardDataNode && stockCardRoot) {
    const items = JSON.parse(stockCardDataNode.textContent || "[]");
    const categorySelect = document.getElementById("stock-card-category");
    const searchInput = document.getElementById("stock-card-search");
    const results = document.getElementById("stock-card-results");
    const preview = document.getElementById("stock-card-preview");
    const sheet = document.getElementById("stock-card-sheet");
    const printButton = document.getElementById("stock-card-print-button");
    const endpointBase = "/api/supplies";
    const initialCategory = stockCardRoot.dataset.initialCategory || "";
    let selectedId = stockCardRoot.dataset.selectedSupplyId
        ? Number(stockCardRoot.dataset.selectedSupplyId)
        : (items[0] ? items[0].id : null);
    let activeRequestKey = 0;

    const escapeHtml = (value) =>
        String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");

    const quantityText = (item) => `${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}`;

    const filterItems = () => {
        const query = searchInput.value.trim().toLowerCase();
        const category = categorySelect.value;
        return items.filter((item) => {
            const matchesCategory = !category || item.category === category;
            const matchesQuery = !query || [item.item_name, item.description, item.category, item.location]
                .join(" ")
                .toLowerCase()
                .includes(query);
            return matchesCategory && matchesQuery;
        });
    };

    const renderResults = (collection) => {
        if (!collection.length) {
            results.innerHTML = '<p class="empty-state">No supplies match the current category or search.</p>';
            preview.innerHTML = '<div class="detail-panel detail-panel--empty"><p>Select another category or search term.</p></div>';
            sheet.className = "stock-card-sheet stock-card-sheet--empty";
            sheet.innerHTML = "<p>No printable stock card is available for the current filter.</p>";
            printButton.disabled = true;
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
                            <p>${escapeHtml(item.category)} &middot; ${escapeHtml(item.current_quantity)} ${escapeHtml(item.unit)}</p>
                        </div>
                        <span class="badge badge--${escapeHtml(item.status_tone)}">${escapeHtml(item.status_label)}</span>
                    </button>
                `
            )
            .join("");
    };

    const renderPreview = (item) => {
        if (!item) {
            preview.innerHTML = '<div class="detail-panel detail-panel--empty"><p>Select a stock item to preview it.</p></div>';
            return;
        }

        preview.innerHTML = `
            <div class="preview-shell">
                <img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.item_name)}">
                <div>
                    <div class="badge-row">
                        <span class="badge badge--${escapeHtml(item.status_tone)}">${escapeHtml(item.status_label)}</span>
                        <span class="badge badge--neutral">${escapeHtml(item.category)}</span>
                    </div>
                    <h3>${escapeHtml(item.item_name)}</h3>
                    <p>${escapeHtml(item.description)}</p>
                </div>
                <dl>
                    <div><dt>Current stock</dt><dd>${quantityText(item)}</dd></div>
                    <div><dt>Minimum stock</dt><dd>${escapeHtml(item.minimum_quantity)} ${escapeHtml(item.unit)}</dd></div>
                    <div><dt>Location</dt><dd>${escapeHtml(item.location)}</dd></div>
                    <div><dt>Last updated</dt><dd>${escapeHtml(item.updated_at)}</dd></div>
                </dl>
                <div class="action-row">
                    <a class="button button--ghost" href="${escapeHtml(item.detail_url)}">Open details</a>
                    <a class="button" href="${escapeHtml(item.restock_url)}">Restock</a>
                    <a class="button button--primary" href="${escapeHtml(item.issue_url)}">Issue</a>
                </div>
            </div>
        `;
    };

    const renderSheet = (card) => {
        const ledgerRows = card.ledger_rows || [];
        const trailingBlankRows = ledgerRows.length ? 4 : 5;
        const rows = ledgerRows
            .map(
                (row) => `
                    <tr>
                        <td>${escapeHtml(row.date)}</td>
                        <td>&nbsp;</td>
                        <td>${escapeHtml(row.receipt_quantity)}</td>
                        <td>${escapeHtml(row.issue_quantity)}</td>
                        <td>${escapeHtml(row.office)}</td>
                        <td>${escapeHtml(row.balance_quantity)}</td>
                        <td>${escapeHtml(row.days_to_consume)}</td>
                    </tr>
                `
            )
            .join("");
        const blankRows = Array.from(
            { length: trailingBlankRows },
            () => `
                <tr>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
            `
        ).join("");

        sheet.className = "stock-card-sheet";
        sheet.innerHTML = `
            <section class="stock-card-form" aria-label="Stock card form">
                <div class="stock-card-form__appendix">${escapeHtml(card.appendix_label)}</div>
                <div class="stock-card-form__title">STOCK CARD</div>
                <div class="stock-card-form__line stock-card-form__line--two">
                    <div><span>Entity Name:</span> ${escapeHtml(card.entity_name)}</div>
                    <div><span>Fund Cluster:</span> _________________</div>
                </div>
                <div class="stock-card-form__line stock-card-form__line--two">
                    <div><span>Item :</span> ${escapeHtml(card.item_name)}</div>
                    <div><span>Stock No. :</span> ${escapeHtml(card.stock_no)}</div>
                </div>
                <div class="stock-card-form__line">
                    <div><span>Description :</span> ${escapeHtml(card.description)}</div>
                </div>
                <div class="stock-card-form__line">
                    <div><span>Unit of Measurement :</span> ${escapeHtml(card.unit)}</div>
                </div>
                <table class="stock-card-table">
                    <colgroup>
                        <col class="stock-card-col-date">
                        <col class="stock-card-col-reference">
                        <col class="stock-card-col-receipt">
                        <col class="stock-card-col-issue-qty">
                        <col class="stock-card-col-office">
                        <col class="stock-card-col-balance">
                        <col class="stock-card-col-days">
                    </colgroup>
                    <thead>
                        <tr>
                            <th rowspan="2">Date</th>
                            <th rowspan="2">Reference</th>
                            <th>Receipt</th>
                            <th colspan="2">Issue</th>
                            <th>Balance</th>
                            <th rowspan="2">No. of Days to Consume</th>
                        </tr>
                        <tr>
                            <th>Qty.</th>
                            <th>Qty.</th>
                            <th>Office</th>
                            <th>Qty.</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}${blankRows}
                    </tbody>
                </table>
                <div class="stock-card-form__signature">
                    <div class="stock-card-form__signature-name">JASTEN DWIGHT B. DESIERTO</div>
                    <div class="stock-card-form__signature-role">Property Custodian</div>
                </div>
            </section>
        `;
        printButton.disabled = false;
    };

    const loadCard = () => {
        const item = items.find((entry) => entry.id === selectedId);
        renderPreview(item);
        if (!item) {
            printButton.disabled = true;
            return;
        }

        const requestKey = ++activeRequestKey;
        sheet.className = "stock-card-sheet stock-card-sheet--loading";
        sheet.innerHTML = "<p>Loading stock card data...</p>";

        fetch(`${endpointBase}/${selectedId}/stock-card`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Unable to load stock card.");
                }
                return response.json();
            })
            .then((card) => {
                if (requestKey === activeRequestKey) {
                    renderSheet(card);
                }
            })
            .catch(() => {
                if (requestKey === activeRequestKey) {
                    sheet.className = "stock-card-sheet stock-card-sheet--empty";
                    sheet.innerHTML = "<p>The stock card could not be loaded.</p>";
                    printButton.disabled = true;
                }
            });
    };

    const syncView = () => {
        const collection = filterItems();
        renderResults(collection);
        if (!collection.length) {
            return;
        }
        loadCard();
    };

    categorySelect.value = initialCategory;

    searchInput.addEventListener("input", syncView);
    categorySelect.addEventListener("change", syncView);
    results.addEventListener("click", (event) => {
        const card = event.target.closest("[data-supply-id]");
        if (!card) {
            return;
        }
        selectedId = Number(card.dataset.supplyId);
        syncView();
    });
    printButton.addEventListener("click", () => window.print());

    syncView();
}
