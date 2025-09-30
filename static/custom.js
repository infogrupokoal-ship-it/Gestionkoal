document.addEventListener('DOMContentLoaded', function() {
    function fetchNotificationCount() {
        fetch('/notifications/api/unread_notifications_count')
            .then(response => response.json())
            .then(data => {
                document.getElementById('notification-count').textContent = data.unread_count;
            })
            .catch(error => console.error('Error fetching notification count:', error));
    }

    fetchNotificationCount();
    // Fetch every 30 seconds
    setInterval(fetchNotificationCount, 30000);

    // Dropdown Menu Logic for better UX
    let menuTimeout;
    const dropdowns = document.querySelectorAll('.dropdown');

    dropdowns.forEach(dropdown => {
        const content = dropdown.querySelector('.dropdown-content');
        
        dropdown.addEventListener('mouseenter', function() {
            clearTimeout(menuTimeout);
            // Close other open dropdowns before opening a new one
            document.querySelectorAll('.dropdown-content.show-dropdown').forEach(openDropdown => {
                if (openDropdown !== content) {
                    openDropdown.classList.remove('show-dropdown');
                }
            });
            content.classList.add('show-dropdown');
        });

        dropdown.addEventListener('mouseleave', function() {
            menuTimeout = setTimeout(function() {
                content.classList.remove('show-dropdown');
            }, 200); // A small delay to allow moving mouse into the content
        });
    });

    // AI Chat Modal Logic
    const aiChatModal = document.getElementById('aiChatModal');
    const openBtn = document.getElementById('openAiChatModalButton');
    const modalBody = document.getElementById('aiChatModalBody');
    const closeBtn = aiChatModal ? aiChatModal.querySelector('.close-button') : null;

    function openChatModal() {
        if (!aiChatModal) return;
        aiChatModal.classList.add('open');
        if (openBtn) openBtn.setAttribute('aria-expanded', 'true');

        // Cargar contenido del chat
        fetch('/ai_chat/content')
            .then(r => r.text())
            .then(html => {
                modalBody.innerHTML = html;
                attachChatEventListeners(); // engancha handlers del formulario
                // scroll al final
                const chatWindow = modalBody.querySelector('.chat-window');
                if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight;
            })
            .catch(err => {
                console.error('Error cargando chat:', err);
                modalBody.innerHTML = '<p>Error al cargar el chat de IA.</p>';
            });
    }

    function closeChatModal() {
        if (!aiChatModal) return;
        aiChatModal.classList.remove('open');
        if (openBtn) openBtn.setAttribute('aria-expanded', 'false');
    }

    openBtn?.addEventListener('click', openChatModal);
    closeBtn?.addEventListener('click', closeChatModal);
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeChatModal(); });
    window.addEventListener('click', (e) => { if (e.target === aiChatModal) closeChatModal(); });

    function attachChatEventListeners() {
        const chatForm = modalBody.querySelector('#ai-chat-form');
        const chatWindow = modalBody.querySelector('.chat-window');
        const messageInput = modalBody.querySelector('#message');
        const clearHistoryForm = modalBody.querySelector('form[action="/ai_chat/clear_history"]');

        // Enviar con Enter (Shift+Enter conserva salto de línea)
        if (messageInput && chatForm) {
            messageInput.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    chatForm.requestSubmit();
                }
            });
        }

        if (chatForm && chatWindow && messageInput) {
            chatForm.onsubmit = function (event) {
                event.preventDefault();
                const userMessage = messageInput.value.trim();
                if (!userMessage) return;

                // Construir FormData ANTES de limpiar y forzar el valor
                const formData = new FormData(chatForm);
                formData.set('message', userMessage);

                // Pintar mensaje del usuario
                const u = document.createElement('div');
                u.className = 'chat-message user-message';
                u.innerHTML = `<strong>user:</strong> ${userMessage}`;
                chatWindow.appendChild(u);
                chatWindow.scrollTop = chatWindow.scrollHeight;

                messageInput.value = ''; // limpiar input

                fetch(chatForm.action, { method: 'POST', body: formData })
                    .then(r => r.json())
                    .then(data => {
                        const a = document.createElement('div');
                        a.className = 'chat-message ai-message';
                        if (data.ok) {
                            const replyHtml = String(data.reply).replace(/\n/g, '<br>');
                            a.innerHTML = `<strong>model:</strong> ${replyHtml}`;
                        } else {
                            a.innerHTML = `<strong>Error:</strong> ${data.error || 'Error desconocido'}`;
                        }
                        chatWindow.appendChild(a);
                        chatWindow.scrollTop = chatWindow.scrollHeight;
                    })
                    .catch(err => {
                        const e = document.createElement('div');
                        e.className = 'chat-message ai-message';
                        e.innerHTML = `<strong>Error de conexión:</strong> ${err}`;
                        chatWindow.appendChild(e);
                        chatWindow.scrollTop = chatWindow.scrollHeight;
                    });
            };
        }

        if (clearHistoryForm) {
            clearHistoryForm.onsubmit = function (event) {
                event.preventDefault();
                fetch(clearHistoryForm.action, { method: 'POST', body: new FormData(clearHistoryForm) })
                    .then(r => r.text())
                    .then(html => {
                        modalBody.innerHTML = html;
                        attachChatEventListeners(); // reenganchar tras recargar
                        const chatWindow = modalBody.querySelector('.chat-window');
                        if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight;
                    })
                    .catch(err => {
                        console.error('Error al limpiar historial:', err);
                        alert('Error al limpiar el historial.');
                    });
            };
        }
    }
});