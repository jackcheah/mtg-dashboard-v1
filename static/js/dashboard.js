            // ==========================================
            // UI ENHANCEMENTS & UTILITIES
            // ==========================================

            function escapeHtml(str) {
                if (!str) return '';
                return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
            }

            class ModalManager {
                constructor() {
                    this.overlay = null;
                    this.init();
                }

                init() {
                    // Remove existing if any
                    const existing = document.querySelector('.custom-modal-overlay');
                    if (existing) existing.remove();

                    // Create container
                    this.overlay = document.createElement('div');
                    this.overlay.className = 'custom-modal-overlay';
                    document.body.appendChild(this.overlay);
                }

                _show(html) {
                    return new Promise((resolve) => {
                        if (this._cleanupTimer) {
                            clearTimeout(this._cleanupTimer);
                            this._cleanupTimer = null;
                        }
                        this.overlay.innerHTML = html;

                        // Bind buttons
                        const confirmBtn = this.overlay.querySelector('.js-modal-confirm');
                        const cancelBtn = this.overlay.querySelector('.js-modal-cancel');
                        const input = this.overlay.querySelector('.custom-modal-input');

                        if (input) input.focus();

                        const close = (result) => {
                            this.overlay.classList.remove('show');
                            this._cleanupTimer = setTimeout(() => {
                                this.overlay.innerHTML = '';
                                this._cleanupTimer = null;
                            }, 200);
                            resolve(result);
                        };

                        if (confirmBtn) {
                            confirmBtn.onclick = () => {
                                const value = input ? input.value : true;
                                close(value);
                            };
                        }

                        if (cancelBtn) {
                            cancelBtn.onclick = () => close(false);
                        }

                        // Allow Enter key to confirm
                        if (input) {
                            input.addEventListener('keypress', (e) => {
                                if (e.key === 'Enter') confirmBtn.click();
                            });
                        }

                        // Show modal
                        requestAnimationFrame(() => this.overlay.classList.add('show'));
                    });
                }

                async confirm(title, message, confirmText = 'Confirm', cancelText = 'Cancel') {
                    const html = `
                    <div class="custom-modal">
                        <div class="custom-modal-header">${escapeHtml(title)}</div>
                        <div class="custom-modal-body">${escapeHtml(message).replace(/\n/g, '<br>')}</div>
                        <div class="custom-modal-actions">
                            ${cancelText ? `<button class="btn btn-secondary js-modal-cancel">${escapeHtml(cancelText)}</button>` : ''}
                            <button class="btn btn-primary js-modal-confirm">${escapeHtml(confirmText)}</button>
                        </div>
                    </div>
                `;
                    return this._show(html);
                }

                async showHtml(title, bodyHtml, buttonText = 'Got it') {
                    const html = `
                    <div class="custom-modal">
                        <div class="custom-modal-header">${escapeHtml(title)}</div>
                        <div class="custom-modal-body">${bodyHtml}</div>
                        <div class="custom-modal-actions">
                            <button class="btn btn-primary js-modal-confirm">${escapeHtml(buttonText)}</button>
                        </div>
                    </div>
                `;
                    return this._show(html);
                }

                async prompt(title, message, defaultValue = '', placeholder = '') {
                    const html = `
                    <div class="custom-modal">
                        <div class="custom-modal-header">${escapeHtml(title)}</div>
                        <div class="custom-modal-body">
                            ${escapeHtml(message)}
                            <input type="text" class="custom-modal-input" value="${escapeHtml(defaultValue)}" placeholder="${escapeHtml(placeholder)}">
                        </div>
                        <div class="custom-modal-actions">
                            <button class="btn btn-secondary js-modal-cancel">Cancel</button>
                            <button class="btn btn-primary js-modal-confirm">Submit</button>
                        </div>
                    </div>
                `;
                    return this._show(html);
                }
            }

            const modalManager = new ModalManager();

            // Keyboard Navigation Class
            class KeyboardNavigator {
                constructor() {
                    this.init();
                }

                init() {
                    document.addEventListener('keydown', (e) => this.handleKeydown(e));

                    // Add keyboard help to UI
                    this.addKeyboardHelp();
                }

                addKeyboardHelp() {
                    // Could actally be added to DOM here or handled in HTML
                }

                showKeyboardHelp() {
                    const helpContent = `
                    <div style="text-align: left; line-height: 1.8;">
                        <h3 style="margin-top: 0; color: var(--color-primary);">⌨️ Keyboard Shortcuts</h3>

                        <div style="margin-bottom: 1rem;">
                            <strong style="color: var(--color-success);">Scoring:</strong><br>
                            • <kbd>W</kbd> or <kbd>1</kbd> = Win<br>
                            • <kbd>D</kbd> or <kbd>2</kbd> = Draw<br>
                            • <kbd>L</kbd> or <kbd>3</kbd> = Loss
                        </div>

                        <div style="margin-bottom: 1rem;">
                            <strong style="color: var(--color-primary);">Navigation:</strong><br>
                            • <kbd>Tab</kbd> = Next player<br>
                            • <kbd>Shift</kbd>+<kbd>Tab</kbd> = Previous player<br>
                            • <kbd>Ctrl</kbd>+<kbd>Enter</kbd> = Submit active table
                        </div>

                        <div>
                            <strong style="color: var(--color-warning);">Other:</strong><br>
                            • <kbd>Esc</kbd> = Close modal<br>
                            • <kbd>?</kbd> = Show this help
                        </div>
                    </div>
                `;

                    modalManager.showHtml(
                        'Keyboard Shortcuts',
                        helpContent,
                        'Got it'
                    );
                }

                handleKeydown(e) {
                    // If in input/textarea, ignore (except for Esc key)
                    if ((e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') && e.key !== 'Escape') return;

                    // Global Shortcuts

                    // ? key shows help
                    if (e.key === '?' && !e.target.matches('input, textarea')) {
                        e.preventDefault();
                        this.showKeyboardHelp();
                        return;
                    }

                    // Ctrl+Enter: Submit active table (if focus is within a table)
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                        const activeTableCard = e.target.closest('.table-card');
                        if (activeTableCard) {
                            e.preventDefault();
                            const submitBtn = activeTableCard.querySelector('.submit-table-btn');
                            if (submitBtn && !submitBtn.disabled) submitBtn.click();
                            return;
                        }
                    }

                    // Esc: Close any open modal
                    if (e.key === 'Escape') {
                        const modal = document.querySelector('.custom-modal-overlay.show');
                        if (modal) {
                            const cancelBtn = modal.querySelector('.js-modal-cancel');
                            if (cancelBtn) cancelBtn.click();
                        }
                    }

                    // Tab navigation between players (only within table cards)
                    if (e.key === 'Tab') {
                        if (!e.target.closest('.table-card')) return;

                        const allScoreBtns = Array.from(document.querySelectorAll('.score-btn:not(:disabled)'));

                        if (allScoreBtns.length === 0) return;

                        const currentIndex = allScoreBtns.indexOf(document.activeElement);

                        // If no button is focused, focus first button
                        if (currentIndex === -1) {
                            e.preventDefault();
                            allScoreBtns[0].focus();
                            return;
                        }

                        e.preventDefault();

                        if (e.shiftKey) {
                            // Navigate backwards
                            const prevIndex = currentIndex > 0 ? currentIndex - 1 : allScoreBtns.length - 1;
                            allScoreBtns[prevIndex].focus();
                        } else {
                            // Navigate forwards
                            const nextIndex = (currentIndex + 1) % allScoreBtns.length;
                            allScoreBtns[nextIndex].focus();
                        }
                    }

                    // Scoring Shortcuts (W/D/L or 1/2/3)
                    // Only works if focus is on a score button or within a player row
                    const activeEl = document.activeElement;
                    if (activeEl && (activeEl.classList.contains('score-btn') || activeEl.closest('.table-player'))) {
                        const playerRow = activeEl.closest('.table-player');

                        if (playerRow) {
                            let btnToClick = null;

                            // Map keys to actions (improved mapping: 1=Win, 2=Draw, 3=Loss)
                            if (e.key.toLowerCase() === 'w' || e.key === '1') {
                                btnToClick = playerRow.querySelector('.score-btn-win');
                            } else if (e.key.toLowerCase() === 'd' || e.key === '2') {
                                btnToClick = playerRow.querySelector('.score-btn-draw');
                            } else if (e.key.toLowerCase() === 'l' || e.key === '3') {
                                btnToClick = playerRow.querySelector('.score-btn-loss');
                            }

                            if (btnToClick) {
                                e.preventDefault();
                                btnToClick.click();
                            }
                        }
                    }
                }
            }

            const keyboardNav = new KeyboardNavigator();

            // Init
            document.addEventListener('DOMContentLoaded', () => {
                // Restore compact mode preference from localStorage
                if (localStorage.getItem('compactMode') === 'true') {
                    document.body.classList.add('compact-mode');
                    const btn = document.querySelector('button[onclick="toggleCompactMode()"] i');
                    if (btn) btn.className = 'fas fa-expand-alt';
                    const label = document.querySelector('button[onclick="toggleCompactMode()"] span');
                    if (label) label.textContent = 'Expand';
                }
            });

            // Batch Submit Logic
            async function batchSubmitTables() {
                // Find all tables that have full scores but are not submitted
                const filledTables = [];
                const allTableCards = document.querySelectorAll('.table-card');

                allTableCards.forEach(card => {
                    const submitBtn = card.querySelector('.submit-table-btn');
                    if (submitBtn && !submitBtn.disabled && !submitBtn.classList.contains('submitted')) {
                        const tableName = card.id.replace('table-', '').replace(/-/g, ' ');

                        // Check if scores are filled (by checking JS state)
                        const hasScores = tableScores[tableName] &&
                            Object.keys(tableScores[tableName]).length === card.querySelectorAll('.table-player').length;

                        if (hasScores) {
                            filledTables.push(tableName);
                        }
                    }
                });

                if (filledTables.length === 0) {
                    showToast('Batch Submit', 'No unsubmitted tables found with full scores.', 'info');
                    return;
                }

                const confirmed = await modalManager.confirm(
                    'Batch Submit',
                    `Found ${filledTables.length} tables ready to submit.\n\nTables: ${filledTables.join(', ')}\n\nSubmit all?`,
                    `Submit ${filledTables.length} Tables`
                );

                if (confirmed) {
                    for (let i = 0; i < filledTables.length; i++) {
                        showToast('Batch Submit', `Submitting ${i + 1}/${filledTables.length} tables...`, 'info');
                        await submitTableResults(filledTables[i]);
                        // Small delay to prevent race conditions/UI jank
                        await new Promise(r => setTimeout(r, 300));
                    }
                    showToast('Batch Complete', `All ${filledTables.length} tables submitted.`, 'success');
                }
            }

            // Compact Mode Toggle
            function toggleCompactMode() {
                document.body.classList.toggle('compact-mode');
                const isCompact = document.body.classList.contains('compact-mode');

                // Save preference to localStorage
                localStorage.setItem('compactMode', isCompact);

                const btn = document.querySelector('button[onclick="toggleCompactMode()"] i');
                const label = document.querySelector('button[onclick="toggleCompactMode()"] span');
                if (isCompact) {
                    if (btn) btn.className = 'fas fa-expand-alt';
                    if (label) label.textContent = 'Expand';
                    showToast('View Mode', 'Compact mode enabled', 'info');
                } else {
                    if (btn) btn.className = 'fas fa-compress-alt';
                    if (label) label.textContent = 'Compact';
                    showToast('View Mode', 'Standard mode enabled', 'info');
                }
            }

            // ============================================
            // EVENT MODE SELECTION (Team vs Individual)
            // ============================================

            let currentEventMode = null;  // null until selected: 'team' or 'individual'
            let selectedEventModeTemp = null;
            let initialStateLoaded = false;  // Gate for mode-dependent rendering

            function showEventModeModal() {
                const overlay = document.getElementById('event-mode-overlay');
                if (overlay) {
                    overlay.classList.add('show');
                    selectedEventModeTemp = null;
                    document.querySelectorAll('#event-mode-overlay .scoring-mode-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    document.getElementById('confirm-event-mode-btn').disabled = true;
                }
            }

            function closeEventModeModal() {
                const overlay = document.getElementById('event-mode-overlay');
                if (overlay) {
                    overlay.classList.remove('show');
                }
            }

            function selectEventMode(mode) {
                selectedEventModeTemp = mode;
                document.querySelectorAll('#event-mode-overlay .scoring-mode-card').forEach(card => {
                    card.classList.remove('selected');
                });
                const selectedCard = document.querySelector(`#event-mode-overlay .scoring-mode-card[data-mode="${mode}"]`);
                if (selectedCard) {
                    selectedCard.classList.add('selected');
                }
                document.getElementById('confirm-event-mode-btn').disabled = false;
            }

            async function confirmEventMode() {
                if (!selectedEventModeTemp) return;

                try {
                    const response = await fetch('/set_event_mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: selectedEventModeTemp })
                    });

                    const data = await response.json();

                    if (data.success) {
                        currentEventMode = selectedEventModeTemp;
                        closeEventModeModal();

                        if (currentEventMode === 'individual') {
                            showToast('Individual Event Selected',
                                'Solo players will compete individually. Top Cut for 17+ players.',
                                'success', 4000);
                            addIndividualModeIndicator();
                        } else {
                            showToast('Team Event Selected',
                                'Teams of 4 players will compete together.',
                                'success', 3000);
                        }

                        // After event mode is set, show scoring mode modal
                        showScoringModeModal();
                    } else {
                        showToast('Error', data.message || 'Failed to set event mode', 'error');
                    }
                } catch (error) {
                    console.error('Error setting event mode:', error);
                    showToast('Error', 'Failed to set event mode', 'error');
                }
            }

            function addIndividualModeIndicator() {
                const header = document.querySelector('.header p');
                if (header) {
                    // Update subtitle text (find text node safely)
                    const textNode = Array.from(header.childNodes).find(n => n.nodeType === Node.TEXT_NODE);
                    if (textNode) textNode.textContent = 'Knights of Round Table - CEDH Individual Championship ';
                    if (!document.getElementById('individual-badge')) {
                        const badge = document.createElement('span');
                        badge.id = 'individual-badge';
                        badge.className = 'japanese-mode-badge';
                        badge.style.background = '#7c3aed';
                        badge.style.boxShadow = 'none';
                        badge.innerHTML = '<i class="fas fa-user"></i> Individual';
                        badge.style.marginLeft = '10px';
                        header.appendChild(badge);
                    }
                }
            }

            function goBackToEventMode() {
                closeScoringModeModal();
                selectedScoringModeTemp = null;
                document.querySelectorAll('#scoring-mode-overlay .scoring-mode-card').forEach(card => {
                    card.classList.remove('selected');
                });
                document.getElementById('confirm-scoring-mode-btn').disabled = true;
                setTimeout(() => showEventModeModal(), 200);
            }

            // ============================================
            // SCORING MODE SELECTION (Japanese Swiss Point Mode)
            // ============================================

            // Global scoring mode state
            let currentScoringMode = 'western';  // Default to western
            let selectedScoringModeTemp = null;  // Temporary selection before confirmation

            // Show scoring mode selection modal
            function showScoringModeModal() {
                const overlay = document.getElementById('scoring-mode-overlay');
                if (overlay) {
                    overlay.classList.add('show');
                    // Reset selection state (scoped to scoring overlay only)
                    selectedScoringModeTemp = null;
                    overlay.querySelectorAll('.scoring-mode-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    document.getElementById('confirm-scoring-mode-btn').disabled = true;
                }
            }

            // Close scoring mode modal
            function closeScoringModeModal() {
                const overlay = document.getElementById('scoring-mode-overlay');
                if (overlay) {
                    overlay.classList.remove('show');
                }
            }

            // Handle scoring mode card selection
            function selectScoringMode(mode) {
                selectedScoringModeTemp = mode;

                // Update UI to show selection
                document.querySelectorAll('#scoring-mode-overlay .scoring-mode-card').forEach(card => {
                    card.classList.remove('selected');
                });
                const selectedCard = document.querySelector(`#scoring-mode-overlay .scoring-mode-card[data-mode="${mode}"]`);
                if (selectedCard) {
                    selectedCard.classList.add('selected');
                }

                // Enable confirm button
                document.getElementById('confirm-scoring-mode-btn').disabled = false;
            }

            // Confirm scoring mode selection and call API
            async function confirmScoringMode() {
                if (!selectedScoringModeTemp) return;

                try {
                    const response = await fetch('/set_scoring_mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: selectedScoringModeTemp })
                    });

                    if (!response.ok) {
                        showToast('Error', `Server error (${response.status}). Please try again.`, 'error');
                        return;
                    }

                    const data = await response.json();

                    if (data.success) {
                        currentScoringMode = selectedScoringModeTemp;
                        closeScoringModeModal();

                        if (currentScoringMode === 'japanese') {
                            showToast('Japanese Mode Selected',
                                'Players will start with 1000 points. Winner takes 7% pool each round.',
                                'success', 5000);
                            addJapaneseModeIndicator();
                        } else {
                            showToast('Western Mode Selected',
                                'Traditional scoring: Win=5, Draw=1, Loss=0',
                                'success');
                        }

                        // After both event mode and scoring mode are set, proceed to load participants
                        if (currentEventMode) {
                            await loadParticipants();
                        }
                    } else {
                        showToast('Error', data.message || 'Failed to set scoring mode', 'error');
                        selectedScoringModeTemp = null;
                    }
                } catch (error) {
                    console.error('Error setting scoring mode:', error);
                    showToast('Error', 'Network error setting scoring mode. Please try again.', 'error');
                    selectedScoringModeTemp = null;
                }
            }

            // Add Japanese mode indicator to the header
            function addJapaneseModeIndicator() {
                const header = document.querySelector('.header p');
                if (header && !document.getElementById('japanese-badge')) {
                    const badge = document.createElement('span');
                    badge.id = 'japanese-badge';
                    badge.className = 'japanese-mode-badge';
                    badge.innerHTML = '<i class="fas fa-yen-sign"></i> Japanese Mode';
                    badge.style.marginLeft = '10px';
                    header.appendChild(badge);
                }
            }

            // Remove Japanese mode indicator
            // Format score based on current mode
            function formatScore(score) {
                if (currentScoringMode === 'japanese') {
                    return score.toLocaleString() + ' pts';
                }
                return score + ' pts';
            }

            // Toast Notification System (Stacked)
            function showToast(title, message, type = 'success', duration = null) {
                // Get or create container
                let container = document.getElementById('toast-container');
                if (!container) {
                    container = document.createElement('div');
                    container.id = 'toast-container';
                    document.body.appendChild(container); // Add to body, not removed if exists
                }

                // Icon helper
                const icons = {
                    success: 'fas fa-check-circle',
                    error: 'fas fa-exclamation-circle',
                    warning: 'fas fa-exclamation-triangle',
                    info: 'fas fa-info-circle'
                };

                const iconClass = icons[type] || icons.info;
                const colorClass = type === 'success' ? 'var(--color-success)' :
                    type === 'error' ? 'var(--color-danger)' :
                        type === 'warning' ? 'var(--color-warning)' :
                            'var(--color-primary)';

                // Create toast element
                const toast = document.createElement('div');
                toast.className = `toast toast-${type}`;
                toast.innerHTML = `
                <i class="toast-icon ${iconClass}" style="color: ${colorClass}"></i>
                <div class="toast-content">
                    <div class="toast-title">${escapeHtml(title)}</div>
                    <div class="toast-message">${escapeHtml(message)}</div>
                </div>
            `;

                // Add to container
                container.appendChild(toast);

                // Trigger animation
                requestAnimationFrame(() => {
                    toast.classList.add('show');
                });

                // Auto hide duration
                if (duration === null) {
                    const baseTime = type === 'error' ? 6000 : 3000;
                    const messageLength = message.length;
                    duration = Math.max(baseTime, Math.min(messageLength * 50, 10000));
                }

                // Remove function
                const removeToast = () => {
                    toast.classList.remove('show');
                    toast.classList.add('hiding');

                    // Wait for transition end
                    setTimeout(() => {
                        if (toast.parentElement) {
                            toast.parentElement.removeChild(toast);
                        }
                        // Remove container if empty? Maybe not necessary
                    }, 400);
                };

                // Set timeout
                setTimeout(removeToast, duration);

                // Allow manual dismiss on click
                toast.onclick = removeToast;
            }

            // Enhanced error handler with user-friendly messages
            function handleApiError(response, defaultMessage = 'An error occurred') {
                let message = response.error || defaultMessage;

                // Use user_message if available (from Phase 2 validation)
                if (response.user_message) {
                    message = response.user_message;
                    if (response.suggestion) {
                        message += '\n\nSuggestion: ' + response.suggestion;
                    }
                }

                // Show error with longer duration
                showToast('Error', message, 'error', 8000);

                // Log technical details to console
                if (response.error) {
                    console.error('API Error:', response);
                }
            }



            // Show/Hide Control Sections
            function showActiveRoundControls() {
                const setupControls = document.getElementById('setup-controls');
                const activeControls = document.getElementById('active-round-controls');

                if (setupControls) {
                    setupControls.classList.add('hidden');
                }

                if (activeControls) {
                    activeControls.classList.add('visible');
                }

                console.log('Switched to active round controls');
            }

            function showSetupControls() {
                const setupControls = document.getElementById('setup-controls');
                const activeControls = document.getElementById('active-round-controls');

                if (setupControls) {
                    setupControls.classList.remove('hidden');
                }

                if (activeControls) {
                    activeControls.classList.remove('visible');
                }

                console.log('Switched to setup controls');
            }

            // Determine round type based on round number
            function getRoundType(roundNum) {
                const swissRounds = window.tournamentSwissRounds || 4;
                const roundSelect = document.getElementById('round-select');
                const selectedOption = roundSelect.options[roundSelect.selectedIndex];
                const roundText = selectedOption ? selectedOption.textContent : '';

                // Check if it's labeled as Top 8 Cut or Finals
                if (roundText.includes('Top 8 Cut')) {
                    return 'top8cut';
                } else if (roundText.includes('Semifinals')) {
                    // Legacy support
                    return 'top8cut';
                } else if (roundText.includes('Finals')) {
                    return 'finals';
                } else if (roundNum <= swissRounds) {
                    return 'swiss';
                }

                // Fallback logic
                if (roundNum > swissRounds) {
                    return 'finals';  // Assume finals if beyond Swiss rounds
                }
                return 'swiss';
            }

            // Update Round Selector Dropdown
            function updateRoundSelector(swissRounds, hasSemifinals = false, teamCount = null) {
                const roundSelect = document.getElementById('round-select');
                const currentValue = roundSelect.value;

                // Clear existing options
                roundSelect.innerHTML = '<option value="">Select Round</option>';

                // Add Swiss rounds
                for (let i = 1; i <= swissRounds; i++) {
                    const option = document.createElement('option');
                    option.value = i;
                    option.textContent = `Swiss Round ${i}`;
                    roundSelect.appendChild(option);
                }

                // Add Top Cut / Top 8 Cut if applicable
                const hasTopCut = hasSemifinals || (currentEventMode === 'individual' && window.hasIndividualTopCut);
                if (hasTopCut) {
                    const topCutOption = document.createElement('option');
                    topCutOption.value = swissRounds + 1;
                    topCutOption.textContent = currentEventMode === 'individual' ? 'Top Cut (Top 10)' : 'Top 8 Cut';
                    roundSelect.appendChild(topCutOption);

                    // Add Finals
                    const finalsOption = document.createElement('option');
                    finalsOption.value = swissRounds + 2;
                    finalsOption.textContent = 'Finals';
                    roundSelect.appendChild(finalsOption);
                } else {
                    // Finals directly after Swiss
                    const finalsOption = document.createElement('option');
                    finalsOption.value = swissRounds + 1;
                    finalsOption.textContent = 'Finals';
                    roundSelect.appendChild(finalsOption);
                }

                // Restore previous selection if valid
                const maxRounds = hasSemifinals ? swissRounds + 2 : swissRounds + 1;
                if (currentValue && parseInt(currentValue) <= maxRounds) {
                    roundSelect.value = currentValue;
                }

                console.log(`Round selector updated: ${swissRounds} Swiss rounds, Has Top 8 Cut: ${hasSemifinals}, Team count: ${teamCount}`);
            }

            // Load Participants
            async function loadParticipants() {
                // Wait for initial state if not yet loaded
                if (!currentEventMode && !initialStateLoaded) {
                    await new Promise(resolve => {
                        const check = setInterval(() => {
                            if (initialStateLoaded) { clearInterval(check); resolve(); }
                        }, 100);
                        setTimeout(() => { clearInterval(check); resolve(); }, 5000);
                    });
                }
                // If event mode still not set after state load, show modal
                if (!currentEventMode) {
                    showEventModeModal();
                    return;
                }

                try {
                    showToast('Loading...', 'Loading participant data', 'info');

                    const response = await fetch('/load_data', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({})
                    });
                    const data = await response.json();

                    console.log('Load data response:', data);

                    if (data.success && data.teams) {

                        // Restore event mode and scoring mode from server state
                        if (data.event_mode) {
                            currentEventMode = data.event_mode;
                            if (currentEventMode === 'individual') {
                                addIndividualModeIndicator();
                            }
                        }
                        if (data.scoring_mode) {
                            currentScoringMode = data.scoring_mode;
                            if (currentScoringMode === 'japanese') {
                                addJapaneseModeIndicator();
                            }
                        }
                        if (data.has_top_cut) {
                            window.hasIndividualTopCut = true;
                        }

                        // Store max rounds globally
                        if (data.max_rounds) {
                            window.tournamentMaxRounds = data.max_rounds;
                        }

                        // Update round selector with configured Swiss rounds and tournament structure
                        const hasSemifinals = data.has_semifinals || false;
                        const teamCount = data.team_count || Object.keys(data.teams).length;
                        updateRoundSelector(data.swiss_rounds || 4, hasSemifinals, teamCount);

                        displayTeams(data.teams, data.player_scores);
                        updateStats(data);

                        const structureMsg = hasSemifinals ?
                            `${teamCount} teams - ${data.swiss_rounds} Swiss rounds → Top 8 Cut → Finals` :
                            `${teamCount} teams - ${data.swiss_rounds} Swiss rounds → Finals`;
                        showToast('Success!', `Loaded ${data.team_count} teams (${data.player_count} players) | ${structureMsg}`, 'success');
                        document.getElementById('empty-state').style.display = 'none';
                    } else {
                        // Check if server is offering sample data as fallback
                        if (data.offer_sample) {
                            offerSampleData();
                        } else if (data.teams && Object.keys(data.teams).length > 0) {
                            // Teams already loaded from a previous session
                            const hasSemifinals = data.has_semifinals || false;
                            const teamCount = Object.keys(data.teams).length;
                            updateRoundSelector(data.swiss_rounds || 4, hasSemifinals, teamCount);

                            displayTeams(data.teams, data.player_scores);
                            updateStats(data);

                            const structureMsg = hasSemifinals ?
                                `${teamCount} teams - ${data.swiss_rounds} Swiss rounds → Top 8 Cut → Finals` :
                                `${teamCount} teams - ${data.swiss_rounds} Swiss rounds → Finals`;
                            showToast('Data Loaded', `Loaded ${teamCount} teams | ${structureMsg}`, 'success');
                            document.getElementById('empty-state').style.display = 'none';
                        } else {
                            handleApiError(data, 'Failed to load participants');
                        }
                    }
                } catch (error) {
                    showToast('Network Error',
                        'Could not connect to the server. Please check your connection and try again.\n\nError: ' + error.message,
                        'error', 8000);
                    console.error('Load participants error:', error);
                }
            }

            // Offer sample data when no participant file is found
            async function offerSampleData() {
                const confirmed = await modalManager.confirm(
                    'No Participant File Found',
                    'No participant Excel file was found.\n\nWould you like to load sample data for testing/demo purposes?\n\nThis is NOT for real tournaments.',
                    'Load Sample Data',
                    'Cancel'
                );
                if (!confirmed) return;

                try {
                    const response = await fetch('/load_data', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ use_sample_data: true, sample_team_count: 8 })
                    });
                    const data = await response.json();
                    if (data.success && data.teams) {
                        addDemoModeBanner();
                        if (data.event_mode) currentEventMode = data.event_mode;
                        if (data.scoring_mode) currentScoringMode = data.scoring_mode;
                        const hasSemifinals = data.has_semifinals || false;
                        const teamCount = Object.keys(data.teams).length;
                        updateRoundSelector(data.swiss_rounds || 4, hasSemifinals, teamCount);
                        displayTeams(data.teams, data.player_scores);
                        updateStats(data);
                        showToast('Sample Data Loaded', `Loaded ${teamCount} sample teams for demo/testing`, 'warning', 5000);
                        document.getElementById('empty-state').style.display = 'none';
                    } else {
                        showToast('Error', data.error || 'Failed to load sample data', 'error');
                    }
                } catch (error) {
                    showToast('Error', 'Network error loading sample data', 'error');
                }
            }

            function addDemoModeBanner() {
                if (document.getElementById('demo-mode-banner')) return;
                const banner = document.createElement('div');
                banner.id = 'demo-mode-banner';
                banner.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; z-index: 9999; background: linear-gradient(90deg, #dc2626, #b91c1c); color: white; text-align: center; padding: 8px 16px; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px;';
                banner.textContent = 'DEMO MODE — Sample data loaded. Not a real tournament.';
                document.body.prepend(banner);
                document.body.style.paddingTop = '36px';
            }

            // Display Teams
            function displayTeams(teams, playerScores = null, finalsTeamsOnly = false) {
                const teamsGrid = document.getElementById('teams-grid');
                const teamsContainer = document.getElementById('teams-container');

                teamsGrid.innerHTML = '';

                // FORCE 1 column layout
                const isLandscape = window.innerWidth >= 1024;
                if (isLandscape) {
                    // Create style element with !important
                    let forceStyle = document.getElementById('force-teams-grid-style');
                    if (!forceStyle) {
                        forceStyle = document.createElement('style');
                        forceStyle.id = 'force-teams-grid-style';
                        document.head.appendChild(forceStyle);
                    }
                    forceStyle.textContent = `
                    #teams-grid.teams-grid {
                        display: grid !important;
                        grid-template-columns: 1fr !important;
                        gap: 12px !important;
                    }
                `;

                    // Also set inline style
                    teamsGrid.style.display = 'grid';
                    teamsGrid.style.gridTemplateColumns = '1fr';
                    teamsGrid.style.gap = '12px';
                    console.log('✅ FORCE Set teams-grid to 1 column, width:', window.innerWidth);
                }

                // Get list of teams in finals if applicable
                let finalsTeams = null;
                if (finalsTeamsOnly && window.finalsAdvancingTeams) {
                    finalsTeams = new Set(window.finalsAdvancingTeams.map(t => t.trim()));
                    console.log('=== DISPLAY TEAMS - FINALS MODE ===');
                    console.log('Finals teams set:', Array.from(finalsTeams));
                    console.log('All available teams:', Object.keys(teams));
                } else {
                    console.log('=== DISPLAY TEAMS - ALL TEAMS MODE ===');
                }

                // Calculate team scores and create array for sorting
                const teamsArray = [];
                let hiddenCount = 0;
                Object.entries(teams).forEach(([teamName, players]) => {
                    // Skip eliminated teams if in finals mode
                    if (finalsTeams) {
                        const teamNameTrimmed = teamName.trim();
                        if (!finalsTeams.has(teamNameTrimmed)) {
                            hiddenCount++;
                            return;
                        }
                    }

                    // Calculate team score from player scores
                    let teamScore = 0;
                    players.forEach(player => {
                        const playerId = player['Player ID'] || player.id;
                        if (playerScores) {
                            // Try both integer and string keys (JSON converts to string)
                            const score = playerScores[playerId] || playerScores[String(playerId)] || 0;
                            teamScore += score;
                        } else {
                            teamScore += (player.score || 0);
                        }
                    });

                    teamsArray.push({
                        teamName: teamName,
                        players: players,
                        teamScore: teamScore
                    });
                });

                // Sort teams by score (highest to lowest)
                teamsArray.sort((a, b) => {
                    // Primary sort: by score (descending)
                    if (b.teamScore !== a.teamScore) {
                        return b.teamScore - a.teamScore;
                    }
                    // Secondary sort: by team name (alphabetical) if scores are equal
                    return a.teamName.localeCompare(b.teamName);
                });

                let displayedCount = 0;

                // Display teams/players in sorted order
                if (currentEventMode === 'individual') {
                    // Individual mode: flat ranked list of players
                    teamsArray.forEach(({ teamName, players, teamScore }, index) => {
                        if (!players || players.length === 0) return;
                        const player = players[0];
                        if (!player) return;

                        displayedCount++;
                        const playerId = player['Player ID'] || player.id;
                        let playerScore = 0;
                        if (playerScores) {
                            playerScore = playerScores[playerId] || playerScores[String(playerId)] || 0;
                        }
                        const card = document.createElement('div');
                        card.className = 'team-card';
                        card.innerHTML = `
                        <div class="team-header">
                            <div class="team-name">#${index + 1} ${escapeHtml(player['Player Name'] || player.name)}</div>
                            <div class="team-score">${formatScore(playerScore)}</div>
                        </div>
                        `;
                        teamsGrid.appendChild(card);
                    });
                } else {
                    // Team mode: original team cards with nested players
                    teamsArray.forEach(({ teamName, players, teamScore }) => {
                        displayedCount++;
                        const card = document.createElement('div');
                        card.className = 'team-card';

                        card.innerHTML = `
                        <div class="team-header">
                            <div class="team-name">${escapeHtml(teamName)}</div>
                            <div class="team-score">${teamScore} pts</div>
                        </div>
                        <div class="player-list">
                            ${players.map(player => {
                            const playerId = player['Player ID'] || player.id;
                            let playerScore = 0;
                            if (playerScores) {
                                playerScore = playerScores[playerId] || playerScores[String(playerId)] || 0;
                            } else {
                                playerScore = player.score || 0;
                            }
                            return `
                                    <div class="player-item">
                                        <div class="player-id">${playerId}</div>
                                        <div class="player-name">${escapeHtml(player['Player Name'] || player.name)}</div>
                                        <div class="player-score">${playerScore} pts</div>
                                    </div>
                                `;
                        }).join('')}
                        </div>
                    `;

                        teamsGrid.appendChild(card);
                    });
                }

                // Display dropped players (individual mode only)
                if (currentEventMode === 'individual' && window._droppedPlayersCache && Object.keys(window._droppedPlayersCache).length > 0) {
                    const droppedEntries = Object.entries(window._droppedPlayersCache)
                        .map(([pid, info]) => ({ id: pid, ...info }))
                        .sort((a, b) => b.score - a.score);

                    droppedEntries.forEach(dp => {
                        const card = document.createElement('div');
                        card.className = 'team-card';
                        card.style.opacity = '0.5';
                        card.style.borderLeft = '3px solid var(--color-danger)';
                        card.innerHTML = `
                        <div class="team-header">
                            <div class="team-name" style="text-decoration: line-through;">${escapeHtml(dp.name)}</div>
                            <div class="team-score">
                                ${formatScore(dp.score)}
                                <span style="font-size: 0.65rem; background: var(--color-danger); color: white; padding: 2px 6px; border-radius: 8px; margin-left: 8px;">DROPPED R${dp.dropped_after_round}</span>
                            </div>
                        </div>
                        `;
                        teamsGrid.appendChild(card);
                    });
                }

                // Force 1 column FINALLY after all cards are added
                if (isLandscape) {
                    teamsGrid.style.display = 'grid';
                    teamsGrid.style.gridTemplateColumns = '1fr';
                    teamsGrid.style.gap = '12px';
                    console.log(`✅ FINAL: Applied 1-column layout to teams-grid (sorted by score), ${displayedCount} teams rendered`);
                }

                console.log(`=== DISPLAY TEAMS COMPLETE ===`);
                console.log(`Displayed: ${displayedCount} teams (sorted by score: highest to lowest)`);
                if (finalsTeamsOnly) {
                    console.log(`Hidden: ${hiddenCount} eliminated teams`);
                }
                console.log(`Finals mode: ${finalsTeamsOnly}`);

                teamsContainer.style.display = 'block';
            }

            // Setup Tournament
            async function setupTournament() {
                try {
                    showToast('Generating...', 'Setting up tournament and generating Swiss rounds', 'info');

                    const response = await fetch('/setup_tournament', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    const data = await response.json();

                    console.log('Setup tournament response:', data);

                    if (data.success) {
                        showToast('Tournament Ready!', data.message, 'success');

                        // Update round selector with configured Swiss rounds and tournament structure
                        const hasSemifinals = data.has_semifinals || false;
                        const teamCount = data.tournament_teams ? data.tournament_teams.length : 0;
                        const swissRounds = data.swiss_rounds_count || 4;

                        // Store tournament configuration globally
                        window.tournamentSwissRounds = swissRounds;
                        window.swissRoundsCount = swissRounds;
                        window.hasSemifinals = hasSemifinals;
                        window.totalTeams = teamCount;

                        // Store max rounds globally
                        if (data.max_rounds) {
                            window.tournamentMaxRounds = data.max_rounds;
                        }

                        updateRoundSelector(swissRounds, hasSemifinals, teamCount);

                        // Update stats
                        document.getElementById('stat-teams').textContent = teamCount;
                        document.getElementById('stat-round').textContent = '1';
                        document.getElementById('stat-status').textContent = 'Active';

                        // Switch from setup controls to active round controls
                        showActiveRoundControls();

                        // Load Round 1 automatically
                        document.getElementById('round-select').value = '1';
                        loadRound();
                    } else {
                        showToast('Setup Failed', data.message, 'error');
                    }
                } catch (error) {
                    showToast('Error', 'Failed to setup tournament: ' + error.message, 'error');
                    console.error('Setup error:', error);
                }
            }

            // Manual Backup
            async function manualBackup() {
                try {
                    showToast('Saving...', 'Creating manual backup...', 'info');

                    const response = await fetch('/save_backup', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Success', 'Backup saved successfully!', 'success');
                    } else {
                        showToast('Backup Failed', data.message, 'error');
                    }
                } catch (error) {
                    showToast('Error', 'Failed to save backup: ' + error.message, 'error');
                    console.error('Manual backup error:', error);
                }
            }

            // Reset Tournament
            async function resetTournament() {
                const confirmed = await modalManager.confirm(
                    'Reset Tournament',
                    'This will DELETE ALL tournament data including scores, pairings, and results.\n\nBackup files will be preserved and can be restored.\n\nThis action cannot be undone.',
                    'Continue',
                    'Cancel'
                );
                if (!confirmed) return;

                const typed = await modalManager.prompt(
                    'Confirm Reset',
                    'Type RESET to confirm complete tournament reset:',
                    '',
                    'RESET'
                );
                if (!typed || typed.toUpperCase() !== 'RESET') {
                    showToast('Cancelled', 'Tournament reset cancelled.', 'info');
                    return;
                }

                try {
                    const response = await fetch('/reset_tournament', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ confirm: 'RESET' })
                    });
                    const data = await response.json();
                    if (data.success) {
                        showToast('Tournament Reset', 'All data cleared. Reloading...', 'success');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showToast('Error', data.error || 'Reset failed', 'error');
                    }
                } catch (error) {
                    showToast('Error', 'Network error during reset', 'error');
                }
            }

            // Restore Backup
            async function restoreBackup() {
                const confirmed = await modalManager.confirm(
                    'Restore Backup',
                    'Are you sure? This will overwrite the current tournament state.',
                    'Restore',
                    'Cancel'
                );
                if (!confirmed) return;

                try {
                    showToast('Restoring...', 'Restoring tournament from backup...', 'info');

                    const response = await fetch('/restore_backup', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Success', data.message, 'success');

                        // Fetch restored state to set event/scoring mode BEFORE loadParticipants
                        try {
                            const stateRes = await fetch('/get_state_info');
                            const stateData = await stateRes.json();
                            if (stateData.event_mode) {
                                currentEventMode = stateData.event_mode;
                                if (currentEventMode === 'individual') addIndividualModeIndicator();
                            }
                            if (stateData.scoring_mode) {
                                currentScoringMode = stateData.scoring_mode;
                                if (currentScoringMode === 'japanese') addJapaneseModeIndicator();
                            }
                            initialStateLoaded = true;
                        } catch (e) { /* best effort */ }

                        await loadParticipants();

                        // Check if tournament is active and switch controls
                        if (data.current_round) {
                            showActiveRoundControls();
                            document.getElementById('round-select').value = data.current_round;
                            loadRound();
                        }
                    } else {
                        showToast('Restore Failed', data.message, 'error');
                    }
                } catch (error) {
                    showToast('Error', 'Failed to restore backup: ' + error.message, 'error');
                    console.error('Restore error:', error);
                }
            }

            // Load Round Tables
            // Compact Mode Auto-Suggestion for Large Tournaments
            function suggestCompactModeIfNeeded() {
                // Check if suggestion already shown
                if (localStorage.getItem('compactModeSuggestionShown') === 'true') {
                    return;
                }

                // Count number of tables
                const tableCount = document.querySelectorAll('.table-card').length;

                // Suggest for 8+ tables (16 teams = 8 tables per round)
                if (tableCount >= 8) {
                    setTimeout(() => {
                        showToast(
                            'Tip: Compact Mode',
                            `You have ${tableCount} tables. Try the Compact button in the controls bar for easier viewing!`,
                            'info',
                            8000 // 8 second duration
                        );
                        localStorage.setItem('compactModeSuggestionShown', 'true');
                    }, 2000); // Show after 2 seconds (let user orient first)
                }
            }

            let _loadRoundId = 0;
            async function loadRound() {
                const roundSelect = document.getElementById('round-select');
                const round = roundSelect.value;

                if (!round) return;

                // Guard against rapid calls: only the latest call proceeds
                const thisLoadId = ++_loadRoundId;

                // Clear stale scores from previous round
                Object.keys(tableScores).forEach(key => delete tableScores[key]);
                window.currentRoundScores = {};

                try {
                    const response = await fetch(`/get_tables/${round}`);
                    if (thisLoadId !== _loadRoundId) return;
                    const data = await response.json();

                    console.log('Load round response:', data);

                    if (data.success && data.tables) {
                        window.currentTables = data.tables;
                        window.playerScores = data.player_scores || {};

                        displayTables(data.tables, round);

                        // Update section title with round context
                        const label = document.getElementById('tables-section-label');
                        if (label) {
                            const swissCount = window.swissRoundsCount || 4;
                            const roundInt = parseInt(round);
                            if (roundInt <= swissCount) {
                                label.textContent = `Swiss Round ${roundInt} — Tables`;
                            } else if (roundInt === swissCount + 1 && window.hasSemifinals) {
                                label.textContent = 'Top Cut — Tables';
                            } else {
                                label.textContent = 'Finals — Tables';
                            }
                        }

                        // Restore submitted-table visual state from server
                        try {
                            const statusRes = await fetch(`/get_submission_status/${round}`);
                            if (thisLoadId !== _loadRoundId) return;
                            const statusData = await statusRes.json();
                            if (statusData.success && statusData.submitted_tables) {
                                statusData.submitted_tables.forEach(tableName => {
                                    const cardId = `table-${tableName.replace(/\s+/g, '-')}`;
                                    const card = document.getElementById(cardId);
                                    if (card) {
                                        card.classList.add('submitted');
                                        const submitBtn = card.querySelector('.submit-table-btn');
                                        if (submitBtn) submitBtn.classList.add('submitted');
                                        card.querySelectorAll('.score-btn').forEach(btn => { btn.disabled = true; btn.style.opacity = '0.6'; });
                                    }
                                });
                            }
                        } catch (e) { }

                        suggestCompactModeIfNeeded();

                        // Determine round type
                        const roundType = getRoundType(parseInt(round));
                        let roundLabel = round;
                        if (roundType === 'top8cut') {
                            roundLabel = 'Top 8 Cut';
                        } else if (roundType === 'finals') {
                            roundLabel = 'Finals';
                        }

                        showToast('Round Loaded', `Loaded ${Object.keys(data.tables).length} tables for ${roundLabel}`, 'success');

                        // Update current round stat
                        document.getElementById('stat-round').textContent = roundLabel;

                        // If finals, show only advancing teams (top 4)
                        if (roundType === 'finals') {
                            // Get advancing teams from tables
                            const finalsTeams = new Set();
                            Object.values(data.tables).forEach(players => {
                                players.forEach(p => {
                                    const teamName = (p['Team Name'] || p.team || p['Team'] || '').trim();
                                    if (teamName) {
                                        finalsTeams.add(teamName);
                                    }
                                });
                            });

                            window.finalsAdvancingTeams = Array.from(finalsTeams);

                            console.log('=== FINALS MODE ACTIVATED ===');
                            console.log('Finals teams extracted from tables:', window.finalsAdvancingTeams);
                            console.log('Total teams in finals:', window.finalsAdvancingTeams.length);
                            console.log('Team names (normalized):', window.finalsAdvancingTeams.map(t => `"${t}"`));

                            // Refresh team display (will filter to finals teams only)
                            refreshTeamScores(true);  // Pass true for finals mode
                        } else {
                            window.finalsAdvancingTeams = null;
                            console.log(`${roundLabel} - showing all teams`);
                            refreshTeamScores(false);  // Explicitly show all teams
                        }
                    } else {
                        showToast('Error', 'No tables found for this round', 'warning');
                    }
                } catch (error) {
                    showToast('Error', 'Failed to load round tables: ' + error.message, 'error');
                    console.error(error);
                }

                if (thisLoadId !== _loadRoundId) return;

                // Update progression tracker
                updateProgressionTracker(parseInt(round));

                // Update bracket visualization
                updateBracketVisualization(parseInt(round));

                // Update submission progress (Phase 3.1)
                await updateSubmissionProgress(parseInt(round));
            }

            // Update Tournament Progression Tracker
            function updateProgressionTracker(currentRound) {
                const tracker = document.getElementById('progression-tracker');
                const stepsContainer = document.getElementById('progression-steps');

                if (!tracker || !stepsContainer) return;

                // Get tournament configuration
                const swissRounds = window.tournamentSwissRounds || 4;
                const totalTeams = window.totalTeams || 0;
                const hasSemifinals = window.hasSemifinals || totalTeams === 16;

                // Define tournament phases
                const phases = [];

                // Swiss rounds phase
                phases.push({
                    id: 'swiss',
                    icon: 'fas fa-chess-board',
                    label: `Swiss Rounds (${swissRounds})`,
                    rounds: Array.from({ length: swissRounds }, (_, i) => i + 1),
                    completed: currentRound > swissRounds,
                    active: currentRound >= 1 && currentRound <= swissRounds
                });

                // Semifinals phase (only for 16 teams)
                if (hasSemifinals) {
                    const semifinalRound = swissRounds + 1;
                    phases.push({
                        id: 'semifinals',
                        icon: 'fas fa-trophy',
                        label: 'Semifinals (Top 8)',
                        rounds: [semifinalRound],
                        completed: currentRound > semifinalRound,
                        active: currentRound === semifinalRound
                    });
                }

                // Finals phase
                const finalsRound = hasSemifinals ? swissRounds + 2 : swissRounds + 1;
                phases.push({
                    id: 'finals',
                    icon: 'fas fa-crown',
                    label: 'Finals (Top 4)',
                    rounds: [finalsRound],
                    completed: false,
                    active: currentRound === finalsRound
                });

                // Build HTML
                let html = '';
                phases.forEach((phase, index) => {
                    const stateClass = phase.completed ? 'completed' : (phase.active ? 'active' : '');
                    html += `
                    <div class="progression-step ${stateClass}">
                        <div class="progression-circle">
                            <i class="${phase.icon}"></i>
                        </div>
                        <div class="progression-label">${phase.label}</div>
                    </div>
                `;

                    // Add arrow between phases (except after last phase)
                    if (index < phases.length - 1) {
                        html += `<i class="fas fa-arrow-right progression-arrow"></i>`;
                    }
                });

                stepsContainer.innerHTML = html;

                // Ensure display is flex for the compact layout
                if (tracker.classList.contains('compact')) {
                    tracker.style.display = 'flex';
                } else {
                    tracker.style.display = 'block';
                }
            }

            // Update Tournament Bracket Visualization
            async function updateBracketVisualization(currentRound) {
                const bracketContainer = document.getElementById('bracket-container');
                const bracketGrid = document.getElementById('bracket-grid');
                const bracketTitleText = document.getElementById('bracket-title-text');

                if (!bracketContainer || !bracketGrid || !bracketTitleText) return;

                // Get tournament configuration
                const swissRounds = window.tournamentSwissRounds || 4;
                const totalTeams = window.totalTeams || 0;
                const hasSemifinals = window.hasSemifinals || totalTeams === 16;

                const roundType = getRoundType(currentRound);

                // Only show bracket for top8cut and finals
                if (roundType !== 'top8cut' && roundType !== 'finals') {
                    bracketContainer.style.display = 'none';
                    return;
                }

                try {
                    // Fetch bracket standings with current round scores only
                    const standingsResponse = await fetch(`/bracket_standings/${currentRound}`);
                    const standingsData = await standingsResponse.json();

                    if (!standingsData.standings) {
                        bracketContainer.style.display = 'none';
                        return;
                    }

                    const standings = standingsData.standings;
                    console.log(`Bracket standings for round ${currentRound} (${standingsData.score_type}):`, standings);

                    if (roundType === 'top8cut') {
                        // Show top 8 teams in semifinals bracket - 2 pods of 4 teams
                        bracketTitleText.textContent = 'Semifinals Bracket - Top 8 Teams (Current Round Scores)';
                        bracketGrid.className = 'bracket-grid semifinals';

                        // Fetch actual pod groupings from table assignments
                        const groupsResponse = await fetch(`/bracket_groups/${currentRound}`);
                        const groupsData = await groupsResponse.json();

                        if (groupsData.success) {
                            // Map team names to their standing data
                            const pod1Teams = groupsData.pod1.map(teamName =>
                                standings.find(s => s.team === teamName)
                            ).filter(t => t); // Remove nulls

                            const pod2Teams = groupsData.pod2.map(teamName =>
                                standings.find(s => s.team === teamName)
                            ).filter(t => t);

                            const pods = [
                                { teams: pod1Teams, label: 'Matchup 1' },
                                { teams: pod2Teams, label: 'Matchup 2' }
                            ];

                            let html = '';
                            pods.forEach((pod, index) => {
                                html += generatePodMatchupHTML(pod, index + 1);
                            });

                            bracketGrid.innerHTML = html;
                            bracketContainer.style.display = 'block';
                        } else {
                            // Fallback to showing all top 8 with ranks
                            const top8 = standings.slice(0, 8);
                            const pods = [
                                { teams: [top8[0], top8[2], top8[4], top8[6]], label: 'Matchup 1' },
                                { teams: [top8[1], top8[3], top8[5], top8[7]], label: 'Matchup 2' }
                            ];

                            let html = '';
                            pods.forEach((pod, index) => {
                                html += generatePodMatchupHTML(pod, index + 1);
                            });

                            bracketGrid.innerHTML = html;
                            bracketContainer.style.display = 'block';
                        }

                    } else if (roundType === 'finals') {
                        // Show top 4 teams in finals bracket - single pod of 4 teams
                        bracketTitleText.textContent = 'Finals Bracket - Top 4 Teams (Current Round Scores)';
                        bracketGrid.className = 'bracket-grid finals';

                        const top4 = standings.slice(0, 4);

                        // Create single pod with all 4 teams
                        const pods = [
                            { teams: top4, label: 'Finals' }
                        ];

                        let html = '';
                        pods.forEach((pod, index) => {
                            html += generatePodMatchupHTML(pod, index + 1);
                        });

                        bracketGrid.innerHTML = html;
                        bracketContainer.style.display = 'block';
                    }

                } catch (error) {
                    console.error('Error updating bracket visualization:', error);
                    bracketContainer.style.display = 'none';
                }
            }

            // Generate HTML for a pod matchup (4-player format)
            function generatePodMatchupHTML(pod, podNumber) {
                if (!pod.teams || pod.teams.length === 0) return '';

                const teamsHTML = pod.teams.map(team => {
                    if (!team) return '';
                    return `
                    <div class="pod-team">
                        <div class="team-info">
                            <div class="team-seed">${team.rank || '?'}</div>
                            <div class="team-name">${escapeHtml(team.team || 'Unknown')}</div>
                        </div>
                        <div class="team-score">${team.total_points || 0} pts</div>
                    </div>
                `;
                }).join('');

                return `
                <div class="bracket-matchup pod-matchup">
                    <div class="matchup-header">
                        ${pod.label}
                        <span class="pod-info-icon" title="Teams are distributed using alternating pairing (1,3,5,7 vs 2,4,6,8) to create balanced competitive groups. This ensures both pods have similar skill distributions rather than clustering all top seeds together.">
                            <i class="fas fa-info-circle"></i>
                        </span>
                    </div>
                    <div class="pod-teams">
                        ${teamsHTML}
                    </div>
                </div>
            `;
            }

            // Submission Progress Tracking (Phase 3.1)
            async function updateSubmissionProgress(roundNum) {
                try {
                    const response = await fetch(`/get_submission_status/${roundNum}`);
                    const data = await response.json();

                    if (data.success) {
                        // Update or create progress bar
                        let progressContainer = document.getElementById(`submission-progress-${roundNum}`);

                        if (!progressContainer) {
                            // Create progress bar if it doesn't exist
                            const tablesContainer = document.getElementById('tables-container');
                            if (tablesContainer) {
                                progressContainer = document.createElement('div');
                                progressContainer.id = `submission-progress-${roundNum}`;
                                progressContainer.className = 'submission-progress-container';
                                progressContainer.innerHTML = `
                                <div class="progress-header">
                                    <span class="progress-label">Round ${roundNum} Progress</span>
                                    <span class="progress-stats">
                                        <span id="submitted-count-${roundNum}">${data.submitted_count}</span> /
                                        <span id="total-count-${roundNum}">${data.total_tables}</span> tables submitted
                                    </span>
                                </div>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" id="progress-bar-${roundNum}" style="width: ${data.progress_percent}%">
                                        <span class="progress-percent">${Math.round(data.progress_percent)}%</span>
                                    </div>
                                </div>
                            `;
                                tablesContainer.insertBefore(progressContainer, tablesContainer.firstChild);
                            }
                        } else {
                            // Update existing progress bar
                            document.getElementById(`submitted-count-${roundNum}`).textContent = data.submitted_count;
                            document.getElementById(`total-count-${roundNum}`).textContent = data.total_tables;
                            document.getElementById(`progress-bar-${roundNum}`).style.width = `${data.progress_percent}%`;
                            document.getElementById(`progress-bar-${roundNum}`).querySelector('.progress-percent').textContent = `${Math.round(data.progress_percent)}%`;
                        }

                        // Mark submitted tables visually
                        data.submitted_tables.forEach(tableName => {
                            markTableAsSubmitted(tableName, roundNum);
                        });

                        console.log(`Submission progress: ${data.submitted_count}/${data.total_tables} (${data.progress_percent}%)`);

                        // Sync can_finalize from server
                        if (data.can_finalize !== undefined) {
                            window.canFinalize = data.can_finalize;
                            updateFinalizeButtonState();
                        }

                        // Update remaining tables widget
                        updateRemainingTablesWidget(data);

                        // Show drop player button when all tables submitted (individual mode only)
                        if (data.is_complete && currentEventMode === 'individual') {
                            showDropPlayersButton();
                        } else {
                            hideDropPlayersButton();
                        }
                    } else {
                        console.warn('Failed to get submission status:', data.error);
                    }
                } catch (error) {
                    console.error('Error updating submission progress:', error);
                }
            }

            // Remaining Tables Widget - shows which tables still need submission
            function updateRemainingTablesWidget(submissionStatus) {
                const tablesContainer = document.getElementById('tables-container');
                if (!tablesContainer) return;

                let widget = document.getElementById('remaining-tables-widget');

                // If round is already finalized, hide the widget
                if (submissionStatus.is_finalized) {
                    if (widget) widget.style.display = 'none';
                    return;
                }

                if (!widget) {
                    widget = document.createElement('div');
                    widget.id = 'remaining-tables-widget';
                    widget.style.cssText = 'padding: 10px 16px; border-radius: 8px; margin-bottom: 12px; font-size: 0.85rem; font-weight: 500;';
                    const tablesGrid = document.getElementById('tables-grid');
                    if (tablesGrid) {
                        tablesContainer.insertBefore(widget, tablesGrid);
                    } else {
                        tablesContainer.insertBefore(widget, tablesContainer.firstChild);
                    }
                }

                widget.style.display = 'block';

                if (submissionStatus.is_complete) {
                    widget.style.background = 'var(--color-success-light)';
                    widget.style.border = '1px solid var(--color-success)';
                    widget.style.color = 'var(--color-success)';
                    widget.innerHTML = '<i class="fas fa-check-circle"></i> All tables submitted! Ready to finalize.';
                } else {
                    const submitted = submissionStatus.submitted_count || 0;
                    const total = submissionStatus.total_tables || 0;
                    const remaining = submissionStatus.remaining_tables || [];
                    const remainingText = remaining.length > 0 ? remaining.map(t => escapeHtml(t)).join(', ') : '';

                    widget.style.background = 'var(--color-primary-light)';
                    widget.style.border = '1px solid var(--color-primary)';
                    widget.style.color = 'var(--color-text)';
                    widget.innerHTML = `<i class="fas fa-clipboard-list"></i> ${submitted}/${total} tables submitted` +
                        (remainingText ? ` &bull; Remaining: ${remainingText}` : '');
                }
            }

            function markTableAsSubmitted(tableName, roundNum) {
                const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
                if (!tableCard) return;

                // Add submitted class to table card for visual deemphasis
                tableCard.classList.add('submitted');

                // Add submitted badge to header
                const header = tableCard.querySelector('.table-header');
                if (header && !header.querySelector('.submitted-badge')) {
                    const badge = document.createElement('span');
                    badge.className = 'submitted-badge';
                    badge.innerHTML = '<i class="fas fa-check-circle"></i> SUBMITTED';
                    badge.style.marginLeft = '10px';
                    header.appendChild(badge);
                }

                // Disable all score buttons
                const scoreButtons = tableCard.querySelectorAll('.score-btn');
                scoreButtons.forEach(btn => {
                    btn.disabled = true;
                    btn.style.opacity = '0.5';
                    btn.style.cursor = 'not-allowed';
                });

                // Update submit button
                const submitBtn = tableCard.querySelector('.submit-table-btn');
                if (submitBtn && !submitBtn.classList.contains('submitted')) {
                    submitBtn.classList.add('submitted');
                    submitBtn.innerHTML = '<i class="fas fa-check-double"></i> Submitted';
                    submitBtn.disabled = true;
                }

                // Add edit button to submitted table (Task 3.2)
                addEditButton(tableCard, tableName, roundNum);
            }

            // ============================================
            // SCORE EDITING FUNCTIONS (Task 3.2)
            // ============================================

            // Add edit button to all submitted tables in a round
            // Add edit button to a specific table card
            function addEditButton(tableCard, tableName, roundNum) {
                // Check if edit button already exists
                if (tableCard.querySelector('.edit-scores-btn')) {
                    return;
                }

                const submitBtn = tableCard.querySelector('.submit-table-btn');
                if (!submitBtn) return;

                const editBtn = document.createElement('button');
                editBtn.className = 'edit-scores-btn';
                editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
                editBtn.onclick = (e) => {
                    e.stopPropagation();
                    enableScoreEditing(tableName, roundNum);
                };

                const revertBtn = document.createElement('button');
                revertBtn.className = 'edit-scores-btn';
                revertBtn.style.background = 'var(--color-danger-light)';
                revertBtn.style.borderColor = 'var(--color-danger)';
                revertBtn.innerHTML = '<i class="fas fa-undo"></i> Revert';
                revertBtn.onclick = async (e) => {
                    e.stopPropagation();
                    const confirmed = await modalManager.confirm(
                        'Revert Submission',
                        `This will completely undo the submission for ${escapeHtml(tableName)}, restoring all player scores to their pre-submission values.\n\nThis cannot be undone.`,
                        'Revert',
                        'Cancel'
                    );
                    if (!confirmed) return;
                    try {
                        const resp = await fetch('/revert_table_submission', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({round: roundNum, table: tableName})
                        });
                        const data = await resp.json();
                        if (data.success) {
                            showToast('Reverted', `${tableName} submission undone.`, 'success');
                            loadRound();
                        } else {
                            showToast('Error', data.error || 'Revert failed', 'error');
                        }
                    } catch (err) {
                        showToast('Error', 'Network error during revert', 'error');
                    }
                };

                submitBtn.parentElement.appendChild(editBtn);
                submitBtn.parentElement.appendChild(revertBtn);

                // Check for edit history and add badge
                checkAndShowEditHistory(tableName, roundNum, tableCard);
            }

            // Check if table has edit history and show badge
            async function checkAndShowEditHistory(tableName, roundNum, tableCard) {
                try {
                    const response = await fetch(`/get_score_history/${roundNum}/${encodeURIComponent(tableName)}`);
                    const data = await response.json();

                    if (data.success && data.edit_count > 0) {
                        const header = tableCard.querySelector('.table-header');
                        if (header && !header.querySelector('.edit-history-badge')) {
                            const badge = document.createElement('span');
                            badge.className = 'edit-history-badge';
                            badge.innerHTML = `<i class="fas fa-history"></i> ${data.edit_count} edit(s)`;
                            badge.onclick = (e) => {
                                e.stopPropagation();
                                viewScoreHistory(tableName, roundNum);
                            };
                            header.appendChild(badge);
                        }
                    }
                } catch (error) {
                    console.error('Failed to check edit history:', error);
                }
            }

            // Enable score editing mode for a table
            async function enableScoreEditing(tableName, roundNum) {
                const confirmMsg = `You are about to edit scores for ${tableName}.\n\n` +
                    `• The previous scores will be saved in the audit trail\n` +
                    `• Team standings will be recalculated\n` +
                    `• This action can be repeated if needed\n\n` +
                    `Do you want to continue?`;

                // UX Improvement: Use Custom Modal
                const confirmed = await modalManager.confirm('Edit Scores', confirmMsg, 'Continue Editing', 'Cancel');

                if (!confirmed) {
                    return;
                }

                const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
                if (!tableCard) {
                    showToast('Error', 'Table not found', 'error');
                    return;
                }

                // Add editing visual indicator
                tableCard.classList.add('editing');

                // Re-enable score buttons and clear visual selection state
                const scoreButtons = tableCard.querySelectorAll('.score-btn');
                scoreButtons.forEach(btn => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                    btn.style.cursor = 'pointer';
                    btn.classList.remove('active', 'selected');
                });

                // Change submit button to "Update Scores"
                const submitBtn = tableCard.querySelector('.submit-table-btn');
                submitBtn.disabled = false;
                submitBtn.classList.remove('submitted');
                submitBtn.innerHTML = '<i class="fas fa-save"></i> Update Scores';
                submitBtn.onclick = () => updateTableScores(tableName, roundNum);

                // Hide edit button during editing
                const editBtn = tableCard.querySelector('.edit-scores-btn');
                if (editBtn) editBtn.style.display = 'none';

                // Add cancel button
                const cancelBtn = document.createElement('button');
                cancelBtn.className = 'cancel-edit-btn';
                cancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
                cancelBtn.onclick = () => cancelScoreEditing(tableName, roundNum);
                submitBtn.parentElement.appendChild(cancelBtn);

                // Clear any previous score selections for this table
                if (tableScores[tableName]) {
                    delete tableScores[tableName];
                }

                showToast('Edit Mode', `You can now edit scores for ${tableName}. Select new scores and click Update.`, 'info');
            }

            // Submit edited scores to backend
            async function updateTableScores(tableName, roundNum) {
                const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
                const playerElements = tableCard.querySelectorAll('.table-player');

                // Validate all players have scores
                if (!tableScores[tableName] || Object.keys(tableScores[tableName]).length !== playerElements.length) {
                    showToast('Incomplete', 'Please select scores for all players before updating.', 'warning');
                    return;
                }

                // Build results array
                const results = [];
                for (const playerId in tableScores[tableName]) {
                    results.push({
                        player_id: parseInt(playerId),
                        points: tableScores[tableName][playerId]
                    });
                }

                // Ask for edit reason
                // UX Improvement: Use Custom Modal
                const reason = await modalManager.prompt(
                    'Reason for Edit',
                    'Please provide a brief reason for this change:',
                    '', // Default
                    'e.g. Data entry error' // Placeholder
                );

                // If user cancels prompt (returns false/null), abort update
                if (reason === false || reason === null) {
                    return;
                }

                const updateBtn = tableCard.querySelector('.submit-table-btn');
                updateBtn.disabled = true;
                updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

                try {
                    const response = await fetch('/edit_table_results', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            round: roundNum,
                            table: tableName,
                            results: results,
                            reason: reason || 'Score correction'
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Scores Updated!', `${tableName} scores have been updated successfully.`, 'success');

                        // Remove editing state
                        tableCard.classList.remove('editing');

                        // Remove cancel button
                        const cancelBtn = tableCard.querySelector('.cancel-edit-btn');
                        if (cancelBtn) cancelBtn.remove();

                        // Restore submitted state
                        updateBtn.classList.add('submitted');
                        updateBtn.innerHTML = '<i class="fas fa-check-double"></i> Submitted';
                        updateBtn.disabled = true;
                        updateBtn.onclick = () => submitTableResults(tableName);

                        // Show edit button again
                        const editBtn = tableCard.querySelector('.edit-scores-btn');
                        if (editBtn) editBtn.style.display = '';

                        // Disable score buttons
                        const scoreButtons = tableCard.querySelectorAll('.score-btn');
                        scoreButtons.forEach(btn => {
                            btn.disabled = true;
                            btn.style.opacity = '0.5';
                            btn.style.cursor = 'not-allowed';
                        });

                        // Add/update edit history badge
                        checkAndShowEditHistory(tableName, roundNum, tableCard);

                        // Refresh team scores display
                        refreshTeamScores();

                        // Update bracket visualization with edited scores
                        await updateBracketVisualization(roundNum);

                        if (data.edit_count > 0) {
                            showToast('Edit History', `This table has been edited ${data.edit_count} time(s). Click the badge to view history.`, 'info');
                        }
                    } else {
                        showToast('Error', data.user_message || data.error || 'Failed to update scores', 'error');
                        updateBtn.disabled = false;
                        updateBtn.innerHTML = '<i class="fas fa-save"></i> Update Scores';
                    }
                } catch (error) {
                    showToast('Network Error', 'Failed to connect to server. Please try again.', 'error');
                    console.error('Update scores error:', error);
                    updateBtn.disabled = false;
                    updateBtn.innerHTML = '<i class="fas fa-save"></i> Update Scores';
                }
            }

            // Cancel score editing and restore original state
            function cancelScoreEditing(tableName, roundNum) {
                const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);

                // Remove editing state
                tableCard.classList.remove('editing');

                // Clear score selections
                if (tableScores[tableName]) {
                    delete tableScores[tableName];
                }

                // Remove cancel button
                const cancelBtn = tableCard.querySelector('.cancel-edit-btn');
                if (cancelBtn) cancelBtn.remove();

                // Show edit button again
                const editBtn = tableCard.querySelector('.edit-scores-btn');
                if (editBtn) editBtn.style.display = '';

                // Restore submitted state - reload the round to get correct data
                loadRound();

                showToast('Cancelled', 'Score editing cancelled. Original scores restored.', 'info');
            }

            // View score history for a table
            async function viewScoreHistory(tableName, roundNum) {
                try {
                    const response = await fetch(`/get_score_history/${roundNum}/${encodeURIComponent(tableName)}`);
                    const data = await response.json();

                    if (data.success && data.edit_count > 0) {
                        showHistoryModal(tableName, roundNum, data.history);
                    } else {
                        showToast('No History', 'This table has not been edited.', 'info');
                    }
                } catch (error) {
                    showToast('Error', 'Failed to load score history.', 'error');
                    console.error('Score history error:', error);
                }
            }

            // Show modal with score history
            function showHistoryModal(tableName, roundNum, history) {
                // Create modal if it doesn't exist
                let modal = document.getElementById('history-modal');
                if (!modal) {
                    modal = document.createElement('div');
                    modal.id = 'history-modal';
                    modal.className = 'history-modal';
                    modal.innerHTML = `
                    <div class="history-modal-content">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h3 id="history-modal-title" style="margin: 0; color: var(--color-text);"></h3>
                            <button onclick="closeHistoryModal()" style="background: none; border: none; color: var(--color-text-secondary); font-size: 24px; cursor: pointer;">&times;</button>
                        </div>
                        <div id="history-modal-body"></div>
                    </div>
                `;
                    document.body.appendChild(modal);

                    // Close on background click
                    modal.addEventListener('click', (e) => {
                        if (e.target === modal) closeHistoryModal();
                    });
                }

                // Populate modal content
                document.getElementById('history-modal-title').textContent = `Score History: ${tableName} (Round ${roundNum})`;

                let bodyHTML = `<p style="color: var(--color-text-secondary); margin-bottom: 16px;">Total edits: ${history.length}</p>`;

                history.forEach((entry, index) => {
                    const timestamp = new Date(entry.timestamp).toLocaleString();
                    bodyHTML += `
                    <div class="history-entry">
                        <div class="history-entry-header">
                            <span><strong>Edit #${index + 1}</strong></span>
                            <span>${timestamp}</span>
                        </div>
                        ${entry.reason ? `<div class="history-entry-reason">"${escapeHtml(entry.reason)}"</div>` : ''}
                        <div class="history-scores">
                            <div class="history-scores-before">
                                <h5>Before</h5>
                                ${formatScoresForHistory(entry.old_results)}
                            </div>
                            <div class="history-scores-after">
                                <h5>After</h5>
                                ${formatScoresForHistory(entry.new_results)}
                            </div>
                        </div>
                    </div>
                `;
                });

                document.getElementById('history-modal-body').innerHTML = bodyHTML;

                // Show modal
                modal.classList.add('show');
            }

            // Format scores for history display
            function formatScoresForHistory(results) {
                if (!results || results.length === 0) return '<p>No data</p>';

                return results.map(r => {
                    const pointsLabel = r.points === 5 ? 'Win' : (r.points === 1 ? 'Draw' : 'Loss');
                    const scoreText = currentScoringMode === 'japanese' ? pointsLabel : `${r.points} pts (${pointsLabel})`;
                    return `<div style="font-size: 12px; margin: 4px 0;">Player ${r.player_id}: ${scoreText}</div>`;
                }).join('');
            }

            // Close history modal
            function closeHistoryModal() {
                const modal = document.getElementById('history-modal');
                if (modal) modal.classList.remove('show');
            }

            // Display Tables with Score Input
            function displayTables(tables, round) {
                const tablesGrid = document.getElementById('tables-grid');
                const tablesContainer = document.getElementById('tables-container');
                const keyboardHints = document.getElementById('keyboard-hints');
                if (keyboardHints) keyboardHints.style.display = Object.keys(tables).length > 0 ? 'block' : 'none';

                console.log('displayTables called with:', { round, tableCount: Object.keys(tables).length });

                // Clean up all previous round progress bars - only show current round progress
                const oldProgressBars = document.querySelectorAll('.submission-progress-container');
                oldProgressBars.forEach(bar => bar.remove());

                tablesGrid.innerHTML = '';

                if (!tables || Object.keys(tables).length === 0) {
                    tablesGrid.innerHTML = '<div class="empty-state"><h3>No tables available</h3></div>';
                    return;
                }

                // Responsive grid — let CSS handle column count based on viewport
                const tableCount = Object.keys(tables).length;
                const width = window.innerWidth;
                const isLandscape = width >= 1024;
                let cols = Math.min(tableCount, width >= 1400 ? 4 : width >= 1024 ? 3 : width >= 768 ? 2 : 1);
                tablesGrid.style.display = 'grid';
                tablesGrid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
                tablesGrid.style.gap = '12px';

                // Sort tables by number (Table 1, Table 2, ..., Table 16)
                const sortedTables = Object.entries(tables).sort(([tableA], [tableB]) => {
                    // Extract number from table name (e.g., "Table 1" -> 1, "Table 10" -> 10)
                    const numA = parseInt(tableA.replace(/[^0-9]/g, '')) || 0;
                    const numB = parseInt(tableB.replace(/[^0-9]/g, '')) || 0;
                    return numA - numB;
                });

                console.log('📊 Tables sorted in numerical order:', sortedTables.map(([name]) => name));

                sortedTables.forEach(([tableName, players]) => {
                    console.log(`Creating card for ${tableName} with ${players.length} players`);

                    const card = document.createElement('div');
                    card.className = 'table-card';
                    card.id = `table-${tableName.replace(/\s+/g, '-')}`;

                    // Create card with inline score buttons
                    card.innerHTML = `
                    <div class="table-header">
                        <i class="fas fa-chair"></i>
                        ${tableName}
                    </div>
                    <div class="table-score-legend">
                        <i class="fas fa-star"></i> ${currentScoringMode === 'japanese' ? '7% Pool | Winner takes all | Losers contribute' : 'Win=5pts | Draw=1pt | Loss=0pts'}
                    </div>
                    <div class="table-players">
                        ${players.map(player => {
                        const playerId = player['Player ID'] || player.id;
                        // Show cumulative score from previous rounds, or '-' if no score yet
                        const cumulativeScore = window.playerScores?.[playerId] || window.playerScores?.[String(playerId)] || 0;
                        // Show current round score being entered, or cumulative if not entered yet
                        const currentRoundScore = window.currentRoundScores?.[tableName]?.[playerId];
                        const playerScore = currentRoundScore !== undefined ? currentRoundScore : cumulativeScore;
                        return `
                                <div class="table-player">
                                    <div class="table-player-info">
                                        <i class="fas fa-user"></i>
                                        <div class="table-player-details">
                                            <div class="table-player-name">
                                                ${escapeHtml(player['Player Name'] || player.name || 'Unknown')}
                                            </div>
                                            <div class="table-player-team" ${currentEventMode === 'individual' ? 'style="display:none"' : ''}>
                                                ${escapeHtml(player['Team Name'] || player.team || 'Unknown Team')}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="table-player-score" id="score-display-${playerId}">
                                        ${currentRoundScore !== undefined
                                            ? (currentScoringMode === 'japanese'
                                                ? (currentRoundScore === 5 ? 'Win' : currentRoundScore === 1 ? 'Draw' : 'Loss')
                                                : currentRoundScore + ' pts')
                                            : (cumulativeScore + ' pts')}
                                    </div>
                                    <div class="score-buttons-inline">
                                        <button class="score-btn score-btn-win"
                                                data-table="${tableName.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}"
                                                data-player="${playerId}"
                                                data-points="5"
                                                title="${currentScoringMode === 'japanese' ? 'Win (takes pool)' : 'Win (5 points)'}">
                                            W
                                        </button>
                                        <button class="score-btn score-btn-draw"
                                                data-table="${tableName.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}"
                                                data-player="${playerId}"
                                                data-points="1"
                                                title="${currentScoringMode === 'japanese' ? 'Draw (lose contribution)' : 'Draw (1 point)'}">
                                            D
                                        </button>
                                        <button class="score-btn score-btn-loss"
                                                data-table="${tableName.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}"
                                                data-player="${playerId}"
                                                data-points="0"
                                                title="${currentScoringMode === 'japanese' ? 'Loss (lose contribution)' : 'Loss (0 points)'}">
                                            L
                                        </button>
                                    </div>
                                </div>
                            `;
                    }).join('')}
                    </div>
                    <div class="table-submit-container">
                        <button class="submit-table-btn" onclick="submitTableResults('${tableName.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">
                            <i class="fas fa-check-circle"></i> Submit Table Results
                        </button>
                    </div>
                `;

                    tablesGrid.appendChild(card);

                    // Force 4 columns after EACH card is added
                    if (isLandscape) {
                        tablesGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
                        tablesGrid.style.gap = '12px';
                    }
                });

                // Force 4 columns FINALLY after all cards are added
                if (isLandscape) {
                    tablesGrid.style.display = 'grid';
                    tablesGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
                    tablesGrid.style.gap = '12px';
                    console.log(`✅ FINAL: Applied 4-column layout to tables-grid, ${Object.keys(tables).length} tables rendered`);
                }

                tablesContainer.style.display = 'block';

                // Display bye players for individual mode
                if (currentEventMode === 'individual') {
                    displayByePlayers(round, tablesGrid);
                }

                console.log(`displayTables complete: ${Object.keys(tables).length} tables rendered`);
            }

            function displayByePlayers(round, container) {
                fetch('/get_tournament_state')
                    .then(res => res.json())
                    .then(data => {
                        const byePlayers = data.bye_players || {};
                        const roundByes = byePlayers[round] || byePlayers[String(round)] || [];
                        if (!roundByes || roundByes.length === 0) return;

                        const byeCard = document.createElement('div');
                        byeCard.className = 'table-card';
                        byeCard.style.borderColor = 'var(--color-success)';
                        byeCard.style.opacity = '0.85';

                        const byePointsLabel = currentScoringMode === 'japanese' ? 'BYE (no change)' : 'BYE +5';

                        const playerNames = roundByes.map(pid => {
                            // Find player name from teams
                            for (const [name, players] of Object.entries(data.teams || {})) {
                                if (!players || !players[0]) continue;
                                const playerId = players[0]['Player ID'] || players[0].id;
                                if (String(playerId) === String(pid)) {
                                    return `<div class="table-player" style="padding: 8px 12px; display: flex; align-items: center; gap: 8px;">
                                        <i class="fas fa-forward" style="color: var(--color-success);"></i>
                                        <span>${escapeHtml(name)}</span>
                                        <span style="margin-left: auto; background: var(--color-success); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 700;">${byePointsLabel}</span>
                                    </div>`;
                                }
                            }
                            return `<div class="table-player" style="padding: 8px 12px; display: flex; align-items: center; gap: 8px;">
                                <i class="fas fa-forward" style="color: var(--color-warning);"></i>
                                <span>Player ${pid}</span>
                                <span style="margin-left: auto; background: var(--color-success); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 700;">${byePointsLabel}</span>
                            </div>`;
                        }).join('');

                        byeCard.innerHTML = `
                            <div class="table-header" style="background: var(--color-success-light);">
                                <div class="table-name"><i class="fas fa-forward"></i> Bye This Round</div>
                                <span class="submitted-badge" style="background: var(--color-success); color: white;">Auto-Win</span>
                            </div>
                            <div class="table-players">${playerNames}</div>
                        `;
                        container.appendChild(byeCard);
                    })
                    .catch(err => console.error('Error fetching bye players:', err));
            }

            // ============================================
            // PLAYER DROP FEATURE (Individual Events Only)
            // ============================================

            function showDropPlayersButton() {
                if (currentEventMode !== 'individual') return;

                // Remove any existing drop button
                const existing = document.getElementById('drop-players-btn');
                if (existing) existing.remove();

                const activeControls = document.getElementById('active-round-controls');
                if (!activeControls) return;

                const btn = document.createElement('button');
                btn.id = 'drop-players-btn';
                btn.className = 'btn btn-danger';
                btn.title = 'Drop players from future rounds';
                btn.innerHTML = '<i class="fas fa-user-minus"></i><span>Drop Player</span>';
                btn.onclick = showDropPlayerModal;
                activeControls.appendChild(btn);
            }

            function hideDropPlayersButton() {
                const btn = document.getElementById('drop-players-btn');
                if (btn) btn.remove();
            }

            async function showDropPlayerModal() {
                const currentRound = document.getElementById('round-select').value;
                if (!currentRound) {
                    showToast('Error', 'No round selected', 'error');
                    return;
                }

                // Fetch current state to get active players
                try {
                    const res = await fetch('/get_tournament_state');
                    const data = await res.json();

                    const teams = data.teams || {};
                    const playerScores = data.player_scores || {};
                    const droppedIds = new Set(Object.keys(data.dropped_players || {}).map(Number));

                    // Build player list (active only)
                    const players = [];
                    for (const [name, playerArr] of Object.entries(teams)) {
                        if (!playerArr || !playerArr[0]) continue;
                        const p = playerArr[0];
                        const pid = p['Player ID'];
                        if (droppedIds.has(pid)) continue;
                        players.push({
                            id: pid,
                            name: p['Player Name'] || name,
                            score: playerScores[pid] || playerScores[String(pid)] || 0
                        });
                    }

                    players.sort((a, b) => b.score - a.score);

                    // Build modal content
                    const playerListHtml = players.map(p => `
                        <div style="display: flex; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--color-border-subtle);">
                            <span style="flex: 1; font-weight: 500;">${escapeHtml(p.name)}</span>
                            <span style="margin-right: 16px; color: var(--color-text-secondary);">${formatScore(p.score)}</span>
                            <button class="btn btn-danger drop-player-btn" style="padding: 4px 12px; font-size: 0.75rem;"
                                data-player-id="${p.id}"
                                data-player-name="${escapeHtml(p.name)}">
                                <i class="fas fa-times"></i> Drop
                            </button>
                        </div>
                    `).join('');

                    const modalHtml = `
                        <div id="drop-player-overlay" class="scoring-mode-overlay show" style="z-index: 10001;">
                            <div class="scoring-mode-modal" style="max-width: 500px; max-height: 80vh; overflow-y: auto;">
                                <h2 class="scoring-mode-title">
                                    <i class="fas fa-user-minus"></i> Drop Players
                                </h2>
                                <p class="scoring-mode-subtitle">Select a player to remove from future rounds. Their score will be frozen.</p>
                                <div style="margin: 16px 0; border-radius: 8px; background: var(--color-surface-hover); overflow: hidden;">
                                    ${playerListHtml}
                                </div>
                                <div class="scoring-mode-actions">
                                    <button class="btn btn-secondary" onclick="closeDropPlayerModal()">
                                        <i class="fas fa-times"></i> Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;

                    // Insert modal
                    const existingModal = document.getElementById('drop-player-overlay');
                    if (existingModal) existingModal.remove();
                    document.body.insertAdjacentHTML('beforeend', modalHtml);

                    // Attach drop button handlers (safe from XSS — no inline JS)
                    document.querySelectorAll('.drop-player-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            confirmDropPlayer(
                                parseInt(this.dataset.playerId),
                                this.dataset.playerName
                            );
                        });
                    });

                } catch (error) {
                    console.error('Error showing drop player modal:', error);
                    showToast('Error', 'Failed to load player list', 'error');
                }
            }

            function closeDropPlayerModal() {
                const modal = document.getElementById('drop-player-overlay');
                if (modal) modal.remove();
            }

            async function confirmDropPlayer(playerId, playerName) {
                const confirmed = await modalManager.confirm(
                    'Drop Player',
                    `Drop ${playerName} from the tournament?\n\nThey will not participate in future rounds. Their current score will be frozen.`,
                    'Drop Player',
                    'Cancel'
                );
                if (!confirmed) return;

                const currentRound = document.getElementById('round-select').value;

                try {
                    const response = await fetch('/drop_player', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ player_id: playerId, round: parseInt(currentRound) })
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Player Dropped', `${playerName} removed from future rounds.`, 'warning', 4000);
                        closeDropPlayerModal();
                        refreshTeamScores();
                    } else {
                        showToast('Error', data.message || 'Failed to drop player', 'error');
                    }
                } catch (error) {
                    console.error('Error dropping player:', error);
                    showToast('Error', 'Network error dropping player', 'error');
                }
            }

            // Update Stats
            function updateStats(data) {
                const statsProgressContainer = document.getElementById('stats-progress-container');

                if (data.teams) {
                    const teamCount = Object.keys(data.teams).length;
                    const totalPlayers = Object.values(data.teams).reduce((sum, players) => sum + players.length, 0);

                    if (currentEventMode === 'individual') {
                        document.getElementById('stat-teams').textContent = totalPlayers;
                        // Update label if possible
                        const teamsLabel = document.querySelector('[data-stat="teams-label"]');
                        if (teamsLabel) teamsLabel.textContent = 'Players';
                    } else {
                        document.getElementById('stat-teams').textContent = teamCount;
                    }
                    document.getElementById('stat-players').textContent = totalPlayers;
                }

                // Show the combined container
                if (statsProgressContainer) {
                    statsProgressContainer.style.display = 'grid';
                }
            }

            // Track table scores
            const tableScores = {};

            // Refresh team scores without reloading entire page
            async function refreshTeamScores(finalsMode = null) {
                try {
                    // Auto-detect finals mode if not explicitly provided
                    if (finalsMode === null) {
                        const currentRound = document.getElementById('round-select').value;
                        const maxRounds = window.tournamentMaxRounds || 5;
                        finalsMode = (parseInt(currentRound) === maxRounds);
                        if (finalsMode && !window.finalsAdvancingTeams) {
                            // Try to get teams from current tables
                            const tablesGrid = document.getElementById('tables-grid');
                            if (tablesGrid) {
                                const finalsPlayers = [];
                                tablesGrid.querySelectorAll('.table-player').forEach(playerEl => {
                                    const teamName = playerEl.querySelector('.table-player-team')?.textContent;
                                    if (teamName) finalsPlayers.push(teamName);
                                });
                                if (finalsPlayers.length > 0) {
                                    window.finalsAdvancingTeams = [...new Set(finalsPlayers)];
                                    console.log('Auto-detected finals teams:', window.finalsAdvancingTeams);
                                }
                            }
                        }
                    }

                    const response = await fetch('/get_tournament_state');
                    const data = await response.json();

                    if (data.success && data.teams) {
                        // Update dropped players cache from server response
                        if (currentEventMode === 'individual') {
                            window._droppedPlayersCache = data.dropped_players || {};
                        }

                        // Update team display with fresh scores
                        displayTeams(data.teams, data.player_scores, finalsMode);
                        console.log('Team scores refreshed' + (finalsMode ? ' (finals mode - top 4 only)' : ' (all teams)'));
                    }
                } catch (error) {
                    console.error('Error refreshing scores:', error);
                }
            }

            // Set player score
            function setPlayerScore(tableName, playerId, points, button) {
                // Initialize table scores if needed
                if (!tableScores[tableName]) {
                    tableScores[tableName] = {};
                }

                // Initialize global current round scores if needed
                if (!window.currentRoundScores) {
                    window.currentRoundScores = {};
                }
                if (!window.currentRoundScores[tableName]) {
                    window.currentRoundScores[tableName] = {};
                }

                // Check if this button is already active (allow deselect)
                if (button.classList.contains('active')) {
                    // Deselect - remove score
                    button.classList.remove('active');
                    delete tableScores[tableName][playerId];
                    delete window.currentRoundScores[tableName][playerId];

                    // Update score display next to player name
                    const scoreDisplay = document.getElementById(`score-display-${playerId}`);
                    if (scoreDisplay) {
                        scoreDisplay.textContent = '-';
                    }

                    console.log(`Deselected score: Table ${tableName}, Player ${playerId}`);
                    showToast('Score Removed', 'Click a button to set the score again', 'info');
                    return;
                }

                // Store the score
                tableScores[tableName][playerId] = points;
                window.currentRoundScores[tableName][playerId] = points;

                // Update score display next to player name
                const scoreDisplay = document.getElementById(`score-display-${playerId}`);
                if (scoreDisplay) {
                    if (currentScoringMode === 'japanese') {
                        const label = points === 5 ? 'Win' : points === 1 ? 'Draw' : 'Loss';
                        scoreDisplay.textContent = label;
                    } else {
                        scoreDisplay.textContent = `${points} pts`;
                    }
                }

                // Update button states (remove active from siblings)
                const parent = button.parentElement;
                parent.querySelectorAll('.score-btn').forEach(btn => {
                    btn.classList.remove('active');
                });

                // Make this button active
                button.classList.add('active');

                console.log(`Set score: Table ${tableName}, Player ${playerId} = ${points} pts`);

                // Auto-Fill Losers Logic (UX Improvement)
                // If Win (5 points) is selected, clear any existing selections on other players
                // and set them all to Loss (0). A winner means everyone else lost.
                if (points === 5) {
                    const tableCard = button.closest('.table-card');
                    if (tableCard) {
                        const allLossBtns = tableCard.querySelectorAll('.score-btn-loss');
                        let autoFilledCount = 0;

                        allLossBtns.forEach(lossBtn => {
                            const otherPlayerId = parseInt(lossBtn.dataset.player);
                            if (otherPlayerId === playerId) return;

                            const otherPlayerRow = lossBtn.closest('.table-player');

                            // Clear any existing selection (e.g., draws) before setting loss
                            const activeBtn = otherPlayerRow.querySelector('.score-btn.active');
                            if (activeBtn) {
                                activeBtn.classList.remove('active');
                            }

                            // Set loss directly (avoid .click() to prevent redundant DOM event dispatch)
                            setPlayerScore(tableName, otherPlayerId, 0, lossBtn);
                            autoFilledCount++;
                        });

                        if (autoFilledCount > 0) {
                            showToast('Auto-Fill', `Marked ${autoFilledCount} other players as Loss`, 'info');
                        }
                    }
                }
            }

            // Submit table results
            async function submitTableResults(tableName) {
                const currentRound = document.getElementById('round-select').value;

                if (!currentRound) {
                    showToast('Error', 'Please select a round first', 'error');
                    return;
                }

                // Get submit button to prevent double-click
                const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
                const submitBtn = tableCard ? tableCard.querySelector('.submit-table-btn') : null;

                // Prevent double-submission (check if already disabled/submitted)
                if (submitBtn && submitBtn.disabled) {
                    showToast('Already Submitted', `${tableName} results have already been submitted`, 'info');
                    return;
                }

                if (!tableScores[tableName]) {
                    showToast('Error', 'Please enter scores for all players first', 'warning');
                    return;
                }

                // Check if all players have scores
                const table = window.currentTables[tableName];

                if (!table) {
                    showToast('Error', 'Table not found', 'error');
                    return;
                }

                const expectedCount = table.length;
                const actualCount = Object.keys(tableScores[tableName]).length;
                if (actualCount < expectedCount) {
                    const missing = expectedCount - actualCount;
                    showToast('Incomplete Scores', `${missing} player(s) at ${tableName} still need scores`, 'warning');
                    return;
                }

                // Build results array
                const results = [];
                for (const playerId in tableScores[tableName]) {
                    results.push({
                        player_id: parseInt(playerId),
                        points: tableScores[tableName][playerId]
                    });
                }

                // Disable button immediately to prevent double-click
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
                }

                try {
                    const response = await fetch('/submit_table_results', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            round: parseInt(currentRound),
                            table: tableName,
                            results: results
                        })
                    });

                    const data = await response.json();

                    console.log('Submit table response:', data);

                    if (data.success) {
                        showToast('Table Submitted!', `Results recorded for ${tableName}`, 'success');

                        // Update remaining tables widget if submission_status is present
                        if (data.submission_status) {
                            updateRemainingTablesWidget(data.submission_status);
                            // Update canFinalize state
                            window.canFinalize = data.can_finalize || data.submission_status.is_complete || false;
                            updateFinalizeButtonState();
                        }

                        // Mark button as submitted
                        if (submitBtn) {
                            submitBtn.classList.add('submitted');
                            submitBtn.innerHTML = '<i class="fas fa-check-double"></i> Submitted';
                            // Keep button disabled
                        }

                        // Update team display with new scores
                        console.log('Updated scores:', data.scores);
                        console.log('Updated player scores:', data.player_scores);

                        // Fetch fresh data to update display
                        refreshTeamScores();

                        // Update bracket visualization with new scores (Phase 3.1)
                        const roundNum = parseInt(document.getElementById('round-select').value);
                        await updateBracketVisualization(roundNum);

                        // Update submission progress (Phase 3.1)
                        await updateSubmissionProgress(roundNum);
                    } else if (data.already_submitted) {
                        // Backend says already submitted
                        showToast('Already Submitted', data.error || `${tableName} has already been submitted`, 'info');
                        if (submitBtn) {
                            submitBtn.classList.add('submitted');
                            submitBtn.innerHTML = '<i class="fas fa-check-double"></i> Already Submitted';
                            // Keep button disabled
                        }
                    } else {
                        // Other error - re-enable button
                        showToast('Error', data.error || data.message || 'Failed to submit results', 'error');
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Table Results';
                        }
                    }
                } catch (error) {
                    showToast('Error', 'Network error submitting results. Please try again.', 'error');
                    console.error(error);
                    // Re-enable button on network error so user can retry
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Table Results';
                    }
                }
            }

            // Update finalize button state based on can_finalize
            function updateFinalizeButtonState() {
                // Find the finalize/submit round results button
                const finalizeBtn = document.querySelector('button[onclick="submitRoundResults()"]');
                if (!finalizeBtn) return;

                if (window.canFinalize !== true) {
                    finalizeBtn.disabled = true;
                    finalizeBtn.style.opacity = '0.5';
                    finalizeBtn.style.cursor = 'not-allowed';
                    finalizeBtn.classList.remove('finalize-pulse');
                    finalizeBtn.title = 'Submit all tables before finalizing the round';
                } else {
                    finalizeBtn.disabled = false;
                    finalizeBtn.style.opacity = '1';
                    finalizeBtn.style.cursor = 'pointer';
                    finalizeBtn.classList.add('finalize-pulse');
                    finalizeBtn.title = 'All tables submitted — click to finalize and generate next round';
                }
            }

            // Submit all round results and finalize
            async function submitRoundResults() {
                const currentRound = document.getElementById('round-select').value;

                if (!currentRound) {
                    showToast('Error', 'Please select a round first', 'error');
                    return;
                }

                // Gate: check if finalization is allowed
                if (window.canFinalize !== true) {
                    showToast('Not Ready', 'All tables must be submitted before finalizing the round.', 'warning');
                    return;
                }

                // Check if any tables have been submitted (local or already submitted)
                const hasLocalSubmissions = Object.keys(tableScores).length > 0;
                const hasConfirmedSubmissions = document.querySelectorAll('.submit-table-btn.submitted').length > 0;

                if (!hasLocalSubmissions && !hasConfirmedSubmissions) {
                    showToast('Warning', 'No table results have been submitted yet', 'warning');
                    return;
                }

                const confirmMsg = `Finalize Round ${currentRound}? This will generate the next round and cannot be undone.`;
                const confirmed = await modalManager.confirm('Finalize Round', confirmMsg, 'Finalize');
                if (!confirmed) return;

                try {
                    showToast('Finalizing...', 'Finalizing round results', 'info');

                    const response = await fetch('/submit_player_results', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            round: parseInt(currentRound),
                            results: []  // Empty as scores already added via table submissions
                        })
                    });

                    if (!response.ok) {
                        const errData = await response.json().catch(() => ({}));
                        showToast('Error', errData.error || `Server error (${response.status}). Please try again.`, 'error');
                        return;
                    }
                    const data = await response.json();

                    if (data.success) {
                        showToast('Round Complete!', data.message, 'success');

                        // Clear table scores for next round
                        Object.keys(tableScores).forEach(key => delete tableScores[key]);

                        // Check if semifinals or finals were generated
                        if (data.semifinals) {
                            const roundType = getRoundType(parseInt(currentRound));

                            if (roundType === 'swiss') {
                                // Just finished Swiss rounds
                                const roundSelect = document.getElementById('round-select');
                                const nextOption = roundSelect.options[roundSelect.selectedIndex + 1];

                                if (nextOption) {
                                    const nextRoundText = nextOption.textContent;
                                    if (nextRoundText.includes('Semifinals') || nextRoundText.includes('Top 8')) {
                                        console.log('Semifinals generated!', data.semifinals);
                                        showToast('Top 8 Ready!', 'Top 8 teams advance!', 'success');
                                    } else if (nextRoundText.includes('Finals')) {
                                        console.log('Finals generated!', data.semifinals);
                                        showToast('Finals Ready!', 'Top 4 teams advance to finals!', 'success');
                                    }

                                    // Auto-select next round
                                    setTimeout(() => {
                                        document.getElementById('round-select').value = nextOption.value;
                                        loadRound();
                                    }, 2000);
                                }
                            } else if (roundType === 'semifinals' || roundType === 'top8cut') {
                                // Just finished Semifinals/Top8
                                console.log('Finals generated after semifinals!', data.semifinals);
                                showToast('Finals Ready!', 'Top 4 teams advance to finals!', 'success');

                                // Auto-select finals
                                const roundSelect = document.getElementById('round-select');
                                const nextOption = roundSelect.options[roundSelect.selectedIndex + 1];
                                if (nextOption) {
                                    setTimeout(() => {
                                        document.getElementById('round-select').value = nextOption.value;
                                        loadRound();
                                    }, 2000);
                                }
                            }
                        }

                        // Check if tournament complete (after Finals)
                        if (data.tournament_winner) {
                            console.log('Tournament complete!', data.tournament_winner);
                            showToast('Tournament Complete!',
                                `Champion: ${data.tournament_winner.winning_team}!`,
                                'success');

                            // Show championship modal
                            setTimeout(() => {
                                showChampionshipModal(data.tournament_winner);
                            }, 1000);
                        } else if (!data.semifinals) {
                            // Auto-advance to next round (if still in Swiss rounds and no special round generated)
                            const roundType = getRoundType(parseInt(currentRound));
                            if (roundType === 'swiss') {
                                const nextRound = parseInt(currentRound) + 1;
                                const swissRounds = window.tournamentSwissRounds || 4;

                                if (nextRound <= swissRounds) {
                                    showToast('Loading Next Round...', `Moving to Swiss Round ${nextRound}`, 'info');

                                    setTimeout(async () => {
                                        try {
                                            const checkRes = await fetch(`/get_tables/${nextRound}`);
                                            const checkData = await checkRes.json();
                                            if (checkData.tables && Object.keys(checkData.tables).length > 0) {
                                                document.getElementById('round-select').value = String(nextRound);
                                                loadRound();
                                            } else {
                                                showToast('Please Wait', 'Next round is being generated...', 'info');
                                            }
                                        } catch (e) {
                                            showToast('Error', 'Could not load next round', 'error');
                                        }
                                    }, 1500);
                                }
                            }
                        }

                        // Refresh team scores to show updated standings
                        console.log('Round finalized, refreshing team scores...');
                        refreshTeamScores();
                    } else {
                        showToast('Error', data.message || 'Failed to finalize round', 'error');
                    }
                } catch (error) {
                    showToast('Error', 'Network error finalizing round', 'error');
                    console.error(error);
                }
            }

            // Store tables globally for reference
            window.currentTables = {};

            // Championship Modal Functions
            function showChampionshipModal(winnerData) {
                const modal = document.getElementById('championship-modal');
                const championName = document.getElementById('champion-team-name');
                const standingsList = document.getElementById('final-standings-list');
                const mvpName = document.getElementById('mvp-name');
                const mvpScore = document.getElementById('mvp-score');

                if (!winnerData || !modal) return;

                // Set champion name
                championName.textContent = winnerData.winning_team || 'Champion';

                // Set MVP (null-safe)
                if (winnerData.mvp_player) {
                    mvpName.textContent = `${winnerData.mvp_player.name} (${winnerData.mvp_player.team})`;
                    mvpScore.textContent = `${winnerData.mvp_player.total_points} Total Points`;
                } else {
                    mvpName.textContent = 'N/A';
                    mvpScore.textContent = '';
                }

                // Build standings list
                standingsList.innerHTML = '';

                (winnerData.final_standings || []).forEach((team, index) => {
                    const row = document.createElement('div');
                    row.className = 'standing-row' + (index === 0 ? ' champion' : '');

                    const rank = index + 1;
                    const rankClass = index === 0 ? 'standing-rank first' : 'standing-rank';

                    row.innerHTML = `
                    <div class="${rankClass}">${rank}</div>
                    <div>
                        <div class="standing-team">${escapeHtml(team.team)}</div>
                        <div class="standing-finals">Finals: ${team.final_points} pts</div>
                        <div class="standing-swiss">Swiss: ${team.swiss_points} pts</div>
                    </div>
                    <div class="standing-total">${team.total_points}</div>
                    <div style="font-size: var(--text-xs); color: var(--color-text-tertiary);">pts</div>
                `;

                    standingsList.appendChild(row);
                });

                // Show modal with animation
                modal.classList.add('show');
            }

            function closeChampionshipModal() {
                const modal = document.getElementById('championship-modal');
                modal.classList.remove('show');
            }

            // Close modal when clicking outside
            document.addEventListener('DOMContentLoaded', () => {
                const modal = document.getElementById('championship-modal');
                if (modal) modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        closeChampionshipModal();
                    }
                });
            });

            // ============================================
            // PLAYER/TABLE SEARCH
            // ============================================

            let searchDebounceTimer = null;

            // Find which table a player is currently seated at (from loaded round data)
            function findPlayerTable(playerId) {
                if (!window.currentTables) return '';
                for (const [tableName, players] of Object.entries(window.currentTables)) {
                    for (const player of players) {
                        const pid = player['Player ID'] || player.id;
                        if (String(pid) === String(playerId)) {
                            return tableName;
                        }
                    }
                }
                return '';
            }

            function clearPlayerSearch() {
                const input = document.getElementById('player-search-input');
                const clearBtn = document.getElementById('search-clear-btn');
                const dropdown = document.getElementById('search-results-dropdown');

                if (input) input.value = '';
                if (clearBtn) clearBtn.style.display = 'none';
                if (dropdown) {
                    dropdown.innerHTML = '';
                    dropdown.style.display = 'none';
                }

                // Remove any existing highlights
                document.querySelectorAll('.table-card.search-highlight').forEach(card => {
                    card.classList.remove('search-highlight');
                });
            }

            async function handlePlayerSearch(query) {
                const dropdown = document.getElementById('search-results-dropdown');
                const clearBtn = document.getElementById('search-clear-btn');

                if (!query || query.trim().length === 0) {
                    if (dropdown) {
                        dropdown.innerHTML = '';
                        dropdown.style.display = 'none';
                    }
                    if (clearBtn) clearBtn.style.display = 'none';
                    return;
                }

                if (clearBtn) clearBtn.style.display = 'inline-flex';

                try {
                    const response = await fetch(`/search_player?q=${encodeURIComponent(query.trim())}`);
                    const data = await response.json();

                    if (!dropdown) return;

                    if (data.results && data.results.length > 0) {
                        dropdown.innerHTML = data.results.map(result => {
                            const playerName = result.player_name || result.name || '';
                            const teamName = result.team_name || result.team || '';
                            const tableName = result.table || findPlayerTable(result.player_id) || '';
                            const droppedBadge = result.dropped ? '<span class="search-dropped-badge">(Dropped)</span>' : '';
                            const safePlayerId = String(result.player_id).replace(/'/g, "\\'");
                            return `
                                <div class="search-result-item" onclick="selectSearchResult('${safePlayerId}', '${escapeHtml(tableName)}')">
                                    <div class="search-result-name">
                                        <i class="fas fa-user"></i>
                                        ${escapeHtml(playerName)} ${droppedBadge}
                                    </div>
                                    <div class="search-result-details">
                                        <span class="search-result-team">${escapeHtml(teamName)}</span>
                                        <span class="search-result-score">${result.score !== undefined ? result.score + ' pts' : ''}</span>
                                    </div>
                                    ${tableName ? '<div class="search-result-table"><i class="fas fa-chair"></i> ' + escapeHtml(tableName) + '</div>' : ''}
                                </div>
                            `;
                        }).join('');
                        dropdown.style.display = 'block';
                    } else {
                        dropdown.innerHTML = '<div class="search-no-results"><i class="fas fa-search"></i> No results found</div>';
                        dropdown.style.display = 'block';
                    }
                } catch (error) {
                    console.error('Search error:', error);
                    if (dropdown) {
                        dropdown.innerHTML = '<div class="search-no-results">Search unavailable</div>';
                        dropdown.style.display = 'block';
                    }
                }
            }

            function selectSearchResult(playerId, tableName) {
                const dropdown = document.getElementById('search-results-dropdown');
                if (dropdown) {
                    dropdown.innerHTML = '';
                    dropdown.style.display = 'none';
                }

                // Remove previous highlights
                document.querySelectorAll('.table-card.search-highlight').forEach(card => {
                    card.classList.remove('search-highlight');
                });

                if (tableName) {
                    const cardId = `table-${tableName.replace(/\s+/g, '-')}`;
                    const card = document.getElementById(cardId);
                    if (card) {
                        card.classList.add('search-highlight');
                        card.scrollIntoView({ behavior: 'smooth', block: 'center' });

                        // Remove highlight after 3 seconds
                        setTimeout(() => {
                            card.classList.remove('search-highlight');
                        }, 3000);
                    }
                }
            }

            // Initialize search input listener
            document.addEventListener('DOMContentLoaded', () => {
                const searchInput = document.getElementById('player-search-input');
                if (searchInput) {
                    searchInput.addEventListener('input', (e) => {
                        const query = e.target.value;

                        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);

                        searchDebounceTimer = setTimeout(() => {
                            handlePlayerSearch(query);
                        }, 300);
                    });

                    // Close dropdown on escape
                    searchInput.addEventListener('keydown', (e) => {
                        if (e.key === 'Escape') {
                            clearPlayerSearch();
                            searchInput.blur();
                        }
                    });
                }

                // Close dropdown when clicking outside
                document.addEventListener('click', (e) => {
                    const searchBar = document.getElementById('player-search-bar');
                    if (searchBar && !searchBar.contains(e.target)) {
                        const dropdown = document.getElementById('search-results-dropdown');
                        if (dropdown) {
                            dropdown.style.display = 'none';
                        }
                    }
                });
            });

            // ============================================
            // SETUP WIZARD DISMISS (Close Button)
            // ============================================

            function dismissSetupWizard() {
                // Only block dismiss if we KNOW state is initial (not when unknown/null)
                if (lastKnownState === 'initial') {
                    showToast('Setup Required', 'Please complete setup to continue', 'warning');
                    return;
                }

                const eventOverlay = document.getElementById('event-mode-overlay');
                const scoringOverlay = document.getElementById('scoring-mode-overlay');

                if (eventOverlay) eventOverlay.classList.remove('show');
                if (scoringOverlay) scoringOverlay.classList.remove('show');
            }

            // Click-outside-to-dismiss for wizard overlays
            document.addEventListener('DOMContentLoaded', () => {
                const eventOverlay = document.getElementById('event-mode-overlay');
                const scoringOverlay = document.getElementById('scoring-mode-overlay');

                if (eventOverlay) {
                    eventOverlay.addEventListener('click', (e) => {
                        // Only dismiss if clicking the overlay background, not the modal content
                        if (e.target === eventOverlay) {
                            dismissSetupWizard();
                        }
                    });
                }

                if (scoringOverlay) {
                    scoringOverlay.addEventListener('click', (e) => {
                        if (e.target === scoringOverlay) {
                            dismissSetupWizard();
                        }
                    });
                }
            });

            // Event delegation for score buttons (XSS-safe)
            document.addEventListener('click', function (e) {
                if (e.target.matches('.score-btn')) {
                    if (!e.target.dataset.player || !e.target.dataset.points) return;
                    const tableName = e.target.dataset.table;
                    const playerId = parseInt(e.target.dataset.player);
                    const points = parseInt(e.target.dataset.points);
                    setPlayerScore(tableName, playerId, points, e.target);
                }
            });

            // Session recovery: detect server restart and prompt backup restore
            let lastKnownState = null;
            let initialLoadDone = false;
            let _checkServerRunning = false;
            async function checkServerState() {
                if (_checkServerRunning) return;
                _checkServerRunning = true;
                try {
                    const res = await fetch('/get_state_info');
                    const data = await res.json();
                    const currentState = data.current_state;
                    const info = data.tournament_info || {};

                    // Update canFinalize from state info if available
                    if (data.can_finalize !== undefined) {
                        window.canFinalize = data.can_finalize;
                        updateFinalizeButtonState();
                    }

                    // Show/hide search bar based on tournament state
                    const searchBar = document.getElementById('player-search-bar');
                    if (searchBar) {
                        if (currentState && currentState !== 'initial') {
                            searchBar.style.display = '';
                        } else {
                            searchBar.style.display = 'none';
                        }
                    }

                    // Auto-restore active tournament view on first page load
                    if (!initialLoadDone && currentState && currentState !== 'initial' && currentState !== 'participants_loaded') {
                        initialLoadDone = true;
                        console.log(`[AUTO-RESTORE] Tournament active (state: ${currentState}, round: ${info.current_round})`);

                        // Restore event/scoring mode from server
                        const stateRes = await fetch('/get_tournament_state');
                        const stateData = await stateRes.json();
                        if (stateData.event_mode) {
                            currentEventMode = stateData.event_mode;
                            if (currentEventMode === 'individual') addIndividualModeIndicator();
                        }
                        if (stateData.scoring_mode) {
                            currentScoringMode = stateData.scoring_mode;
                            if (currentScoringMode === 'japanese') addJapaneseModeIndicator();
                        }

                        // Update round selector
                        window.tournamentSwissRounds = info.swiss_rounds_count || 4;
                        window.swissRoundsCount = info.swiss_rounds_count || 4;
                        window.hasSemifinals = info.has_semifinals || false;
                        window.totalTeams = info.team_count || 0;
                        window.tournamentMaxRounds = info.max_rounds || 5;
                        window.hasIndividualTopCut = stateData.has_top_cut || false;
                        updateRoundSelector(info.swiss_rounds_count || 4, info.has_semifinals || false, info.team_count);

                        // Switch to active controls and select current round
                        showActiveRoundControls();
                        document.getElementById('round-select').value = String(info.current_round || 1);
                        loadRound();

                        // Update teams display
                        if (stateData.teams) {
                            displayTeams(stateData.teams, stateData.player_scores);
                            document.getElementById('empty-state').style.display = 'none';
                        }
                    } else if (!initialLoadDone) {
                        initialLoadDone = true;
                    }

                    if (lastKnownState && lastKnownState !== 'initial' && currentState === 'initial') {
                        initialLoadDone = false;
                        const restore = await modalManager.confirm('Server Restarted', 'The server appears to have restarted. Would you like to restore from backup?', 'Restore', 'Skip');
                        if (restore) {
                            const restoreRes = await fetch('/restore_backup', { method: 'POST' });
                            const restoreData = await restoreRes.json();
                            if (restoreData.success) {
                                showToast('Restored', 'Tournament restored from backup', 'success');
                                location.reload();
                            } else {
                                showToast('Error', 'Failed to restore backup', 'error');
                            }
                        }
                    }
                    lastKnownState = currentState;
                    initialStateLoaded = true;
                } catch (e) { }
                _checkServerRunning = false;
                setTimeout(checkServerState, 5000);
            }

            // Auto-load on page load
            window.addEventListener('DOMContentLoaded', () => {
                checkServerState();
            });
