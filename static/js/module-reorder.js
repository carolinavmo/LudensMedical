// Enhanced drag-and-drop functionality for module reordering
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
    
    // Create success toast notification
    function showSuccessToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        toast.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                ${message}
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease-out';
            setTimeout(() => toast.remove(), 500);
        }, 2000);
    }
    
    // Create error toast notification
    function showErrorToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        toast.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                ${message}
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease-out';
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }
    
    // Function to get CSRF token from meta tag
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    // Function to update module order on the server
    function updateModuleOrder() {
        const modules = Array.from(moduleList.querySelectorAll('.module-item'));
        
        if (!modules.length) {
            console.error('No modules found to reorder');
            return;
        }
        
        // Collect modules data
        const modulesData = modules.map((module, index) => {
            const moduleId = module.dataset.moduleId;
            const newOrder = index + 1;
            
            // Update the order number displayed in the UI
            const orderDisplay = module.querySelector('.module-order');
            if (orderDisplay) {
                orderDisplay.textContent = newOrder;
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
            
            return {
                module_id: moduleId,
                order: newOrder
            };
        });
        
        console.log('Sending updated order data:', modulesData);
        
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
                showSuccessToast('Module order saved');
            } else {
                showErrorToast(data.message || 'Failed to update module order');
            }
        })
        .catch(error => {
            console.error('Error updating module order:', error);
            showErrorToast('Error saving module order');
        });
    }
    
    // Initialize Sortable with simpler configuration
    new Sortable(moduleList, {
        handle: '.drag-handle',
        animation: 150,
        ghostClass: 'bg-gray-100',
        dragClass: 'dragging',
        onStart(evt) {
            evt.item.classList.add('dragging');
            // Add visual drop indicator
            const indicator = document.createElement('div');
            indicator.className = 'module-drop-indicator';
            document.body.appendChild(indicator);
        },
        onEnd(evt) {
            evt.item.classList.remove('dragging');
            // Remove any drop indicators
            document.querySelectorAll('.module-drop-indicator').forEach(el => el.remove());
            
            // Always update the order after a drag operation completes
            updateModuleOrder();
        }
    });
});