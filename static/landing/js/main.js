/* ============================================
   SatyaBio Website — Main JavaScript
   Cream/Coral Branding — Knowledge Graph + Transitions
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {
  function waitForGSAP(cb) {
    if (window.gsap && window.ScrollTrigger) {
      cb();
    } else {
      setTimeout(function () { waitForGSAP(cb); }, 50);
    }
  }

  waitForGSAP(function () {
    gsap.registerPlugin(ScrollTrigger);

    initHeroAnimation();
    initScrollReveals();
    initSlideAnimations();
    initNavbar();
    initKnowledgeGraph();
    initThesisGraph();
    initDealsTable();
    initInsightToggles();
    initBarChartAnimations();
    initRadarAnimation();
    initVizTabs();
    initParallaxSections();
    initSectionTransitions();
  });
});

/* ============================================
   Hero Canvas — Live Knowledge Graph (Sleuth-style)
   Light bg, dot grid, labeled nodes, central diamond,
   corner brackets, connection lines
   ============================================ */
function initHeroAnimation() {
  var canvas = document.getElementById('hero-canvas');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var W, H, time = 0;
  var COL = '#C4603C';
  var COL_LIGHT = 'rgba(196,96,60,';

  // Graph data — biopharma targets
  var graphNodes = [
    { label: 'KRAS G12C',  rx: 0.52, ry: 0.28, size: 7 },
    { label: 'EGFR',       rx: 0.30, ry: 0.18, size: 6 },
    { label: 'HER2',       rx: 0.72, ry: 0.22, size: 6 },
    { label: 'PD-L1',      rx: 0.80, ry: 0.45, size: 7 },
    { label: 'VEGF',       rx: 0.65, ry: 0.60, size: 5 },
    { label: 'CD33',       rx: 0.42, ry: 0.68, size: 6 },
    { label: 'FLT3',       rx: 0.22, ry: 0.52, size: 5 },
    { label: 'BTK',        rx: 0.18, ry: 0.35, size: 5 },
    { label: 'BCL-2',      rx: 0.55, ry: 0.82, size: 5 },
    { label: 'GLP-1R',     rx: 0.85, ry: 0.70, size: 6 },
  ];

  // Edges (pairs of node indices)
  var edges = [
    [0,1],[0,2],[0,3],[1,7],[2,3],[3,4],[4,5],[5,6],[6,7],[1,6],[4,9],[5,8],[8,9],[2,4],[0,5]
  ];

  var anim = []; // animated positions

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    W = rect.width; H = rect.height || 500;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // Init animated positions
    if (anim.length === 0) {
      var cx = W * 0.5, cy = H * 0.5;
      anim = graphNodes.map(function (n) {
        return { x: cx, y: cy, tx: n.rx * W, ty: n.ry * H, size: n.size, label: n.label };
      });
    } else {
      anim.forEach(function (a, i) {
        a.tx = graphNodes[i].rx * W;
        a.ty = graphNodes[i].ry * H;
      });
    }
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    time++;

    // Lerp nodes toward targets
    anim.forEach(function (a) {
      a.x = lerp(a.x, a.tx + Math.sin(time * 0.006 + a.tx) * 3, 0.04);
      a.y = lerp(a.y, a.ty + Math.cos(time * 0.008 + a.ty) * 3, 0.04);
    });

    // Dot grid
    var GRID = 24;
    for (var gx = GRID/2; gx < W; gx += GRID) {
      for (var gy = GRID/2; gy < H; gy += GRID) {
        ctx.beginPath();
        ctx.arc(gx, gy, 0.8, 0, Math.PI * 2);
        ctx.fillStyle = COL_LIGHT + '0.12)';
        ctx.fill();
      }
    }

    // Corner bracket decorations
    var BK = 30, BKW = 1.5;
    ctx.strokeStyle = COL_LIGHT + '0.2)';
    ctx.lineWidth = BKW;
    // Top-left
    ctx.beginPath(); ctx.moveTo(15, 15 + BK); ctx.lineTo(15, 15); ctx.lineTo(15 + BK, 15); ctx.stroke();
    // Top-right
    ctx.beginPath(); ctx.moveTo(W - 15 - BK, 15); ctx.lineTo(W - 15, 15); ctx.lineTo(W - 15, 15 + BK); ctx.stroke();
    // Bottom-left
    ctx.beginPath(); ctx.moveTo(15, H - 15 - BK); ctx.lineTo(15, H - 15); ctx.lineTo(15 + BK, H - 15); ctx.stroke();
    // Bottom-right
    ctx.beginPath(); ctx.moveTo(W - 15 - BK, H - 15); ctx.lineTo(W - 15, H - 15); ctx.lineTo(W - 15, H - 15 - BK); ctx.stroke();

    // Draw edges
    edges.forEach(function (e, idx) {
      var a = anim[e[0]], b = anim[e[1]];
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = COL_LIGHT + '0.25)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Pulse traveling along edge
      var frac = ((time * 0.005 + idx * 0.4) % 1);
      var px = lerp(a.x, b.x, frac), py = lerp(a.y, b.y, frac);
      ctx.beginPath();
      ctx.arc(px, py, 1.5, 0, Math.PI * 2);
      ctx.fillStyle = COL_LIGHT + (0.5 * (1 - frac)) + ')';
      ctx.fill();
    });

    // Central diamond (at graph centroid)
    var centX = 0, centY = 0;
    anim.forEach(function (a) { centX += a.x; centY += a.y; });
    centX /= anim.length; centY /= anim.length;
    var ds = 10 + Math.sin(time * 0.02) * 1.5;

    ctx.save();
    ctx.translate(centX, centY);
    ctx.rotate(Math.PI / 4);
    ctx.beginPath();
    ctx.rect(-ds, -ds, ds * 2, ds * 2);
    ctx.fillStyle = COL_LIGHT + '0.12)';
    ctx.fill();
    ctx.strokeStyle = COL;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();

    // Small inner dot
    ctx.beginPath();
    ctx.arc(centX, centY, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = COL;
    ctx.fill();

    // Draw nodes
    anim.forEach(function (node) {
      // Outer glow
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.size + 5, 0, Math.PI * 2);
      ctx.fillStyle = COL_LIGHT + '0.06)';
      ctx.fill();

      // Circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.size, 0, Math.PI * 2);
      ctx.fillStyle = COL_LIGHT + '0.5)';
      ctx.fill();
      ctx.strokeStyle = COL;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label
      ctx.font = '11px Inter, sans-serif';
      ctx.fillStyle = COL_LIGHT + '0.8)';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y - node.size - 8);
    });

    requestAnimationFrame(draw);
  }

  resize(); draw();
  window.addEventListener('resize', resize);

  // Hero text — line by line reveal
  gsap.from('.hero-heading .line', {
    yPercent: 100, opacity: 0, duration: 1, ease: 'power3.out', stagger: 0.15, delay: 0.3
  });
  gsap.from('.hero-description', {
    opacity: 0, y: 35, duration: 0.9, ease: 'power2.out', delay: 0.9
  });
  gsap.from('.hero-buttons', {
    opacity: 0, y: 25, duration: 0.8, ease: 'power2.out', delay: 1.2
  });
}

