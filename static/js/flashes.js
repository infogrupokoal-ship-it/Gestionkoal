(function(){
  function ready(fn){
    if(document.readyState !== 'loading'){ fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }
  ready(function(){
    try{
      const colors = {info:'#2d7ef7', error:'#d9534f', warning:'#f0ad4e', success:'#5cb85c'};
      document.querySelectorAll('.toast').forEach(function(t){
        const cls = Array.from(t.classList).find(function(c){ return Object.prototype.hasOwnProperty.call(colors, c); });
        t.style.backgroundColor = colors[cls] || colors.info;
        setTimeout(function(){ t.style.transition='opacity .4s'; t.style.opacity='0'; setTimeout(function(){ t.remove(); }, 400); }, 3500);
      });
    }catch(e){}
  });
})();

