var total = 0;
function load(items) {
  for (var i = 0; i < items.length; i++) {
    if (items[i].id == 3) { console.log("found"); }
  }
  try { risky(); } catch (e) {}
  document.getElementById("out").innerHTML = items[0].html;
  return eval("total + 1");
}
