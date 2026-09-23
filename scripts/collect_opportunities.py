"""Collect public listing metadata only. No login, applications or full job descriptions."""
import datetime as dt, hashlib, html, json, os, re, time, unicodedata, urllib.parse, urllib.request, urllib.robotparser
from pathlib import Path
import xml.etree.ElementTree as ET
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
NOW=dt.datetime.now(dt.timezone.utc); TODAY=NOW.date().isoformat()
UA='IPPSEF-Opportunities/1.0'
KEYWORDS=r'\b(?:educat\w*|educacion|enseign\w*|pedagog\w*|formations?|training|skills|competenc\w*|curricul\w*|learning|apprenti\w*|emploi|employab\w*|research|recherche|statistics|statistique\w*|sige|planification|docente)'
def plain(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',s))).strip()
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')
def urlsafe(u):
 p=urllib.parse.urlsplit(u)
 if p.scheme!='https' or not p.netloc:raise ValueError('HTTPS required')
 return urllib.parse.urlunsplit((p.scheme,p.netloc.lower(),p.path,p.query,''))
def fetch(u):
 req=urllib.request.Request(urlsafe(u),headers={'User-Agent':UA,'Accept':'*/*'})
 with urllib.request.urlopen(req,timeout=30) as r:
  if urllib.parse.urlsplit(r.url).hostname!=urllib.parse.urlsplit(u).hostname:raise ValueError('Cross-domain redirect requires review')
  b=r.read(3_000_001)
 if len(b)>3_000_000:raise ValueError('Response too large')
 return b.decode('utf-8',errors='replace')
def robots_ok(url,cache):
 origin=urllib.parse.urlsplit(url);root=f'{origin.scheme}://{origin.netloc}/robots.txt'
 if root not in cache:
  rp=urllib.robotparser.RobotFileParser()
  try:rp.parse(fetch(root).splitlines())
  except urllib.error.HTTPError as e:
   if e.code!=404:raise
   rp.parse([])
  cache[root]=rp
 if not cache[root].can_fetch(UA,url):raise ValueError('Automated collection disallowed by robots.txt')
def date_value(s):
 m=re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',s)
 if m:
  d,m,y=map(int,m.groups());return dt.date(y,m,d).isoformat()
 return None

def parse_sap(s,src,seen_at):
 if 'id="searchresults"' not in s:raise ValueError('Listing format changed or unavailable')
 rows=re.findall(r'<tr\b[^>]*class="[^"]*data-row[^"]*"[^>]*>(.*?)</tr>',s,re.S)
 results=[]
 for row in rows:
  a=re.search(r'<a\b[^>]*href="([^"]*/job/[^"]+)"[^>]*>(.*?)</a>',row,re.S)
  if not a:continue
  title=plain(a[2])
  if not re.search(KEYWORDS,norm(title)):continue
  def col(name):
   m=re.search(r'<td\b[^>]*class="[^\"]*col'+name+r'\b[^\"]*"[^>]*>(.*?)</td>',row,re.S)
   return plain(m[1]) if m else ''
  deadline=date_value(col('Shifttype'))
  # Do not infer a deadline from a publication date or publish a stale undated offer.
  if not deadline or deadline<TODAY:continue
  url=urlsafe(urllib.parse.urljoin(src['url'],html.unescape(html.unescape(a[1]))))
  if urllib.parse.urlsplit(url).hostname!=urllib.parse.urlsplit(src['url']).hostname:continue
  location=col('Location') or 'Lieu à vérifier sur la source'
  contract=col('Facility') or 'À préciser sur la source'
  title_n=norm(title+' '+contract)
  category='stage' if re.search(r'\b(?:internship|intern|stage|trainee|young professional|junior professional)\b',title_n) else 'consultance' if re.search('consult|expert',title_n) else 'emploi'
  country=location.split(',',1)[-1].strip() if ',' in location else location
  if country=='Congo, Democratic Republic of the':country='République démocratique du Congo'
  if country=='Multiple':country='Plusieurs pays'
  results.append({'id':hashlib.sha256(url.encode()).hexdigest()[:16],'title':title,'organization':src['organization'],'location':location,'country':country,'contract':contract,'grade':col('Department'),'category':category,'deadline':deadline,'url':url,'source_id':src['id'],'source':src['name'],'checked_at':seen_at,'origin':'listing'})
 return results

def metadata(src,title,url,deadline,stamp,location='Lieu à vérifier sur la source',organization=None):
 if not re.search(KEYWORDS+'|\\b(?:lecturer|professor|academic|student|postdoctoral)',norm(title)):return None
 if not deadline or deadline<TODAY:return None
 url=urlsafe(urllib.parse.urljoin(src['url'],html.unescape(url)))
 if urllib.parse.urlsplit(url).hostname!=urllib.parse.urlsplit(src['url']).hostname:return None
 category='stage' if re.search(r'\b(intern|internship|trainee|stage)\b',norm(title)) else 'consultance' if re.search('consult|expert',norm(title)) else 'emploi'
 return dict(id=hashlib.sha256(url.encode()).hexdigest()[:16],title=title,organization=organization or src['organization'],location=location,country='À vérifier sur la source',contract='À préciser sur la source',grade='',category=category,deadline=deadline,url=url,source_id=src['id'],source=src['name'],checked_at=stamp,origin='listing')

def parse_rss(s,src,stamp):
 root=ET.fromstring(s)
 if root.tag!='rss' or root.find('channel') is None:raise ValueError('RSS format unavailable')
 results=[]
 for row in root.findall('./channel/item'):
  desc=plain(html.unescape(row.findtext('description','')))
  close=row.findtext('dateOffInternet','')
  match=re.search(r'(?:closing date|application deadline|date de cloture)\s*(?:\([^)]*\))?\s*:\s*(\d{1,2}[ /][a-z0-9]+[ /]\d{4})',norm(desc),re.I)
  if not close and match:close=match[1]
  deadline=date_value(close)
  if not deadline and close:
   months={'jan':1,'fev':2,'feb':2,'mar':3,'avr':4,'apr':4,'mai':5,'may':5,'jun':6,'jui':6,'jul':7,'aou':8,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
   try:
    day,month,year=close.split();number=7 if month.startswith('juillet') else months[norm(month)[:3]]
    deadline=dt.date(int(year),number,int(day)).isoformat()
   except (ValueError,KeyError):continue
  item=metadata(src,plain(row.findtext('title','')),row.findtext('link',''),deadline,stamp)
  if item:results.append(item)
 return results

def parse_unicef(s,src,stamp):
 if 'list-view--item' not in s:raise ValueError('UNICEF listing format unavailable')
 results=[]
 for row in s.split('class="list-view--item"')[1:]:
  a=re.search(r'<a[^>]*class="job-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',row,re.S)
  if not a:a=re.search(r'<a[^>]*href="([^"]+)"[^>]*class="job-link"[^>]*>(.*?)</a>',row,re.S)
  d=re.search(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})',row)
  loc=re.search(r'<span class="location">(.*?)</span>',row,re.S)
  if a and d:
   item=metadata(src,plain(a[2]),a[1],d[1],stamp,plain(loc[1]) if loc else 'Lieu à vérifier sur la source')
   if item:results.append(item)
 return results

def parse_euraxess(s,src,stamp):
 if 'id="job-teaser-content"' not in s:raise ValueError('EURAXESS listing format unavailable')
 results=[]
 for row in s.split('id="job-teaser-content"')[1:]:
  a=re.search(r'<h3[^>]*>\s*<a[^>]*href="(/jobs/\d+)"[^>]*>(.*?)</a>',row,re.S)
  d=re.search(r'id-Application-Deadline.*?<time[^>]*datetime="(\d{4}-\d{2}-\d{2})',row,re.S)
  org=re.search(r'<a[^>]*href="/partnering/organisations/profile/[^"]*"[^>]*>(.*?)</a>',row,re.S)
  if a and d:
   item=metadata(src,plain(a[2]),a[1],d[1],stamp,organization=plain(org[1]) if org else None)
   if item:results.append(item)
 return results

def identity(j):
 m=re.search(r'/job/[^/]+/(\d+)/?$',urllib.parse.urlsplit(j['url']).path)
 key=urllib.parse.urlsplit(j['url']).hostname+':'+m[1] if m else j['url']
 aliases=json.loads((ROOT/'data/opportunity_sources.json').read_text()).get('duplicate_job_ids',{})
 return aliases.get(key,key)

def merge(previous,fresh,statuses,today):
 # Replace successful sources in full. On failure keep only recent, non-expired previous items.
 succeeded={s['id'] for s in statuses if s['ok']};out={}
 for j in previous:
  if j['source_id'] in succeeded:continue
  age=(dt.date.fromisoformat(today)-dt.date.fromisoformat(j['checked_at'][:10])).days
  if j.get('deadline','')>=today and age<=7:out[identity(j)]=j
 for j in fresh:
  if j['deadline']>=today:out[identity(j)]=j
 return sorted(out.values(),key=lambda j:(j['deadline'],j['title']))

def main():
 cfg=json.loads((ROOT/'data/opportunity_sources.json').read_text());path=ROOT/'data/opportunities.json'
 old=json.loads(path.read_text()) if path.exists() else {'items':[],'last_success':None}
 stamp=NOW.isoformat();statuses=[];fresh=[];cache={}
 for src in cfg['collectors']:
  if not src.get('enabled'):continue
  try:
   robots_ok(src['url'],cache);items=[]
   for n in range(src.get('pages',1)):
    u=src['url']+('&' if '?' in src['url'] else '?')+'startrow='+str(n*25) if src['adapter']=='sap' else src['url']
    robots_ok(u,cache);s=fetch(u);part={'sap':parse_sap,'rss':parse_rss,'unicef':parse_unicef,'euraxess':parse_euraxess}[src['adapter']](s,src,stamp);items.extend(part)
    rows=len(re.findall(r'<tr\b[^>]*class="[^\"]*data-row',s))
    if rows<25:break
    time.sleep(1)
   fresh.extend(items);statuses.append({'id':src['id'],'name':src['name'],'ok':True,'count':len(items),'checked_at':stamp})
  except Exception as e:statuses.append({'id':src['id'],'name':src['name'],'ok':False,'error':str(e),'checked_at':stamp})
  time.sleep(1)
 successful=any(s['ok'] for s in statuses)
 result={'generated_at':stamp,'last_success':stamp if successful else old.get('last_success'),'collection_state':'complete' if statuses and all(s['ok'] for s in statuses) else 'partial' if successful else 'failed','automation_active':os.environ.get('IPPSEF_AUTOMATION_ACTIVE')=='true','sources':statuses,'items':merge(old['items'],fresh,statuses,TODAY)}
 # automation_active is rendered from the build environment, not falsely claimed by a local run.
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2));os.replace(temp,path)
 print(json.dumps({'offers':len(result['items']),'sources':statuses},ensure_ascii=False))
 if not successful:raise SystemExit(1)
if __name__=='__main__':main()
