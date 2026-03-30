document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-pageable]").forEach((container) => {
        // This generic paginator is reused by any server-rendered list that
        // exposes pageable items and a matching controls target.
        const paginationKey = container.dataset.pageable;
        const controls = paginationKey
            ? document.querySelector(`[data-page-controls="${paginationKey}"]`)
            : null;
        const items = Array.from(container.querySelectorAll("[data-page-item]"));
        const pageSize = Math.max(1, Number(container.dataset.pageSize || 10));

        if (!controls || !items.length) {
            if (controls) {
                controls.hidden = true;
            }
            return;
        }

        let currentPage = 1;

        const renderControls = (totalPages) => {
            if (totalPages <= 1) {
                controls.hidden = true;
                controls.innerHTML = "";
                return;
            }

            controls.hidden = false;
            controls.innerHTML = `
                <button class="button button--ghost" type="button" data-page-action="prev" ${currentPage === 1 ? "disabled" : ""}>Previous</button>
                <span class="pagination-bar__status">Page ${currentPage} of ${totalPages}</span>
                <button class="button button--ghost" type="button" data-page-action="next" ${currentPage === totalPages ? "disabled" : ""}>Next</button>
            `;

            controls.querySelector('[data-page-action="prev"]')?.addEventListener("click", () => {
                currentPage -= 1;
                update();
            });
            controls.querySelector('[data-page-action="next"]')?.addEventListener("click", () => {
                currentPage += 1;
                update();
            });
        };

        const update = () => {
            const totalPages = Math.ceil(items.length / pageSize);
            currentPage = Math.min(Math.max(currentPage, 1), totalPages);

            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = startIndex + pageSize;

            items.forEach((item, index) => {
                item.hidden = index < startIndex || index >= endIndex;
            });

            renderControls(totalPages);
        };

        update();
    });
});
