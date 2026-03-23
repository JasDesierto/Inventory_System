document.addEventListener("DOMContentLoaded", () => {
    let pageIsLeaving = false;
    const loginEntryStorageKey = "app-entry-from-login";

    const startPageTransition = () => {
        if (pageIsLeaving) {
            return false;
        }

        pageIsLeaving = true;
        document.body.classList.add("page-is-leaving");
        return true;
    };

    const isNavigableLink = (link) => {
        if (!link || !link.href) {
            return false;
        }

        if (link.target && link.target !== "_self") {
            return false;
        }

        if (link.hasAttribute("download")) {
            return false;
        }

        const url = new URL(link.href, window.location.href);
        return url.origin === window.location.origin && url.href !== window.location.href && !url.hash;
    };

    window.addEventListener("pageshow", () => {
        pageIsLeaving = false;
        document.body.classList.remove("page-is-leaving");
    });

    document.addEventListener("click", (event) => {
        if (event.defaultPrevented || event.button !== 0) {
            return;
        }

        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }

        const link = event.target.closest("a[href]");
        if (!isNavigableLink(link)) {
            return;
        }

        event.preventDefault();

        if (!startPageTransition()) {
            return;
        }

        window.setTimeout(() => {
            window.location.assign(link.href);
        }, 55);
    });

    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) {
            return;
        }

        if (form.dataset.noPageTransition === "true" || form.dataset.transitionSubmitted === "true") {
            return;
        }

        if (!startPageTransition()) {
            return;
        }

        try {
            if (document.body.classList.contains("body--landing")) {
                const actionUrl = new URL(form.action || window.location.href, window.location.href);
                if (actionUrl.pathname.includes("/auth/login")) {
                    sessionStorage.setItem(loginEntryStorageKey, "1");
                }
            }
        } catch (_error) {
            // Ignore storage access issues and continue with the standard navigation.
        }

        form.dataset.transitionSubmitted = "true";
        event.preventDefault();

        const submitter = event.submitter;
        window.setTimeout(() => {
            if (submitter && typeof form.requestSubmit === "function") {
                form.requestSubmit(submitter);
                return;
            }

            HTMLFormElement.prototype.submit.call(form);
        }, 55);
    });

    document.querySelectorAll("[data-image-input]").forEach((input) => {
        input.addEventListener("change", () => {
            const targetSelector = input.getAttribute("data-preview-target");
            const target = targetSelector ? document.querySelector(targetSelector) : null;
            const file = input.files && input.files[0];
            if (!target || !file) {
                return;
            }

            const reader = new FileReader();
            reader.onload = (event) => {
                target.innerHTML = `<img src="${event.target.result}" alt="Selected image preview">`;
            };
            reader.readAsDataURL(file);
        });
    });

    document.querySelectorAll("[data-video-shell]").forEach((shell) => {
        const videos = Array.from(shell.querySelectorAll("[data-bg-video]"));
        if (!videos.length) {
            return;
        }

        let activeIndex = 0;
        let loopTimer = null;

        const clearLoopTimer = () => {
            if (loopTimer) {
                window.clearTimeout(loopTimer);
                loopTimer = null;
            }
        };

        const settleComposition = () => {
            window.setTimeout(() => {
                shell.classList.add("auth-layout--is-settled");
                shell.classList.remove("auth-layout--booting");
            }, 40);
        };

        const markReady = () => {
            shell.classList.add("auth-layout--video-ready");
        };

        const activateVideo = (index) => {
            activeIndex = index;
            videos.forEach((video, videoIndex) => {
                video.classList.toggle("is-active", videoIndex === index);
            });
        };

        const playVideo = (video, restart = false) => {
            if (restart) {
                video.currentTime = 0;
            }

            const playPromise = video.play();
            if (playPromise && typeof playPromise.catch === "function") {
                playPromise.catch(() => {
                    markReady();
                });
            }
        };

        const scheduleLoopBlend = () => {
            clearLoopTimer();

            if (videos.length < 2) {
                videos[0].loop = true;
                return;
            }

            const activeVideo = videos[activeIndex];
            if (!Number.isFinite(activeVideo.duration) || activeVideo.duration <= 0) {
                loopTimer = window.setTimeout(scheduleLoopBlend, 120);
                return;
            }

            const nextIndex = activeIndex === 0 ? 1 : 0;
            const nextVideo = videos[nextIndex];
            const blendLead = Math.min(0.28, Math.max(0.14, activeVideo.duration * 0.08));
            const waitMs = Math.max(90, (activeVideo.duration - activeVideo.currentTime - blendLead) * 1000);

            loopTimer = window.setTimeout(() => {
                playVideo(nextVideo, true);
                activateVideo(nextIndex);
                window.requestAnimationFrame(() => {
                    markReady();
                });
                window.setTimeout(() => {
                    activeVideo.pause();
                    activeVideo.currentTime = 0;
                }, 180);
                scheduleLoopBlend();
            }, waitMs);
        };

        videos.forEach((video) => {
            video.loop = false;
            video.muted = true;
            video.defaultMuted = true;
            video.playsInline = true;
        });

        settleComposition();
        activateVideo(0);

        const initialVideo = videos[0];
        const startLoopingPlayback = () => {
            markReady();
            playVideo(initialVideo);
            scheduleLoopBlend();
        };

        if (initialVideo.readyState >= 2) {
            startLoopingPlayback();
        } else {
            initialVideo.addEventListener("loadeddata", startLoopingPlayback, { once: true });
            initialVideo.addEventListener("canplay", startLoopingPlayback, { once: true });
        }
    });
});
