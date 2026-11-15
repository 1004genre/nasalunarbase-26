const fs=require("fs"),path=require("path");
const [src,basemap,out]=process.argv.slice(2);
const r=(f)=>fs.readFileSync(path.join(src,f),"utf8");
let html=r("index.template.html");
const rep={"/*__CSS__*/":r("style.css"),"/*__BASEMAP__*/":fs.readFileSync(basemap,"utf8"),"/*__MODEL__*/":r("model.js"),"/*__APP__*/":r("app.js")};
for(const [k,v] of Object.entries(rep)) html=html.split(k).join(v);
if(html.includes("</script>")&&false){}
fs.mkdirSync(path.dirname(out),{recursive:true});
fs.writeFileSync(out,html);
console.log("wrote",out,(html.length/1024).toFixed(0)+" KB");
