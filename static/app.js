// Car Yard App JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Vehicle Carousel functionality
    const carousel = document.getElementById('vehicleCarousel');
    if (carousel) {
        let currentSlide = 0;
        const slides = carousel.querySelectorAll('.carousel-slide');
        const totalSlides = slides.length;

        if (totalSlides > 0) {
            // Show carousel after 3 seconds
            setTimeout(() => {
                carousel.style.opacity = '1';
                carousel.style.transform = 'translateY(0)';

                // Start auto-sliding
                setInterval(() => {
                    slides[currentSlide].classList.remove('active');
                    currentSlide = (currentSlide + 1) % totalSlides;
                    slides[currentSlide].classList.add('active');
                }, 4000); // Change slide every 4 seconds
            }, 3000);
        }
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            if (!isValid) {
                e.preventDefault();
            }
        });
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
});