/* ============================================
   Scroll-Triggered Reveals (fade-up)
   ============================================ */
function initScrollReveals() {
  // [data-animate] elements — scrub-linked smooth reveal
  document.querySelectorAll('[data-animate]:not(.slide-left):not(.slide-right)').forEach(function (el) {
    // Set initial state immediately
    gsap.set(el, { opacity: 0, y: 60 });

    gsap.to(el, {
      opacity: 1,
      y: 0,
      ease: 'none',
      scrollTrigger: {
        trigger: el,
        start: 'top 92%',
        end: 'top 55%',
        scrub: 0.8
      }
    });
  });

  // Stagger children — each child fades up as section scrolls in
  document.querySelectorAll('[data-animate-stagger]').forEach(function (el) {
    var children = Array.from(el.children);
    children.forEach(function (child, i) {
      gsap.set(child, { opacity: 0, y: 40 });
      gsap.to(child, {
        opacity: 1,
        y: 0,
        ease: 'power2.out',
        duration: 0.8,
        scrollTrigger: {
          trigger: el,
          start: 'top 85%',
          once: true
        },
        delay: i * 0.12
      });
    });
  });

  // Whole-section reveals — each major section fades/slides as a block
  document.querySelectorAll('.section-insights, .section-intelligence, .section-platform, .section-testimonials, .section-how-teams, .section-cta').forEach(function (section) {
    var inner = section.querySelector('.container-large') || section.querySelector('.padding-global');
    if (!inner) return;

    gsap.fromTo(inner,
      { opacity: 0, y: 80 },
      {
        opacity: 1,
        y: 0,
        ease: 'none',
        scrollTrigger: {
          trigger: section,
          start: 'top 90%',
          end: 'top 40%',
          scrub: 1
        }
      }
    );
  });
}

/* ============================================
   Slide-In Animations (left/right)
   ============================================ */
