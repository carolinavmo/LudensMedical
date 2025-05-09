// Enhanced drag-and-drop functionality for module reordering with immediate updates
document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced module reorder script loaded');

    const moduleList = document.getElementById('module-list');
    if (!moduleList) {
        console.error('Module list container not found');
        return;
    }
    
    const reorderUrl = moduleList.dataset.reorderUrl;
    if (!reorderUrl) {
        console.error('Reorder URL not found in module list data attribute');
        return;
    }
    
    console.log('Found module list container with reorder URL:', reorderUrl);
    
    // Create a status indicator for feedback during/after drag operations
    const createStatusIndicator = () => {
        const indicator = document.createElement('div');
        indicator.id = 'module-order-status';
        indicator.className = 'fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300 flex items-center';
        indicator.style.opacity = '0';
        document.body.appendChild(indicator);
        return indicator;
    };
    
    // Get or create the status indicator
    const getStatusIndicator = () => {
        let indicator = document.getElementById('module-order-status');
        if (!indicator) {
            indicator = createStatusIndicator();
        }
        return indicator;
    };
    
    // Create success toast notification
    function showSuccessToast(message) {
        const indicator = getStatusIndicator();
        indicator.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300 flex items-center';
        indicator.innerHTML = `
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            ${message}
        `;
        indicator.style.opacity = '1';
        
        // Add success visual feedback to all modules
        const modules = moduleList.querySelectorAll('.module-item');
        modules.forEach(module => {
            // Add a green border flash effect
            module.classList.add('border');
            module.classList.add('border-green-500');
            module.classList.add('bg-green-50');
            
            // Remove the pending state classes if present
            module.classList.remove('border-blue-500');
            module.classList.remove('animate-pulse');
        });
        
        // Reset module styling after the toast disappears
        setTimeout(() => {
            modules.forEach(module => {
                module.classList.remove('border');
                module.classList.remove('border-green-500');
                module.classList.remove('bg-green-50');
            });
            indicator.style.opacity = '0';
        }, 2000);
    }
    
    // Create pending toast notification
    function showPendingToast(message) {
        const indicator = getStatusIndicator();
        indicator.className = 'fixed top-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300 flex items-center';
        indicator.innerHTML = `
            <svg class="w-5 h-5 mr-2 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${message}
        `;
        indicator.style.opacity = '1';
        
        // Add pending visual feedback to all modules
        const modules = moduleList.querySelectorAll('.module-item');
        modules.forEach(module => {
            // Add a blue border and pulse effect
            module.classList.add('border');
            module.classList.add('border-blue-500');
            module.classList.add('animate-pulse');
            
            // Remove any previous state styles
            module.classList.remove('border-green-500');
            module.classList.remove('border-red-500');
            module.classList.remove('bg-green-50');
            module.classList.remove('bg-red-50');
        });
    }
    
    // Create error toast notification
    function showErrorToast(message) {
        const indicator = getStatusIndicator();
        indicator.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300 flex items-center';
        indicator.innerHTML = `
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
            ${message}
        `;
        indicator.style.opacity = '1';
        
        // Add error visual feedback to all modules
        const modules = moduleList.querySelectorAll('.module-item');
        modules.forEach(module => {
            // Add a red border and background
            module.classList.add('border');
            module.classList.add('border-red-500');
            module.classList.add('bg-red-50');
            
            // Remove any pending state classes
            module.classList.remove('border-blue-500');
            module.classList.remove('animate-pulse');
            module.classList.remove('border-green-500');
            module.classList.remove('bg-green-50');
            
            // Shake effect for visual feedback
            module.classList.add('shake-animation');
            setTimeout(() => {
                module.classList.remove('shake-animation');
            }, 1000);
        });
        
        setTimeout(() => {
            // Reset module styling and hide toast
            modules.forEach(module => {
                module.classList.remove('border');
                module.classList.remove('border-red-500');
                module.classList.remove('bg-red-50');
            });
            indicator.style.opacity = '0';
        }, 3000);
    }
    
    // Function to get CSRF token from meta tag
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    // Update the module order display immediately in the UI without waiting for the server
    function updateModuleOrderDisplay() {
        const modules = Array.from(moduleList.querySelectorAll('.module-item'));
        
        modules.forEach((module, index) => {
            const newOrder = index + 1;
            
            // Store the new order as a data attribute
            module.dataset.newOrder = newOrder;
            
            // Update the order number displayed in the UI
            const orderDisplay = module.querySelector('.module-order');
            if (orderDisplay) {
                orderDisplay.textContent = newOrder;
            }
            
            // Force update the order in module edit form if it's expanded or not
            const orderInput = module.querySelector('input[name="order"]');
            if (orderInput) {
                // This directly changes the form field value
                orderInput.value = newOrder;
            }
            
            // Update the title display if it contains the order number
            const titleElement = module.querySelector('.text-primary-600');
            if (titleElement) {
                const currentTitle = titleElement.textContent;
                const dotIndex = currentTitle.indexOf('.');
                if (dotIndex > -1) {
                    titleElement.textContent = `${newOrder}${currentTitle.substring(dotIndex)}`;
                }
            }
        });
    }
    
    // Function to update module order on the server
    function saveModuleOrderToServer() {
        showPendingToast('Saving order...');
        
        const modules = Array.from(moduleList.querySelectorAll('.module-item'));
        
        if (!modules.length) {
            console.error('No modules found to reorder');
            showErrorToast('No modules found');
            return;
        }
        
        // Collect modules data
        const modulesData = modules.map((module, index) => {
            const moduleId = module.dataset.moduleId;
            const newOrder = index + 1;
            
            return {
                module_id: moduleId,
                order: newOrder
            };
        });
        
        console.log('Sending updated order data to server:', modulesData);
        
        // Get CSRF token
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.error('CSRF token not found');
            showErrorToast('Security token missing. Please refresh the page.');
            return;
        }
        
        // Send the update to the server
        fetch(reorderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ modules: modulesData })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Server response:', data);
            if (data.success) {
                showSuccessToast('Order saved successfully');
            } else {
                showErrorToast(data.message || 'Failed to update module order');
            }
        })
        .catch(error => {
            console.error('Error updating module order:', error);
            showErrorToast('Error saving module order');
        });
    }
    
    // Track the last module order string to detect changes
    let lastOrderString = '';
    
    // Function to generate a string representing the current module order
    function getModuleOrderString() {
        return Array.from(moduleList.querySelectorAll('.module-item'))
            .map(module => module.dataset.moduleId)
            .join(',');
    }
    
    // Initialize last order string
    lastOrderString = getModuleOrderString();
    
    // Initialize Sortable with real-time updates
    new Sortable(moduleList, {
        handle: '.drag-handle',
        animation: 150,
        ghostClass: 'bg-gray-100',
        dragClass: 'dragging',
        // Set a delay so short clicks don't trigger drag
        delay: 150,
        delayOnTouchOnly: true,
        
        onStart(evt) {
            evt.item.classList.add('dragging');
            
            // Create visual feedback
            const indicator = document.createElement('div');
            indicator.className = 'module-drop-indicator';
            document.body.appendChild(indicator);
            
            // Store the initial order
            lastOrderString = getModuleOrderString();
        },
        
        onChange(evt) {
            // Update the visual order in the UI immediately while dragging
            updateModuleOrderDisplay();
        },
        
        onEnd(evt) {
            evt.item.classList.remove('dragging');
            
            // Remove any drop indicators
            document.querySelectorAll('.module-drop-indicator').forEach(el => el.remove());
            
            // Get the new order string after drag
            const newOrderString = getModuleOrderString();
            
            // If the order has changed, update the server
            if (newOrderString !== lastOrderString) {
                // Immediately update the display
                updateModuleOrderDisplay();
                
                // Save to server
                saveModuleOrderToServer();
                
                // Update last order string
                lastOrderString = newOrderString;
            }
        }
    });
});