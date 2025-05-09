// Drag and drop functionality for module reordering
document.addEventListener('DOMContentLoaded', function() {
    const moduleList = document.getElementById('module-list');
    if (!moduleList) return;
    
    // Initialize Sortable.js
    const sortable = new Sortable(moduleList, {
        handle: '.cursor-move', // Updated to use the correct handle class
        animation: 150,
        ghostClass: 'bg-gray-100',
        onEnd: function(evt) {
            updateModuleOrder();
        }
    });
    
    // Function to update module order after dragging
    function updateModuleOrder() {
        const modules = document.querySelectorAll('#module-list .module-item');
        
        // Get the reorder URL directly from the data attribute
        const reorderUrl = moduleList.dataset.reorderUrl;
        
        if (!reorderUrl) {
            console.error('Reorder URL not found in data-reorder-url attribute');
            showErrorToast('Configuration error: Missing reorder URL');
            return;
        }
        
        const orderData = [];
        
        modules.forEach((module, index) => {
            const moduleId = module.dataset.moduleId;
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
                const updatedTitle = (index + 1) + '.' + currentTitle.substring(currentTitle.indexOf('.'));
                titleElement.textContent = updatedTitle;
            }
        });
        
        console.log('Sending updated order to:', reorderUrl);
        console.log('Order data:', orderData);
        
        // Send the new order to the server using the URL from data attribute
        fetch(reorderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({modules: orderData})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessToast('Module order updated successfully');
            } else {
                showErrorToast('Failed to update module order');
            }
        })
        .catch(error => {
            console.error('Error updating module order:', error);
            showErrorToast('An error occurred while updating module order');
        });
    }
    
    // Helper function to get CSRF token
    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
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