/**
 * Vantix Neural Map Visualizer
 * High-performance Canvas-based Graph Rendering for Fraud Rings.
 */
class NeuralMap {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.nodes = [];
        this.links = [];
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.init();
    }

    init() {
        // Generate a simulated fraud ring cluster
        const centerX = this.width / 2;
        const centerY = this.height / 2;
        
        // Root node (The fraud ring epicenter)
        this.nodes.push({ id: 'root', x: centerX, y: centerY, r: 10, color: '#f43f5e', label: 'Fraud Epicenter', pulse: 0 });
        
        for (let i = 0; i < 8; i++) {
            const angle = (i / 8) * Math.PI * 2;
            const dist = 120 + Math.random() * 40;
            const node = {
                id: `node_${i}`,
                x: centerX + Math.cos(angle) * dist,
                y: centerY + Math.sin(angle) * dist,
                r: 6,
                color: '#14b8a6',
                label: `Identity CLS_${i}`
            };
            this.nodes.push(node);
            this.links.push({ source: 'root', target: node.id });
            
            // Sub-nodes
            for (let j = 0; j < 2; j++) {
                const subAngle = angle + (j - 0.5) * 0.5;
                const subDist = dist + 60;
                const subNode = {
                    id: `node_${i}_${j}`,
                    x: centerX + Math.cos(subAngle) * subDist,
                    y: centerY + Math.sin(subAngle) * subDist,
                    r: 4,
                    color: '#94a3b8',
                    label: `Signal_${i}_${j}`
                };
                this.nodes.push(subNode);
                this.links.push({ source: node.id, target: subNode.id });
            }
        }
        
        this.animate();
    }

    draw() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        // Draw Links
        this.ctx.beginPath();
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        this.ctx.lineWidth = 1;
        this.links.forEach(link => {
            const s = this.nodes.find(n => n.id === link.source);
            const t = this.nodes.find(n => n.id === link.target);
            if (s && t) {
                this.ctx.moveTo(s.x, s.y);
                this.ctx.lineTo(t.x, t.y);
            }
        });
        this.ctx.stroke();
        
        // Draw Nodes
        this.nodes.forEach(node => {
            // Pulse effect for root
            if (node.id === 'root') {
                node.pulse += 0.05;
                const pulseR = node.r + Math.sin(node.pulse) * 4;
                this.ctx.shadowBlur = 20;
                this.ctx.shadowColor = node.color;
                this.ctx.beginPath();
                this.ctx.fillStyle = 'rgba(244, 63, 94, 0.2)';
                this.ctx.arc(node.x, node.y, pulseR + 10, 0, Math.PI * 2);
                this.ctx.fill();
            } else {
                this.ctx.shadowBlur = 0;
            }
            
            this.ctx.beginPath();
            this.ctx.fillStyle = node.color;
            this.ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
            this.ctx.fill();
            
            // Labels for large nodes
            if (node.r > 5) {
                this.ctx.fillStyle = '#94a3b8';
                this.ctx.font = '10px JetBrains Mono';
                this.ctx.fillText(node.label, node.x + 12, node.y + 4);
            }
        });
    }

    animate() {
        this.draw();
        requestAnimationFrame(() => this.animate());
    }
}
