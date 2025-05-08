document.addEventListener('DOMContentLoaded', function() {
    // Flash message dismissal
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        const dismissButton = message.querySelector('.dismiss-button');
        if (dismissButton) {
            dismissButton.addEventListener('click', () => {
                message.remove();
            });
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                message.remove();
            }, 5000);
        }
    });

    // Course progress updates
    const progressBars = document.querySelectorAll('[data-progress-course]');
    progressBars.forEach(bar => {
        const courseId = bar.getAttribute('data-progress-course');
        const moduleButtons = document.querySelectorAll(`[data-module-course="${courseId}"]`);
        
        moduleButtons.forEach(button => {
            button.addEventListener('click', function() {
                const progress = parseInt(this.getAttribute('data-module-progress'));
                if (!isNaN(progress)) {
                    updateProgress(courseId, progress);
                }
            });
        });
    });

    // Quiz submission
    const quizForm = document.getElementById('quiz-form');
    if (quizForm) {
        quizForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const quizId = this.getAttribute('data-quiz-id');
            const courseId = this.getAttribute('data-course-id');
            const answers = [];
            
            const questions = document.querySelectorAll('.quiz-question');
            let allAnswered = true;
            
            questions.forEach(question => {
                const questionId = question.getAttribute('data-question-id');
                const selectedOption = question.querySelector('input[type="radio"]:checked');
                
                if (selectedOption) {
                    answers.push({
                        questionId: questionId,
                        answer: selectedOption.value
                    });
                } else {
                    allAnswered = false;
                }
            });
            
            if (!allAnswered) {
                alert('Please answer all questions');
                return;
            }
            
            // In a real app, this would be an AJAX request to submit the quiz
            // Here we're just simulating the progress update
            updateProgress(courseId, 100);
            
            // Show quiz results
            const resultsElement = document.getElementById('quiz-results');
            if (resultsElement) {
                resultsElement.classList.remove('hidden');
                resultsElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // Module sorting in admin dashboard
    const moduleList = document.getElementById('module-list');
    if (moduleList && typeof Sortable !== 'undefined') {
        new Sortable(moduleList, {
            animation: 150,
            ghostClass: 'bg-blue-100',
            onEnd: function(evt) {
                const modules = Array.from(moduleList.querySelectorAll('li'));
                
                // Update order in DB (in a real app, this would be an AJAX request)
                modules.forEach((module, index) => {
                    const moduleId = module.getAttribute('data-module-id');
                    module.querySelector('.module-order').textContent = index + 1;
                });
            }
        });
    }
});

function updateProgress(courseId, progress) {
    // Update progress bar UI
    const progressBar = document.querySelector(`[data-progress-course="${courseId}"] .progress-bar-fill`);
    const progressText = document.querySelector(`[data-progress-course="${courseId}"] .progress-text`);
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
    
    if (progressText) {
        progressText.textContent = `${progress}%`;
    }
    
    // Submit progress to server
    fetch(`/update_progress/${courseId}/${progress}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && progress === 100) {
            // If course completed, show certificate notification
            const notification = document.getElementById('completion-notification');
            if (notification) {
                notification.classList.remove('hidden');
                setTimeout(() => {
                    notification.classList.add('hidden');
                }, 5000);
            }
            
            // Reload page to show certificate
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
    })
    .catch(error => console.error('Error updating progress:', error));
}
