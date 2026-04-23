/**
 * FairSight — Jaw-Dropping 3D Animations
 */

document.addEventListener('DOMContentLoaded', () => {
    initLoader();
    initParticles();
    initCustomCursor();
    initCardTilt();
    initScrollAnimations();
    animateHeroText();
    initMagneticButton();
    initStatsCountUp();
    initUploadEntrances();
    initReportAnimations();
});

function initLoader() {
    if (!sessionStorage.getItem('fairsight_loaded')) {
        const loader = document.getElementById('page-loader');
        if (loader) {
            setTimeout(() => {
                loader.style.opacity = '0';
                setTimeout(() => {
                    loader.style.display = 'none';
                    sessionStorage.setItem('fairsight_loaded', 'true');
                }, 500);
            }, 1500);
        }
    } else {
        const loader = document.getElementById('page-loader');
        if (loader) loader.style.display = 'none';
    }
}

function initParticles() {
    if (typeof THREE === 'undefined') return;
    const canvas = document.createElement('canvas');
    canvas.id = 'particle-canvas';
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:-1;pointer-events:none;';
    document.body.prepend(canvas);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);

    const geometry = new THREE.BufferGeometry();
    const count = 3000;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const color1 = new THREE.Color('#7c3aed');
    const color2 = new THREE.Color('#06b6d4');

    for (let i = 0; i < count; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 40;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 40;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 40;

        const mixedColor = color1.clone().lerp(color2, Math.random());
        colors[i * 3] = mixedColor.r;
        colors[i * 3 + 1] = mixedColor.g;
        colors[i * 3 + 2] = mixedColor.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true,
        transparent: true,
        opacity: 0.8
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    camera.position.z = 10;
    let mouseX = 0;
    let mouseY = 0;

    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    function animate() {
        requestAnimationFrame(animate);
        
        const positions = particles.geometry.attributes.position.array;
        for (let i = 0; i < count; i++) {
            positions[i * 3 + 2] += 0.05;
            if (positions[i * 3 + 2] > 15) {
                positions[i * 3 + 2] = -25;
            }
        }
        particles.geometry.attributes.position.needsUpdate = true;

        camera.position.x += (mouseX * 2 - camera.position.x) * 0.05;
        camera.position.y += (mouseY * 2 - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

function initCustomCursor() {
    const cursorDot = document.createElement('div');
    const cursorRing = document.createElement('div');
    cursorDot.className = 'custom-cursor-dot';
    cursorRing.className = 'custom-cursor-ring';
    document.body.appendChild(cursorDot);
    document.body.appendChild(cursorRing);

    let mouseX = 0, mouseY = 0;
    let ringX = 0, ringY = 0;

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        cursorDot.style.transform = `translate(${mouseX}px, ${mouseY}px)`;
    });

    function render() {
        ringX += (mouseX - ringX) * 0.12;
        ringY += (mouseY - ringY) * 0.12;
        cursorRing.style.transform = `translate(${ringX}px, ${ringY}px)`;
        requestAnimationFrame(render);
    }
    render();

    document.querySelectorAll('a, button, .card, .glass-card, .drop-zone').forEach(el => {
        el.addEventListener('mouseenter', () => cursorRing.classList.add('hover'));
        el.addEventListener('mouseleave', () => cursorRing.classList.remove('hover'));
    });
}

function initCardTilt() {
    document.querySelectorAll('.glass-card, .card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = (e.clientX - cx) / (rect.width / 2);
            const dy = (e.clientY - cy) / (rect.height / 2);
            const tiltX = dy * -12;
            const tiltY = dx * 12;
            card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateZ(8px)`;
            
            let shine = card.querySelector('.card-shine');
            if (!shine) {
                shine = document.createElement('div');
                shine.className = 'card-shine';
                shine.style.cssText = 'position:absolute; inset:0; border-radius:inherit; pointer-events:none; z-index:1; transition:background 0.1s;';
                card.style.position = card.style.position || 'relative';
                card.style.overflow = 'hidden';
                card.appendChild(shine);
            }
            shine.style.background = `radial-gradient(circle at ${(dx+1)*50}% ${(dy+1)*50}%, rgba(255,255,255,0.08) 0%, transparent 60%)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(800px) rotateX(0) rotateY(0) translateZ(0)';
            const shine = card.querySelector('.card-shine');
            if (shine) shine.style.background = 'transparent';
        });
        card.style.transformStyle = 'preserve-3d';
        card.style.transition = 'transform 0.1s, box-shadow 0.1s';
    });
}

function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.transition = 'transform 0.6s cubic-bezier(0.34,1.56,0.64,1), opacity 0.6s cubic-bezier(0.34,1.56,0.64,1)';
                entry.target.style.transform = 'translateY(0) scale(1)';
                entry.target.style.opacity = '1';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.glass-card, .card, .fade-up').forEach(card => {
        if (!card.classList.contains('no-observer')) {
            card.style.transform = 'translateY(60px) scale(0.9)';
            card.style.opacity = '0';
            observer.observe(card);
        }
    });
}

