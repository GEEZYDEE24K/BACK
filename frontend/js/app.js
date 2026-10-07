/**
 * Controlador Principal de la Aplicación CampusSwap
 * Orquestación de Vistas, Eventos, Modales y Renderizado Reactivo.
 */

document.addEventListener("DOMContentLoaded", () => {
    window.app = new CampusSwapApp();
    window.app.init();
});

class CampusSwapApp {
    constructor() {
        this.currentView = "catalog";
        this.activeTradeChatId = 101;
        this.selectedRating = 5;
        this.books = [];
        this.trades = [];
        this.matches = [];
        this.activeCategory = null;
        this.searchQuery = "";
    }

    escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }

    async init() {
        this._bindEvents();
        this._applyTheme();
        await this.loadInitialData();
        this.updateUserBadge();
        this.renderCurrentView();
    }

    // -------------------------------------------------------------------------
    // Eventos y Navegación
    // -------------------------------------------------------------------------
    _bindEvents() {
        // Escucha de autenticación OAuth federada (Google, X, Facebook) desde ventana emergente
        window.addEventListener("message", async (event) => {
            if (event.data && event.data.type === "OAUTH_SUCCESS") {
                const { token, user, provider } = event.data;
                api.setToken(token);
                api.setCurrentUser(user);
                this.updateUserBadge();
                this.closeModal("auth-modal");
                this.closeModal("login-modal");
                this.closeModal("register-modal");
                const provName = provider ? provider.toUpperCase() : "red social";
                this.showToast(`¡Bienvenido, ${user.name || user.email}! Sesión iniciada con ${provName}`, "success");
                this.renderCurrentView();
            }
        });

        // Navegación en Header y Mobile Bar
        document.querySelectorAll("[data-nav]").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const view = btn.getAttribute("data-nav");
                this.navigateTo(view);
            });
        });

        // Alternar tema claro / oscuro
        const themeBtn = document.getElementById("theme-toggle-btn");
        if (themeBtn) {
            themeBtn.addEventListener("click", () => this.toggleTheme());
        }

        // Barra de búsqueda en catálogo
        const searchInput = document.getElementById("book-search-input");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                this.searchQuery = e.target.value;
                this.filterAndRenderBooks();
            });
        }

        // Píldoras de Categorías
        document.querySelectorAll(".category-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                const catId = pill.getAttribute("data-category");
                this.activeCategory = catId === "all" ? null : parseInt(catId);
                this.filterAndRenderBooks();
            });
        });

        // Pestañas de Trueques
        document.querySelectorAll(".trade-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                document.querySelectorAll(".trade-tab").forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                const estado = tab.getAttribute("data-trade-status");
                this.renderTrades(estado);
            });
        });

        // Envío de chat
        const chatSendBtn = document.getElementById("chat-send-btn");
        const chatInput = document.getElementById("chat-input");
        if (chatSendBtn && chatInput) {
            chatSendBtn.addEventListener("click", () => this.sendChatMessage());
            chatInput.addEventListener("keypress", (e) => {
                if (e.key === "Enter") this.sendChatMessage();
            });
        }

        // Chips de respuesta rápida en chat
        document.querySelectorAll(".quick-reply-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                if (chatInput) {
                    chatInput.value = chip.textContent;
                    this.sendChatMessage();
                }
            });
        });

        // Estrellas en modal de calificación
        document.querySelectorAll(".star-select-btn").forEach(star => {
            star.addEventListener("click", () => {
                const val = parseInt(star.getAttribute("data-star-val"));
                this.setRatingStars(val);
            });
        });
    }

    async loadInitialData() {
        try {
            this.books = await api.getPublicaciones();
            this.trades = await api.getTrueques();
            this.matches = await api.getMatches();
        } catch (e) {
            console.error("Error al cargar datos iniciales:", e);
        }
    }

    navigateTo(viewName) {
        this.currentView = viewName;

        // Actualizar active en nav
        document.querySelectorAll("[data-nav]").forEach(el => {
            if (el.getAttribute("data-nav") === viewName) {
                el.classList.add("active");
            } else {
                el.classList.remove("active");
            }
        });

        // Mostrar sección correspondiente
        document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
        const target = document.getElementById(`view-${viewName}`);
        if (target) {
            target.classList.add("active");
            window.scrollTo({ top: 0, behavior: "smooth" });
        }

        this.renderCurrentView();
    }

    renderCurrentView() {
        switch (this.currentView) {
            case "catalog":
                this.filterAndRenderBooks();
                break;
            case "matches":
                this.renderMatches();
                break;
            case "trades":
                this.renderTrades();
                break;
            case "chat":
                // Auto-seleccionar la primera conversación habilitada si la actual está bloqueada
                const currentChatTrade = this.trades.find(t => t.id === this.activeTradeChatId);
                if (!this.isChatAvailable(currentChatTrade)) {
                    const firstAvailable = this.trades.find(t => this.isChatAvailable(t));
                    if (firstAvailable) this.activeTradeChatId = firstAvailable.id;
                }
                this.renderChatList();
                this.loadChatMessages(this.activeTradeChatId);
                break;
            case "profile":
                this.renderProfile();
                break;
            case "admin":
                this.renderAdminPanel();
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Catálogo de Libros y Filtros
    // -------------------------------------------------------------------------
    filterAndRenderBooks() {
        const grid = document.getElementById("books-grid");
        if (!grid) return;

        let filtered = [...this.books];
        if (this.activeCategory) {
            filtered = filtered.filter(b => b.categoria_id === this.activeCategory);
        }
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            filtered = filtered.filter(b => 
                b.titulo.toLowerCase().includes(q) ||
                (b.autor && b.autor.toLowerCase().includes(q)) ||
                (b.libro_buscado && b.libro_buscado.toLowerCase().includes(q))
            );
        }

        if (filtered.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem;">
                    <i class="fa-solid fa-book-open" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
                    <h3>No se encontraron libros con estos criterios</h3>
                    <p style="color: var(--text-secondary); margin-top: 0.5rem;">Intenta con otra búsqueda o sé el primero en publicar este título.</p>
                    <button class="btn btn-primary" onclick="app.openModal('publish-book-modal')" style="margin-top: 1.5rem;">
                        <i class="fa-solid fa-plus"></i> Publicar Libro
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = filtered.map(book => {
            const coverSrc = (book.portada && !book.portada.includes("openlibrary.org")) 
                ? book.portada 
                : (api.getThematicCover ? api.getThematicCover(book.titulo, book.categoria_id) : 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80');
            const fallbackSrc = (book.portada_fallback && !book.portada_fallback.includes("openlibrary.org"))
                ? book.portada_fallback
                : (api.getThematicCover ? api.getThematicCover(book.titulo, book.categoria_id) : 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80');

            return `
            <div class="book-card">
                <div class="book-card-header">
                    <img src="${this.escapeHtml(coverSrc)}" alt="${this.escapeHtml(book.titulo)}" class="book-cover-img" data-fallback="${this.escapeHtml(fallbackSrc)}" onerror="this.onerror=null;this.src=this.dataset.fallback">
                    <span class="book-condition-badge">${this.escapeHtml(book.estado_libro || 'Buen estado')}</span>
                    <span class="book-category-tag">${this.escapeHtml(book.categoria_nombre || 'General')}</span>
                </div>
                <div class="book-card-body">
                    <h3 class="book-title">${this.escapeHtml(book.titulo)}</h3>
                    <p class="book-author">Por ${this.escapeHtml(book.autor || 'Autor desconocido')} • ${this.escapeHtml(book.edicion || 'Edición estándar')}</p>
                    
                    <div class="looking-for-box">
                        <div class="looking-for-header">
                            <i class="fa-solid fa-arrows-rotate"></i> Busca a cambio
                        </div>
                        <div class="looking-for-text">${this.escapeHtml(book.libro_buscado || 'Cualquier texto afín al área')}</div>
                    </div>

                    <div class="book-owner-row">
                        <div class="owner-info">
                            <img src="${this.escapeHtml(book.usuario_avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80')}" class="owner-avatar" alt="${this.escapeHtml(book.usuario_nombre)}">
                            <div class="owner-details">
                                <span class="owner-name">
                                    ${this.escapeHtml(book.usuario_nombre)}
                                    <i class="fa-solid fa-circle-check verified-badge" title="Usuario Verificado"></i>
                                </span>
                                <span class="owner-univ">${book.usuario_carrera ? `${this.escapeHtml(book.usuario_carrera)} • ` : ''}${this.escapeHtml(book.usuario_universidad || 'Comunidad')}</span>
                            </div>
                        </div>
                        <div class="owner-rating">
                            <i class="fa-solid fa-star"></i>
                            <span>${book.usuario_reputacion ? Number(book.usuario_reputacion).toFixed(1) : '4.9'}</span>
                        </div>
                    </div>

                    <div class="book-card-actions">
                        <button class="btn btn-secondary btn-sm" onclick="app.showBookDetail(${book.id})">
                            <i class="fa-regular fa-eye"></i> Detalle
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="app.startTradeWithBook(${book.id})">
                            <i class="fa-solid fa-bolt"></i> Trueque
                        </button>
                    </div>
                </div>
            </div>
        `;
        }).join("");
    }

    showBookDetail(bookId) {
        const book = this.books.find(b => b.id === bookId);
        if (!book) return;

        const coverSrc = (book.portada && !book.portada.includes("openlibrary.org")) 
            ? book.portada 
            : (api.getThematicCover ? api.getThematicCover(book.titulo, book.categoria_id) : 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80');

        const container = document.getElementById("book-detail-content");
        if (container) {
            container.innerHTML = `
                <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
                    <img src="${this.escapeHtml(coverSrc)}" style="width: 140px; height: 190px; object-fit: cover; border-radius: var(--radius-md);" alt="${this.escapeHtml(book.titulo)}">
                    <div style="flex: 1; min-width: 240px;">
                        <span class="status-badge confirmado">${this.escapeHtml(book.categoria_nombre || 'General')}</span>
                        <h2 style="font-size: 1.4rem; margin: 0.5rem 0 0.25rem 0;">${this.escapeHtml(book.titulo)}</h2>
                        <p style="color: var(--text-secondary); margin-bottom: 0.75rem;">Autor: <strong>${this.escapeHtml(book.autor || 'No especificado')}</strong></p>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">ISBN: ${this.escapeHtml(book.isbn || 'N/A')} • Edición: ${this.escapeHtml(book.edicion || '1ra Edición')}</p>
                        <p style="font-size: 0.85rem; color: var(--text-muted);">Estado: <strong>${this.escapeHtml(book.estado_libro || 'Buen estado')}</strong></p>
                    </div>
                </div>
                <div style="margin-top: 1.5rem;">
                    <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem;">Descripción del ejemplar:</h4>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6;">${this.escapeHtml(book.descripcion || 'Sin descripción adicional provista por el estudiante.')}</p>
                </div>
                <div class="looking-for-box" style="margin-top: 1.5rem;">
                    <div class="looking-for-header">
                        <i class="fa-solid fa-arrows-rotate"></i> Material deseado a cambio por el dueño
                    </div>
                    <div class="looking-for-text" style="font-size: 1rem;">${this.escapeHtml(book.libro_buscado || 'No especificado')}</div>
                </div>
                <div style="margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
                    <button class="btn btn-secondary" onclick="app.closeModal('book-detail-modal')">Cerrar</button>
                    <button class="btn btn-primary" onclick="app.closeModal('book-detail-modal'); app.startTradeWithBook(${book.id})">
                        <i class="fa-solid fa-bolt"></i> Proponer Trueque Inmediato
                    </button>
                </div>
            `;
            this.openModal("book-detail-modal");
        }
    }

    async startTradeWithBook(bookId, ownPublicationId = null) {
        const book = this.books.find(b => b.id === bookId);
        if (!book) return;

        const current = api.getCurrentUser();
        if (!current) {
            this.showToast("Debes iniciar sesión para proponer un trueque", "warning");
            this.openAuthModal("login");
            return;
        }

        if (String(book.usuario_id) === String(current.id)) {
            this.showToast("No puedes proponer trueque a tu propia publicación", "warning");
            return;
        }

        const ownPublicationSelect = document.getElementById("trade-prop-book-propone");
        const destinationId = document.getElementById("trade-prop-publicacion-destino-id");
        const inputBookRecibe = document.getElementById("trade-prop-book-recibe");
        const inputUsuarioRecibe = document.getElementById("trade-prop-user-recibe");
        const inputUsuarioId = document.getElementById("trade-prop-user-id");

        try {
            const ownPublications = (await api.getMisPublicaciones())
                .filter(publication => publication.estado_publicacion === "activa");
            if (ownPublications.length === 0) {
                this.showToast("Primero publica un libro activo para ofrecer en el trueque", "warning");
                return;
            }
            ownPublicationSelect.innerHTML = ownPublications.map(publication =>
                `<option value="${publication.id}">${this.escapeHtml(publication.titulo)}</option>`
            ).join("");
            if (ownPublicationId && ownPublications.some(pub => String(pub.id) === String(ownPublicationId))) {
                ownPublicationSelect.value = ownPublicationId;
            }
        } catch (e) {
            this.showToast(e.message || "No se pudieron cargar tus publicaciones", "error");
            return;
        }

        if (destinationId) destinationId.value = book.id;
        if (inputBookRecibe) inputBookRecibe.value = book.titulo;
        if (inputUsuarioRecibe) inputUsuarioRecibe.value = `${book.usuario_nombre} (${book.usuario_universidad || 'Universidad'})`;
        if (inputUsuarioId) inputUsuarioId.value = book.usuario_id;

        this.openModal("propose-trade-modal");
    }

    async submitTradeProposal() {
        const publicacionOrigenId = document.getElementById("trade-prop-book-propone")?.value;
        const publicacionDestinoId = document.getElementById("trade-prop-publicacion-destino-id")?.value;
        const usuarioRecibeId = document.getElementById("trade-prop-user-id")?.value;

        if (!publicacionOrigenId || !publicacionDestinoId) {
            this.showToast("Selecciona la publicación que ofreces", "warning");
            return;
        }

        try {
            await api.proposeTrade({
                usuario_recibe_id: usuarioRecibeId,
                publicacion_origen_id: Number(publicacionOrigenId),
                publicacion_destino_id: Number(publicacionDestinoId)
            });

            this.showToast("¡Propuesta de trueque enviada exitosamente!", "success");
            this.closeModal("propose-trade-modal");
            this.trades = await api.getTrueques();
            this.navigateTo("trades");
        } catch (e) {
            this.showToast(e.message || "Error al enviar propuesta", "error");
        }
    }

    async submitNewBook() {
        const titulo = document.getElementById("new-book-titulo")?.value;
        const autor = document.getElementById("new-book-autor")?.value;
        const categoria_id = document.getElementById("new-book-categoria")?.value;
        const estado_libro = document.getElementById("new-book-estado")?.value;
        const libro_buscado = document.getElementById("new-book-buscado")?.value;
        const descripcion = document.getElementById("new-book-descripcion")?.value;
        const isbn = document.getElementById("new-book-isbn")?.value;
        const edicion = document.getElementById("new-book-edicion")?.value;

        if (!titulo || !libro_buscado) {
            this.showToast("El título y el libro que buscas son obligatorios", "warning");
            return;
        }

        try {
            const newBook = await api.createPublicacion({
                titulo,
                autor,
                categoria_id: parseInt(categoria_id),
                estado_libro,
                libro_buscado,
                descripcion,
                isbn,
                edicion
            });

            this.books = await api.getPublicaciones();
            this.closeModal("publish-book-modal");
            this.filterAndRenderBooks();

            // Resetear estados del modal de verificación
            const formContainer = document.getElementById("book-verification-form-container");
            const aiStatus = document.getElementById("book-verification-ai-status");
            const aiResult = document.getElementById("book-verification-ai-result");
            if (formContainer) formContainer.style.display = "block";
            if (aiStatus) aiStatus.style.display = "none";
            if (aiResult) aiResult.style.display = "none";

            document.getElementById("book-verification-publication-id").value = newBook.id;
            document.getElementById("book-verification-id").value = challenge.verificacion_id;
            document.getElementById("book-verification-code").textContent = challenge.codigo;
            document.getElementById("book-verification-instructions").textContent = challenge.instrucciones;
            this.openModal("book-verification-modal");
        } catch (e) {
            this.showToast(e.message || "Error al publicar libro", "error");
        }
    }

    async submitBookVerification() {
        const publicationId = document.getElementById("book-verification-publication-id").value;
        const verificationId = document.getElementById("book-verification-id").value;
        const code = document.getElementById("book-verification-code").textContent.trim();
        const coverPhoto = document.getElementById("book-verification-cover").files[0];
        const isbnPhoto = document.getElementById("book-verification-isbn").files[0];
        if (!coverPhoto || !isbnPhoto) {
            this.showToast("Adjunta la portada y la página del ISBN", "warning");
            return;
        }

        const formContainer = document.getElementById("book-verification-form-container");
        const aiStatus = document.getElementById("book-verification-ai-status");
        const aiResult = document.getElementById("book-verification-ai-result");
        const stepEl = document.getElementById("ai-loading-step");

        // Mostrar fase de análisis con IA
        if (formContainer) formContainer.style.display = "none";
        if (aiStatus) aiStatus.style.display = "block";
        if (aiResult) aiResult.style.display = "none";

        // Animación progresiva de pasos para la demostración en clase
        let stepInterval = null;
        if (stepEl) {
            const steps = [
                "1. Clasificando morfología del libro con MobileNetV3 (Red Neuronal)...",
                "2. Escaneando texto y código de seguridad con EasyOCR...",
                "3. Comparando código con token criptográfico generado...",
                "4. Generando veredicto automatizado..."
            ];
            let currentStep = 0;
            stepInterval = setInterval(() => {
                currentStep = (currentStep + 1) % steps.length;
                stepEl.textContent = steps[currentStep];
            }, 1800);
        }

        try {
            const resp = await api.submitBookVerification(
                publicationId,
                verificationId,
                code,
                coverPhoto,
                isbnPhoto
            );

            if (stepInterval) clearInterval(stepInterval);
            if (aiStatus) aiStatus.style.display = "none";
            if (aiResult) aiResult.style.display = "block";

            // Limpiar inputs
            document.getElementById("book-verification-cover").value = "";
            document.getElementById("book-verification-isbn").value = "";

            const fueAprobado = resp.ia_aprobado === true || resp.estado === "aprobada";

            if (fueAprobado) {
                // Actualizar libros inmediatamente para que aparezca en el catálogo
                this.books = await api.getPublicaciones();
                this.filterAndRenderBooks();

                aiResult.innerHTML = `
                    <div style="text-align: center; padding: 1.5rem 0.5rem;">
                        <div style="width: 64px; height: 64px; margin: 0 auto 1rem auto; background: rgba(34, 197, 94, 0.15); border: 2px solid #22c55e; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fa-solid fa-circle-check" style="font-size: 2.2rem; color: #22c55e;"></i>
                        </div>
                        <h3 style="font-size: 1.3rem; margin-bottom: 0.5rem; color: #22c55e;">¡Verificado por Red Neuronal!</h3>
                        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.25rem;">
                            El análisis automático confirmó los parámetros de seguridad. Tu libro ya está <strong>activo en el catálogo</strong>.
                        </p>
                        
                        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1rem; text-align: left; margin-bottom: 1.5rem; font-size: 0.85rem;">
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span><i class="fa-solid fa-network-wired" style="color: var(--primary); margin-right: 0.4rem;"></i> Red MobileNetV3:</span>
                                <strong style="color: #22c55e;">Libro Detectado ✓</strong>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span><i class="fa-solid fa-qrcode" style="color: var(--primary); margin-right: 0.4rem;"></i> OCR Código '${this.escapeHtml(code)}':</span>
                                <strong style="color: #22c55e;">Coincidencia Confirmada ✓</strong>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span><i class="fa-solid fa-bolt" style="color: #fbbf24; margin-right: 0.4rem;"></i> Estado Publicación:</span>
                                <strong style="color: #22c55e;">Activa Automáticamente</strong>
                            </div>
                        </div>

                        <div style="display: flex; gap: 0.75rem;">
                            <button class="btn btn-secondary" style="flex: 1;" onclick="app.closeModal('book-verification-modal')">
                                Cerrar
                            </button>
                            <button class="btn btn-primary" style="flex: 1;" onclick="app.closeModal('book-verification-modal'); app.navigateTo('catalog');">
                                <i class="fa-solid fa-book"></i> Ver en Catálogo
                            </button>
                        </div>
                    </div>
                `;
                this.showToast("¡Libro verificado y activado automáticamente por IA!", "success");
            } else {
                aiResult.innerHTML = `
                    <div style="text-align: center; padding: 1.5rem 0.5rem;">
                        <div style="width: 64px; height: 64px; margin: 0 auto 1rem auto; background: rgba(245, 158, 11, 0.15); border: 2px solid #f59e0b; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fa-solid fa-clock-rotate-left" style="font-size: 2rem; color: #f59e0b;"></i>
                        </div>
                        <h3 style="font-size: 1.25rem; margin-bottom: 0.5rem; color: #f59e0b;">En cola de moderación humana</h3>
                        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.25rem;">
                            Las fotos se recibieron correctamente. La IA requiere revisión complementaria de un moderador antes de activarlo.
                        </p>
                        ${resp.ia_detalle ? `
                        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.85rem; text-align: left; margin-bottom: 1.5rem; font-size: 0.82rem; color: var(--text-muted);">
                            <strong>Detalle técnico IA:</strong> ${this.escapeHtml(resp.ia_detalle)}
                        </div>
                        ` : ''}
                        <button class="btn btn-primary" style="width: 100%;" onclick="app.closeModal('book-verification-modal')">
                            Entendido
                        </button>
                    </div>
                `;
                this.showToast("Fotos recibidas. Quedan pendientes de revisión humana.", "info");
            }
        } catch (e) {
            if (stepInterval) clearInterval(stepInterval);
            if (aiStatus) aiStatus.style.display = "none";
            if (formContainer) formContainer.style.display = "block";
            this.showToast(e.message || "No se pudieron enviar las fotos", "error");
        }
    }

    /** Muestra un modal con los matches encontrados tras publicar un libro */
    _showPostPublishMatches(book, matches) {
        const existing = document.getElementById('post-publish-matches-modal');
        if (existing) existing.remove();

        const matchCount = matches.length;
        const modal = document.createElement('div');
        modal.id = 'post-publish-matches-modal';
        modal.className = 'modal-backdrop active';
        modal.innerHTML = `
            <div class="modal-box" style="max-width: 480px;">
                <div class="modal-header">
                    <div style="display:flex; align-items:center; gap:0.6rem;">
                        <i class="fa-solid fa-wand-magic-sparkles" style="color: var(--primary); font-size: 1.3rem;"></i>
                        <h3 style="margin:0; font-size:1.15rem; font-weight:700;">¡${matchCount} match${matchCount > 1 ? 'es' : ''} encontrado${matchCount > 1 ? 's' : ''}!</h3>
                    </div>
                    <button class="btn-icon" onclick="document.getElementById('post-publish-matches-modal').remove()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <p style="color:var(--text-secondary); margin-bottom:1.25rem; font-size:0.9rem;">
                        Tu libro <strong>«${this.escapeHtml(book.titulo)}»</strong> ya tiene compatibilidad con ${matchCount} publicación${matchCount > 1 ? 'es' : ''} de la comunidad. ¡Puedes proponer un trueque de inmediato!
                    </p>
                    <div style="display:flex; flex-direction:column; gap:0.75rem; max-height:260px; overflow-y:auto;">
                        ${matches.slice(0, 5).map(m => `
                            <div style="display:flex; align-items:center; justify-content:space-between; padding:0.9rem; background:var(--bg-surface-elevated); border-radius:var(--radius-md); border:1px solid var(--border-color);">
                                <div style="min-width:0; flex:1;">
                                    <div style="font-weight:700; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${this.escapeHtml(m.libro_ofrecido || m.titulo_destino || 'Libro disponible')}</div>
                                    <div style="font-size:0.78rem; color:var(--text-muted); margin-top:2px;">Por ${this.escapeHtml(m.usuario_match || 'otro usuario')} · ${Math.round(m.puntuacion || 85)}% compatibilidad</div>
                                </div>
                                <button class="btn btn-primary btn-sm" style="margin-left:0.75rem; flex-shrink:0;" onclick="document.getElementById('post-publish-matches-modal').remove(); app.navigateTo('matches');">
                                    <i class="fa-solid fa-bolt"></i> Ver
                                </button>
                            </div>
                        `).join('')}
                    </div>
                    <div style="display:flex; gap:0.75rem; margin-top:1.5rem;">
                        <button class="btn btn-secondary" style="flex:1;" onclick="document.getElementById('post-publish-matches-modal').remove();">Cerrar</button>
                        <button class="btn btn-primary" style="flex:1;" onclick="document.getElementById('post-publish-matches-modal').remove(); app.navigateTo('matches');">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Ver todos los matches
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // -------------------------------------------------------------------------
    // Matches y Porcentajes de Compatibilidad
    // -------------------------------------------------------------------------
    renderMatches() {
        const container = document.getElementById("matches-list");
        if (!container) return;

        if (!this.matches || this.matches.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 4rem 1rem;">
                    <i class="fa-solid fa-wand-magic-sparkles" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
                    <h3>Aún no tienes coincidencias automáticas</h3>
                    <p style="color: var(--text-secondary); margin-top: 0.5rem;">Publica más libros y añade qué títulos buscas para que el motor correlacione ofertas.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.matches.map(m => {
            const score = m.puntuacion || 90;
            const circumference = 2 * Math.PI * 28;
            const strokeDashoffset = circumference - (score / 100) * circumference;

            return `
                <div class="match-card">
                    <div class="match-score-badge">
                        <div class="circle-progress">
                            <svg width="72" height="72">
                                <circle class="circle-bg" cx="36" cy="36" r="28"></circle>
                                <circle class="circle-fill" cx="36" cy="36" r="28"
                                    style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${strokeDashoffset};"></circle>
                            </svg>
                            <span class="circle-text">${Math.round(score)}%</span>
                        </div>
                        <span class="match-type-text">${m.tipo_match}</span>
                    </div>

                    <div class="match-flow">
                        <div class="match-book-item">
                            <div class="match-book-label">Tu libro en oferta</div>
                            <div class="match-book-title">${this.escapeHtml(m.mi_libro || 'Libro publicado')}</div>
                            <span style="font-size: 0.8rem; color: var(--success); font-weight: 600;">✓ Disponible para trueque</span>
                        </div>

                        <div class="match-swap-icon">
                            <i class="fa-solid fa-arrow-right-arrow-left"></i>
                        </div>

                        <div class="match-book-item">
                            <div class="match-book-label">Libro ofrecido por estudiante</div>
                            <div class="match-book-title">${this.escapeHtml(m.libro_ofrecido || 'Libro publicado')}</div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.4rem; margin-top: 0.25rem;">
                                <span>Por <strong>${this.escapeHtml(m.usuario_match || 'Estudiante')}</strong> (${this.escapeHtml(m.universidad || 'Campus')})</span>
                            </div>
                        </div>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <button class="btn btn-primary btn-sm" ${m.publicacion_destino_id ? `onclick="app.openProposeTradeFromMatch(${m.publicacion_origen_id}, ${m.publicacion_destino_id})"` : "disabled title=\"Este match de demostración no está asociado a publicaciones reales\""}>
                            <i class="fa-solid fa-bolt"></i> Iniciar Trueque
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    }

    openProposeTradeFromMatch(publicacionOrigenId, publicacionDestinoId) {
        return this.startTradeWithBook(publicacionDestinoId, publicacionOrigenId);
    }

    // -------------------------------------------------------------------------
    // Seguimiento de Trueques
    // -------------------------------------------------------------------------
    async renderTrades(filterStatus = "todos") {
        const container = document.getElementById("trades-list");
        if (!container) return;

        const current = api.getCurrentUser();
        if (!current) {
            container.innerHTML = `
                <div style="text-align: center; padding: 4rem 1rem;">
                    <i class="fa-solid fa-lock" style="font-size: 3rem; color: var(--primary); margin-bottom: 1rem;"></i>
                    <h3>Inicia sesión para gestionar tus trueques</h3>
                    <p style="color: var(--text-secondary); margin-top: 0.5rem; margin-bottom: 1.5rem;">Crea una cuenta o ingresa para supervisar propuestas y entregas.</p>
                    <button class="btn btn-primary" onclick="app.openAuthModal('login')">
                        <i class="fa-solid fa-arrow-right-to-bracket"></i> Iniciar Sesión
                    </button>
                </div>
            `;
            return;
        }

        this.trades = await api.getTrueques(filterStatus);

        if (this.trades.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 4rem 1rem;">
                    <i class="fa-solid fa-handshake-slash" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
                    <h3>No tienes trueques en esta sección</h3>
                    <p style="color: var(--text-secondary); margin-top: 0.5rem;">Explora el catálogo o revisa tus matches para proponer intercambios.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.trades.map(trade => {
            const isProposer = String(trade.usuario_propone_id) === String(current.id);
            const otherParty = isProposer ? trade.usuario_recibe_nombre : trade.usuario_propone_nombre;

            return `
                <div class="trade-card">
                    <div class="trade-card-header">
                        <span class="trade-id">ID #${trade.id} • ${new Date(trade.fecha_propuesta).toLocaleDateString()}</span>
                        <span class="status-badge ${trade.estado}">${trade.estado}</span>
                    </div>

                    <div class="trade-body">
                        <div class="trade-party">
                            <div class="trade-party-role">${isProposer ? 'Tú ofreces' : `${this.escapeHtml(otherParty)} ofrece`}</div>
                            <div class="trade-party-book">${this.escapeHtml(trade.libro_propone || 'Publicación')}</div>
                        </div>

                        <div style="color: var(--primary); font-size: 1.25rem;">
                            <i class="fa-solid fa-arrow-right-arrow-left"></i>
                        </div>

                        <div class="trade-party">
                            <div class="trade-party-role">${isProposer ? `${this.escapeHtml(otherParty)} ofrece` : 'Tú recibes'}</div>
                            <div class="trade-party-book">${this.escapeHtml(trade.libro_recibe || 'Publicación')}</div>
                        </div>
                    </div>

                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.85rem;">
                        <i class="fa-solid fa-location-dot" style="color: var(--danger); margin-right: 0.3rem;"></i>
                        Coordina el punto de encuentro en el chat.
                    </div>

                    <div class="trade-actions">
                        ${this.isChatAvailable(trade) ? `
                        <button class="btn btn-secondary btn-sm" onclick="app.openChatForTrade(${trade.id})">
                            <i class="fa-solid fa-comments"></i> Abrir Chat
                        </button>
                        ` : `
                        <button class="btn btn-secondary btn-sm" style="opacity:0.45; cursor:not-allowed;" title="Chat disponible cuando ambas partes acepten el trueque" disabled>
                            <i class="fa-solid fa-lock"></i> Chat Bloqueado
                        </button>
                        `}

                        ${!isProposer && trade.estado === 'propuesto' ? `
                            <button class="btn btn-primary btn-sm" onclick="app.confirmTrade(${trade.id})">
                                <i class="fa-solid fa-check"></i> Aceptar Propuesta
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="app.rejectTrade(${trade.id})">
                                <i class="fa-solid fa-xmark"></i> Rechazar
                            </button>
                        ` : ''}

                        ${trade.estado === 'confirmado' ? `
                            <button class="btn btn-success btn-sm" onclick="app.completeTrade(${trade.id})">
                                <i class="fa-solid fa-handshake"></i> Marcar como Completado
                            </button>
                        ` : ''}

                        ${trade.estado === 'completado' ? (
                            trade.calificacion ? `
                                <span style="font-size: 0.85rem; color: #fbbf24; font-weight: 600;">
                                    ★ Calificado (${trade.calificacion.estrellas} estrellas)
                                </span>
                            ` : `
                                <button class="btn btn-primary btn-sm" onclick="app.openRateModal(${trade.id})">
                                    <i class="fa-solid fa-star"></i> Calificar Intercambio
                                </button>
                            `
                        ) : ''}
                    </div>
                </div>
            `;
        }).join("");
    }

    async confirmTrade(tradeId) {
        try {
            const updated = await api.confirmTrade(tradeId);
            this.showToast("¡Trueque confirmado! Coordinad la entrega en el chat.", "success");
            this.trades = await api.getTrueques();
            this.renderTrades();
            // Si está en el chat de este trueque, recargar el banner de acciones
            if (this.currentView === 'chat' && this.activeTradeChatId === tradeId) {
                await this.loadChatMessages(tradeId);
            }
        } catch (e) {
            this.showToast(e.message || "Error al confirmar", "error");
        }
    }

    async completeTrade(tradeId) {
        try {
            await api.completeTrade(tradeId);
            this.showToast("¡Intercambio finalizado! Recuerda calificar la experiencia.", "success");
            this.trades = await api.getTrueques();
            this.renderTrades();
            if (this.currentView === 'chat' && this.activeTradeChatId === tradeId) {
                await this.loadChatMessages(tradeId);
            }
        } catch (e) {
            this.showToast(e.message || "Error al completar", "error");
        }
    }

    async rejectTrade(tradeId) {
        try {
            await api.rejectTrade(tradeId);
            this.showToast("Trueque rechazado", "info");
            this.trades = await api.getTrueques();
            this.renderTrades();
            if (this.currentView === 'chat' && this.activeTradeChatId === tradeId) {
                await this.loadChatMessages(tradeId);
            }
        } catch (e) {
            this.showToast(e.message || "Error al rechazar", "error");
        }
    }

    // -------------------------------------------------------------------------
    // Chat Asociado al Intercambio
    // -------------------------------------------------------------------------

    /** Determina si el chat está habilitado para un trueque dado su estado */
    isChatAvailable(trade) {
        if (!trade) return false;
        // Chat disponible en todos los estados activos (propuesto, confirmado, completado)
        return ['propuesto', 'confirmado', 'completado'].includes(trade.estado);
    }

    openChatForTrade(tradeId) {
        const trade = this.trades.find(t => t.id === tradeId);
        if (!this.isChatAvailable(trade)) {
            this.showToast(
                "🔒 El chat no está disponible para trueques rechazados o finalizados sin acuerdo",
                "warning"
            );
            return;
        }
        this.activeTradeChatId = tradeId;
        this.navigateTo("chat");
    }

    renderChatList() {
        const list = document.getElementById("chat-conversation-list");
        if (!list) return;

        const current = api.getCurrentUser();
        if (!current) {
            list.innerHTML = `
                <div style="text-align: center; padding: 2rem 1rem; color: var(--text-muted);">
                    <i class="fa-solid fa-lock" style="font-size: 2rem; margin-bottom: 0.5rem; color: var(--primary);"></i>
                    <p style="font-size: 0.85rem;">Inicia sesión para ver tus conversaciones</p>
                </div>
            `;
            return;
        }

        list.innerHTML = this.trades.map(trade => {
            const isProposer = String(trade.usuario_propone_id) === String(current.id);
            const otherParty = isProposer ? trade.usuario_recibe_nombre : trade.usuario_propone_nombre;
            const participantName = otherParty || "Compañero";
            const activeClass = trade.id === this.activeTradeChatId ? "active" : "";
            const chatLocked = !this.isChatAvailable(trade);

            return `
                <div
                    class="chat-list-item ${activeClass} ${chatLocked ? 'chat-locked' : ''}"
                    onclick="app.${chatLocked ? 'showChatLockedHint' : 'loadChatMessages'}(${trade.id})"
                    title="${chatLocked ? 'El chat está cerrado porque el trueque fue rechazado' : ''}"
                >
                    <div style="width: 40px; height: 40px; border-radius: var(--radius-full); background: ${chatLocked ? 'var(--border-color)' : 'var(--primary-light)'}; color: ${chatLocked ? 'var(--text-muted)' : 'var(--primary)'}; display: flex; align-items: center; justify-content: center; font-weight: 700; position: relative;">
                        ${chatLocked ? '<i class="fa-solid fa-lock" style="font-size:0.9rem;"></i>' : this.escapeHtml(participantName.charAt(0))}
                    </div>
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-size: 0.9rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; ${chatLocked ? 'opacity:0.5;' : ''}">
                            ${this.escapeHtml(participantName)}
                        </div>
                        <div style="font-size: 0.78rem; color: ${chatLocked ? 'var(--danger)' : 'var(--text-muted)'}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${chatLocked ? '🔒 Trueque rechazado' : `Trueque #${trade.id} • ${trade.estado}`}
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }

    showChatLockedHint(tradeId) {
        this.showToast("🔒 El chat está inhabilitado porque este trueque fue rechazado", "warning");
    }

    async loadChatMessages(tradeId) {
        this.activeTradeChatId = tradeId;
        this.renderChatList();

        // En pantallas móviles, cerrar la barra lateral al seleccionar un chat
        const sidebar = document.getElementById("chat-sidebar");
        if (sidebar) sidebar.classList.remove("mobile-open");

        const messagesBox = document.getElementById("chat-messages-body");
        const chatHeaderTitle = document.getElementById("chat-partner-name");
        const chatHeaderSub = document.getElementById("chat-trade-details");
        const chatInput = document.getElementById("chat-input");
        const chatSendBtn = document.getElementById("chat-send-btn");
        const chatQuickReplies = document.getElementById("chat-quick-replies-area");

        const trade = this.trades.find(t => t.id === tradeId) || this.trades[0];
        const current = api.getCurrentUser();

        // Chat rechazado — bloqueado
        if (trade && trade.estado === 'rechazado') {
            if (chatHeaderTitle) chatHeaderTitle.textContent = 'Trueque Rechazado';
            if (chatHeaderSub) chatHeaderSub.textContent = `Trueque #${tradeId} • RECHAZADO`;
            if (messagesBox) messagesBox.innerHTML = `<div style="text-align:center; margin:auto; padding:2rem; color:var(--text-muted);"><i class="fa-solid fa-ban" style="font-size:2.5rem; margin-bottom:0.75rem; color:var(--danger);"></i><p>Este trueque fue rechazado.</p></div>`;
            if (chatInput) { chatInput.disabled = true; chatInput.placeholder = "Chat no disponible"; }
            if (chatSendBtn) chatSendBtn.disabled = true;
            if (chatQuickReplies) chatQuickReplies.style.display = 'none';
            return;
        }

        // Chat disponible (propuesto, confirmado, completado) — habilitar controles
        const isCompleted = trade && trade.estado === 'completado';
        if (chatInput) {
            chatInput.disabled = isCompleted;
            chatInput.placeholder = isCompleted
                ? "Intercambio completado — chat archivado"
                : "Escribe un mensaje para coordinar la entrega...";
        }
        if (chatSendBtn) chatSendBtn.disabled = isCompleted;
        if (chatQuickReplies) chatQuickReplies.style.display = isCompleted ? 'none' : '';

        // Cargar info enriquecida del trueque (nombres reales desde backend)
        let tradeInfo;
        try {
            tradeInfo = await api.getTradeInfo(tradeId);
        } catch (e) {
            this.showToast(e.message || "No se pudo cargar el trueque", "error");
            return;
        }
        const infoTrade = tradeInfo || trade;

        if (infoTrade && chatHeaderTitle && chatHeaderSub) {
            const isProposer = String(infoTrade.usuario_propone_id) === String(current.id);
            const otherParty = isProposer
                ? (infoTrade.usuario_recibe_nombre || trade?.usuario_recibe_nombre || 'Compañero')
                : (infoTrade.usuario_propone_nombre || trade?.usuario_propone_nombre || 'Compañero');
            chatHeaderTitle.textContent = otherParty;
            const libroA = infoTrade.libro_propone || trade?.libro_propone || '?';
            const libroB = infoTrade.libro_recibe || trade?.libro_recibe || '?';
            chatHeaderSub.textContent = `${libroA} ⇄ ${libroB} • Estado: ${(infoTrade.estado || trade?.estado || '').toUpperCase()}`;
            
            // Guardar ID del compañero de chat para presencia
            this.activeChatPartnerId = isProposer
                ? Number(infoTrade.usuario_recibe_id || trade?.usuario_recibe_id)
                : Number(infoTrade.usuario_propone_id || trade?.usuario_propone_id);
            this.updateChatPresence([]);
        }

        // Renderizar banner de acciones contextual (aceptar/rechazar/completar/calificar)
        this._renderChatActionBanner(infoTrade, current);

        let messages;
        try {
            messages = await api.getChatMessages(tradeId);
        } catch (e) {
            this.showToast(e.message || "No se pudo cargar la conversación", "error");
            return;
        }

        if (!messages || messages.length === 0) {
            messagesBox.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); margin: auto;">
                    <i class="fa-regular fa-comments" style="font-size: 2.5rem; margin-bottom: 0.5rem;"></i>
                    <p>No hay mensajes todavía.<br>Coordinad los detalles del intercambio aquí.</p>
                </div>
            `;
        } else {
            messagesBox.replaceChildren(
                ...(messages.length === 50
                    ? [this.createOlderMessagesButton(tradeId, messages[0].id)]
                    : []),
                ...messages.filter(m => m && m.contenido && String(m.contenido).trim()).map(msg => this.createChatBubble(msg, current))
            );
        }

        // Auto-scroll
        messagesBox.scrollTop = messagesBox.scrollHeight;
        
        // Conectar WebSocket para tiempo real
        this.connectChatWebSocket(tradeId);
    }

    updateChatPresence(onlineUsers) {
        const presenceEl = document.getElementById("chat-partner-presence");
        if (!presenceEl) return;

        const partnerId = this.activeChatPartnerId;
        const isPartnerOnline = Array.isArray(onlineUsers) && onlineUsers.map(Number).includes(Number(partnerId));

        if (isPartnerOnline) {
            presenceEl.className = "chat-presence online";
            presenceEl.innerHTML = `<span class="presence-dot"></span><span class="presence-text">En línea</span>`;
        } else {
            presenceEl.className = "chat-presence offline";
            presenceEl.innerHTML = `<span class="presence-dot"></span><span class="presence-text">Desconectado</span>`;
        }
    }

    createChatBubble(msg, currentUser = api.getCurrentUser()) {
        const isMine = String(msg.remitente_id) === String(currentUser.id);
        
        // Formateo seguro de fecha y hora para evitar 'Invalid Date'
        let time = "";
        try {
            if (msg.fecha_envio) {
                const parsed = new Date(msg.fecha_envio);
                if (!isNaN(parsed.getTime())) {
                    time = parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                }
            }
        } catch (_) {}
        if (!time) {
            time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }

        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${isMine ? "mine" : "theirs"}`;
        if (msg.id) bubble.dataset.messageId = msg.id;

        const sender = document.createElement("div");
        sender.style.cssText = "font-weight: 700; font-size: 0.75rem; margin-bottom: 0.2rem; opacity: 0.9;";
        sender.textContent = isMine ? "Tú" : (msg.remitente_nombre || "Compañero");

        const content = document.createElement("div");
        content.textContent = msg.contenido || "";

        const timestamp = document.createElement("div");
        timestamp.className = "chat-time";
        timestamp.textContent = time;
        bubble.append(sender, content, timestamp);
        return bubble;
    }

    createOlderMessagesButton(tradeId, beforeId) {
        const button = document.createElement("button");
        button.className = "btn btn-secondary btn-sm";
        button.textContent = "Cargar mensajes anteriores";
        button.addEventListener("click", () => this.loadOlderChatMessages(tradeId, beforeId, button));
        return button;
    }

    async loadOlderChatMessages(tradeId, beforeId, button) {
        button.disabled = true;
        try {
            const messages = await api.getChatMessages(tradeId, { beforeId });
            const messagesBox = document.getElementById("chat-messages-body");
            const oldHeight = messagesBox.scrollHeight;
            const olderMessages = (messages || [])
                .filter(m => m && m.contenido && String(m.contenido).trim())
                .map(message => this.createChatBubble(message));
            if (messages.length === 50) {
                olderMessages.unshift(this.createOlderMessagesButton(tradeId, messages[0].id));
            }
            button.remove();
            messagesBox.prepend(...olderMessages);
            messagesBox.scrollTop = messagesBox.scrollHeight - oldHeight;
        } catch (e) {
            button.disabled = false;
            this.showToast(e.message || "No se pudieron cargar mensajes anteriores", "error");
        }
    }

    connectChatWebSocket(tradeId) {
        if (this.chatWs) {
            this.chatWs.close();
            this.chatWs = null;
        }
        const token = api.getToken();
        if (!token) {
            this.showToast("Inicia sesión para abrir la conversación", "warning");
            return;
        }
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = api.baseUrl.replace(/^http(s?):\/\//, '');
        this.chatWs = new WebSocket(
            `${wsProtocol}//${wsHost}/trueques/${tradeId}/ws`,
            ["bearer", token]
        );
        
        this.chatWs.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (!data) return;

                // 1. Manejo de presencia y usuarios conectados
                if (data.type === "room_state" || data.type === "presence") {
                    this.updateChatPresence(data.online_users);
                    return;
                }

                // 2. Indicadores de escritura
                if (data.type === "typing") {
                    return;
                }

                // 3. Ignorar errores o mensajes de sistema sin texto
                if (data.type === "error" || !data.contenido) {
                    return;
                }

                // 4. Mensajes de texto normales
                this.appendMessageToUI(data);
            } catch (e) {
                console.error("Error parsing WS message:", e);
            }
        };

        this.chatWs.onclose = event => {
            this.updateChatPresence([]);
            if (event.code === 4401 || event.code === 4403) {
                this.showToast("No tienes permiso para abrir esta conversación", "error");
            }
        };
    }

    appendMessageToUI(msg) {
        // Ignorar si el mensaje no tiene contenido textual válido
        if (!msg || !msg.contenido || !String(msg.contenido).trim()) return;

        const messagesBox = document.getElementById("chat-messages-body");
        if (!messagesBox) return;
        
        // Remove empty state message if exists
        const emptyState = messagesBox.querySelector('.fa-comments');
        if (emptyState) {
            messagesBox.innerHTML = '';
        }
        
        if (msg.id && messagesBox.querySelector(`[data-message-id="${msg.id}"]`)) return;
        messagesBox.appendChild(this.createChatBubble(msg));
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    /** Renderiza el banner de acciones del trueque dentro del chat */
    _renderChatActionBanner(trade, currentUser) {
        const lockBanner = document.getElementById("chat-lock-banner");
        const actionBanner = document.getElementById("chat-action-banner");
        if (!trade) return;

        const isProposer = String(trade.usuario_propone_id) === String(currentUser.id);
        const isReceiver = !isProposer;
        const estado = trade.estado;

        // Ocultar el banner de bloqueado legacy
        if (lockBanner) lockBanner.style.display = 'none';

        // Crear o actualizar el banner de acciones
        let banner = document.getElementById("chat-action-banner");
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'chat-action-banner';
            const messagesBody = document.getElementById('chat-messages-body');
            if (messagesBody) messagesBody.parentNode.insertBefore(banner, messagesBody);
        }

        if (estado === 'propuesto') {
            if (isReceiver) {
                banner.innerHTML = `
                    <div class="chat-status-banner propuesto">
                        <div class="chat-status-info">
                            <i class="fa-solid fa-handshake-angle"></i>
                            <div>
                                <strong>${this.escapeHtml(trade.usuario_propone_nombre || 'El otro usuario')}</strong> te propuso este intercambio
                                ${trade.libro_propone ? `<div style="font-size:0.78rem; opacity:0.85; margin-top:2px;">«Ofrece: ${this.escapeHtml(trade.libro_propone)}»</div>` : ''}
                            </div>
                        </div>
                        <div class="chat-status-actions">
                            <button class="btn btn-primary btn-sm" onclick="app.confirmTrade(${trade.id})">
                                <i class="fa-solid fa-check"></i> Aceptar Trueque
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="app.rejectTrade(${trade.id})">
                                <i class="fa-solid fa-xmark"></i> Rechazar
                            </button>
                        </div>
                    </div>
                `;
            } else {
                banner.innerHTML = `
                    <div class="chat-status-banner propuesto">
                        <div class="chat-status-info">
                            <i class="fa-solid fa-hourglass-half"></i>
                            <div>
                                <strong>Propuesta enviada</strong> — esperando que <strong>${this.escapeHtml(trade.usuario_recibe_nombre || 'el receptor')}</strong> la acepte
                                <div style="font-size:0.78rem; opacity:0.85; margin-top:2px;">Puedes chatear mientras tanto para coordinar</div>
                            </div>
                        </div>
                        <div class="chat-status-actions">
                            <button class="btn btn-danger btn-sm" onclick="app.rejectTrade(${trade.id})">
                                <i class="fa-solid fa-xmark"></i> Cancelar Propuesta
                            </button>
                        </div>
                    </div>
                `;
            }
        } else if (estado === 'confirmado') {
            banner.innerHTML = `
                <div class="chat-status-banner confirmado">
                    <div class="chat-status-info">
                        <i class="fa-solid fa-circle-check"></i>
                        <div>
                            <strong>¡Trueque confirmado!</strong> Coordinad la entrega aquí
                            ${trade.libro_propone && trade.libro_recibe ? `<div style="font-size:0.78rem; opacity:0.85; margin-top:2px;">${this.escapeHtml(trade.libro_propone)} ⇄ ${this.escapeHtml(trade.libro_recibe)}</div>` : ''}
                        </div>
                    </div>
                    <div class="chat-status-actions">
                        <button class="btn btn-success btn-sm" onclick="app.completeTrade(${trade.id})">
                            <i class="fa-solid fa-handshake"></i> Marcar como Completado
                        </button>
                    </div>
                </div>
            `;
        } else if (estado === 'completado') {
            banner.innerHTML = `
                <div class="chat-status-banner completado">
                    <div class="chat-status-info">
                        <i class="fa-solid fa-trophy"></i>
                        <div><strong>¡Intercambio completado!</strong> Recuerda calificar la experiencia</div>
                    </div>
                    <div class="chat-status-actions">
                        <button class="btn btn-primary btn-sm" onclick="app.openRateModal(${trade.id})">
                            <i class="fa-solid fa-star"></i> Calificar
                        </button>
                    </div>
                </div>
            `;
        } else {
            banner.innerHTML = '';
        }
    }

    async sendChatMessage() {
        const input = document.getElementById("chat-input");
        if (!input || !input.value.trim()) return;

        const text = input.value.trim();
        input.value = "";

        try {
            const message = await api.sendChatMessage(this.activeTradeChatId, text);
            this.appendMessageToUI(message);
            if (message.realtime_delivery === "unavailable") {
                this.showToast("Mensaje guardado en base de datos", "info");
            }
        } catch (e) {
            input.value = text;
            this.showToast(e.message || "Error al enviar mensaje", "error");
        }
    }

    // -------------------------------------------------------------------------
    // Perfil de Estudiante y Reputación
    // -------------------------------------------------------------------------
    async renderProfile() {
        const user = api.getCurrentUser();
        const profileCard = document.querySelector(".profile-card");
        if (!user) {
            if (profileCard) {
                profileCard.innerHTML = `
                    <div style="text-align: center; padding: 4rem 1.5rem;">
                        <i class="fa-solid fa-user-lock" style="font-size: 3.5rem; color: var(--primary); margin-bottom: 1rem;"></i>
                        <h2 style="margin-bottom: 0.5rem;">Inicia sesión para ver tu perfil</h2>
                        <p style="color: var(--text-secondary); max-width: 450px; margin: 0 auto 1.5rem auto;">
                            Crea una cuenta o ingresa con tus credenciales para gestionar tus publicaciones, reputación y solicitudes de trueque.
                        </p>
                        <div style="display: flex; justify-content: center; gap: 0.75rem;">
                            <button class="btn btn-primary" onclick="app.openAuthModal('login')">
                                <i class="fa-solid fa-arrow-right-to-bracket"></i> Iniciar Sesión
                            </button>
                            <button class="btn btn-secondary" onclick="app.openAuthModal('register')">
                                <i class="fa-solid fa-user-plus"></i> Registrarse
                            </button>
                        </div>
                    </div>
                `;
            }
            return;
        }

        const nameEl = document.getElementById("prof-name");
        const univEl = document.getElementById("prof-univ");
        const carreraEl = document.getElementById("prof-carrera");
        const emailEl = document.getElementById("prof-email");
        const telEl = document.getElementById("prof-tel");
        const avatarEl = document.getElementById("prof-avatar-img");
        const statTrades = document.getElementById("prof-stat-trades");
        const statRating = document.getElementById("prof-stat-rating");

        if (nameEl) nameEl.textContent = user.name;
        if (univEl) univEl.textContent = user.universidad || "Universidad";
        if (carreraEl) carreraEl.textContent = user.carrera || "Carrera";
        if (emailEl) emailEl.textContent = user.email;
        if (telEl) telEl.textContent = user.telefono || "No especificado";
        if (avatarEl) avatarEl.src = user.avatar || "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80";
        if (statTrades) statTrades.textContent = user.trueques_completados || "14";
        if (statRating) statRating.textContent = user.reputacion?.promedio ? Number(user.reputacion.promedio).toFixed(1) + " ★" : "4.9 ★";

        // Renderizar publicaciones propias
        const myBooks = this.books.filter(b => String(b.usuario_id) === String(user.id));
        const myBooksContainer = document.getElementById("prof-my-books");
        if (myBooksContainer) {
            if (myBooks.length === 0) {
                myBooksContainer.innerHTML = `<p style="color: var(--text-muted); padding: 1rem 0;">No tienes libros publicados actualmente.</p>`;
            } else {
                myBooksContainer.innerHTML = myBooks.map(b => `
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.85rem; background: var(--bg-surface-elevated); border-radius: var(--radius-md); margin-bottom: 0.5rem;">
                        <div>
                            <strong>${b.titulo}</strong>
                            <div style="font-size: 0.8rem; color: var(--text-muted);">Buscas: ${b.libro_buscado}</div>
                        </div>
                        <span class="status-badge confirmado">${b.estado_libro}</span>
                    </div>
                `).join("");
            }
        }

        // Renderizar reseñas recibidas
        const reviews = await api.getReviews();
        const reviewsContainer = document.getElementById("prof-reviews-list");
        if (reviewsContainer) {
            reviewsContainer.innerHTML = reviews.map(r => `
                <div class="review-item">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <strong>${r.autor}</strong>
                            <span style="font-size: 0.78rem; color: var(--text-muted);"> • ${r.carrera || 'Estudiante'}</span>
                        </div>
                        <div class="star-rating" style="margin: 0; font-size: 0.95rem;">
                            ${'★'.repeat(r.estrellas)}${'☆'.repeat(5 - r.estrellas)}
                        </div>
                    </div>
                    <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.4;">${r.comentario}</p>
                    <span style="font-size: 0.72rem; color: var(--text-muted);">${r.fecha || 'Reciente'}</span>
                </div>
            `).join("");
        }
    }

    openEditProfile() {
        const user = api.getCurrentUser();
        const nameInput = document.getElementById("edit-prof-name");
        const carreraInput = document.getElementById("edit-prof-carrera");
        const univInput = document.getElementById("edit-prof-univ");
        const telInput = document.getElementById("edit-prof-tel");

        if (nameInput) nameInput.value = user.name;
        if (carreraInput) carreraInput.value = user.carrera || "";
        if (univInput) univInput.value = user.universidad || "";
        if (telInput) telInput.value = user.telefono || "";

        this.openModal("edit-profile-modal");
    }

    async submitEditProfile() {
        const name = document.getElementById("edit-prof-name")?.value;
        const carrera = document.getElementById("edit-prof-carrera")?.value;
        const universidad = document.getElementById("edit-prof-univ")?.value;
        const telefono = document.getElementById("edit-prof-tel")?.value;

        try {
            await api.updateProfile({ name, carrera, universidad, telefono });
            this.showToast("Perfil actualizado correctamente", "success");
            this.closeModal("edit-profile-modal");
            this.updateUserBadge();
            this.renderProfile();
        } catch (e) {
            this.showToast(e.message || "Error al actualizar perfil", "error");
        }
    }

    // -------------------------------------------------------------------------
    // Panel de Administración (Acceso Restringido)
    // -------------------------------------------------------------------------
    async renderAdminPanel() {
        const user = api.getCurrentUser();
        const restrictedNotice = document.getElementById("admin-restricted-view");
        const adminContent = document.getElementById("admin-content-view");

        const canReviewBooks = user && ["admin", "administrador", "moderador"].includes(user.role);
        const isAdmin = ["admin", "administrador"].includes(user?.role);
        if (!canReviewBooks) {
            if (restrictedNotice) restrictedNotice.style.display = "block";
            if (adminContent) adminContent.style.display = "none";
            return;
        }

        if (restrictedNotice) restrictedNotice.style.display = "none";
        if (adminContent) adminContent.style.display = "block";

        const managementContent = document.getElementById("admin-management-content");
        const statusEl = document.getElementById("admin-backend-status");
        if (managementContent) managementContent.style.display = isAdmin ? "block" : "none";
        if (statusEl) statusEl.style.display = isAdmin ? "block" : "none";

        if (isAdmin) {
            const users = await api.listUsers();
            const tableBody = document.getElementById("admin-users-table-body");
            if (tableBody) {
                tableBody.innerHTML = users.map(u => `
                <tr>
                    <td><strong>#${u.id}</strong></td>
                    <td>
                        <div style="font-weight: 600;">${u.name || 'Sin nombre'}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${u.email || u.correo_institucional}</div>
                    </td>
                    <td>${u.carrera || u.programa_area || 'Estudiante'}</td>
                    <td>
                        <span class="status-badge ${u.role === 'admin' ? 'rechazado' : u.role === 'moderador' ? 'confirmado' : 'propuesto'}">
                            ${u.role || u.rol || 'usuario'}
                        </span>
                    </td>
                    <td>
                        <span style="color: var(--success); font-weight: 600;">Activo</span>
                    </td>
                    <td>
                        ${u.role !== 'admin' && u.role !== 'moderador' ? `
                            <button class="btn btn-secondary btn-sm" onclick="app.promoteToModerator('${u.id}')">
                                <i class="fa-solid fa-shield-halved"></i> Promover a Moderador
                            </button>
                        ` : `
                            <span style="color: var(--text-muted); font-size: 0.8rem;">Privilegios asignados</span>
                        `}
                    </td>
                </tr>
            `).join("");
            }

            const health = await api.getHealth();
            const dbHealth = await api.getDbHealth();
            if (statusEl) {
                statusEl.innerHTML = `
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <span class="status-badge completado">API: ${health.status}</span>
                    <span class="status-badge confirmado">DB: ${dbHealth.database?.status || 'conectada'} (${dbHealth.database?.dialecto || 'PostgreSQL'})</span>
                </div>
            `;
            }
        }

        try {
            const pendingVerifications = await api.getPendingBookVerifications();
            const queue = document.getElementById("admin-book-verification-queue");
            if (queue) {
                queue.innerHTML = pendingVerifications.length
                    ? pendingVerifications.map(verification => `
                        <article style="padding:1rem;border:1px solid var(--border-color);border-radius:var(--radius-md);">
                            <strong>${this.escapeHtml(verification.titulo)}</strong>
                            <div style="color:var(--text-secondary);font-size:.85rem;">
                                Autor: ${this.escapeHtml(verification.autor || "No indicado")} ·
                                ISBN: ${this.escapeHtml(verification.isbn || "No indicado")} ·
                                Usuario #${verification.usuario_id}
                            </div>
                            <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.75rem;">
                                <button class="btn btn-secondary btn-sm" onclick="app.viewVerificationPhotos(${verification.verificacion_id})">
                                    Ver fotos
                                </button>
                                <input id="verification-note-${verification.verificacion_id}" class="form-control" style="flex:1;min-width:180px;" value="Portada, código e ISBN revisados">
                                <button class="btn btn-success btn-sm" onclick="app.reviewBookVerification(${verification.verificacion_id}, 'aprobada')">Aprobar</button>
                                <button class="btn btn-danger btn-sm" onclick="app.reviewBookVerification(${verification.verificacion_id}, 'rechazada')">Rechazar</button>
                            </div>
                        </article>
                    `).join("")
                    : '<p style="color:var(--text-muted);">No hay libros pendientes de revisión.</p>';
            }
        } catch (e) {
            this.showToast(e.message || "No se pudo cargar la cola de verificación", "error");
        }
    }

    async viewVerificationPhotos(verificationId) {
        try {
            const [cover, isbnPage] = await Promise.all([
                api.getBookVerificationEvidence(verificationId, "portada"),
                api.getBookVerificationEvidence(verificationId, "pagina-isbn")
            ]);
            this.closeVerificationPhotos();
            this.verificationPhotoUrls = [
                URL.createObjectURL(cover),
                URL.createObjectURL(isbnPage)
            ];
            document.getElementById("review-book-cover-photo").src = this.verificationPhotoUrls[0];
            document.getElementById("review-book-isbn-photo").src = this.verificationPhotoUrls[1];
            this.openModal("review-book-photos-modal");
        } catch (e) {
            this.showToast(e.message || "No se pudieron abrir las fotos", "error");
        }
    }

    closeVerificationPhotos() {
        (this.verificationPhotoUrls || []).forEach(url => URL.revokeObjectURL(url));
        this.verificationPhotoUrls = [];
        document.getElementById("review-book-cover-photo").removeAttribute("src");
        document.getElementById("review-book-isbn-photo").removeAttribute("src");
        this.closeModal("review-book-photos-modal");
    }

    async reviewBookVerification(verificationId, decision) {
        const note = document.getElementById(`verification-note-${verificationId}`)?.value?.trim();
        if (!note || note.length < 3) {
            this.showToast("Escribe una nota breve de revisión", "warning");
            return;
        }
        try {
            await api.reviewBookVerification(verificationId, decision, note);
            this.showToast(
                decision === "aprobada" ? "Libro aprobado y publicado" : "Evidencia rechazada",
                "success"
            );
            await this.renderAdminPanel();
        } catch (e) {
            this.showToast(e.message || "No se pudo guardar la revisión", "error");
        }
    }

    async promoteToModerator(userId) {
        try {
            await api.promoteUser(userId);
            this.showToast(`Usuario promovido a moderador exitosamente`, "success");
            this.renderAdminPanel();
        } catch (e) {
            this.showToast(e.message || "Error al promover usuario", "error");
        }
    }

    loginAsAdmin() {
        const adminUser = MOCK_USUARIOS.find(u => u.role === "admin");
        if (adminUser) {
            api.setCurrentUser(adminUser);
            api.setToken("admin_mock_token");
            this.updateUserBadge();
            this.showToast("Sesión iniciada como Administrador", "success");
            this.renderAdminPanel();
        }
    }

    // -------------------------------------------------------------------------
    // Calificación de Trueques
    // -------------------------------------------------------------------------
    openRateModal(tradeId) {
        this.ratingTradeId = tradeId;
        this.setRatingStars(5);
        const textInput = document.getElementById("rate-review-text");
        if (textInput) textInput.value = "";
        this.openModal("rate-trade-modal");
    }

    setRatingStars(count) {
        this.selectedRating = count;
        document.querySelectorAll(".star-select-btn").forEach(btn => {
            const val = parseInt(btn.getAttribute("data-star-val"));
            if (val <= count) {
                btn.style.color = "#fbbf24";
            } else {
                btn.style.color = "var(--text-muted)";
            }
        });
    }

    async submitTradeRating() {
        const text = document.getElementById("rate-review-text")?.value;
        const trade = this.trades.find(t => t.id === this.ratingTradeId);
        if (!trade) return;
        
        const current = api.getCurrentUser();
        const otherUserId = String(trade.usuario_propone_id) === String(current.id) ? trade.usuario_recibe_id : trade.usuario_propone_id;

        try {
            await api.rateTrade(this.ratingTradeId, {
                estrellas: this.selectedRating,
                resena: text || "Intercambio completado satisfactoriamente.",
                usuario_calificado_id: otherUserId
            });

            this.showToast("¡Gracias! Tu calificación ha sido registrada para la reputación comunitaria.", "success");
            this.closeModal("rate-trade-modal");
            this.trades = await api.getTrueques();
            this.renderTrades();
        } catch (e) {
            this.showToast(e.message || "Error al calificar", "error");
        }
    }

    // -------------------------------------------------------------------------
    // Auth & Social Login (Modales Separados)
    // -------------------------------------------------------------------------
    openLoginModal() {
        this.closeModal("register-modal");
        this.closeModal("auth-modal");
        this.openModal("login-modal");
    }

    openRegisterModal() {
        this.closeModal("login-modal");
        this.closeModal("auth-modal");
        this.openModal("register-modal");
    }

    switchToLogin() {
        this.closeModal("register-modal");
        this.openModal("login-modal");
    }

    switchToRegister() {
        this.closeModal("login-modal");
        this.openModal("register-modal");
    }

    openAuthModal(tab = "login") {
        if (tab === "register") {
            this.openRegisterModal();
        } else {
            this.openLoginModal();
        }
    }

    toggleChatSidebar() {
        const sidebar = document.getElementById("chat-sidebar");
        if (sidebar) {
            sidebar.classList.toggle("mobile-open");
        }
    }

    async submitLogin() {
        const email = document.getElementById("login-email")?.value?.trim();
        const pass = document.getElementById("login-password")?.value;

        if (!email || !pass) {
            this.showToast("Ingresa tu correo y contraseña", "warning");
            return;
        }

        try {
            const result = await api.login(email, pass);
            this.updateUserBadge();
            this.showToast(`¡Bienvenido de nuevo, ${result.user?.name || ''}!`, "success");
            this.closeModal("login-modal");
            this.closeModal("auth-modal");
            const emailInput = document.getElementById("login-email");
            const passInput = document.getElementById("login-password");
            if (emailInput) emailInput.value = "";
            if (passInput) passInput.value = "";
            this.renderCurrentView();
        } catch (e) {
            this.showToast(e.message || "Credenciales inválidas", "error");
        }
    }

    async submitRegister() {
        const name = document.getElementById("reg-name")?.value?.trim();
        const email = document.getElementById("reg-email")?.value?.trim();
        const pass = document.getElementById("reg-password")?.value;
        const telefono = document.getElementById("reg-tel")?.value?.trim();

        if (!name) {
            this.showToast("Por favor escribe tu nombre completo", "warning");
            return;
        }
        if (!email || !email.includes("@")) {
            this.showToast("Por favor escribe un correo electrónico válido", "warning");
            return;
        }
        if (!pass || pass.length < 6) {
            this.showToast("La contraseña debe tener al menos 6 caracteres", "warning");
            return;
        }

        try {
            const result = await api.register({ name, email, password: pass, telefono });
            this.updateUserBadge();
            this.showToast(`¡Cuenta creada con éxito! Bienvenido, ${result.user?.name || name}`, "success");
            this.closeModal("register-modal");
            this.closeModal("auth-modal");
            ["reg-name", "reg-email", "reg-password", "reg-tel"].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = "";
            });
            this.renderCurrentView();
        } catch (e) {
            this.showToast(e.message || "Error al registrar la cuenta", "error");
        }
    }

    async logout() {
        if (this.chatWs) {
            this.chatWs.close();
            this.chatWs = null;
        }
        await api.logout();
        this.updateUserBadge();
        this.showToast("Has cerrado sesión", "info");
        this.renderCurrentView();
    }

    openPublishBookModal() {
        const user = api.getCurrentUser();
        if (!user) {
            this.showToast("Debes iniciar sesión para publicar un libro", "warning");
            this.openAuthModal("login");
            return;
        }
        this.openModal("publish-book-modal");
    }

    async socialLogin(provider) {
        await api.socialLogin(provider);
    }

    updateUserBadge() {
        const user = api.getCurrentUser();
        const guestBox = document.getElementById("header-guest-box");
        const userBox = document.getElementById("header-user-box");
        const avatarMini = document.getElementById("header-user-avatar");
        const nameMini = document.getElementById("header-user-name");
        const roleMini = document.getElementById("header-user-role");
        const adminNavBtn = document.getElementById("nav-admin-btn");

        if (user) {
            if (guestBox) guestBox.style.display = "none";
            if (userBox) userBox.style.display = "flex";
            if (avatarMini) avatarMini.src = user.avatar || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80";
            if (nameMini) nameMini.textContent = user.name;
            if (roleMini) roleMini.textContent = (user.role || "usuario").toUpperCase();

            // Mostrar u ocultar nav de Admin
            if (adminNavBtn) {
                adminNavBtn.style.display = ["admin", "administrador", "moderador"].includes(user.role)
                    ? "inline-flex"
                    : "none";
            }
        } else {
            if (guestBox) guestBox.style.display = "flex";
            if (userBox) userBox.style.display = "none";
            if (adminNavBtn) adminNavBtn.style.display = "none";
        }
    }

    // -------------------------------------------------------------------------
    // Modales Generales
    // -------------------------------------------------------------------------
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add("active");
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove("active");
    }

    // -------------------------------------------------------------------------
    // Tema & Toasts
    // -------------------------------------------------------------------------
    toggleTheme() {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("campus_swap_theme", next);

        const icon = document.getElementById("theme-toggle-icon");
        if (icon) {
            icon.className = next === "dark" ? "fa-solid fa-moon" : "fa-solid fa-sun";
        }
    }

    _applyTheme() {
        const saved = localStorage.getItem("campus_swap_theme") || "dark";
        document.documentElement.setAttribute("data-theme", saved);
        const icon = document.getElementById("theme-toggle-icon");
        if (icon) {
            icon.className = saved === "dark" ? "fa-solid fa-moon" : "fa-solid fa-sun";
        }
    }

    showToast(message, type = "info") {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            document.body.appendChild(container);
        }

        const icons = {
            success: "fa-circle-check",
            warning: "fa-triangle-exclamation",
            error: "fa-circle-xmark",
            info: "fa-circle-info"
        };
        const colors = {
            success: "var(--success)",
            warning: "var(--warning)",
            error: "var(--danger)",
            info: "var(--primary)"
        };

        const toast = document.createElement("div");
        toast.className = "toast";
        toast.innerHTML = `
            <i class="fa-solid ${icons[type] || icons.info}" style="color: ${colors[type] || colors.info}; font-size: 1.1rem;"></i>
            <span>${message}</span>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
}