function initSlideAnimations() {
  document.querySelectorAll('.slide-left[data-animate]').forEach(function (el) {
    gsap.set(el, { opacity: 0, x: -80 });
    gsap.to(el, {
      opacity: 1,
      x: 0,
      ease: 'none',
      scrollTrigger: {
        trigger: el,
        start: 'top 90%',
        end: 'top 45%',
        scrub: 0.8
      }
    });
  });

  document.querySelectorAll('.slide-right[data-animate]').forEach(function (el) {
    gsap.set(el, { opacity: 0, x: 80 });
    gsap.to(el, {
      opacity: 1,
      x: 0,
      ease: 'none',
      scrollTrigger: {
        trigger: el,
        start: 'top 90%',
        end: 'top 45%',
        scrub: 0.8
      }
    });
  });
}

/* ============================================
   Section Transition Parallax
   ============================================ */
function initSectionTransitions() {
  // Section transitions scale up slightly as you scroll through
  document.querySelectorAll('.section-transition').forEach(function (el) {
    gsap.fromTo(el,
      { scaleY: 0.6, opacity: 0.5 },
      {
        scaleY: 1,
        opacity: 1,
        ease: 'none',
        scrollTrigger: {
          trigger: el,
          start: 'top bottom',
          end: 'bottom 60%',
          scrub: 1
        }
      }
    );
  });

  // Hero heading has a special scrub-linked parallax as you scroll away
  gsap.to('.hero-content', {
    y: -60,
    opacity: 0.3,
    ease: 'none',
    scrollTrigger: {
      trigger: '.section-hero',
      start: 'top top',
      end: 'bottom top',
      scrub: 1
    }
  });

  // Hero SVG also drifts up
  gsap.to('.hero-animation', {
    y: -40,
    opacity: 0.2,
    ease: 'none',
    scrollTrigger: {
      trigger: '.section-hero',
      start: '60% top',
      end: 'bottom top',
      scrub: 1
    }
  });
}

/* ============================================
   Section Parallax (subtle depth)
   ============================================ */
function initParallaxSections() {
  // Parallax on section headings
  document.querySelectorAll('.platform-header h2, .testimonials-header h2, .how-teams-header h2, .cta-content h2').forEach(function (heading) {
    gsap.fromTo(heading,
      { y: 30 },
      {
        y: -15,
        ease: 'none',
        scrollTrigger: {
          trigger: heading,
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1.5
        }
      }
    );
  });

  // CTA glow parallax
  var glow = document.querySelector('.cta-glow');
  if (glow) {
    gsap.fromTo(glow,
      { scale: 0.8, opacity: 0.3 },
      {
        scale: 1.2,
        opacity: 0.7,
        ease: 'none',
        scrollTrigger: {
          trigger: '.section-cta',
          start: 'top bottom',
          end: 'bottom top',
          scrub: 2
        }
      }
    );
  }

  // Intel cards reveal with slight rotation
  document.querySelectorAll('.intel-card').forEach(function (card, i) {
    gsap.fromTo(card,
      { opacity: 0, y: 40, rotateY: 5 },
      {
        opacity: 1,
        y: 0,
        rotateY: 0,
        duration: 0.8,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: card,
          start: 'top 90%',
          once: true
        },
        delay: i * 0.08
      }
    );
  });
}

/* ============================================
   Navbar Scroll Effect
   ============================================ */
function initNavbar() {
  var navbar = document.getElementById('navbar');

  // Smooth navbar background transition
  ScrollTrigger.create({
    start: 60,
    onUpdate: function (self) {
      if (self.scroll() > 60) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    }
  });

  // Mobile menu toggle
  var mobileBtn = document.getElementById('mobile-menu-btn');
  var navMenu = document.getElementById('nav-menu');
  if (mobileBtn) {
    mobileBtn.addEventListener('click', function () {
      navMenu.classList.toggle('is-open');
      mobileBtn.classList.toggle('is-active');
    });
  }
}

/* ============================================
   Insight Card Expand/Collapse
   ============================================ */
function initInsightToggles() {
  document.querySelectorAll('.insight-text h2').forEach(function (heading) {
    heading.style.cursor = 'pointer';
    heading.addEventListener('click', function () {
      var parent = heading.closest('.insight-text');
      toggleInsight(parent.id);
    });
  });
}

window.toggleInsight = function (id) {
  var el = document.getElementById(id);
  if (!el) return;

  var p = el.querySelector('p');
  var icon = el.querySelector('.expand-icon');

  if (el.classList.contains('expanded')) {
    el.classList.remove('expanded');
    gsap.to(p, { height: 0, duration: 0.4, ease: 'power2.inOut' });
    if (icon) gsap.to(icon, { rotation: 0, duration: 0.3 });
  } else {
    el.classList.add('expanded');
    p.style.height = 'auto';
    var naturalHeight = p.offsetHeight;
    p.style.height = '0px';
    gsap.to(p, { height: naturalHeight, duration: 0.5, ease: 'power3.out' });
    if (icon) gsap.to(icon, { rotation: 180, duration: 0.3 });
  }
};

