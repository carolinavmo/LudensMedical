// Drag and drop functionality for module reordering
document.addEventListener('DOMContentLoaded', function() {
    const moduleList = document.getElementById('module-list');
    if (!moduleList) return;
    
    // Initialize Sortable.js
    const sortable = new Sortable(moduleList, {
        handle: '.module-drag-handle',
        animation: 150,
        ghostClass: 'bg-gray-100',
        onEnd: function(evt) {
            updateModuleOrder();
        }
    });
    
    // Function to update module order after dragging
    function updateModuleOrder() {
        const modules = document.querySelectorAll('#module-list .module-item');
        const courseId = moduleList.dataset.courseId;
        const orderData = [];
        
        modules.forEach((module, index) => {
            const moduleId = module.dataset.moduleId;
            orderData.push({
                module_id: moduleId,
                order: index + 1
            });
            
            // Update displayed order number
            const orderDisplay = module.querySelector('.module-order');
            if (orderDisplay) {
                orderDisplay.textContent = index + 1;
            }
        });
        
        // Send the new order to the server
        fetch('/admin/courses/' + courseId + '/modules/reorder', {
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