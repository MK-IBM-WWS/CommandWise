"use strict";
const $ = id => document.getElementById(id);
const key = "linux-rag-kt1-demo-v1";
const labels = {debian:"Debian",ubuntu:"Ubuntu",fedora:"Fedora",arch:"Arch Linux"};
const releases = {debian:["13","12"],ubuntu:["24.04"],fedora:["версия из будущего корпуса"],arch:["snapshot из будущего корпуса"]};
let chats=[], activeId, timer=null;
try { const value=JSON.parse(localStorage.getItem(key)||"[]"); if(Array.isArray(value)) chats=value.filter(c=>c&&typeof c.id==="string"&&labels[c.distribution]&&typeof c.release==="string"&&Array.isArray(c.messages)); } catch {}
function save(){try{localStorage.setItem(key,JSON.stringify(chats));}catch{$("status").textContent="Хранилище недоступно: демо-история останется до закрытия страницы.";}}
function active(){return chats.find(c=>c.id===activeId);}
function create(distribution="debian",release="13"){const c={id:crypto.randomUUID?crypto.randomUUID():String(Date.now()),distribution,release,title:"Новый чат",messages:[]};chats.unshift(c);activeId=c.id;save();render();}
function node(tag,text,cls){const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;}
function render(){const c=active();$("title").textContent=c.title;$("target").textContent=labels[c.distribution]+" · "+c.release+" · demo";$("chats").replaceChildren();for(const item of chats){const b=node("button",item.title);b.type="button";b.setAttribute("aria-current",String(item.id===activeId));b.append(node("small",labels[item.distribution]+" · "+item.release));b.onclick=()=>{stop();activeId=item.id;render();};$("chats").append(b);}$("messages").replaceChildren();for(const m of c.messages){const article=node("article","","message "+m.role);article.append(node("h3",m.role==="user"?"Вы":"Помощник · mock"),node("div",m.text));if(m.code)article.append(node("pre",m.code));if(m.source){const b=node("button","[1] find · SIZE / PATH · открыть фрагмент","source");b.type="button";b.onclick=showSource;article.append(b);}if(m.status&&m.status!=="completed")article.append(node("p",{streaming:"Демонстрационное появление текста…",cancelled:"Ответ остановлен",error:"Демонстрационная ошибка модели"}[m.status]||m.status,"state"));$("messages").append(article);}$("send").disabled=timer!==null;$("stop").hidden=timer===null;$("sample").disabled=timer!==null;$("unknown").disabled=timer!==null;$("simulate-error").disabled=timer!==null;}
function stop(){if(timer!==null){clearInterval(timer);timer=null;const m=active().messages.at(-1);if(m&&m.status==="streaming")m.status="cancelled";save();render();$("status").textContent="Ответ остановлен. Можно задать следующий вопрос.";}}
function send(text,error=false){text=text.trim();if(!text||timer!==null)return;if(text.length>4000){$("status").textContent="Вопрос должен содержать не более 4000 символов.";return;}const c=active();if(c.messages.length===0)c.title=text.slice(0,44);c.messages.push({role:"user",text});const m={role:"assistant",text:"",status:error?"error":"streaming"};c.messages.push(m);$("question").value="";let answer,code,source;
if(error){m.text="Не удалось получить ответ модели. Попробуйте отправить вопрос ещё раз. Это демонстрация ошибки, сетевой запрос не выполнялся.";save();render();return;}
if(/исключ|cache|кэш/i.test(text)){answer="В демонстрационном примере каталог ./cache исключается через -prune. Затем -print выводит остальные обычные файлы больше выбранного размера. Проверьте путь каталога перед использованием. [1]";code="find . -path './cache' -prune -o -type f -size +100M -print";source=true;}
else if(/файл|100|find|размер/i.test(text)){answer="Для поиска обычных файлов в текущем каталоге и его подкаталогах используйте find. Параметр -type f выбирает обычные файлы, -size +100M — размер больше 100 единиц по 1 МиБ. Проверка размера учитывает округление вверх до целой единицы; это не точное сравнение байтов. Команда только выводит пути. [1]";code="find . -type f -size +100M";source=true;}
else{answer="В демонстрационном наборе нет фрагментов для этого вопроса. Уточните команду или попробуйте предложенный пример про find. В рабочей версии такое состояние определяется поиском по корпусу.";source=false;}
let i=0;timer=setInterval(()=>{i=Math.min(i+18,answer.length);m.text=answer.slice(0,i);if(i===answer.length){clearInterval(timer);timer=null;m.status="completed";m.code=code;m.source=source;save();$("status").textContent="Демонстрационный ответ завершён · Enter — отправить";}render();},35);render();}
function showSource(){const c=active();$("source-title").textContent="[1] GNU find · демонстрационный фрагмент";$("source-meta").textContent="Выбранный target: "+labels[c.distribution]+" "+c.release+". Общая семантика GNU find; наличие пакета для target не проверено.";$("source-text").textContent=`Раздел SIZE: -size nM сравнивает размер с n единицами по 1 МиБ (1 048 576 байт). Размер округляется вверх до полной единицы. Префикс + означает больше n.

Раздел TYPE: -type f соответствует обычным файлам.

Раздел PATH: -prune предотвращает спуск в каталог; -o задаёт альтернативу.

Это сокращённый учебный пересказ для интерфейса, не индексированный документ корпуса.`;$("source-dialog").showModal();}
$("composer").onsubmit=e=>{e.preventDefault();send($("question").value);};$("question").onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();send($("question").value);}};$("stop").onclick=stop;
$("sample").onclick=()=>send("Как найти обычные файлы больше 100 МиБ?");$("unknown").onclick=()=>send("Как приготовить борщ?");$("simulate-error").onclick=()=>send("Проверка недоступности модели",true);
function options(){$("release").replaceChildren(...releases[$("distribution").value].map(r=>{const o=node("option",r);o.value=r;return o;}));}$("distribution").onchange=options;options();
$("new-chat").onclick=()=>{stop();$("new-dialog").showModal();};$("cancel-new").onclick=()=>$("new-dialog").close();$("new-form").onsubmit=e=>{e.preventDefault();create($("distribution").value,$("release").value);$("new-dialog").close();$("question").focus();};$("close-source").onclick=()=>$("source-dialog").close();$("reset").onclick=()=>{stop();chats=[];create();};
for(const c of chats)for(const m of c.messages)if(m.status==="streaming")m.status="cancelled";
if(chats.length){activeId=chats[0].id;render();}else create();