/* ============================================
   Knowledge Graph — Constellation Visualization
   ============================================ */
function initKnowledgeGraph() {
  var canvas = document.getElementById('knowledge-graph');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var W, H;

  // Knowledge graph datasets — real biotech depth
  var datasets = {
    kras: {
      center: { label: 'ADC Landscape', sub: '142 programs · 8 payload classes' },
      nodes: [
        { angle: 0,   dist: 0.32, label: 'Enhertu', sub: 'Daiichi/AZ · T-DXd · $4.1B', size: 15 },
        { angle: 40,  dist: 0.35, label: 'Tubulis', sub: 'Gilead acq. · Novel linker', size: 12 },
        { angle: 80,  dist: 0.28, label: 'Padcev', sub: 'Seagen/Pfizer · EV+pembro', size: 14 },
        { angle: 120, dist: 0.36, label: 'CrossBridge', sub: 'Lilly · Bispecific ADC', size: 10 },
        { angle: 160, dist: 0.30, label: 'Midekin', sub: 'Roche · Topo-I payload', size: 11 },
        { angle: 200, dist: 0.34, label: 'Kelun-Biotech', sub: 'Merck · China out-license', size: 12 },
        { angle: 240, dist: 0.32, label: 'Dato-DXd', sub: 'AZ · TROP2 · Phase III', size: 13 },
        { angle: 300, dist: 0.28, label: 'RemeGen', sub: 'Disitamab · HER2 China', size: 10 },
      ]
    },
    ms: {
      center: { label: 'Obesity / GLP-1', sub: 'Amylin · dual/triple agonists' },
      nodes: [
        { angle: 0,   dist: 0.30, label: 'Viking VKTX', sub: 'VK2735 · dual GLP/GIP', size: 14 },
        { angle: 45,  dist: 0.34, label: 'Kailera', sub: 'KAI-9145 · oral amylin', size: 13 },
        { angle: 90,  dist: 0.28, label: 'Structure', sub: 'GSBR-1290 · oral GLP-1', size: 12 },
        { angle: 135, dist: 0.36, label: 'Retatrutide', sub: 'Lilly · triple agonist', size: 11 },
        { angle: 180, dist: 0.32, label: 'Orforglipron', sub: 'Lilly · oral non-peptide', size: 12 },
        { angle: 225, dist: 0.30, label: 'Survodutide', sub: 'BI/Zealand · GCG/GLP', size: 11 },
        { angle: 270, dist: 0.34, label: 'CagriSema', sub: 'Novo · sema + cagri', size: 13 },
        { angle: 315, dist: 0.28, label: 'Pemvidutide', sub: 'Altimmune · GLP/GCG', size: 10 },
      ]
    },
    glp1: {
      center: { label: 'China Biopharma', sub: '60+ cross-border deals in 2025' },
      nodes: [
        { angle: 0,   dist: 0.32, label: 'Kelun-Biotech', sub: 'ADC platform · Merck deal', size: 14 },
        { angle: 50,  dist: 0.30, label: 'Legend Bio', sub: 'CART · Carvykti · J&J', size: 13 },
        { angle: 100, dist: 0.35, label: 'Harbour BioMed', sub: 'Bispecifics · AbbVie', size: 11 },
        { angle: 150, dist: 0.28, label: 'Gracell', sub: 'Cell therapy · AZ acq.', size: 12 },
        { angle: 200, dist: 0.33, label: 'BeiGene', sub: 'Brukinsa · global IO', size: 15 },
        { angle: 250, dist: 0.30, label: 'Zymeworks', sub: 'Bispecific ADC · HER2', size: 10 },
        { angle: 310, dist: 0.32, label: 'Hengrui', sub: 'SHR-A1921 · ADC pipeline', size: 11 },
      ]
    }
  };

  var currentDataset = 'kras';
  var mouseX = -1, mouseY = -1;
  var particles = [];
  var animNodes = [];
  var time = 0;

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    W = rect.width; H = rect.height || 450;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildNodes();
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  function buildNodes() {
    var data = datasets[currentDataset];
    if (!data || !data.center) return;
    var cx = W * 0.5, cy = H * 0.5, radius = Math.min(W, H) * 0.38;
    var targets = data.nodes.map(function (n) {
      var rad = (n.angle * Math.PI) / 180, r = radius * (n.dist / 0.36);
      return { x: cx + Math.cos(rad) * r, y: cy + Math.sin(rad) * r, size: n.size, label: n.label, sub: n.sub || '' };
    });
    if (animNodes.length !== targets.length) {
      animNodes = targets.map(function (t) {
        return { x: cx, y: cy, size: 0, label: t.label, sub: t.sub, tx: t.x, ty: t.y, ts: t.size };
      });
    } else {
      animNodes.forEach(function (n, i) { n.tx = targets[i].x; n.ty = targets[i].y; n.ts = targets[i].size; n.label = targets[i].label; n.sub = targets[i].sub; });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H); time++;
    var data = datasets[currentDataset];
    if (!data || !data.center) { requestAnimationFrame(draw); return; }
    var cx = W * 0.5, cy = H * 0.5;
    animNodes.forEach(function (n) { n.x = lerp(n.x, n.tx, 0.06); n.y = lerp(n.y, n.ty, 0.06); n.size = lerp(n.size || 0, n.ts, 0.08); });

    // Background grid
    for (var gx = 16; gx < W; gx += 32) for (var gy = 16; gy < H; gy += 32) {
      var dC = Math.sqrt((gx-cx)*(gx-cx)+(gy-cy)*(gy-cy));
      ctx.beginPath(); ctx.arc(gx, gy, 0.7, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(196,96,60,' + (0.05 + Math.max(0, 1 - dC/(Math.min(W,H)*0.45))*0.07) + ')'; ctx.fill();
    }

    // Spokes from center to nodes
    animNodes.forEach(function (node, idx) {
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(node.x, node.y);
      ctx.strokeStyle = 'rgba(196,96,60,0.25)'; ctx.lineWidth = 1; ctx.stroke();
      var pf = ((time * 0.008 + idx * 0.3) % 1);
      ctx.beginPath(); ctx.arc(lerp(cx, node.x, pf), lerp(cy, node.y, pf), 2, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(196,96,60,' + (0.6*(1-pf)) + ')'; ctx.fill();
    });

    // Adjacent node connections
    for (var i = 0; i < animNodes.length; i++) {
      var j = (i+1) % animNodes.length;
      var d = Math.hypot(animNodes[i].x-animNodes[j].x, animNodes[i].y-animNodes[j].y);
      if (d < Math.min(W,H)*0.35) { ctx.beginPath(); ctx.moveTo(animNodes[i].x, animNodes[i].y); ctx.lineTo(animNodes[j].x, animNodes[j].y); ctx.strokeStyle='rgba(196,96,60,0.08)'; ctx.lineWidth=0.5; ctx.stroke(); }
    }

    // Center node
    var cp = 1 + Math.sin(time*0.03)*0.08, cr = 22*cp;
    var grad = ctx.createRadialGradient(cx,cy,cr,cx,cy,cr*2.5);
    grad.addColorStop(0,'rgba(196,96,60,0.12)'); grad.addColorStop(1,'rgba(196,96,60,0)');
    ctx.beginPath(); ctx.arc(cx,cy,cr*2.5,0,Math.PI*2); ctx.fillStyle=grad; ctx.fill();
    ctx.beginPath(); ctx.arc(cx,cy,cr,0,Math.PI*2); ctx.fillStyle='rgba(196,96,60,0.15)'; ctx.fill();
    ctx.strokeStyle='#C4603C'; ctx.lineWidth=2; ctx.stroke();
    ctx.font='bold 13px Inter,sans-serif'; ctx.fillStyle='rgba(250,248,244,0.95)'; ctx.textAlign='center';
    ctx.fillText(data.center.label, cx, cy-4);
    ctx.font='10px Inter,sans-serif'; ctx.fillStyle='rgba(196,96,60,0.8)'; ctx.fillText(data.center.sub, cx, cy+12);

    // Outer nodes
    animNodes.forEach(function (node) {
      if (node.size < 1) return;
      var hov = mouseX > 0 && Math.hypot(node.x-mouseX, node.y-mouseY) < node.size+15;
      var r = node.size + (hov?3:0);
      ctx.beginPath(); ctx.arc(node.x,node.y,r+8,0,Math.PI*2); ctx.fillStyle='rgba(196,96,60,'+(hov?0.1:0.03)+')'; ctx.fill();
      ctx.beginPath(); ctx.arc(node.x,node.y,r,0,Math.PI*2); ctx.fillStyle='rgba(196,96,60,'+(hov?0.2:0.08)+')'; ctx.fill();
      ctx.strokeStyle='rgba(196,96,60,'+(hov?0.8:0.45)+')'; ctx.lineWidth=hov?1.5:1; ctx.stroke();
      ctx.beginPath(); ctx.arc(node.x,node.y,2.5,0,Math.PI*2); ctx.fillStyle='#C4603C'; ctx.fill();
      ctx.font=(hov?'bold ':'')+' 11px Inter,sans-serif'; ctx.fillStyle='rgba(250,248,244,'+(hov?0.95:0.7)+')'; ctx.textAlign='center';
      ctx.fillText(node.label, node.x, node.y+r+16);
      if (node.sub) { ctx.font='9px Inter,sans-serif'; ctx.fillStyle='rgba(250,248,244,'+(hov?0.6:0.35)+')'; ctx.fillText(node.sub, node.x, node.y+r+28); }
    });

    // Particles from center
    particles = particles.filter(function(p) { p.x+=p.vx; p.y+=p.vy; p.life--; ctx.beginPath(); ctx.arc(p.x,p.y,1,0,Math.PI*2); ctx.fillStyle='rgba(196,96,60,'+((p.life/p.maxLife)*0.4)+')'; ctx.fill(); return p.life>0; });
    if (Math.random()<0.05) { var a=Math.random()*Math.PI*2, sp=0.15+Math.random()*0.3; particles.push({x:cx,y:cy,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,life:150+Math.random()*150,maxLife:150+Math.random()*150}); }
    requestAnimationFrame(draw);
  }

  canvas.addEventListener('mousemove', function(e){var r=canvas.getBoundingClientRect();mouseX=e.clientX-r.left;mouseY=e.clientY-r.top;});
  canvas.addEventListener('mouseleave', function(){mouseX=-1;mouseY=-1;});
  resize(); draw(); window.addEventListener('resize', resize);
  window.switchDataset = function(key){if(datasets[key]&&datasets[key].center){currentDataset=key;animNodes=[];buildNodes();}};
}

/* ============================================
   Bar Chart Animations
   ============================================ */
function initBarChartAnimations() {
  document.querySelectorAll('.bar-fill').forEach(function (bar, i) {
    var targetWidth = bar.dataset.width || '50%';

    ScrollTrigger.create({
      trigger: bar,
      start: 'top 92%',
      once: true,
      onEnter: function () {
        gsap.to(bar, {
          width: targetWidth,
          duration: 1.2 + i * 0.1,
          ease: 'power3.out',
          delay: i * 0.08
        });
      }
    });
  });
}

/* ============================================
   Radar Chart Animation
   ============================================ */
function initRadarAnimation() {
  document.querySelectorAll('.radar-series').forEach(function (series) {
    ScrollTrigger.create({
      trigger: series,
      start: 'top 92%',
      once: true,
      onEnter: function () {
        series.classList.add('animate');
      }
    });
  });
}

/* ============================================
   Platform Viz Tab Switching
   ============================================ */
function initVizTabs() {
  var tabs = document.querySelectorAll('.viz-tab');
  if (!tabs.length) return;

  var tabKeys = ['kras', 'ms', 'glp1'];
  var currentIndex = 0;
  var autoInterval;

  function activateTab(index) {
    tabs.forEach(function (t) { t.classList.remove('active'); });
    tabs[index].classList.add('active');
    if (window.switchDataset) window.switchDataset(tabKeys[index]);
    currentIndex = index;
  }

  tabs.forEach(function (tab, i) {
    tab.addEventListener('click', function () {
      activateTab(i);
      clearInterval(autoInterval);
      startAutoCycle();
    });
  });

  function startAutoCycle() {
    autoInterval = setInterval(function () {
      activateTab((currentIndex + 1) % tabKeys.length);
    }, 5000);
  }

  startAutoCycle();
}

/* ============================================
   Thesis Graph — Mini knowledge graph for insight #3
   ============================================ */
function initThesisGraph() {
  var canvas = document.getElementById('thesis-graph');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var W, H, time = 0;
  var COL = 'rgba(196,96,60,';

  var nodes = [
    { label: 'Your thesis',   rx: 0.50, ry: 0.42, size: 9, center: true },
    { label: 'Targets',       rx: 0.25, ry: 0.20, size: 5 },
    { label: 'Trials',        rx: 0.75, ry: 0.18, size: 5 },
    { label: 'Competitors',   rx: 0.82, ry: 0.55, size: 5 },
    { label: 'Deal terms',    rx: 0.68, ry: 0.80, size: 5 },
    { label: 'IP landscape',  rx: 0.32, ry: 0.78, size: 5 },
    { label: 'Mechanisms',    rx: 0.15, ry: 0.52, size: 5 },
  ];
  var edges = [[0,1],[0,2],[0,3],[0,4],[0,5],[0,6],[1,2],[2,3],[3,4],[4,5],[5,6],[6,1]];
  var anim = [];

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    W = rect.width; H = rect.height;
    if (!W || !H) return;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var cx = W / 2, cy = H / 2;
    if (anim.length === 0) {
      anim = nodes.map(function (n) {
        return { x: cx, y: cy, tx: n.rx * W, ty: n.ry * H, size: n.size, label: n.label, center: n.center };
      });
    } else {
      anim.forEach(function (a, i) { a.tx = nodes[i].rx * W; a.ty = nodes[i].ry * H; });
    }
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  function draw() {
    if (!W || !H) { resize(); }
    ctx.clearRect(0, 0, W, H);
    time++;

    anim.forEach(function (a) {
      a.x = lerp(a.x, a.tx + Math.sin(time * 0.007 + a.tx) * 4, 0.04);
      a.y = lerp(a.y, a.ty + Math.cos(time * 0.009 + a.ty) * 4, 0.04);
    });

    // Edges
    edges.forEach(function (e, idx) {
      var a = anim[e[0]], b = anim[e[1]];
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = COL + '0.2)'; ctx.lineWidth = 0.8; ctx.stroke();
      var frac = ((time * 0.006 + idx * 0.35) % 1);
      ctx.beginPath(); ctx.arc(lerp(a.x, b.x, frac), lerp(a.y, b.y, frac), 1.5, 0, Math.PI * 2);
      ctx.fillStyle = COL + (0.5 * (1 - frac)) + ')'; ctx.fill();
    });

    // Nodes
    anim.forEach(function (node) {
      var r = node.size + (node.center ? Math.sin(time * 0.03) * 1.5 : 0);
      ctx.beginPath(); ctx.arc(node.x, node.y, r + 6, 0, Math.PI * 2);
      ctx.fillStyle = COL + (node.center ? '0.08' : '0.04') + ')'; ctx.fill();
      ctx.beginPath(); ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fillStyle = COL + (node.center ? '0.35' : '0.25') + ')'; ctx.fill();
      ctx.strokeStyle = '#C4603C'; ctx.lineWidth = node.center ? 1.5 : 0.8; ctx.stroke();
      ctx.font = (node.center ? 'bold 12px' : '10px') + ' Inter, sans-serif';
      ctx.fillStyle = COL + (node.center ? '0.9' : '0.7') + ')';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y - r - 8);
    });

    requestAnimationFrame(draw);
  }

  resize(); draw();
  window.addEventListener('resize', resize);
}

/* ============================================
   Deals Table — Animated M&A table for insight #2
   ============================================ */
function initDealsTable() {
  var canvas = document.getElementById('deals-table-canvas');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var W, H, time = 0;
  var COL = '#C4603C';

  var deals = [
    { acquirer: 'Pfizer', target: 'Seagen', value: '$43B', type: 'ADC platform' },
    { acquirer: 'AbbVie', target: 'ImmunoGen', value: '$10.1B', type: 'ADC (Elahere)' },
    { acquirer: 'Lilly', target: 'Kelonia', value: '$3.25B', type: 'In vivo CAR-T' },
    { acquirer: 'Novartis', target: 'Chinook', value: '$3.2B', type: 'Nephrology' },
    { acquirer: 'Roche', target: 'Carmot Tx', value: '$2.7B', type: 'GLP-1 oral' },
    { acquirer: 'AZ', target: 'Gracell Bio', value: '$1.2B', type: 'CAR-T (China)' },
    { acquirer: 'Merck', target: 'Kelun-Bio', value: '~$1.4B', type: 'ADC license' },
    { acquirer: 'Amneal', target: 'Kashiv Bio', value: '$1.1B', type: 'Biosimilars' },
  ];

  var visibleRows = 0;
  var scanY = 0;

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    W = rect.width; H = rect.height;
    if (!W || !H) return;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function draw() {
    if (!W || !H) { resize(); }
    ctx.clearRect(0, 0, W, H);
    time++;

    var pad = 16;
    var rowH = 28;
    var headerY = pad + 20;
    var startY = headerY + 18;

    // Title
    ctx.font = 'bold 11px Inter, sans-serif';
    ctx.fillStyle = 'rgba(90,86,80,0.9)';
    ctx.textAlign = 'left';
    ctx.fillText('Recent Biopharma M&A (2025-26)', pad, pad + 8);

    // Column headers
    ctx.font = '9px Inter, sans-serif';
    ctx.fillStyle = 'rgba(139,134,128,0.7)';
    ctx.fillText('ACQUIRER', pad, headerY);
    ctx.fillText('TARGET', pad + W * 0.25, headerY);
    ctx.fillText('VALUE', pad + W * 0.55, headerY);
    ctx.fillText('MODALITY', pad + W * 0.7, headerY);

    // Header line
    ctx.beginPath();
    ctx.moveTo(pad, headerY + 6);
    ctx.lineTo(W - pad, headerY + 6);
    ctx.strokeStyle = 'rgba(232,226,218,0.6)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Animate rows appearing
    if (visibleRows < deals.length) {
      if (time % 20 === 0) visibleRows++;
    }

    // Draw rows
    for (var i = 0; i < Math.min(visibleRows, deals.length); i++) {
      var y = startY + i * rowH;
      if (y > H - 20) break;

      var d = deals[i];
      var age = (visibleRows - i) / deals.length;
      var alpha = Math.min(1, age * 2);

      // Row bg on hover-like alternation
      if (i % 2 === 0) {
        ctx.fillStyle = 'rgba(196,96,60,0.03)';
        ctx.fillRect(pad - 4, y - 10, W - pad * 2 + 8, rowH);
      }

      ctx.font = '11px Inter, sans-serif';
      ctx.fillStyle = 'rgba(90,86,80,' + (alpha * 0.85) + ')';
      ctx.textAlign = 'left';
      ctx.fillText(d.acquirer, pad, y + 4);

      ctx.fillStyle = 'rgba(90,86,80,' + (alpha * 0.7) + ')';
      ctx.fillText(d.target, pad + W * 0.25, y + 4);

      ctx.font = 'bold 11px Inter, sans-serif';
      ctx.fillStyle = 'rgba(196,96,60,' + alpha + ')';
      ctx.fillText(d.value, pad + W * 0.55, y + 4);

      ctx.font = '9px Inter, sans-serif';
      ctx.fillStyle = 'rgba(139,134,128,' + (alpha * 0.6) + ')';
      ctx.fillText(d.type, pad + W * 0.7, y + 4);
    }

    // Scanning line animation
    scanY = (time * 0.5) % (H - startY);
    var scanAlpha = 0.12 + Math.sin(time * 0.05) * 0.05;
    ctx.beginPath();
    ctx.moveTo(pad, startY + scanY);
    ctx.lineTo(W - pad, startY + scanY);
    ctx.strokeStyle = 'rgba(196,96,60,' + scanAlpha + ')';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Pulsing dot at end of scan line
    ctx.beginPath();
    ctx.arc(W - pad, startY + scanY, 2, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(196,96,60,' + (scanAlpha * 3) + ')';
    ctx.fill();

    requestAnimationFrame(draw);
  }

  resize(); draw();
  window.addEventListener('resize', resize);
}

/* ============================================
   Email Gate — intercept intel card clicks
   ============================================ */
(function () {
  var currentCardTitle = '';

  // Intercept all intel card clicks
  document.addEventListener('click', function (e) {
    var card = e.target.closest('.intel-card');
    if (card) {
      e.preventDefault();
      currentCardTitle = (card.querySelector('h4') || {}).textContent || 'Analysis';
      openEmailModal();
    }

    // Backdrop click closes
    if (e.target.classList.contains('email-modal-backdrop')) {
      closeEmailModal();
    }
  });

  window.openEmailModal = function () {
    var modal = document.getElementById('email-modal');
    if (modal) modal.style.display = 'flex';
  };

  window.closeEmailModal = function () {
    var modal = document.getElementById('email-modal');
    if (modal) modal.style.display = 'none';
  };

  window.handleEmailSubmit = function (e) {
    e.preventDefault();
    var form = e.target;
    var data = {
      name: form.name.value,
      email: form.email.value,
      company: form.company.value,
      report: currentCardTitle,
      timestamp: new Date().toISOString()
    };

    // Store locally (you can replace with API call later)
    var leads = JSON.parse(localStorage.getItem('satyabio_leads') || '[]');
    leads.push(data);
    localStorage.setItem('satyabio_leads', JSON.stringify(leads));

    // Show thank you
    var content = document.querySelector('.email-modal-content');
    content.innerHTML = '<div style="text-align:center;padding:2rem 0;">' +
      '<div style="font-size:2rem;margin-bottom:1rem;">&#10003;</div>' +
      '<h3 style="margin-bottom:0.5rem;">Thank you, ' + data.name.split(' ')[0] + '</h3>' +
      '<p style="color:var(--color-text-mid);font-size:14px;">We\'ll send the <strong>' + currentCardTitle.substring(0, 50) + '</strong> report to <strong>' + data.email + '</strong> shortly.</p>' +
      '<button onclick="closeEmailModal()" class="btn btn-primary" style="margin-top:1.5rem;"><span>Close</span></button>' +
      '</div>';

    console.log('Lead captured:', data);
  };

  // Escape key closes modal
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeEmailModal();
  });
})();