function animateHeroText() {
    const h1 = document.querySelector('.hero-headline, h1.hero-title');
    if (!h1) return;
    const nodes = Array.from(h1.childNodes);
    h1.innerHTML = '';
    h1.style.transformStyle = 'preserve-3d';
    h1.style.perspective = '600px';
    let globalIndex = 0;
    nodes.forEach(node => {
        if (node.nodeType === Node.TEXT_NODE) {
            [...node.textContent].forEach((char) => {
                const span = document.createElement('span');
                span.textContent = char === ' ' ? '\u00A0' : char;
                span.style.cssText = `
                    display:inline-block;
                    opacity:0;
                    transform:translateZ(-200px) rotateY(90deg);
                    animation: charIn 0.6s cubic-bezier(0.34,1.56,0.64,1) ${globalIndex * 0.03}s forwards;
                    will-change: transform, opacity;
                `;
                h1.appendChild(span);
                globalIndex++;
            });
        } else {
            h1.appendChild(node.cloneNode(true));
        }
    });
}

function initMagneticButton() {
    const btn = document.querySelector('.btn-primary.magnetic');
    if (!btn) return;
    document.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dist = Math.hypot(e.clientX - cx, e.clientY - cy);
        if (dist < 80) {
            const dx = (e.clientX - cx) * 0.3;
            const dy = (e.clientY - cy) * 0.3;
            btn.style.transform = `translate(${dx}px, ${dy}px) scale(1.05)`;
        } else {
            btn.style.transform = 'translate(0px, 0px) scale(1)';
        }
    });
    btn.style.transition = 'transform 0.2s cubic-bezier(0.34,1.56,0.64,1)';
}

function initStatsCountUp() {
    if (typeof gsap === 'undefined') return;
    document.querySelectorAll('.stat-number').forEach(el => {
        const target = parseFloat(el.textContent.replace(/,/g, ''));
        if (isNaN(target)) return;
        el.textContent = '0';
        gsap.to(el, {
            innerHTML: target,
            duration: 2,
            ease: "power2.out",
            snap: { innerHTML: 1 },
            onUpdate: function() {
                el.innerHTML = Math.round(this.targets()[0].innerHTML).toLocaleString();
            }
        });
    });
}

function initUploadEntrances() {
    const container = document.querySelector('.upload-container');
    if (!container) return;
    const cards = container.querySelectorAll('.card, .glass-card, form');
    cards.forEach((c, i) => {
        c.style.opacity = '0';
        c.style.transform = 'translateY(40px)';
        c.style.animation = `fadeUp 0.6s cubic-bezier(0.34,1.56,0.64,1) ${i * 0.12}s forwards`;
    });
}

function initReportAnimations() {
    // Fairness Score 3D Flip
    const gaugeCard = document.querySelector('.gauge-card, .score-card');
    if (gaugeCard) {
        gaugeCard.style.opacity = '0';
        gaugeCard.style.transform = 'rotateX(90deg)';
        setTimeout(() => {
            gaugeCard.style.transition = 'transform 0.8s cubic-bezier(0.34,1.56,0.64,1), opacity 0.8s';
            gaugeCard.style.transform = 'rotateX(0deg)';
            gaugeCard.style.opacity = '1';
        }, 300);
        
        // Count up score
        if (typeof gsap !== 'undefined') {
            const scoreVal = gaugeCard.querySelector('.score-value, .gauge-value');
            if (scoreVal) {
                const target = parseFloat(scoreVal.textContent);
                if (!isNaN(target)) {
                    scoreVal.innerHTML = '0';
                    gsap.to(scoreVal, {
                        innerHTML: target,
                        duration: 1.5,
                        ease: "power2.out",
                        snap: { innerHTML: 1 }
                    });
                }
            }
        }
    }

    // Sequential Slide for Metric Cards
    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach((c, i) => {
        c.style.opacity = '0';
        c.style.transform = 'translateX(120px) rotateY(8deg)';
        c.style.transformStyle = 'preserve-3d';
        setTimeout(() => {
            c.style.transition = 'transform 0.8s cubic-bezier(0.34,1.56,0.64,1), opacity 0.8s';
            c.style.transform = 'translateX(0) rotateY(0)';
            c.style.opacity = '1';
        }, 500 + i * 200);
    });
}

function initDropZoneEffects() { document.querySelectorAll('.drop-zone').forEach(zone => { zone.addEventListener('dragenter', () => zone.classList.add('dragover')); zone.addEventListener('dragleave', () => zone.classList.remove('dragover')); zone.addEventListener('drop', () => zone.classList.remove('dragover')); }); }
document.addEventListener('DOMContentLoaded', initDropZoneEffects);
