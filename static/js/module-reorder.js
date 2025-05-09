// Drag and drop functionality for module reordering
document.addEventListener('DOMContentLoaded', function() {
    console.log('Module reorder script loaded');
    
    const moduleList = document.getElementById('module-list');
    if (!moduleList) {
        console.warn('Module list container not found on the page');
        return;
    }
    
    console.log('Found module list container with ID:', moduleList.id);
    console.log('Reorder URL from data attribute:', moduleList.dataset.reorderUrl);
    
    // Initialize Sortable.js
    const sortable = new Sortable(moduleList, {
        handle: '.drag-handle', // Updated to match the handle in HTML
        animation: 150,
        ghostClass: 'bg-gray-100',
        onStart: function(evt) {
            console.log('Drag started');
            // Add visual feedback
            evt.item.classList.add('bg-blue-50');
        },
        onChange: function(evt) {
            console.log('Order changing during drag');
        },
        onEnd: function(evt) {
            console.log('Drag ended at index:', evt.newIndex);
            console.log('Previous index was:', evt.oldIndex);
            evt.item.classList.remove('bg-blue-50');
            
            // Only update if the position actually changed
            if (evt.oldIndex !== evt.newIndex) {
                console.log('Position changed, updating module order');
                updateModuleOrder();
            } else {
                console.log('No position change detected, skipping update');
            }
        }
    });
    
    // Function to update module order after dragging
    function updateModuleOrder() {
        console.log("updateModuleOrder function called");
        
        // Get a fresh reference to the module list
        const moduleListElement = document.getElementById('module-list');
        if (!moduleListElement) {
            console.error('Module list element not found on page');
            return;
        }
        
        const modules = Array.from(moduleListElement.querySelectorAll('.module-item'));
        console.log(`Found ${modules.length} module items to reorder`);
        
        // Get the reorder URL directly from the data attribute
        const reorderUrl = moduleListElement.dataset.reorderUrl;
        
        if (!reorderUrl) {
            console.error('Reorder URL not found in data-reorder-url attribute');
            showErrorToast('Configuration error: Missing reorder URL');
            return;
        }
        
        console.log('Using reorder URL:', reorderUrl);
        
        const orderData = [];
        
        modules.forEach((module, index) => {
            const moduleId = module.dataset.moduleId;
            if (!moduleId) {
                console.error('Module is missing data-module-id attribute:', module);
                return;
            }
            
            console.log(`Setting module ${moduleId} to order ${index + 1}`);
            
            orderData.push({
                module_id: moduleId,
                order: index + 1
            });
            
            // Update displayed order number in UI
            const orderDisplay = module.querySelector('.module-order');
            if (orderDisplay) {
                orderDisplay.textContent = index + 1;
            }
            
            // Also update the displayed order number in the module title
            const titleElement = module.querySelector('.text-primary-600');
            if (titleElement) {
                const currentTitle = titleElement.textContent;
                const dotIndex = currentTitle.indexOf('.');
                if (dotIndex > -1) {
                    const updatedTitle = (index + 1) + currentTitle.substring(dotIndex);
                    titleElement.textContent = updatedTitle;
                    console.log(`Updated module title to: ${updatedTitle}`);
                }
            }
        });
        
        if (orderData.length === 0) {
            console.error('No valid modules found to reorder');
            return;
        }
        
        console.log('Sending updated order to:', reorderUrl);
        console.log('Order data:', orderData);
        
        // Get CSRF token
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.error('CSRF token not found, cannot proceed with update');
            showErrorToast('Security token missing, please refresh the page');
            return;
        }
        
        // Send the new order to the server using the URL from data attribute
        fetch(reorderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({modules: orderData})
        })
        .then(response => {
            console.log(`Server responded with status: ${response.status}`);
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Server response:', data);
            if (data.success) {
                showSuccessToast('Module order updated successfully');
            } else {
                showErrorToast(data.message || 'Failed to update module order');
            }
        })
        .catch(error => {
            console.error('Error updating module order:', error);
            showErrorToast('An error occurred while updating module order');
        });
    }
    
    // Helper function to get CSRF token
    function getCSRFToken() {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (!csrfMeta) {
            console.error('CSRF token meta tag not found.');
            return '';
        }
        const token = csrfMeta.getAttribute('content');
        console.log('CSRF token found:', token ? 'Yes (value hidden)' : 'No');
        return token || '';
    }
    
    // Toast notification functions
    function showSuccessToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity duration-500 ease-in-out';
        toast.innerHTML = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 500);
        }, 3000);
    }
    
    function showErrorToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity duration-500 ease-in-out';
        toast.innerHTML = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 500);
        }, 3000);
    }
});