document.addEventListener("DOMContentLoaded", () => {
    let pageIsLeaving = false;
    const loginEntryStorageKey = "app-entry-from-login";
    const pageTransitionDelayMs = 16;

    const setPreviewMarkup = (target, markup) => {
        if (!target) {
            return;
        }

        target.innerHTML = markup;
        target.classList.add("is-filled");
    };

    const resetPreviewMarkup = (target, message) => {
        if (!target) {
            return;
        }

        target.innerHTML = `<span>${message}</span>`;
        target.classList.remove("is-filled");
    };

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
        }, pageTransitionDelayMs);
    });

    document.addEventListener("submit", (event) => {
        if (event.defaultPrevented) {
            return;
        }

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
            const actionUrl = new URL(form.action || window.location.href, window.location.href);
            if (document.body.classList.contains("body--landing")) {
                if (actionUrl.pathname.includes("/auth/login")) {
                    sessionStorage.setItem(loginEntryStorageKey, "1");
                    if (event.submitter instanceof HTMLElement) {
                        event.submitter.classList.add("is-loading");
                        event.submitter.setAttribute("aria-disabled", "true");
                    }
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
        }, pageTransitionDelayMs);
    });

    document.querySelectorAll("[data-image-input]").forEach((input) => {
        input.addEventListener("change", () => {
            const targetSelector = input.getAttribute("data-preview-target");
            const target = targetSelector ? document.querySelector(targetSelector) : null;
            const file = input.files && input.files[0];
            const captureRoot = input.closest("[data-photo-capture-root]");
            const capturedInput = captureRoot ? captureRoot.querySelector("[data-captured-photo]") : null;

            if (!target || !file) {
                const emptyMessage =
                    captureRoot?.getAttribute("data-preview-empty") || "Image preview will appear here.";
                resetPreviewMarkup(target, emptyMessage);
                return;
            }

            if (capturedInput) {
                capturedInput.value = "";
            }

            const reader = new FileReader();
            reader.onload = (event) => {
                setPreviewMarkup(target, `<img src="${event.target.result}" alt="Selected image preview">`);
            };
            reader.readAsDataURL(file);
        });
    });

    document.querySelectorAll("[data-photo-capture-root]").forEach((root) => {
        const form = root.closest("form");
        const modeInput = root.querySelector("[data-capture-mode-input]");
        const capturedInput = root.querySelector("[data-captured-photo]");
        const uploadInput = root.querySelector("[data-upload-input]");
        const previewTargetSelector = uploadInput?.getAttribute("data-preview-target");
        const previewTarget = previewTargetSelector ? document.querySelector(previewTargetSelector) : null;
        const emptyPreviewMessage =
            root.getAttribute("data-preview-empty") || "Choose a file or capture a photo to preview it here.";
        const modeButtons = Array.from(root.querySelectorAll("[data-capture-mode-button]"));
        const panels = Array.from(root.querySelectorAll("[data-capture-panel]"));
        const video = root.querySelector("[data-camera-video]");
        const placeholder = root.querySelector("[data-camera-placeholder]");
        const startButton = root.querySelector("[data-camera-start]");
        const captureButton = root.querySelector("[data-camera-capture]");
        const retakeButton = root.querySelector("[data-camera-retake]");
        const status = root.querySelector("[data-camera-status]");

        let stream = null;

        const stopStream = () => {
            if (!stream) {
                return;
            }

            stream.getTracks().forEach((track) => track.stop());
            stream = null;
        };

        const setStatus = (message) => {
            if (status) {
                status.textContent = message;
            }
        };

        const syncButtons = ({ canCapture = false, canRetake = false } = {}) => {
            if (captureButton) {
                captureButton.disabled = !canCapture;
            }
            if (retakeButton) {
                retakeButton.hidden = !canRetake;
            }
        };

        const updateMode = (nextMode) => {
            if (!modeInput) {
                return;
            }

            modeInput.value = nextMode;
            modeButtons.forEach((button) => {
                const isActive = button.dataset.mode === nextMode;
                button.classList.toggle("is-active", isActive);
                button.setAttribute("aria-pressed", isActive ? "true" : "false");
            });
            panels.forEach((panel) => {
                panel.classList.toggle("is-active", panel.dataset.capturePanel === nextMode);
            });

            if (uploadInput) {
                uploadInput.required = nextMode === "upload";
                if (nextMode === "camera") {
                    uploadInput.value = "";
                }
            }

            if (nextMode !== "camera") {
                if (capturedInput) {
                    capturedInput.value = "";
                }
                stopStream();
                placeholder?.classList.remove("is-hidden");
                syncButtons({ canCapture: false, canRetake: false });
                setStatus("Select a photo file from the current device.");
                resetPreviewMarkup(previewTarget, emptyPreviewMessage);
                return;
            }

            setStatus("Allow camera access, then capture the item.");
            if (!capturedInput?.value) {
                placeholder?.classList.remove("is-hidden");
                resetPreviewMarkup(previewTarget, "Camera capture preview will appear here.");
                syncButtons({ canCapture: false, canRetake: false });
            } else {
                placeholder?.classList.add("is-hidden");
                syncButtons({ canCapture: false, canRetake: true });
            }
        };

        const startCamera = async () => {
            if (!video) {
                return;
            }

            if (!navigator.mediaDevices?.getUserMedia) {
                setStatus("This browser does not support direct camera capture. Use attach file instead.");
                return;
            }

            if (!window.isSecureContext && window.location.hostname !== "localhost") {
                setStatus("Camera access requires HTTPS or localhost in this browser.");
                return;
            }

            stopStream();

            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    audio: false,
                    video: {
                        facingMode: { ideal: "environment" },
                    },
                });
                video.srcObject = stream;
                await video.play();
                placeholder?.classList.add("is-hidden");
                syncButtons({ canCapture: true, canRetake: Boolean(capturedInput?.value) });
                setStatus("Camera is live. Frame the item and capture the photo.");
            } catch (_error) {
                setStatus("Camera access was blocked or is unavailable on this device.");
                syncButtons({ canCapture: false, canRetake: Boolean(capturedInput?.value) });
            }
        };

        const capturePhoto = () => {
            if (!video || !capturedInput || !previewTarget || !video.videoWidth || !video.videoHeight) {
                setStatus("Wait for the camera preview to load before capturing.");
                return;
            }

            const maxDimension = 1600;
            const scale = Math.min(1, maxDimension / Math.max(video.videoWidth, video.videoHeight));
            const canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
            canvas.height = Math.max(1, Math.round(video.videoHeight * scale));

            const context = canvas.getContext("2d");
            if (!context) {
                setStatus("The browser could not prepare the captured image.");
                return;
            }

            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const dataUrl = canvas.toDataURL("image/jpeg", 0.86);

            capturedInput.value = dataUrl;
            setPreviewMarkup(previewTarget, `<img src="${dataUrl}" alt="Captured item preview">`);
            placeholder?.classList.add("is-hidden");
            setStatus("Photo captured. Retake if you want a sharper image.");
            syncButtons({ canCapture: false, canRetake: true });
            stopStream();
        };

        const clearCapture = () => {
            if (capturedInput) {
                capturedInput.value = "";
            }
            syncButtons({ canCapture: false, canRetake: false });
            placeholder?.classList.remove("is-hidden");
            resetPreviewMarkup(previewTarget, "Camera capture preview will appear here.");
            setStatus("Start the camera again to capture a new image.");
        };

        modeButtons.forEach((button) => {
            button.addEventListener("click", () => {
                updateMode(button.dataset.mode || "upload");
            });
        });

        startButton?.addEventListener("click", () => {
            updateMode("camera");
            void startCamera();
        });

        captureButton?.addEventListener("click", capturePhoto);

        retakeButton?.addEventListener("click", () => {
            clearCapture();
            void startCamera();
        });

        form?.addEventListener("submit", (event) => {
            const mode = modeInput?.value || "upload";
            if (mode === "camera") {
                if (!capturedInput?.value) {
                    event.preventDefault();
                    setStatus("Capture a photo before saving the new supply.");
                }
                return;
            }

            if (!uploadInput?.files?.length) {
                event.preventDefault();
                resetPreviewMarkup(previewTarget, emptyPreviewMessage);
            }
        });

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                stopStream();
                syncButtons({ canCapture: false, canRetake: Boolean(capturedInput?.value) });
            }
        });

        window.addEventListener("pagehide", stopStream);

        updateMode(modeInput?.value || "upload");
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
