document.addEventListener('DOMContentLoaded', () => {
    const ERROR_SUGGESTIONS = {
        "Squat too shallow": "💡 Tip: Widen your stance slightly and drop your hips until your thighs are parallel to the floor.",
        "Back bending too forward": "💡 Tip: Brace your core and look straight ahead to keep your chest up and torso vertical.",
        "Heel lift": "💡 Tip: Drive through your mid-foot and heels. Consider using lifting shoes with an elevated heel if mobility is an issue.",
        "Swinging (back/spine movement)": "💡 Tip: Lower the weight slightly and pin your elbows to your sides to isolate the biceps.",
        "Not full extension (bottom)": "💡 Tip: Control the eccentric phase and straighten your arm fully at the bottom of the curl.",
        "Not full flexion (top)": "💡 Tip: Squeeze your biceps hard at the top and ensure your hand comes all the way to your shoulder.",
        "Shoulder shrugging": "💡 Tip: Depress your shoulder blades before lifting the weight to keep the tension on your deltoids.",
        "Arms bent too much": "💡 Tip: Keep a slight, fixed bend in your elbows. Don't turn the lateral raise into a rowing motion."
    };

    // --- Profile System & Migration ---
    let currentProfile = localStorage.getItem('current_profile') || 'Guest';
    let profilesList = JSON.parse(localStorage.getItem('profiles') || '["Guest"]');

    // Migration script for old data
    if (localStorage.getItem('workout_history') && !localStorage.getItem('workout_history_Guest')) {
        localStorage.setItem('workout_history_Guest', localStorage.getItem('workout_history'));
        localStorage.removeItem('workout_history');
    }
    if (localStorage.getItem('nutri_data') && !localStorage.getItem('nutri_data_Guest')) {
        localStorage.setItem('nutri_data_Guest', localStorage.getItem('nutri_data'));
        localStorage.removeItem('nutri_data');
    }
    // ----------------------------------

    const exerciseBtns = document.querySelectorAll('.exercise-selection .ex-btn');
    const currentModeDisplay = document.getElementById('current-mode-display');
    const feedbackOverlay = document.getElementById('feedback-overlay');
    
    const correctCounter = document.getElementById('correct-counter');
    const accuracyScore = document.getElementById('accuracy-score');

    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const endSessionBtn = document.getElementById('end-session-btn');
    
    const summaryModal = document.getElementById('summary-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalBreakdown = document.getElementById('modal-breakdown');

    // Tab Elements
    const navLive = document.getElementById('nav-live');
    const navHistory = document.getElementById('nav-history');
    const navNutrition = document.getElementById('nav-nutrition');
    const liveView = document.getElementById('live-view');
    const historyView = document.getElementById('history-view');
    const nutritionView = document.getElementById('nutrition-view');
    const sidebarExerciseSection = document.getElementById('sidebar-exercise-section');
    const sidebarControlsSection = document.getElementById('sidebar-controls-section');

    let pollInterval = null;
    let currentMode = null;
    let sessionHistory = {};
    let lastData = null;

    // Profile UI Logic
    const profileSelector = document.getElementById('profile-selector');
    
    function initProfiles() {
        if (!profileSelector) return;
        
        profilesList = JSON.parse(localStorage.getItem('profiles') || '["Guest"]');
        profileSelector.innerHTML = '';
        
        profilesList.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = `👤 ${p}`;
            profileSelector.appendChild(opt);
        });
        
        const addOpt = document.createElement('option');
        addOpt.value = 'ADD_NEW';
        addOpt.textContent = '➕ Add New Profile...';
        profileSelector.appendChild(addOpt);
        
        if (!profilesList.includes(currentProfile)) {
            currentProfile = profilesList[0];
        }
        profileSelector.value = currentProfile;
        localStorage.setItem('current_profile', currentProfile);
    }
    
    if (profileSelector) {
        initProfiles();
        profileSelector.addEventListener('change', (e) => {
            if (e.target.value === 'ADD_NEW') {
                const newName = prompt('Enter new profile name:');
                if (newName && newName.trim() !== '') {
                    const safeName = newName.trim();
                    if (!profilesList.includes(safeName)) {
                        profilesList.push(safeName);
                        localStorage.setItem('profiles', JSON.stringify(profilesList));
                    }
                    currentProfile = safeName;
                }
                initProfiles();
            } else {
                currentProfile = e.target.value;
                localStorage.setItem('current_profile', currentProfile);
            }
            
            // Re-render views with new profile data
            renderHistory();
            
            // Clear nutrition form first, then load
            document.getElementById('nutri-age').value = '';
            document.getElementById('nutri-height').value = '';
            document.getElementById('nutri-weight').value = '';
            document.getElementById('nutri-target').value = '';
            document.getElementById('res-calories').textContent = '--';
            document.getElementById('res-protein').textContent = '--';
            document.getElementById('res-goal-type').textContent = 'Maintenance';
            
            loadNutritionData();
        });
    }

    // Handle Tabs
    if (navLive && navHistory && navNutrition) {
        navLive.addEventListener('click', () => {
            navLive.classList.add('active');
            navHistory.classList.remove('active');
            navNutrition.classList.remove('active');
            liveView.classList.remove('d-none');
            historyView.classList.add('d-none');
            nutritionView.classList.add('d-none');
            sidebarExerciseSection.style.display = 'block';
            sidebarControlsSection.style.display = 'block';
        });

        navHistory.addEventListener('click', () => {
            navHistory.classList.add('active');
            navLive.classList.remove('active');
            navNutrition.classList.remove('active');
            historyView.classList.remove('d-none');
            liveView.classList.add('d-none');
            nutritionView.classList.add('d-none');
            sidebarExerciseSection.style.display = 'none';
            sidebarControlsSection.style.display = 'none';
            renderHistory();
        });

        navNutrition.addEventListener('click', () => {
            navNutrition.classList.add('active');
            navLive.classList.remove('active');
            navHistory.classList.remove('active');
            nutritionView.classList.remove('d-none');
            liveView.classList.add('d-none');
            historyView.classList.add('d-none');
            sidebarExerciseSection.style.display = 'none';
            sidebarControlsSection.style.display = 'none';
            loadNutritionData();
        });
    }

    function renderHistory() {
        const historyContainer = document.getElementById('history-list-container');
        if (!historyContainer) return;
        
        let history = JSON.parse(localStorage.getItem('workout_history_' + currentProfile) || '[]');
        if (history.length === 0) {
            historyContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; margin-top: 50px;">No workout history found. Complete a session to see it here!</p>';
            return;
        }
        
        let html = '';
        let needsSave = false;
        
        history.forEach(record => {
            let breakdownHtml = record.htmlBreakdown;
            
            // Retroactive parsing for old workouts
            if (!breakdownHtml.includes("Suggestions for Improvement")) {
                let foundErrors = new Set();
                Object.keys(ERROR_SUGGESTIONS).forEach(err => {
                    if (breakdownHtml.includes(err)) {
                        foundErrors.add(err);
                    }
                });
                
                if (foundErrors.size > 0) {
                    let suggestionsHtml = `
                        <div class="breakdown-item" style="border-left: 4px solid var(--accent-green); margin-top: 20px;">
                            <h3 style="color: var(--accent-green); margin-bottom: 10px;">Suggestions for Improvement</h3>
                            <ul style="list-style-type: none; padding: 0;">
                    `;
                    foundErrors.forEach(err => {
                        suggestionsHtml += `<li style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 8px;">${ERROR_SUGGESTIONS[err]}</li>`;
                    });
                    suggestionsHtml += `</ul></div>`;
                    breakdownHtml += suggestionsHtml;
                    record.htmlBreakdown = breakdownHtml;
                    needsSave = true;
                }
            }

            html += `
                <div style="background: rgba(0,0,0,0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; border-left: 4px solid var(--accent-blue);">
                    <h3 style="color: var(--text-secondary); margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">📅 ${record.date}</h3>
                    ${breakdownHtml}
                </div>
            `;
        });
        
        if (needsSave) {
            localStorage.setItem('workout_history_' + currentProfile, JSON.stringify(history));
        }
        
        historyContainer.innerHTML = html;
    }

    // Macro Calculator Logic
    const calcMacroBtn = document.getElementById('calc-macro-btn');
    if (calcMacroBtn) {
        calcMacroBtn.addEventListener('click', () => {
            const gender = document.getElementById('nutri-gender').value;
            const age = parseFloat(document.getElementById('nutri-age').value);
            const height = parseFloat(document.getElementById('nutri-height').value);
            const weight = parseFloat(document.getElementById('nutri-weight').value);
            const target = parseFloat(document.getElementById('nutri-target').value);

            if (!age || !height || !weight || !target) {
                alert("Please fill out all fields!");
                return;
            }

            // Save to localStorage
            const nutriData = { gender, age, height, weight, target };
            localStorage.setItem('nutri_data_' + currentProfile, JSON.stringify(nutriData));

            // Mifflin-St Jeor
            let bmr = (10 * weight) + (6.25 * height) - (5 * age);
            bmr = gender === 'male' ? bmr + 5 : bmr - 161;

            // TDEE (Moderate activity multiplier)
            let tdee = bmr * 1.55;
            
            // Goal logic
            let calories = tdee;
            let goalText = "Maintenance";
            
            if (target < weight) {
                calories -= 500;
                goalText = "Weight Loss (500 kcal Deficit)";
            } else if (target > weight) {
                calories += 500;
                goalText = "Weight Gain (500 kcal Surplus)";
            }

            // Protein: 1.8g per kg of CURRENT weight
            const protein = weight * 1.8;

            document.getElementById('res-calories').textContent = Math.round(calories);
            document.getElementById('res-goal-type').textContent = goalText;
            document.getElementById('res-protein').textContent = Math.round(protein);
        });
    }

    function loadNutritionData() {
        const saved = localStorage.getItem('nutri_data_' + currentProfile);
        if (saved) {
            const data = JSON.parse(saved);
            document.getElementById('nutri-gender').value = data.gender || 'male';
            document.getElementById('nutri-age').value = data.age || '';
            document.getElementById('nutri-height').value = data.height || '';
            document.getElementById('nutri-weight').value = data.weight || '';
            document.getElementById('nutri-target').value = data.target || '';
            
            if (data.age && data.weight) {
                calcMacroBtn.click();
            }
        }
    }

    // Helper to save stats
    function saveCurrentStats() {
        if (currentMode && lastData) {
            sessionHistory[currentMode] = {
                correct_reps: lastData.correct_reps,
                incorrect_reps: lastData.incorrect_reps,
                error_frequencies: lastData.error_frequencies || {}
            };
        }
    }

    // Handle Exercise Selection
    exerciseBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            saveCurrentStats(); // Save previous mode's stats

            const mode = btn.dataset.mode;
            currentMode = mode;
            
            // UI Updates
            exerciseBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentModeDisplay.textContent = `Current Mode: ${mode}`;

            startBtn.classList.remove('d-none');
            stopBtn.classList.add('d-none');

            // API Call
            try {
                const response = await fetch(`/set_mode/${mode}`, { method: 'POST' });
                if (response.ok) {
                    if (!pollInterval) {
                        startPolling();
                    }
                }
            } catch (err) {
                console.error("Error setting mode:", err);
            }
        });
    });

    startBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/start', { method: 'POST' });
            if (res.ok) {
                startBtn.classList.add('d-none');
                stopBtn.classList.remove('d-none');
            }
        } catch (err) { console.error(err); }
    });

    stopBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/stop', { method: 'POST' });
            if (res.ok) {
                stopBtn.classList.add('d-none');
                startBtn.classList.remove('d-none');
                saveCurrentStats();
            }
        } catch (err) { console.error(err); }
    });

    // Poll State
    function startPolling() {
        pollInterval = setInterval(async () => {
            try {
                const res = await fetch('/state');
                const data = await res.json();
                lastData = data;

                if (data.mode) {
                    updateDashboard(data);
                }
            } catch (err) {
                console.error("Error polling state:", err);
            }
        }, 300); // 300ms for responsive feel
    }

    function updateDashboard(data) {
        // Update Feedback Overlay
        feedbackOverlay.textContent = data.feedback;
        if (data.feedback !== "Correct" && !data.feedback.includes("Waiting") && !data.feedback.includes("Paused") && !data.feedback.includes("Ready")) {
            feedbackOverlay.classList.add('error');
        } else {
            feedbackOverlay.classList.remove('error');
        }

        // Update Counters
        const c = data.correct_reps;
        const i = data.incorrect_reps;
        correctCounter.textContent = c;

        // Update Accuracy
        const total = c + i;
        const acc = total === 0 ? 0 : Math.round((c / total) * 100);
        accuracyScore.textContent = `${acc}%`;
    }

    // Modal Logic
    endSessionBtn.addEventListener('click', async () => {
        // Stop current
        try {
            await fetch('/stop', { method: 'POST' });
            stopBtn.classList.add('d-none');
            startBtn.classList.remove('d-none');
        } catch(e) {}
        
        saveCurrentStats();
        clearInterval(pollInterval);
        pollInterval = null;

        // Build HTML for Breakdown
        modalBreakdown.innerHTML = '';
        const modes = Object.keys(sessionHistory);
        let allUniqueErrors = new Set();
        
        if (modes.length === 0) {
            modalBreakdown.innerHTML = '<p style="color: var(--text-secondary);">No exercises recorded this session.</p>';
        } else {
            modes.forEach(mode => {
                const stats = sessionHistory[mode];
                const total = stats.correct_reps + stats.incorrect_reps;
                if (total === 0) return; // Skip if no reps done

                const acc = Math.round((stats.correct_reps / total) * 100);
                
                let errorsHtml = '';
                const errorKeys = Object.keys(stats.error_frequencies);
                if (errorKeys.length > 0) {
                    errorsHtml = `<ul class="error-list">`;
                    // Sort errors by frequency descending
                    errorKeys.sort((a, b) => stats.error_frequencies[b] - stats.error_frequencies[a]).forEach(err => {
                        errorsHtml += `<li>${err} (${stats.error_frequencies[err]} times)</li>`;
                        allUniqueErrors.add(err);
                    });
                    errorsHtml += `</ul>`;
                } else {
                    errorsHtml = `<p style="color: var(--accent-green); font-size: 0.9rem; margin-top: 10px;">Perfect form! No mistakes made.</p>`;
                }

                const itemHtml = `
                    <div class="breakdown-item">
                        <div class="breakdown-header">
                            <h3>${mode}</h3>
                            <span class="text-blue" style="font-weight: 800; font-size: 1.5rem;">${acc}%</span>
                        </div>
                        <div class="breakdown-stats">
                            <span><strong class="text-green">${stats.correct_reps}</strong> Correct</span>
                            <span><strong class="text-red">${stats.incorrect_reps}</strong> Incorrect</span>
                        </div>
                        ${errorsHtml}
                    </div>
                `;
                modalBreakdown.innerHTML += itemHtml;
            });
            
            if (allUniqueErrors.size > 0) {
                let suggestionsHtml = `
                    <div class="breakdown-item" style="border-left: 4px solid var(--accent-green); margin-top: 20px;">
                        <h3 style="color: var(--accent-green); margin-bottom: 10px;">Suggestions for Improvement</h3>
                        <ul style="list-style-type: none; padding: 0;">
                `;
                allUniqueErrors.forEach(err => {
                    if (ERROR_SUGGESTIONS[err]) {
                        suggestionsHtml += `<li style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 8px;">${ERROR_SUGGESTIONS[err]}</li>`;
                    }
                });
                suggestionsHtml += `</ul></div>`;
                modalBreakdown.innerHTML += suggestionsHtml;
            }
        }

        if (modalBreakdown.innerHTML === '') {
             modalBreakdown.innerHTML = '<p style="color: var(--text-secondary);">No exercises recorded this session.</p>';
        } else {
            // Save to localStorage if actual exercises were done
            const dateStr = new Date().toLocaleString();
            const workoutRecord = {
                date: dateStr,
                htmlBreakdown: modalBreakdown.innerHTML
            };
            let history = JSON.parse(localStorage.getItem('workout_history_' + currentProfile) || '[]');
            history.unshift(workoutRecord);
            localStorage.setItem('workout_history_' + currentProfile, JSON.stringify(history));
            renderHistory();
        }

        summaryModal.classList.remove('hidden');
    });

    closeModalBtn.addEventListener('click', () => {
        summaryModal.classList.add('hidden');
        sessionHistory = {};
        currentMode = null;
        lastData = null;
        
        // Reset visually
        exerciseBtns.forEach(b => b.classList.remove('active'));
        currentModeDisplay.textContent = "Select an exercise to begin";
        feedbackOverlay.textContent = "Waiting for data...";
        feedbackOverlay.classList.remove('error');
        correctCounter.textContent = "0";
        accuracyScore.textContent = "0%";
        startBtn.classList.add('d-none');
        stopBtn.classList.add('d-none');
    });
});
