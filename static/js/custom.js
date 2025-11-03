document.addEventListener('DOMContentLoaded', function() {
    // Dropdown menu logic
    const dropdowns = document.querySelectorAll('.dropdown');
    let leaveTimeout;

    dropdowns.forEach(dropdown => {
        const dropbtn = dropdown.querySelector('.dropbtn');
        const content = dropdown.querySelector('.dropdown-content');

        // Function to open the dropdown
        const openDropdown = () => {
            clearTimeout(leaveTimeout);
            // Close other open dropdowns
            dropdowns.forEach(d => {
                if (d !== dropdown) {
                    d.classList.remove('dropdown-active');
                }
            });
            dropdown.classList.add('dropdown-active');
        };

        // Function to close the dropdown
        const closeDropdown = () => {
            leaveTimeout = setTimeout(() => {
                dropdown.classList.remove('dropdown-active');
            }, 300); // 300ms delay before closing
        };

        // Event listeners for mouse interaction
        dropdown.addEventListener('mouseenter', openDropdown);
        dropdown.addEventListener('mouseleave', closeDropdown);

        // Keep dropdown open if mouse enters the content area
        if (content) {
            content.addEventListener('mouseenter', () => {
                clearTimeout(leaveTimeout);
            });
            content.addEventListener('mouseleave', closeDropdown);
        }

        // Support for touch devices (click to toggle)
        if (dropbtn) {
            dropbtn.addEventListener('click', function(event) {
                // Prevent the link from navigating if it's a '#'
                if (dropbtn.getAttribute('href') === '#') {
                    event.preventDefault();
                }
                
                const isActive = dropdown.classList.contains('dropdown-active');
                
                // Close all dropdowns first
                dropdowns.forEach(d => d.classList.remove('dropdown-active'));

                // If it wasn't active, open it
                if (!isActive) {
                    dropdown.classList.add('dropdown-active');
                }
            });
        }
    });

    // Close dropdowns if clicking outside
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.dropdown')) {
            dropdowns.forEach(dropdown => {
                dropdown.classList.remove('dropdown-active');
            });
        }
    });

    // AI Chat Modal Logic
    const openModalButton = document.getElementById('openAiChatModalButton');
    const aiChatModal = document.getElementById('aiChatModal');
    const closeModalButton = aiChatModal ? aiChatModal.querySelector('.close-button') : null;
    const aiChatModalBody = document.getElementById('aiChatModalBody');

    const openModal = () => {
        if (!aiChatModal || !aiChatModalBody) return;
        
        aiChatModal.classList.add('open');
        openModalButton.setAttribute('aria-expanded', 'true');
        
        // Fetch chat content only if it's not already loaded
        if (aiChatModalBody.innerHTML.trim() === '') {
            aiChatModalBody.innerHTML = '<p>Cargando asistente...</p>';
            fetch('/ai_chat/')
                .then(response => response.text())
                .then(html => {
                    aiChatModalBody.innerHTML = html;
                    // If there's a form, focus the input
                    const chatInput = aiChatModalBody.querySelector('#chat-input');
                    if (chatInput) {
                        chatInput.focus();
                    }
                })
                .catch(error => {
                    console.error('Error loading AI chat:', error);
                    aiChatModalBody.innerHTML = '<p>Error al cargar el asistente. Inténtalo de nuevo más tarde.</p>';
                });
        }
    };

    const closeModal = () => {
        if (!aiChatModal) return;
        aiChatModal.classList.remove('open');
        openModalButton.setAttribute('aria-expanded', 'false');
    };

    if (openModalButton) {
        openModalButton.addEventListener('click', openModal);
    }
    if (closeModalButton) {
        closeModalButton.addEventListener('click', closeModal);
    }

    // Close modal on escape key
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && aiChatModal && aiChatModal.classList.contains('open')) {
            closeModal();
        }
    });
    
    // Close modal on outside click
    if (aiChatModal) {
        aiChatModal.addEventListener('click', (event) => {
            if (event.target === aiChatModal) {
                closeModal();
            }
        });
    }
});