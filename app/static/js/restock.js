const restockDataNode = document.getElementById("restock-data");
const restockSelect = document.querySelector("[data-restock-select]");
const restockPreview = document.getElementById("restock-preview");

if (restockDataNode && restockSelect && restockPreview) {
    const items = JSON.parse(restockDataNode.textContent || "[]");

    const render = (item) => {
        if (!item) {
            restockPreview.innerHTML = `<div class="detail-panel detail-panel--empty"><p>Select a supply to preview its current stock and details.</p></div>`;
            return;
        }

        restockPreview.innerHTML = `
            <div class="preview-shell">
                <img src="${item.photo_url}" alt="${item.item_name}">
                <div class="badge-row">
                    <span class="badge badge--${item.status_tone}">${item.status_label}</span>
                    <span class="badge badge--neutral">${item.location}</span>
                </div>
                <h3>${item.item_name}</h3>
                <p>${item.description}</p>
                <dl>
                    <div><dt>Category</dt><dd>${item.category}</dd></div>
                    <div><dt>Current stock</dt><dd>${item.current_quantity} ${item.unit}</dd></div>
                    <div><dt>Minimum stock</dt><dd>${item.minimum_quantity} ${item.unit}</dd></div>
                    <div><dt>Updated</dt><dd>${item.updated_at}</dd></div>
                </dl>
            </div>
        `;
    };

    const sync = () => {
        const selected = items.find((item) => item.id === Number(restockSelect.value));
        render(selected);
    };

    restockSelect.addEventListener("change", sync);
    sync();
}
