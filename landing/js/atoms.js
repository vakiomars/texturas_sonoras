(function(){
  var canvas = document.getElementById('atoms');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
  }
  resize();

  var N = 180;
  var particles = [];
  var BOND_DIST = 90;
  var COLORS_CHAOS = [[34,211,238],[20,180,210],[60,220,240]];
  var COLORS_ORDER = [[245,158,11],[220,130,30],[34,211,238]];
  var time = 0;
  var CYCLE = 400;
  var TRANS = 100;

  function W(){ return canvas.width; }
  function H(){ return canvas.height; }

  for (var i = 0; i < N; i++) {
    particles.push({
      x: Math.random() * 800,
      y: Math.random() * 800,
      vx: (Math.random()-0.5)*2,
      vy: (Math.random()-0.5)*2,
      size: 2 + Math.random()*3,
      orbit: 6 + Math.random()*8,
      orbitSpeed: 0.02 + Math.random()*0.03,
      orbitPhase: Math.random()*Math.PI*2,
      colorIdx: Math.floor(Math.random()*3)
    });
  }

  function getBlend(t){
    var pos = t % CYCLE;
    if(pos < CYCLE*0.35 - TRANS/2) return 0;
    if(pos < CYCLE*0.35 + TRANS/2){
      var p=(pos-(CYCLE*0.35-TRANS/2))/TRANS;
      return p*p*(3-2*p);
    }
    if(pos < CYCLE*0.75 - TRANS/2) return 1;
    if(pos < CYCLE*0.75 + TRANS/2){
      var p=(pos-(CYCLE*0.75-TRANS/2))/TRANS;
      return 1-p*p*(3-2*p);
    }
    return 0;
  }

  function lerp(a,b,t){ return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t]; }

  function flowTarget(px,py,t){
    var cx=W()*0.5, cy=H()*0.5;
    var angle=Math.atan2(py-cy,px-cx);
    var dist=Math.sqrt((px-cx)*(px-cx)+(py-cy)*(py-cy));
    var maxR=Math.min(W(),H())*0.38;
    var spiral=angle+0.04+Math.sin(t*0.005+dist*0.002)*0.4;
    var r=Math.min(dist,maxR)*0.97;
    return {x:cx+Math.cos(spiral)*r, y:cy+Math.sin(spiral)*r};
  }

  function draw(){
    ctx.fillStyle='#0B1020';
    ctx.fillRect(0,0,W(),H());

    var blend=getBlend(time);

    for(var i=0;i<N;i++){
      var p=particles[i];
      var flow=flowTarget(p.x,p.y,time);
      var chaosVx=Math.sin(time*0.012+i*0.7)*1.8+(Math.random()-0.5)*0.6;
      var chaosVy=Math.cos(time*0.01+i*0.9)*1.8+(Math.random()-0.5)*0.6;
      var orderVx=(flow.x-p.x)*0.018;
      var orderVy=(flow.y-p.y)*0.018;
      p.vx=chaosVx*(1-blend)+orderVx*blend;
      p.vy=chaosVy*(1-blend)+orderVy*blend;
      p.x+=p.vx; p.y+=p.vy;
      if(p.x<-20)p.x=W()+20; if(p.x>W()+20)p.x=-20;
      if(p.y<-20)p.y=H()+20; if(p.y>H()+20)p.y=-20;
    }

    for(var i=0;i<N;i++){
      for(var j=i+1;j<N;j++){
        var a=particles[i],b=particles[j];
        var dx=a.x-b.x,dy=a.y-b.y;
        var dist=Math.sqrt(dx*dx+dy*dy);
        var threshold=BOND_DIST+blend*30;
        if(dist<threshold){
          var alpha=(1-dist/threshold)*(0.06+blend*0.12);
          ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y);
          ctx.strokeStyle=blend>0.5?'rgba(245,158,11,'+alpha*0.6+')':'rgba(34,211,238,'+alpha+')';
          ctx.lineWidth=0.6; ctx.stroke();
        }
      }
    }

    for(var i=0;i<N;i++){
      var p=particles[i];
      var col=lerp(COLORS_CHAOS[p.colorIdx],COLORS_ORDER[p.colorIdx],blend);
      var orbitAngle=time*p.orbitSpeed+p.orbitPhase;
      var orbitR=p.orbit*(0.7+blend*0.5);
      var orbitAlpha=0.08+blend*0.15;

      ctx.beginPath();
      ctx.ellipse(p.x,p.y,orbitR,orbitR*0.4,orbitAngle*0.3,0,Math.PI*2);
      ctx.strokeStyle='rgba('+~~col[0]+','+~~col[1]+','+~~col[2]+','+orbitAlpha+')';
      ctx.lineWidth=0.5; ctx.stroke();

      var ex=p.x+Math.cos(orbitAngle)*orbitR;
      var ey=p.y+Math.sin(orbitAngle)*orbitR*0.4;
      ctx.beginPath(); ctx.arc(ex,ey,1,0,Math.PI*2);
      ctx.fillStyle='rgba('+~~col[0]+','+~~col[1]+','+~~col[2]+','+(0.3+blend*0.3)+')';
      ctx.fill();

      var coreAlpha=0.5+blend*0.4;
      var glow=p.size+2;
      var grad=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,glow);
      grad.addColorStop(0,'rgba('+~~col[0]+','+~~col[1]+','+~~col[2]+','+coreAlpha+')');
      grad.addColorStop(0.4,'rgba('+~~col[0]+','+~~col[1]+','+~~col[2]+','+coreAlpha*0.4+')');
      grad.addColorStop(1,'rgba('+~~col[0]+','+~~col[1]+','+~~col[2]+',0)');
      ctx.beginPath(); ctx.arc(p.x,p.y,glow,0,Math.PI*2);
      ctx.fillStyle=grad; ctx.fill();

      ctx.beginPath(); ctx.arc(p.x,p.y,p.size*0.6,0,Math.PI*2);
      ctx.fillStyle='rgba('+Math.min(255,~~col[0]+60)+','+Math.min(255,~~col[1]+60)+','+Math.min(255,~~col[2]+60)+','+coreAlpha+')';
      ctx.fill();
    }

    if(blend>0.4){
      var cx=W()*0.5,cy=H()*0.5,a=(blend-0.4)*0.06;
      var grad=ctx.createRadialGradient(cx,cy,0,cx,cy,100);
      grad.addColorStop(0,'rgba(245,158,11,'+a+')');
      grad.addColorStop(1,'rgba(245,158,11,0)');
      ctx.fillStyle=grad; ctx.fillRect(cx-100,cy-100,200,200);
    }

    time++;
    requestAnimationFrame(draw);
  }

  draw();
  window.addEventListener('resize',resize);
})();
