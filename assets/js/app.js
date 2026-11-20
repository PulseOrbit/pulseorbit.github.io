(() => {
'use strict';
const DATA='/posts/index.json', grid=document.getElementById('storyGrid'), search=document.getElementById('searchInput'), filters=document.getElementById('filters'), empty=document.getElementById('emptyState'), count=document.getElementById('storyCount');
let posts=[], category='All', query='', language='en';
const words={
en:{latest:'Latest stories',search:'Search stories…',all:'All',technology:'Technology',science:'Science',business:'Business',culture:'Culture',about:'Clarity in a noisy world.',purpose:'OUR PURPOSE',explore:'Explore the latest',fresh:'FRESH PERSPECTIVES',empty:'No stories match your search. Try another keyword.',noStories:'No stories yet. Fresh stories will appear here soon.',hero:'Ideas move fast.',hero2:'Stay in the orbit.',intro:'Thoughtful explainers and fresh perspectives on the stories shaping our world.',navLatest:'Latest',navTopics:'Topics',navAbout:'About',contact:'Get in touch',stay:'Stay curious. Stay informed.',read:'Read the stories ↗',footer:'Clear perspectives for a changing world.',updated:'Updated regularly',curious:'Curious minds welcome'},
bn:{latest:'সর্বশেষ লেখা',search:'লেখা খুঁজুন…',all:'সব',technology:'প্রযুক্তি',science:'বিজ্ঞান',business:'ব্যবসা',culture:'সংস্কৃতি',about:'তথ্যের ভিড়ে স্পষ্ট ধারণা।',purpose:'আমাদের উদ্দেশ্য',explore:'সর্বশেষ লেখা দেখুন',fresh:'নতুন দৃষ্টিভঙ্গি',empty:'আপনার অনুসন্ধানের সঙ্গে মেলে এমন লেখা নেই। অন্য শব্দ দিয়ে চেষ্টা করুন।',noStories:'এখনো কোনো লেখা নেই। নতুন লেখা শিগগিরই আসবে।',hero:'ভাবনা বদলায় দ্রুত।',hero2:'থাকুন সময়ের সঙ্গে।',intro:'প্রযুক্তি, বিজ্ঞান, ব্যবসা ও সংস্কৃতির গুরুত্বপূর্ণ বিষয় নিয়ে সহজ ও চিন্তাশীল লেখা।',navLatest:'সর্বশেষ',navTopics:'বিষয়সমূহ',navAbout:'আমাদের সম্পর্কে',contact:'যোগাযোগ',stay:'জানুন, শিখুন, কৌতূহলী থাকুন।',read:'লেখা পড়ুন ↗',footer:'পরিবর্তনশীল বিশ্বের জন্য স্পষ্ট ও সহজ ব্যাখ্যা।',updated:'নিয়মিত আপডেট',curious:'কৌতূহলী পাঠকদের জন্য'}
};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const t=k=>words[language][k]||words.en[k]||k;
const dateText=v=>{const d=new Date(String(v||'')+'T00:00:00');return Number.isNaN(d.getTime())?'':new Intl.DateTimeFormat(language==='bn'?'bn-BD':'en',{day:'numeric',month:'short',year:'numeric'}).format(d)};
function render(){
 if(!grid)return;
 const list=posts.filter(p=>(category==='All'||p.category===category)&&[p.title,p.description,p.category].join(' ').toLowerCase().includes(query));
 if(count)count.textContent=language==='bn'?String(list.length)+'টি লেখা':String(list.length)+' '+(list.length===1?'story':'stories');
 if(empty){empty.hidden=!!list.length;empty.textContent=t('empty');}
 grid.innerHTML=list.map(p=>{
  const href='/posts/'+encodeURIComponent(p.slug)+'/'; const img=p.image||'/assets/images/placeholder.svg';
  return '<article class="story-card"><a class="story-link" href="'+href+'"><img class="story-image" loading="lazy" src="'+esc(img)+'" alt="'+esc(p.image_alt||p.title)+'" onerror="this.onerror=null;this.src=\'/assets/images/placeholder.svg\'"><div class="story-body"><span class="story-category">'+esc(p.category||'Stories')+'</span><h3>'+esc(p.title)+'</h3><p>'+esc(p.description||'Read the latest story from PulseOrbit.')+'</p><div class="story-meta"><span>'+esc(dateText(p.date))+'</span><span>'+esc(p.read_time||'4 min read')+' ↗</span></div></div></a></article>';
 }).join('')||'<div class="loading-card">'+esc(posts.length?t('empty'):t('noStories'))+'</div>';
}
function applyLanguage(){
 document.documentElement.lang=language;
 const set=(sel,val)=>{const el=document.querySelector(sel);if(el)el.textContent=val;};
 const setHTML=(sel,val)=>{const el=document.querySelector(sel);if(el)el.innerHTML=val;};
 set('#langToggle',language==='en'?'বাংলা':'English');
 setHTML('.hero h1',esc(t('hero'))+'<br><span>'+esc(t('hero2'))+'</span>');
 set('.hero-copy > p',t('intro'));
 setHTML('.hero .primary-btn',esc(t('explore'))+' <span>↗</span>');
 setHTML('#latest h2',esc(t('latest'))+'<span class="accent">'+(language==='bn'?'।':'.')+'</span>');
 set('#latest .eyebrow',t('fresh'));
 if(search)search.placeholder=t('search');
 filters?.querySelectorAll('[data-category]').forEach(b=>b.textContent=t(b.dataset.category.toLowerCase()));
 set('#about h2',t('about'));set('#about .eyebrow',t('purpose'));
 set('.newsletter h2',t('stay'));set('.newsletter .outline-btn',t('read'));
 const nav=document.querySelectorAll('#mainNav a');
 [t('navLatest'),t('navTopics'),t('navAbout')].forEach((v,i)=>{if(nav[i])nav[i].textContent=v;});
 set('.footer-main > div:last-child h3',t('contact'));set('.footer-brand p',t('footer'));
 const meta=document.querySelectorAll('.hero-meta span');if(meta[0])meta[0].textContent=t('curious');if(meta[2])meta[2].textContent=t('updated');
 render();
}
async function init(){
 const year=document.getElementById('year');if(year)year.textContent=new Date().getFullYear();
 try{const r=await fetch(DATA,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();if(!d||!Array.isArray(d.posts))throw Error('Invalid posts data');posts=d.posts.filter(p=>p&&typeof p.slug==='string'&&typeof p.title==='string');posts.sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));render();}
 catch(e){if(grid)grid.innerHTML='<div class="loading-card">Stories could not be loaded. Please refresh in a moment.</div>';if(count)count.textContent='Temporarily unavailable';console.error('PulseOrbit content error:',e);}
}
search?.addEventListener('input',e=>{query=e.target.value.trim().toLowerCase();render();});
filters?.addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(!b)return;category=b.dataset.category;filters.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));render();});
const nav=document.getElementById('mainNav'),menu=document.getElementById('menuToggle');
menu?.addEventListener('click',()=>{const open=nav?.classList.toggle('open')||false;menu.setAttribute('aria-expanded',String(open));});
nav?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');menu?.setAttribute('aria-expanded','false');}));
document.getElementById('themeToggle')?.addEventListener('click',()=>{document.body.classList.toggle('light');try{localStorage.setItem('po-theme',document.body.classList.contains('light')?'light':'dark');}catch(_){}});
try{if(localStorage.getItem('po-theme')==='light')document.body.classList.add('light');}catch(_){}
document.getElementById('langToggle')?.addEventListener('click',()=>{language=language==='en'?'bn':'en';applyLanguage();});
init();
})();