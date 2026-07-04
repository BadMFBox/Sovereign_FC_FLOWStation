console.log('FlowStation UI placeholder');
window.addEventListener('DOMContentLoaded', function(){
  const status = document.getElementById('status');
  if(status) status.innerText = 'UI placeholder loaded at ' + new Date().toISOString();
});
